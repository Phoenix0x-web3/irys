# utils/pyarmor_bootstrap.py
import platform
import sys
from pathlib import Path


def ensure_pyarmor_runtime_on_path():
    here = Path(__file__).resolve().parent.parent
    # adjust if this file isn't next to /runtimes
    project_root = here.parent if (here / "runtimes").exists() else here
    rt_root = project_root / "runtimes"

    plat_map = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}
    plat = plat_map.get(platform.system())
    if not plat:
        raise RuntimeError(f"Unsupported platform: {platform.system()}")

    major, minor, micro = sys.version_info[:3]
    exact_tag = f"{major}{minor:02d}{micro:02d}"

    # 1) Try exact Python tag (e.g. windows_py31210)
    exact = rt_root / f"{plat}_py{exact_tag}" / "pyarmor_runtime_000000"
    if exact.exists():
        sys.path.insert(0, str(exact.parent))
        return

    # 2) Fallback: best match by major.minor prefix (pick the highest available)
    prefix = f"{plat}_py{major}{minor:02d}"
    candidates = sorted(
        rt_root.glob(f"{prefix}*/pyarmor_runtime_000000"),
        key=lambda p: p.parent.name,  # lexicographic is fine for these tags
        reverse=True,
    )
    if candidates:
        sys.path.insert(0, str(candidates[0].parent))
     

