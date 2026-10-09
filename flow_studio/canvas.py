import os
import base64
import asyncio
from typing import List, Optional
from playwright.async_api import Page

class FlowCanvasController:
    """
    Controls and interacts with Google Flow web canvas interface:
    - ProseMirror input & typing engine
    - Native clipboard image pasting (anti-drag-drop duplicate)
    - Dismissing popups/toasts
    - Submitting prompt execution
    """

    def __init__(self, page: Page):
        self.page = page

    async def wait_for_canvas(self, timeout_sec: int = 45) -> bool:
        """Waits until Google Flow canvas and prompt editor are mounted."""
        print("⏳ Waiting for Google Flow editor interface...", flush=True)
        try:
            await self.page.wait_for_selector(".ProseMirror, textarea, [contenteditable='true']", timeout=timeout_sec * 1000)
            print("✅ Google Flow editor is ready and mounted.", flush=True)
            return True
        except Exception as e:
            print(f"⚠️ Timed out waiting for editor selector: {e}", flush=True)
            return False

    async def dismiss_toasts(self) -> None:
        """Dismisses any transient popups or toast notifications that obstruct UI clicks."""
        try:
            await self.page.evaluate("""() => {
                const buttons = Array.from(document.querySelectorAll('button')).filter(b => {
                    const txt = (b.innerText || '').trim().toLowerCase();
                    const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                    return txt === 'dismiss' || aria === 'dismiss' || aria === 'close' || txt === 'got it';
                });
                buttons.forEach(btn => { try { btn.click(); } catch(e){} });
            }""")
        except Exception:
            pass

    async def reset_prompt_box(self) -> None:
        """Cleans existing media chips and clears prompt text box."""
        await self.dismiss_toasts()

        # 1. Remove thumbnail chips
        try:
            await self.page.evaluate("""() => {
                const removeBtns = Array.from(document.querySelectorAll(
                    '[aria-label*="Remove"], [aria-label*="remove"], [aria-label*="Delete"], .chip-close, .remove-btn'
                ));
                removeBtns.forEach(btn => { try { btn.click(); } catch(e){} });
            }""")
        except Exception:
            pass

        await asyncio.sleep(0.4)

        # 2. Clear text in ProseMirror editor
        try:
            await self.page.evaluate("""() => {
                const pm = document.querySelector('.ProseMirror, [contenteditable="true"]');
                if (pm) {
                    pm.focus();
                    pm.innerHTML = '<p><br></p>';
                    pm.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true }));
                }
            }""")
        except Exception:
            pass

        await asyncio.sleep(0.3)

    async def paste_image_from_file(self, image_path: str) -> bool:
        """
        Encodes image into base64 and simulates native clipboard paste into ProseMirror.
        Bypasses drag-and-drop quirks and ensures clean attachment.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file to paste does not exist: {image_path}")

        with open(image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")

        ext = os.path.splitext(image_path)[1].lower().replace(".", "")
        mime_type = "image/png" if ext == "png" else "image/jpeg"

        js_script = """async ({ b64, mime }) => {
            const byteCharacters = atob(b64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: mime });
            const file = new File([blob], "input_image." + (mime === 'image/png' ? 'png' : 'jpg'), { type: mime });

            const pm = document.querySelector('.ProseMirror, [contenteditable="true"]') || document.body;
            pm.focus();

            const dt = new DataTransfer();
            dt.items.add(file);

            const pasteEvt = new ClipboardEvent('paste', {
                bubbles: true,
                cancelable: true,
                clipboardData: dt
            });
            pm.dispatchEvent(pasteEvt);
            return true;
        }"""

        try:
            await self.page.evaluate(js_script, {"b64": b64_data, "mime": mime_type})
            await asyncio.sleep(1.0)
            return True
        except Exception as err:
            print(f"⚠️ Error simulating clipboard paste: {err}", flush=True)
            return False

    async def inject_prompt(self, prompt_text: str) -> None:
        """
        Focuses ProseMirror and types prompt text, triggering synthetic
        InputEvent so the Generate button turns active.
        """
        js_inject = """(text) => {
            const pm = document.querySelector('.ProseMirror, [contenteditable="true"]');
            if (!pm) return false;
            pm.focus();
            
            // Set text with standard paragraph wrapper
            pm.innerHTML = `<p>${text.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>`;
            
            // Dispatch input and change events
            pm.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true }));
            pm.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }"""

        await self.page.evaluate(js_inject, prompt_text)
        await asyncio.sleep(0.5)

    async def trigger_generate(self) -> bool:
        """Finds and clicks the active Generate / Submit button."""
        # Check for enter key or submit button
        clicked = False
        try:
            # 1. Search for submit button by selector or aria-label
            btn = await self.page.query_selector(
                'button[aria-label*="Generate"], button[aria-label*="Submit"], button[aria-label*="Send"], '
                'button.send-button, button.generate-button, button:has(svg)'
            )
            if btn:
                is_disabled = await btn.is_disabled()
                if not is_disabled:
                    await btn.click()
                    clicked = True
        except Exception:
            pass

        if not clicked:
            # Fallback to pressing Enter on ProseMirror
            try:
                pm = await self.page.query_selector('.ProseMirror')
                if pm:
                    await pm.press('Enter')
                    clicked = True
            except Exception:
                pass

        return clicked
