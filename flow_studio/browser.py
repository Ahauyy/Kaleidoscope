import os
import sys
import asyncio
from typing import Tuple, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

class FlowBrowserManager:
    """
    Manages Playwright browser lifecycle, Chrome DevTools Protocol (CDP)
    connection, and persistent sessions for Google Flow automation.
    """

    def __init__(
        self,
        cdp_port: int = 9222,
        target_url: str = "https://flow.google.com",
        user_data_dir: str = "flow_browser_profile",
        headless: bool = False
    ):
        self.cdp_port = cdp_port
        self.target_url = target_url
        self.user_data_dir = os.path.abspath(user_data_dir)
        self.headless = headless

    async def connect_or_launch(self, playwright_instance) -> Tuple[Optional[Browser], BrowserContext, Page, bool]:
        """
        Attempts to attach to an existing Chrome/Edge instance via CDP (port 9222).
        If unavailable, launches a persistent browser context.
        Returns: (browser, context, flow_page, is_cdp)
        """
        cdp_endpoint = f"http://localhost:{self.cdp_port}"

        # 1. Try CDP port
        try:
            print(f"🔍 Checking connection to existing browser at CDP {cdp_endpoint}...", flush=True)
            browser = await playwright_instance.chromium.connect_over_cdp(cdp_endpoint, timeout=1800)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()

            flow_page = None
            for page in context.pages:
                if "flow.google.com" in page.url.lower():
                    flow_page = page
                    break

            if not flow_page:
                flow_page = context.pages[0] if context.pages else await context.new_page()
                if "flow.google.com" not in flow_page.url.lower():
                    print(f"🌐 Navigating to {self.target_url}...", flush=True)
                    await flow_page.goto(self.target_url)

            print(f"✅ Successfully attached to browser session via CDP ({cdp_endpoint})!", flush=True)
            return browser, context, flow_page, True

        except Exception as cdp_err:
            print(f"ℹ️ CDP port {self.cdp_port} inactive ({cdp_err}).", flush=True)
            print("🚀 Launching standalone browser with persistent profile...", flush=True)

        # 2. Launch persistent context fallback
        os.makedirs(self.user_data_dir, exist_ok=True)
        launch_args = [
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check"
        ]

        # Use Microsoft Edge if available on Windows, else Chromium
        channel = "msedge" if sys.platform == "win32" else None

        context = await playwright_instance.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            channel=channel,
            headless=self.headless,
            args=launch_args,
            no_viewport=True,
            timeout=30000
        )

        flow_page = context.pages[0] if context.pages else await context.new_page()
        if "flow.google.com" not in flow_page.url.lower():
            print(f"🌐 Navigating to {self.target_url}...", flush=True)
            await flow_page.goto(self.target_url)

        print("✅ Standalone browser window successfully initialized.", flush=True)
        return None, context, flow_page, False
