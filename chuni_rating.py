import asyncio
import base64
import requests
from envparse import env
from playwright.async_api import async_playwright
import json

env.read_envfile()

UPLOAD_PAGE_URL = "https://reiwa.f5.si/newbestimg/chunithm_int/"
DISCORD_WEBHOOK = env("DISCORD_WEBHOOK")
USERNAME = env("USERNAME")
PASSWORD = env("PASSWORD")

INJECT_SCRIPT = """
javascript:(function(){var e=document.createElement("script");e.src="https://reiwa.f5.si/chuni_scoredata/main.js?"+String(Math.floor((new Date).getTime()/1e3)),document.body.appendChild(e)})();
"""

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.tracing.start(
            title="chuni_trace", screenshots=True, snapshots=True, sources=True
        )

        # --- Step 1: Login and Download ---
        page = await context.new_page()
        await page.goto("https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=chuniex"
                      "&redirect_url=https://chunithm-net-eng.com/mobile/&back_url=https://chunithm.sega.com/", wait_until="domcontentloaded")
        await page.locator("span.c-button--openid--segaId").click()
        await page.locator("#sid").fill(USERNAME)
        await page.locator("#password").fill(PASSWORD)
        await page.locator("input#btnSubmit.c-button--login").click()
        await page.wait_for_url("https://chunithm-net-eng.com/mobile/home/", wait_until="domcontentloaded")

        print("✅ Login successful, injecting script…")
        await page.evaluate(INJECT_SCRIPT)

        # 1️⃣ Wait for the “Completed!” popup to appear
        await page.wait_for_selector("text=Completed!", timeout=60000)

        # 2️⃣ Click the “CHUNITHM Best Songs Image Generator NEW” link
        #    but *catch the popup* it opens:
        async with page.expect_popup() as popup_info:
            await page.click("text=CHUNITHM Best Songs Image Generator NEW")
        generator_page = await popup_info.value

        # 3️⃣ Wait for the generator page to load fully must be at least 5 seconds
        await asyncio.sleep(5)

        # 4️⃣ Click the generate button in that page
        await generator_page.click("#generate")
        print("✅ Generate button clicked in generator page!")

        # 5️⃣ Now extract the result image from that page
        img_src = await generator_page.locator("#result-img").get_attribute("src")

        # Send to Discord
        if img_src:
            if img_src.startswith("data:"):
                header, b64data = img_src.split(",", 1)
                mime = header.split(";")[0].split(":")[1]
                ext = mime.split("/")[-1]

                image_bytes = base64.b64decode(b64data)

                files = {"file": (f"result_image.{ext}", image_bytes, mime)}
                payload = {
                    "username": "みのりん",
                    "avatar_url": "https://pbs.twimg.com/media/FiyzOadaAAAX-yG?format=jpg&name=large",
                }
                data = {"payload_json": json.dumps(payload)}
                response = requests.post(DISCORD_WEBHOOK, data=data, files=files)
                print(f"Discord response: {response.status_code}")

        await context.tracing.stop(path="trace.zip")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
