"""Stitch pack driver: `python tasks.py stitch-pack [--only a,b] [--skip-capture] [--no-build-app]`.

Starts a throwaway demo server (judge mode, recorded AI, stub voice, a fresh database) and the built
PWA on ports of their own, captures every manifest entry in a browser, then builds the images and
documents and validates the pack. Nothing here calls a paid API or touches pilot data.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PWA = ROOT / "apps" / "pwa"
PACK = ROOT / "docs" / "design" / "stitch" / "pack"
API_PORT, WEB_PORT = 8031, 4190


def venv_python() -> str:
    for p in (ROOT / ".venv" / "Scripts" / "python.exe", ROOT / ".venv" / "bin" / "python"):
        if p.exists():
            return str(p)
    return sys.executable


def npm() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def wait_for(url: str, seconds: int = 60) -> None:
    end = time.time() + seconds
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    raise SystemExit(f"timed out waiting for {url}")


def main(argv: list[str]) -> int:
    only = None
    skip_capture = "--skip-capture" in argv
    if "--only" in argv:
        only = argv[argv.index("--only") + 1]
    manifest = yaml.safe_load((PACK / "manifest.yaml").read_text(encoding="utf-8"))
    tmp = ROOT / "tools" / "stitch_pack" / ".work"
    tmp.mkdir(exist_ok=True)
    (tmp / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    procs: list[subprocess.Popen[bytes]] = []
    code = 0
    try:
        if not skip_capture:
            if "--no-build-app" not in argv:
                print("building the PWA ...")
                subprocess.run(
                    [npm(), "run", "build"], cwd=PWA, check=True, stdout=subprocess.DEVNULL
                )
            db = tmp / "pack.sqlite"
            db.unlink(missing_ok=True)
            env = {
                **os.environ,
                "PILOT_MODE": "0",
                "AI_MODE": "recorded",
                "SPEECH_MODE": "stub",
                "ADMIN_OPEN": "1",
                "JUDGE_MODE": "1",
                "DATABASE_URL": f"sqlite:///{db.as_posix()}",
                "RATE_LIMIT_SHEETS_READ_PER_MIN": "0",
                "RATE_LIMIT_ASSISTANT_PER_MIN": "0",
                "RATE_LIMIT_PRACTICE_SESSION_PER_MIN": "0",
                "RATE_LIMIT_PRACTICE_TURN_PER_MIN": "0",
                "RETRIEVAL": "off",
            }
            log = open(tmp / "api.log", "wb")
            procs.append(
                subprocess.Popen(
                    [
                        venv_python(),
                        "-m",
                        "uvicorn",
                        "services.api.main:app",
                        "--port",
                        str(API_PORT),
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            )
            procs.append(
                subprocess.Popen(
                    [
                        "node",
                        str(PWA / "node_modules" / "vite" / "bin" / "vite.js"),
                        "preview",
                        "--port",
                        str(WEB_PORT),
                        "--strictPort",
                    ],
                    cwd=PWA,
                    env={**env, "API_PORT": str(API_PORT)},
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.STDOUT,
                )
            )
            wait_for(f"http://localhost:{API_PORT}/api/health")
            wait_for(f"http://localhost:{WEB_PORT}/")
            capenv = {**os.environ}
            if only:
                capenv["ONLY"] = only
            print("capturing ...")
            r = subprocess.run(
                [
                    "node",
                    str(ROOT / "tools" / "stitch_pack" / "capture.mjs"),
                    str(tmp / "manifest.json"),
                    str(PACK),
                    f"http://localhost:{WEB_PORT}",
                    f"http://localhost:{API_PORT}",
                ],
                cwd=ROOT,
                env=capenv,
            )
            code = r.returncode
        sys.path.insert(0, str(ROOT / "tools" / "stitch_pack"))
        import validate  # noqa: PLC0415

        import build  # noqa: PLC0415

        build.main(only.split(",") if only else None)
        failures = validate.main()
        code = code or (1 if failures else 0)
    finally:
        for p in procs:
            p.terminate()
        shutil.rmtree(tmp / "pack.sqlite", ignore_errors=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
