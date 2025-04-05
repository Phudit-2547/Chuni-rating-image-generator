import asyncio
import base64
import requests
from envparse import env
from playwright.async_api import async_playwright

env.read_envfile()

UPLOAD_PAGE_URL = "https://reiwa.f5.si/newbestimg/chunithm_int/"
DISCORD_WEBHOOK = env("DISCORD_WEBHOOK")
USERNAME = env("USERNAME")
PASSWORD = env("PASSWORD")


UPLOAD_PAGE_URL = "https://reiwa.f5.si/newbestimg/chunithm_int/"

INJECT_SCRIPT = """
javascript:(function(){var e=document.createElement("script");e.src="https://reiwa.f5.si/chuni_scoredata/main.js?"+String(Math.floor((new Date).getTime()/1e3)),document.body.appendChild(e)})();
"""

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        upload_page = await context.new_page()

        # --- Step 1: Login and Download ---
        page = await context.new_page()
        await page.goto("https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=chuniex"
                      "&redirect_url=https://chunithm-net-eng.com/mobile/&back_url=https://chunithm.sega.com/", wait_until="domcontentloaded")
        await page.locator("span.c-button--openid--segaId").click()
        await page.locator("#sid").fill(USERNAME)
        await page.locator("#password").fill(PASSWORD)
        await page.locator("input#btnSubmit.c-button--login").click()
        await page.wait_for_url("https://chunithm-net-eng.com/mobile/home/", wait_until="domcontentloaded")

        print("✅ Login successful, injecting script...")
        await page.evaluate(INJECT_SCRIPT)

        try:
            download = await page.wait_for_event("download", timeout=30000)
        except Exception as e:
            await browser.close()
            raise ValueError(f"❌ Download did not start: {e}")

        json_filename = download.suggested_filename
        print(f"📂 Download triggered. Suggested filename: {json_filename}")
        await download.save_as(json_filename)
        print(f"📂 JSON data saved as {json_filename}")

        print("📤 Uploading JSON file...")
        await upload_page.goto(UPLOAD_PAGE_URL, wait_until="domcontentloaded")

        await asyncio.sleep(
            5
        )  # Wait for the page to load for 5 seconds(must be at least 5 seconds)
        await upload_page.locator("#player_data_file").set_input_files(json_filename)

        # Click "Generate"
        await upload_page.locator("#generate").click()
        print("✅ Generate button clicked!")

        # Get Image
        img_src = await upload_page.locator("#result-img").get_attribute("src")

        # Send to Discord
        if img_src:
            if img_src.startswith("data:"):
                header, b64data = img_src.split(",", 1)
                mime = header.split(";")[0].split(":")[1]
                ext = mime.split("/")[-1]

                image_bytes = base64.b64decode(b64data)

                files = {"file": (f"result_image.{ext}", image_bytes, mime)}
                data = {"content": "Here is the generated image:"}
                response = requests.post(DISCORD_WEBHOOK, data=data, files=files)
                print(f"Discord response: {response.status_code}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
