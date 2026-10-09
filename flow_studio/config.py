import os
import json
from typing import Dict, Any

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Loads configuration from a JSON or YAML file.
    Supports native JSON and PyYAML (if installed).
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    ext = os.path.splitext(config_path)[1].lower()

    if ext in [".yaml", ".yml"]:
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            # Fallback simple parser or notify user
            raise ImportError(
                "PyYAML is required for .yaml configs. Run 'pip install pyyaml' or use a .json config file."
            )
    else:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

def save_config(data: Dict[str, Any], config_path: str) -> None:
    """Saves dictionary configuration to disk in JSON or YAML format."""
    os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
    ext = os.path.splitext(config_path)[1].lower()

    if ext in [".yaml", ".yml"]:
        try:
            import yaml
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        except ImportError:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    else:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def get_default_config() -> Dict[str, Any]:
    """Returns baseline default configuration."""
    return {
        "version": "2.0",
        "mode": "dual_image",  # dual_image | single_image | text_only
        "browser": {
            "cdp_port": 9222,
            "target_url": "https://flow.google.com",
            "timeout_seconds": 55,
            "headless": False,
            "user_data_dir": "flow_browser_profile"
        },
        "inputs": {
            "template_image": "inputs/template.jpg",
            "subjects_dir": "inputs/subjects",
            "file_extensions": [".jpg", ".jpeg", ".png", ".webp"]
        },
        "prompt": {
            "template": (
                "In Image 1, keep the main subject on the left completely unchanged. "
                "Modify ONLY the companion on the right: replace them with the person from Image 2. "
                "Transfer exact facial features, skin tone, and outfit. "
                "Photorealistic natural smartphone selfie camera aesthetic."
            ),
            "variables": {}
        },
        "output": {
            "directory": "outputs/flow_results",
            "prefix": "result_",
            "format": "png",
            "overwrite": False
        }
    }
