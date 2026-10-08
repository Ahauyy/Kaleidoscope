import os
import sys

def get_dir_size(path):
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += get_dir_size(entry.path)
            except Exception:
                pass
    except Exception:
        pass
    return total

print("=" * 65)
print("1. UKURAN FILE & FOLDER DI WORKSPACE (Kaleidoscope)")
print("=" * 65)
workspace_items = []
for f in os.listdir('.'):
    p = os.path.join('.', f)
    if os.path.isdir(p):
        size = get_dir_size(p)
    else:
        try:
            size = os.path.getsize(p)
        except Exception:
            size = 0
    workspace_items.append((f, size))

workspace_items.sort(key=lambda x: x[1], reverse=True)
for name, sz in workspace_items[:15]:
    if sz > 1024 * 1024:
        print(f"{name:<35}: {sz / (1024*1024):>10.2f} MB ({sz / (1024**3):>6.2f} GB)")

print("\n" + "=" * 65)
print("2. UKURAN DIREKTORI CACHE GLOBAL DI SISTEM")
print("=" * 65)
home = os.path.expanduser("~")
cache_targets = [
    ("HuggingFace Cache", os.path.join(home, ".cache", "huggingface")),
    ("Torch Cache", os.path.join(home, ".cache", "torch")),
    ("Pip Cache", os.path.join(home, "AppData", "Local", "pip", "cache")),
    ("Playwright Browsers", os.path.join(home, "AppData", "Local", "ms-playwright")),
    ("UV Python / Cache", os.path.join(home, "AppData", "Roaming", "uv")),
    ("Antigravity Brain / Artifacts", os.path.join(home, ".gemini", "antigravity-ide", "brain")),
    ("Temp Folder (Windows)", os.path.join(home, "AppData", "Local", "Temp")),
]

for label, p in cache_targets:
    if os.path.exists(p):
        sz = get_dir_size(p)
        print(f"{label:<30} ({p}):")
        print(f"   -> {sz / (1024*1024):>10.2f} MB ({sz / (1024**3):>6.2f} GB)")
    else:
        print(f"{label:<30}: TIDAK DITEMUKAN")
