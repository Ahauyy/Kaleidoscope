import os
import re
import base64
import asyncio
from typing import Optional
from playwright.async_api import Page

def sanitize_filename(name: str) -> str:
    """Sanitizes filename against Windows and Unix illegal characters."""
    clean = re.sub(r'[<>:"/\\|?*]', '_', str(name))
    clean = re.sub(r'\s+', ' ', clean).strip(' ._')
    return clean if clean else "output_result"

class FlowImageDownloader:
    """
    Detects generated image cards on the canvas, extracts full-resolution blobs,
    and saves them safely to the destination directory.
    """

    def __init__(self, page: Page, output_dir: str = "outputs/flow_results"):
        self.page = page
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    async def wait_for_generation(self, wait_seconds: int = 55) -> None:
        """
        Pauses for the generative diffusion inference duration with status logging.
        """
        print(f"⏳ Generating image (waiting {wait_seconds}s for high-fidelity diffusion)...", flush=True)
        step = 5
        remaining = wait_seconds
        while remaining > 0:
            await asyncio.sleep(min(step, remaining))
            remaining -= step
            if remaining > 0 and remaining % 15 == 0:
                print(f"   ... {remaining}s remaining", flush=True)

    async def extract_and_save_latest_result(self, dest_filename: str) -> Optional[str]:
        """
        Locates the latest generated output card, extracts image bytes,
        and saves to disk.
        """
        sanitized_name = sanitize_filename(dest_filename)
        if not (sanitized_name.endswith('.png') or sanitized_name.endswith('.jpg')):
            sanitized_name += '.png'

        dest_path = os.path.join(self.output_dir, sanitized_name)

        # JavaScript to find the latest generated image blob
        js_extract = """async () => {
            // Find all image elements on canvas cards
            const imgEls = Array.from(document.querySelectorAll('img')).filter(el => {
                const src = el.src || '';
                // Must be a valid content image (not avatar/icon)
                return (src.startsWith('blob:') || src.startsWith('http') || src.startsWith('data:')) &&
                       el.naturalWidth > 200 && el.naturalHeight > 200;
            });

            if (imgEls.length === 0) return null;

            // Pick the latest image (last element in DOM or highest card)
            const latestImg = imgEls[imgEls.length - 1];

            try {
                // If blob: or http, fetch and convert to base64
                const res = await fetch(latestImg.src);
                const blob = await res.blob();
                return await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.readAsDataURL(blob);
                });
            } catch(e) {
                // Fallback to canvas render
                try {
                    const canvas = document.createElement('canvas');
                    canvas.width = latestImg.naturalWidth;
                    canvas.height = latestImg.naturalHeight;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(latestImg, 0, 0);
                    return canvas.toDataURL('image/png');
                } catch(canvasErr) {
                    return null;
                }
            }
        }"""

        try:
            data_url = await self.page.evaluate(js_extract)
            if not data_url or not isinstance(data_url, str):
                print("⚠️ No valid output image detected on canvas cards.", flush=True)
                return None

            # Split base64 header
            if "," in data_url:
                header, encoded = data_url.split(",", 1)
            else:
                encoded = data_url

            img_bytes = base64.b64decode(encoded)

            if len(img_bytes) < 1024:
                print(f"⚠️ Image data too small ({len(img_bytes)} bytes), possible thumbnail.", flush=True)
                return None

            with open(dest_path, "wb") as f:
                f.write(img_bytes)

            file_size_kb = len(img_bytes) / 1024
            print(f"💾 Successfully saved output ({file_size_kb:.1f} KB): {dest_path}", flush=True)
            return dest_path

        except Exception as ex:
            print(f"⚠️ Failed extracting output image: {ex}", flush=True)
            return None
