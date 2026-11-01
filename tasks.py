"""Cross-platform task runner for Cohort Coach (Windows, macOS, Linux).

Usage: python tasks.py <command> [args]      (python tasks.py --list)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PWA = ROOT / "apps" / "pwa"
VENV = ROOT / ".venv"


def venv_python() -> str:
    exe = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(exe) if exe.exists() else sys.executable


def npm() -> str:
    found = shutil.which("npm")
    if not found:
        sys.exit("npm not found. Install Node 20+ from https://nodejs.org")
    return found


def run(cmd: list[str], cwd: Path = ROOT) -> int:
    print("$", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=cwd)


def must(cmd: list[str], cwd: Path = ROOT) -> None:
    code = run(cmd, cwd)
    if code != 0:
        sys.exit(code)


def cmd_setup(args: list[str]) -> int:
    if not VENV.exists():
        uv = shutil.which("uv")
        must([uv, "venv", str(VENV)] if uv else [sys.executable, "-m", "venv", str(VENV)])
    py = venv_python()
    must([py, "-m", "pip", "install", "-q", "-e", ".[dev]"])
    must([npm(), "install"], PWA)
    hook = ROOT / ".git" / "hooks" / "pre-commit"
    if hook.parent.exists():
        hook.write_text("#!/bin/sh\npython tasks.py check\n", encoding="utf-8")
        hook.chmod(0o755)
        print("git pre-commit hook installed (runs `python tasks.py check`)")
    return 0


def cmd_dev(args: list[str]) -> int:
    api = subprocess.Popen(
        [venv_python(), "-m", "uvicorn", "services.api.main:app", "--reload", "--port", "8000"],
        cwd=ROOT,
        env={**os.environ, "JUDGE_MODE": os.environ.get("JUDGE_MODE", "1")},  # local dev is a demo
    )
    pwa = subprocess.Popen([npm(), "run", "dev"], cwd=PWA)
    try:
        return api.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        for proc in (api, pwa):
            proc.terminate()


def cmd_test(args: list[str]) -> int:
    code = run([venv_python(), "-m", "pytest", "-q", *args])
    return code or run([npm(), "run", "test"], PWA)


def cmd_check(args: list[str]) -> int:
    py = venv_python()
    steps: list[tuple[list[str], Path]] = [
        ([py, "-m", "ruff", "check", "."], ROOT),
        ([py, "-m", "ruff", "format", "--check", "."], ROOT),
        ([py, "-m", "mypy"], ROOT),
        ([npm(), "run", "lint"], PWA),
        ([npm(), "run", "typecheck"], PWA),
    ]
    for cmd, cwd in steps:
        if run(cmd, cwd) != 0:
            return 1
    if cmd_test([]) != 0:
        return 1
    if cmd_export_keys(["--check"]) != 0:
        return 1
    # Eval smoke: engine_items at a small N, no file write (the full run writes results).
    smoke = [
        [py, "-m", "evals.runners.engine_items", "--n", "100", "--no-write"],
        [py, "-m", "evals.runners.statistics", "--quick", "--no-write"],
        [py, "-m", "evals.runners.redteam", "--no-write"],
        [py, "-m", "evals.runners.sim_fidelity", "--no-write"],
        [py, "scripts/readme.py", "--check"],
    ]
    return max(run(cmd) for cmd in smoke)


AVAILABLE_EVALS = {
    "engine_items": "evals.runners.engine_items",
    "statistics": "evals.runners.statistics",
    "redteam": "evals.runners.redteam",
    "sim_fidelity": "evals.runners.sim_fidelity",
}


def cmd_eval(args: list[str]) -> int:
    """eval <name|all> [--live]; only evals whose phase has landed run."""
    if not args:
        print("available after P13 (available now: " + ", ".join(AVAILABLE_EVALS) + ")")
        return 0
    name, rest = args[0], args[1:]
    if "--live" in rest:
        if name not in ("redteam", "sim_fidelity"):
            print("live evals other than redteam and sim_fidelity are available after P13")
            return 0
        return run([venv_python(), "-m", AVAILABLE_EVALS[name], *rest])
    if name == "all":
        return max(run([venv_python(), "-m", mod, *rest]) for mod in AVAILABLE_EVALS.values())
    if name not in AVAILABLE_EVALS:
        print(
            f"unknown or not yet built eval '{name}': available after P13 (now: "
            + ", ".join(AVAILABLE_EVALS)
            + ")"
        )
        return 0
    return run([venv_python(), "-m", AVAILABLE_EVALS[name], *rest])


def cmd_seed(args: list[str]) -> int:
    return run([venv_python(), "scripts/seed.py", *args])


def cmd_evidence(args: list[str]) -> int:
    return run([venv_python(), "scripts/evidence.py", *args])


def cmd_budget(args: list[str]) -> int:
    return run([venv_python(), "scripts/budget.py", *args])


def cmd_readme(args: list[str]) -> int:
    return run([venv_python(), "scripts/readme.py", *args])


def cmd_predeploy(args: list[str]) -> int:
    """Before a deploy: rebuild the assistant's reference index (no AI call), then check that every
    role has suggested questions for every screen it reaches, the README is current and the
    assistant tests pass. Questions that are missing are written by the prompt
    docs/build/Claude Code prompt refresh the assistant reference before deploy.md."""
    py = venv_python()
    must([py, "scripts/build_assistant_index.py"])
    steps = [
        [py, "scripts/check_assistant_questions.py"],
        [py, "scripts/build_assistant_index.py", "--check"],
        [py, "scripts/readme.py", "--check"],
        [py, "-m", "pytest", "-q", "tests/assistant"],
    ]
    failed = [" ".join(c[1:3]) for c in steps if run(c) != 0]
    if failed:
        print("predeploy FAILED:", "; ".join(failed))
        return 1
    print("predeploy ok: the assistant's reference and questions are ready to deploy")
    return 0


def cmd_practice(args: list[str]) -> int:
    return run([venv_python(), "scripts/practice_cli.py", *args])


def cmd_bundle(args: list[str]) -> int:
    """Build the PWA, then fail above 1 MB compressed initial JS (warn above 400 KB)."""
    must([npm(), "run", "build"], PWA)
    return run([venv_python(), "scripts/bundle_size.py", "--write", *args])


def cmd_e2e(args: list[str]) -> int:
    """Playwright against the production build: offline, install, languages, counts-only sync."""
    os.environ["PYTHON"] = venv_python()  # the API the tests start runs in this environment
    return run([npm(), "run", "e2e", "--", *args], PWA)


def cmd_stitch_pack(args: list[str]) -> int:
    """Capture, build and validate the Stitch screenshot pack (demo data only, no paid calls)."""
    return run([venv_python(), "tools/stitch_pack/run.py", *args])


def cmd_pilot_ingest(args: list[str]) -> int:
    """Tidy the local pilot sheets and write the answer file (data/pilot/, never committed)."""
    return run([venv_python(), "tools/pilot/ingest.py", *args])


def cmd_export_keys(args: list[str]) -> int:
    return run([venv_python(), "scripts/export_keys.py", *args])


def script(path: str) -> Callable[[list[str]], int]:
    """A command that runs one script with the project's Python (live scripts ask for --yes)."""

    def _run(args: list[str]) -> int:
        return run([venv_python(), path, *args])

    return _run


def deferred(phase: str) -> Callable[[list[str]], int]:
    def _run(args: list[str]) -> int:
        print(f"available after {phase}")
        return 0

    return _run


COMMANDS: dict[str, tuple[Callable[[list[str]], int], str]] = {
    "setup": (cmd_setup, "install Python and PWA dependencies, git hooks"),
    "dev": (cmd_dev, "API (uvicorn --reload) + PWA (vite) together"),
    "test": (cmd_test, "pytest + vitest (no paid API calls)"),
    "check": (cmd_check, "lint + typecheck + test + eval smoke (run before every commit)"),
    "eval": (cmd_eval, "evals: <name|all> [--live]"),
    "seed": (cmd_seed, "build the simulated block (seed 2026) and seed the DB [--check] [--no-db]"),
    "practice": (
        cmd_practice,
        "rehearse in the terminal: --scenario sub-sfl --lang en [--stub|--live]",
    ),
    "bundle": (cmd_bundle, "build the PWA and check the initial JS budget"),
    "e2e": (cmd_e2e, "Playwright end-to-end tests on the production build"),
    "pilot-ingest": (
        cmd_pilot_ingest,
        "tidy local pilot sheets, write pilot_answers.json [--no-ai] [--max-usd N]",
    ),
    "stitch-pack": (
        cmd_stitch_pack,
        "screenshots and descriptions for Stitch [--only a,b] [--skip-capture]",
    ),
    "export-keys": (cmd_export_keys, "answer keys JSON for on-device diagnosis [--check]"),
    "budget": (cmd_budget, "spend by call, model and day, from the audit trail"),
    "evidence": (cmd_evidence, "regenerate docs/evidence/ and the numbers table [--check]"),
    "predeploy": (
        cmd_predeploy,
        "before a deploy: rebuild the assistant index, check its questions",
    ),
    "readme": (cmd_readme, "regenerate README 'Where AI is used' [--check]"),
    "lessons-pregen": (
        script("scripts/lessons_pregen.py"),
        "voice and cache every published demo lesson (prints the cost; --yes to spend)",
    ),
    "practice-pregen": (
        script("scripts/practice_pregen.py"),
        "cache the Practice Class template lines (prints counts and cost; --yes [--limit N])",
    ),
    "speech-eval-pack": (
        script("scripts/speech_eval_pack.py"),
        "blinded listening pack, Bodhan and Sarvam (prints the cost; --yes to spend)",
    ),
    "speech-eval-stt": (
        script("scripts/speech_eval_stt.py"),
        "speech-to-text eval on data/speech-eval/ (prints the cost; --yes) [--record NAME]",
    ),
    "speech-latency": (
        script("scripts/speech_latency.py"),
        "speech latency per function and provider, live and capped (prints the cost; --yes)",
    ),
}


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("--list", "-h", "--help"):
        for name, (_, doc) in COMMANDS.items():
            print(f"{name:<12} {doc}")
        return 0
    name = argv[1]
    if name not in COMMANDS:
        print(f"unknown command: {name}. Try --list", file=sys.stderr)
        return 2
    return COMMANDS[name][0](argv[2:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
