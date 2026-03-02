import os
import re
import time as t
from bot import Artikel_SC
from playwright.sync_api import sync_playwright


def _raise_if_cancelled(should_cancel):
    if should_cancel and should_cancel():
        raise InterruptedError("Task dibatalkan oleh user.")


def _wait_stable_artikel_text(page, timeout_sec=300, stable_sec=2.0, should_cancel=None):
    start = t.time()
    last_text = ""
    last_change = start

    while t.time() - start < timeout_sec:
        _raise_if_cancelled(should_cancel)
        code_blocks = page.locator("code-block")
        if code_blocks.count() > 0:
            current_text = code_blocks.nth(0).inner_text().strip()
            if current_text != last_text:
                last_text = current_text
                last_change = t.time()
            elif current_text and (t.time() - last_change) >= stable_sec:
                return current_text, code_blocks
        t.sleep(0.4)

    raise TimeoutError("Timeout: code block artikel tidak stabil/selesai.")


def _validate_artikel_text(artikel_text):
    text = artikel_text.strip()
    if len(text) < 1500:
        return False, f"Output artikel terlalu pendek ({len(text)} chars)."

    lowered = text.lower()
    if "kesimpulan" not in lowered:
        return False, "Bagian KESIMPULAN tidak ditemukan."

    if not any(tag in lowered for tag in ("</p>", "</ol>", "</li>")):
        return False, "Struktur HTML terlihat belum lengkap."

    return True, ""


def _wait_send_finished(page, timeout_sec=300, should_cancel=None):
    start = t.time()
    stop_button = page.get_by_role("button", name=re.compile("Stop"))
    while t.time() - start < timeout_sec:
        _raise_if_cancelled(should_cancel)
        if stop_button.count() == 0:
            return
        if not stop_button.is_visible():
            return
        t.sleep(0.4)
    raise TimeoutError("Timeout: tombol Stop tidak hilang.")


def run_bot(prompt, judul, idx, should_cancel=None, on_gemini_done=None, on_post_done=None):
    max_attempts = 2

    for attempt in range(1, max_attempts + 1):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False)
            
            context = browser.new_context()
            page = context.new_page()

            try:
                _raise_if_cancelled(should_cancel)
                page.goto("https://gemini.google.com/app", wait_until="domcontentloaded")

                editor = page.locator(".ql-editor")
                editor.wait_for(state="visible", timeout=60000)
                _raise_if_cancelled(should_cancel)

                editor.click()
                editor.press("Control+A")
                editor.press("Backspace")
                editor.fill(prompt)
                t.sleep(1)
                _raise_if_cancelled(should_cancel)

                page.get_by_role("button", name="Send message").click()
                _wait_send_finished(page, should_cancel=should_cancel)

                artikel, code_blocks = _wait_stable_artikel_text(
                    page,
                    should_cancel=should_cancel
                )
                is_valid, reason = _validate_artikel_text(artikel)

                if not is_valid:
                    if attempt < max_attempts:
                        print(f"[WARN idx={idx}] attempt {attempt} invalid: {reason}. Retry...")
                        t.sleep(2)
                        continue
                    raise Exception(f"Output Gemini invalid untuk idx={idx}: {reason}")

                _raise_if_cancelled(should_cancel)
                os.makedirs("data/result/artikel", exist_ok=True)
                with open(f"data/result/artikel/artikel-{idx}.txt", "w", encoding="utf-8") as f:
                    f.write(artikel)
                print("Berhasil save output artikel")

                if code_blocks.count() > 1:
                    hastag = code_blocks.nth(1).inner_text()
                    os.makedirs("data/result/hastag", exist_ok=True)
                    with open(f"data/result/hastag/hastag-{idx}.txt", "w", encoding="utf-8") as f:
                        f.write(hastag)
                    print("Berhasil save output hastag")

                if on_gemini_done:
                    on_gemini_done()

                break
            finally:
                context.close()
                browser.close()

    # Setelah gemini selesai -> jalankan posting
    _raise_if_cancelled(should_cancel)
    Artikel_SC(judul, idx, should_cancel=should_cancel)
    if on_post_done:
        on_post_done()
