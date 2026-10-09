import os
import sys
import glob
import argparse
import asyncio
from typing import Dict, Any, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    except Exception:
        pass

from playwright.async_api import async_playwright
from flow_studio.config import load_config, get_default_config
from flow_studio.browser import FlowBrowserManager
from flow_studio.canvas import FlowCanvasController
from flow_studio.downloader import FlowImageDownloader, sanitize_filename
from flow_studio.prompts import PromptTemplateEngine
from flow_studio.ledger import JobLedger

async def execute_batch_flow(config: Dict[str, Any], retry_failed: bool = False) -> None:
    """Executes the batch automation according to loaded configuration."""
    mode = config.get("mode", "dual_image")
    browser_cfg = config.get("browser", {})
    inputs_cfg = config.get("inputs", {})
    prompt_cfg = config.get("prompt", {})
    output_cfg = config.get("output", {})

    output_dir = output_cfg.get("directory", "outputs/flow_results")
    wait_time = browser_cfg.get("timeout_seconds", 55)
    ledger_path = config.get("ledger_path", os.path.join(output_dir, "jobs_ledger.json"))

    ledger = JobLedger(ledger_path)
    prompt_engine = PromptTemplateEngine(
        prompt_cfg.get("template", ""),
        prompt_cfg.get("variables", {})
    )

    print("=" * 70, flush=True)
    print("🚀 KALEIDOSCOPE FLOW STUDIO - UNIVERSAL BATCH ENGINE", flush=True)
    print(f"• Mode           : {mode.upper()}", flush=True)
    print(f"• Output Dir     : {output_dir}", flush=True)
    print(f"• Inference Wait : {wait_time}s", flush=True)
    print(f"• Ledger State   : {ledger_path}", flush=True)
    print("=" * 70, flush=True)

    # 1. Discover Input Tasks
    tasks = []
    if mode == "dual_image":
        template_img = inputs_cfg.get("template_image")
        subjects_dir = inputs_cfg.get("subjects_dir", "inputs/subjects")
        exts = inputs_cfg.get("file_extensions", [".jpg", ".jpeg", ".png", ".webp"])

        if not template_img or not os.path.exists(template_img):
            print(f"❌ Error: Base template image not found: {template_img}", flush=True)
            return

        subject_files = []
        if os.path.exists(subjects_dir):
            for f in sorted(os.listdir(subjects_dir)):
                if os.path.splitext(f.lower())[1] in exts:
                    subject_files.append(os.path.join(subjects_dir, f))

        print(f"📁 Found {len(subject_files)} subject image(s) in {subjects_dir}", flush=True)
        for idx, sub_path in enumerate(subject_files):
            item_id = os.path.splitext(os.path.basename(sub_path))[0]
            out_name = f"{output_cfg.get('prefix', 'res_')}{item_id}.png"
            check_out = os.path.join(output_dir, out_name)

            meta = {
                "template": template_img,
                "subject": sub_path,
                "dest_name": out_name,
                "index": idx + 1
            }
            ledger.register_item(item_id, meta, output_check_path=check_out)
            tasks.append((item_id, meta))

    elif mode == "single_image":
        inputs_dir = inputs_cfg.get("inputs_dir", "inputs")
        exts = inputs_cfg.get("file_extensions", [".jpg", ".jpeg", ".png", ".webp"])
        input_files = []
        if os.path.exists(inputs_dir):
            for f in sorted(os.listdir(inputs_dir)):
                if os.path.splitext(f.lower())[1] in exts:
                    input_files.append(os.path.join(inputs_dir, f))

        print(f"📁 Found {len(input_files)} input image(s) in {inputs_dir}", flush=True)
        for idx, in_path in enumerate(input_files):
            item_id = os.path.splitext(os.path.basename(in_path))[0]
            out_name = f"{output_cfg.get('prefix', 'restyle_')}{item_id}.png"
            check_out = os.path.join(output_dir, out_name)

            meta = {
                "input_image": in_path,
                "dest_name": out_name,
                "index": idx + 1
            }
            ledger.register_item(item_id, meta, output_check_path=check_out)
            tasks.append((item_id, meta))

    elif mode == "text_only":
        prompt_list = prompt_cfg.get("prompt_list", [])
        if not prompt_list and "matrix" in prompt_cfg:
            prompt_list = PromptTemplateEngine.generate_matrix(
                prompt_cfg.get("template", ""),
                prompt_cfg.get("matrix", {})
            )

        print(f"📝 Found {len(prompt_list)} prompt task(s)", flush=True)
        for idx, p_entry in enumerate(prompt_list):
            item_id = f"prompt_{idx+1:04d}"
            p_text = p_entry.get("prompt") if isinstance(p_entry, dict) else str(p_entry)
            p_vars = p_entry.get("variables", {}) if isinstance(p_entry, dict) else {}
            out_name = f"{output_cfg.get('prefix', 'gen_')}{item_id}.png"
            check_out = os.path.join(output_dir, out_name)

            meta = {
                "custom_prompt": p_text,
                "variables": p_vars,
                "dest_name": out_name,
                "index": idx + 1
            }
            ledger.register_item(item_id, meta, output_check_path=check_out)
            tasks.append((item_id, meta))

    summary = ledger.get_summary()
    pending_items = ledger.get_pending(retry_failed=retry_failed)
    print(f"📊 Total Tasks: {summary['total']} | Already Done: {summary['COMPLETED']} | Queue: {len(pending_items)}\n", flush=True)

    if not pending_items:
        print("🏆 All tasks are already completed! Nothing to run.", flush=True)
        return

    # 2. Connect Browser
    browser_mgr = FlowBrowserManager(
        cdp_port=browser_cfg.get("cdp_port", 9222),
        target_url=browser_cfg.get("target_url", "https://flow.google.com"),
        user_data_dir=browser_cfg.get("user_data_dir", "flow_browser_profile"),
        headless=browser_cfg.get("headless", False)
    )

    async with async_playwright() as pw:
        browser, context, flow_page, is_cdp = await browser_mgr.connect_or_launch(pw)
        canvas_ctrl = FlowCanvasController(flow_page)
        downloader = FlowImageDownloader(flow_page, output_dir=output_dir)

        is_mounted = await canvas_ctrl.wait_for_canvas(timeout_sec=45)
        if not is_mounted:
            print("❌ Cannot proceed without mounted Google Flow editor canvas.", flush=True)
            return

        # 3. Process Execution Queue
        for task_idx, item in enumerate(pending_items):
            item_id = item["id"]
            meta = item["meta"]
            print(f"\n[{task_idx+1}/{len(pending_items)}] 🎨 Processing Task: {item_id}", flush=True)

            try:
                # Reset Prompt Box
                await canvas_ctrl.reset_prompt_box()

                # Paste images according to mode
                if mode == "dual_image":
                    t_img = meta.get("template")
                    s_img = meta.get("subject")
                    print(f"📎 Pasting Image 1 (Template): {os.path.basename(t_img)}...", flush=True)
                    await canvas_ctrl.paste_image_from_file(t_img)
                    await asyncio.sleep(0.8)

                    print(f"📎 Pasting Image 2 (Subject): {os.path.basename(s_img)}...", flush=True)
                    await canvas_ctrl.paste_image_from_file(s_img)
                    await asyncio.sleep(0.8)

                elif mode == "single_image":
                    in_img = meta.get("input_image")
                    print(f"📎 Pasting Image: {os.path.basename(in_img)}...", flush=True)
                    await canvas_ctrl.paste_image_from_file(in_img)
                    await asyncio.sleep(0.8)

                # Format & Inject Prompt
                if meta.get("custom_prompt"):
                    final_prompt = meta["custom_prompt"]
                else:
                    final_prompt = prompt_engine.render(meta)

                print(f"✍️ Injecting Prompt: \"{final_prompt[:85]}...\"", flush=True)
                await canvas_ctrl.inject_prompt(final_prompt)
                await asyncio.sleep(0.6)

                # Click Generate
                print("⚡ Submitting generation...", flush=True)
                triggered = await canvas_ctrl.trigger_generate()
                if not triggered:
                    print("⚠️ Note: Generate button trigger returned false, pressing Enter as fallback...", flush=True)

                # Wait for Generation
                await downloader.wait_for_generation(wait_seconds=wait_time)

                # Extract and Save
                saved_path = await downloader.extract_and_save_latest_result(meta["dest_name"])
                if saved_path:
                    ledger.mark_completed(item_id, saved_path)
                else:
                    ledger.mark_failed(item_id, "Output image could not be extracted from canvas")

            except Exception as task_err:
                print(f"❌ Error processing task {item_id}: {task_err}", flush=True)
                ledger.mark_failed(item_id, str(task_err))

            await asyncio.sleep(2.0)

    print("\n" + "=" * 70, flush=True)
    print("🏁 BATCH EXECUTION CYCLE FINISHED", flush=True)
    final_summary = ledger.get_summary()
    print(f"• Completed : {final_summary['COMPLETED']} / {final_summary['total']}", flush=True)
    print(f"• Failed    : {final_summary['FAILED']}", flush=True)
    print(f"• Ledger    : {ledger_path}", flush=True)
    print("=" * 70, flush=True)

def main():
    parser = argparse.ArgumentParser(
        description="Kaleidoscope Flow Studio - Universal Generative Batch Automation"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available commands")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run batch generation task")
    run_parser.add_argument("--config", "-c", type=str, default=None, help="Path to YAML or JSON configuration file")
    run_parser.add_argument("--mode", "-m", choices=["dual_image", "single_image", "text_only"], default=None, help="Operational mode")
    run_parser.add_argument("--template", "-t", type=str, default=None, help="Base template image for dual_image mode")
    run_parser.add_argument("--inputs-dir", "-i", type=str, default=None, help="Directory containing input images")
    run_parser.add_argument("--output-dir", "-o", type=str, default=None, help="Directory to save generated outputs")
    run_parser.add_argument("--prompt", "-p", type=str, default=None, help="Custom prompt text or template")
    run_parser.add_argument("--wait", "-w", type=int, default=None, help="Seconds to wait per generation")
    run_parser.add_argument("--port", type=int, default=None, help="CDP Remote Debugging Port (default 9222)")
    run_parser.add_argument("--retry-failed", action="store_true", help="Retry failed tasks in ledger")

    # Command: list-presets
    subparsers.add_parser("list-presets", help="List available configuration presets")

    # Command: status
    status_parser = subparsers.add_parser("status", help="Check ledger status of a job")
    status_parser.add_argument("--ledger", "-l", type=str, default="outputs/flow_results/jobs_ledger.json", help="Path to jobs_ledger.json")

    args = parser.parse_args()

    if args.subcommand == "list-presets":
        preset_dir = os.path.join(os.path.dirname(__file__), "..", "configs", "presets")
        print("\n📦 AVAILABLE CONFIGURATION PRESETS:")
        print("=" * 60)
        if os.path.exists(preset_dir):
            for fn in sorted(os.listdir(preset_dir)):
                if fn.endswith(('.yaml', '.yml', '.json')):
                    print(f"• {fn:<30} -> configs/presets/{fn}")
        else:
            print("No presets found in configs/presets/.")
        print("=" * 60)
        return

    elif args.subcommand == "status":
        if os.path.exists(args.ledger):
            led = JobLedger(args.ledger)
            sum_data = led.get_summary()
            print("\n📊 JOB LEDGER STATUS:")
            print(f"• Path      : {args.ledger}")
            print(f"• Total     : {sum_data['total']}")
            print(f"• Completed : {sum_data['COMPLETED']}")
            print(f"• Pending   : {sum_data['PENDING']}")
            print(f"• Failed    : {sum_data['FAILED']}")
        else:
            print(f"Ledger file not found at: {args.ledger}")
        return

    # Default to run
    config = get_default_config()
    if args.config:
        config = load_config(args.config)

    # CLI Overrides
    if args.mode:
        config["mode"] = args.mode
    if args.template:
        config.setdefault("inputs", {})["template_image"] = args.template
    if args.inputs_dir:
        config.setdefault("inputs", {})["subjects_dir"] = args.inputs_dir
        config.setdefault("inputs", {})["inputs_dir"] = args.inputs_dir
    if args.output_dir:
        config.setdefault("output", {})["directory"] = args.output_dir
    if args.prompt:
        config.setdefault("prompt", {})["template"] = args.prompt
    if args.wait:
        config.setdefault("browser", {})["timeout_seconds"] = args.wait
    if args.port:
        config.setdefault("browser", {})["cdp_port"] = args.port

    asyncio.run(execute_batch_flow(config, retry_failed=getattr(args, 'retry_failed', False)))

if __name__ == "__main__":
    main()
