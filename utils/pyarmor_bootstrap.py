import platform
import sys
from pathlib import Path


def ensure_pyarmor_runtime_on_path():
    here = Path(__file__).resolve()
    rt_root = None
    # Walk up until we find a folder named "runtimes"
    for parent in [here.parent] + list(here.parents):
        cand = parent / "runtimes"
        if cand.is_dir():
            rt_root = cand
            break

    if rt_root is None:
        return False

    plat = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}[platform.system()]
    major, minor, micro = sys.version_info[:3]
    exact_tag = f"py{major}{minor:02d}{micro:02d}"

    # 1) exact python tag
    exact_base = rt_root / f"{plat}_{exact_tag}"
    if (exact_base / "pyarmor_runtime_000000").is_dir():
        sys.path.insert(0, str(exact_base))
        return True

    # 2) best match by major.minor (pick highest patch available)
    prefix = f"{plat}_py{major}{minor:02d}"
    candidates = sorted(
        (p.parent for p in rt_root.glob(f"{prefix}*/pyarmor_runtime_000000")),
        key=lambda p: p.name,
        reverse=True,
    )
    if candidates:
        sys.path.insert(0, str(candidates[0]))
        return True

    return False
