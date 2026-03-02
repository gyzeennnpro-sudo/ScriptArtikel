import os
import re
import uuid
import threading
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
# from bot_prompt import run_bot

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

DEV_USER = os.getenv("DEV_USER")
DEV_PASS = os.getenv("DEV_PASS")

# Task progress store
TASKS = {}
TASKS_LOCK = threading.Lock()


def _to_title_case(text):
    if not text:
        return text
    return re.sub(
        r"\b([A-Za-z])([A-Za-z]*)\b",
        lambda m: m.group(1).upper() + m.group(2).lower(),
        text
    )


def _is_task_cancelled(task_id):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        return bool(task and task.get("cancelled"))


def _update_task_item(task_id, item_index, **fields):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task:
            return
        if item_index < 0 or item_index >= len(task["items"]):
            return
        task["items"][item_index].update(fields)


def _run_batch(task_id, judul_list):
    from bot_prompt import run_bot

    for idx, judul in enumerate(judul_list, start=1):
        item_index = idx - 1
        with TASKS_LOCK:
            if TASKS[task_id].get("cancelled"):
                break
            TASKS[task_id]["items"][item_index]["status"] = "running"
            TASKS[task_id]["items"][item_index]["progress"] = 0

        try:
            with open("data/prompt/prompt-art.txt", "r", encoding="utf-8") as f:
                prompt = f.read().replace("MASUKKAN TOPIK DI SINI", judul)

            def on_gemini_done():
                with TASKS_LOCK:
                    task = TASKS.get(task_id)
                    if not task:
                        return
                    item = task["items"][item_index]
                    item["progress"] = max(item.get("progress", 0), 50)
                    if item["status"] == "running":
                        item["status"] = "gemini_done"

            def on_post_done():
                _update_task_item(task_id, item_index, status="success", progress=100)

            run_bot(
                prompt,
                judul,
                idx,
                should_cancel=lambda: _is_task_cancelled(task_id),
                on_gemini_done=on_gemini_done,
                on_post_done=on_post_done
            )

            with TASKS_LOCK:
                if TASKS[task_id].get("cancelled"):
                    break
                TASKS[task_id]["items"][item_index]["status"] = "success"
                TASKS[task_id]["items"][item_index]["progress"] = 100

        except InterruptedError:
            with TASKS_LOCK:
                TASKS[task_id]["items"][item_index]["status"] = "cancelled"
            break
        except Exception as e:
            with TASKS_LOCK:
                TASKS[task_id]["items"][item_index]["status"] = "error"
                TASKS[task_id]["items"][item_index]["error"] = str(e)
                TASKS[task_id]["items"][item_index]["progress"] = 100

    with TASKS_LOCK:
        if TASKS[task_id].get("cancelled"):
            for item in TASKS[task_id]["items"]:
                if item["status"] in ("pending", "running"):
                    item["status"] = "cancelled"
                    item["progress"] = 0
        TASKS[task_id]["done"] = True


# ===================== ROUTES =====================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate")
def generate():
    return render_template("generate.html")


@app.route("/cek")
def cek():
    return render_template("cek.html")


@app.route("/check_login")
def check_login():
    return {"logged_in": bool(session.get("login"))}


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if username == DEV_USER and password == DEV_PASS:
        session["login"] = True
        return jsonify({"status": "success"})

    return jsonify({"status": "fail"})


@app.route("/logout")
def logout():
    session.pop("login", None)
    return jsonify({"status": "logout"})


@app.route("/proses", methods=["POST"])
def proses():
    if not session.get("login"):
        return jsonify({"status": "unauthorized"}), 401

    data = request.get_json()
    raw_judul_list = data.get("judul_list", [])
    judul_list = []

    for judul in raw_judul_list:
        if not isinstance(judul, str):
            continue
        cleaned = re.sub(r"^\s*\d+\.\s*", "", judul).strip()
        cleaned = _to_title_case(cleaned)
        if cleaned:
            judul_list.append(cleaned)

    if not judul_list:
        return jsonify({"status": "empty"}), 400

    task_id = uuid.uuid4().hex

    with TASKS_LOCK:
        TASKS[task_id] = {
            "done": False,
            "cancelled": False,
            "items": [{"judul": j, "status": "pending", "progress": 0, "error": ""} for j in judul_list]
        }

    thread = threading.Thread(target=_run_batch, args=(task_id, judul_list), daemon=True)
    thread.start()
    # thread.join() #biar 1 1 berurutan

    return jsonify({"status": "running", "task_id": task_id})


@app.route("/progress/<task_id>")
def progress(task_id):
    with TASKS_LOCK:
        task = TASKS.get(task_id)

    if not task:
        return jsonify({"status": "not_found"}), 404

    return jsonify(task)


@app.route("/cancel/<task_id>", methods=["POST"])
def cancel_task(task_id):
    with TASKS_LOCK:
        task = TASKS.get(task_id)

        if not task:
            return jsonify({"status": "not_found"}), 404

        if task.get("done"):
            return jsonify({"status": "already_done"})

        task["cancelled"] = True
        for item in task["items"]:
            if item["status"] == "pending":
                item["status"] = "cancelled"
                item["progress"] = 0

    return jsonify({"status": "cancelled"})


# ===================== RUN =====================

if __name__ == "__main__":
    app.run(debug=True)
