import re
import traceback
import time as t
from datetime import datetime
from playwright.sync_api import sync_playwright


usrname = "ayu12345"
passwd = "gektita123"

date = datetime.now().strftime("%Y-%m-%dT%H:%M")


def _raise_if_cancelled(should_cancel):
    if should_cancel and should_cancel():
        raise InterruptedError("Task dibatalkan oleh user.")


def Artikel_SC(judul, idx, should_cancel=None):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        _raise_if_cancelled(should_cancel)
        page.goto("https://portalnews.stekom.ac.id/login")
        t.sleep(1)
        _raise_if_cancelled(should_cancel)

        # Baca artikel (hapus line pertama)
        with open(f"data/result/artikel/artikel-{idx}.txt", "r", encoding="utf-8") as f:
            article_lines = f.read().splitlines()
        isi_artikel = "\n".join(article_lines[1:]) if len(article_lines) > 1 else ""

        # Baca hashtag (hapus line pertama)
        with open(f"data/result/hastag/hastag-{idx}.txt", "r", encoding="utf-8") as f:
            tag_lines = f.read().splitlines()
        tag_text = "\n".join(tag_lines[1:]) if len(tag_lines) > 1 else ""

        if not isi_artikel.strip():
            raise Exception(f"isi_artikel kosong untuk idx={idx}")

        # LOGIN PAGE
        _raise_if_cancelled(should_cancel)
        page.get_by_role("textbox", name="Email or Username").fill(usrname)
        page.get_by_role("textbox", name="Password").fill(passwd)
        page.get_by_role("button", name="Sign in").click()
        t.sleep(2)
        _raise_if_cancelled(should_cancel)

        page.get_by_role("link", name="Add Posts").click()
        t.sleep(2)
        _raise_if_cancelled(should_cancel)

        page.get_by_role("textbox", name="Judul").fill(judul)
        t.sleep(1)
        _raise_if_cancelled(should_cancel)

        show_more_btn = page.get_by_role("button", name="Show more items")
        show_more_btn.wait_for(state="visible", timeout=15000)
        show_more_btn.click()

        page.get_by_role("button", name="Source").click()

        source_box = page.get_by_role("textbox", name="Source code editing area")
        source_box.wait_for(state="visible", timeout=20000)
        source_box.click()
        source_box.press("ControlOrMeta+a")
        source_box.press("Backspace")
        source_box.fill(isi_artikel)
        _raise_if_cancelled(should_cancel)

        page.get_by_text("Selected Indonesia Bahasa").click()
        t.sleep(1.5)
        _raise_if_cancelled(should_cancel)

        page.get_by_role("textbox", name="select").click()
        page.get_by_role("searchbox").nth(1).fill("informasi")
        page.get_by_role("searchbox").nth(1).press("Enter")
        t.sleep(1)
        _raise_if_cancelled(should_cancel)

        page.locator("tags").click()
        page.locator("tags").get_by_role("textbox").fill(tag_text)
        t.sleep(0.5)
        _raise_if_cancelled(should_cancel)

        page.get_by_role("list").filter(has_text=re.compile(r"^$")).click()
        page.get_by_role("option", name="Universitas STEKOM", exact=True).click()
        t.sleep(0.5)
        _raise_if_cancelled(should_cancel)

        page.get_by_role("textbox", name="Tanggal Publish").fill(date)
        t.sleep(0.5)
        _raise_if_cancelled(should_cancel)

        page.get_by_text("Selected Draft Simpan sebagai").click()
        t.sleep(0.5)
        page.get_by_text("Selected Articles Artikel").click()
        t.sleep(0.5)
        _raise_if_cancelled(should_cancel)

        page.locator("#image_media_input").set_input_files("static/images/poster.png")
        t.sleep(0.5)
        _raise_if_cancelled(should_cancel)

        try:
            save_btn = page.get_by_role("button", name=re.compile("Save Data", re.I))
            save_btn.wait_for(state="visible", timeout=15000)
            save_btn.click(no_wait_after=True)
            page.wait_for_timeout(3000)
            print(f"Done idx={idx}", flush=True)
        except Exception as e:
            print(f"[ERROR idx={idx}] {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            raise
        finally:
            context.close()
            browser.close()
