#!/usr/bin/env python3
"""Check that ANTHROPIC_API_KEY from .env works. Standard library only.
Usage: python check_key.py [--env path/to/.env] [--no-message]
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.anthropic.com/v1"
VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-haiku-5-5"

HINTS = {
    None: "Could not reach the API. Check the network, proxy or firewall.",
    400: "Bad request. If the message mentions credit or usage limits, the account is limited.",
    401: "The key is invalid, revoked or mistyped.",
    402: "Billing problem. Add credit or check the plan.",
    403: "The key is valid but not allowed to do this (workspace or permission).",
    404: "Not found. The model name may not be available to this key.",
    429: "Rate limit or usage limit reached. Wait, or check the spend limit in the Console.",
    500: "Anthropic server error. Try again shortly.",
    529: "Anthropic is overloaded. Try again shortly.",
}


def find_env(start=None):
    here = Path(start or Path.cwd()).resolve()
    for d in [here, *here.parents]:
        f = d / ".env"
        if f.is_file():
            return f
    return None


def read_key(env_file):
    key = None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        name, sep, val = line.partition("=")
        if not sep or name.strip() != "ANTHROPIC_API_KEY":
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        else:
            val = val.split(" #")[0].strip()
        key = val
    return key


def call(method, path, key, body=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body else None,
        headers={
            "x-api-key": key,
            "anthropic-version": VERSION,
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}"), r.headers.get("request-id")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            data = json.loads(raw)
        except Exception:
            data = {"error": {"message": raw[:300]}}
        return e.code, data, e.headers.get("request-id")
    except urllib.error.URLError as e:
        return None, {"error": {"message": str(e.reason)}}, None


def error_text(status, data, rid):
    msg = (data.get("error") or {}).get("message", "")
    etype = (data.get("error") or {}).get("type", "")
    hint = HINTS.get(status, "Unexpected response.")
    return f"HTTP {status} {etype}: {msg}\n    Meaning: {hint}\n    request-id: {rid}"


def main():
    args = sys.argv[1:]
    env_path = Path(args[args.index("--env") + 1]) if "--env" in args else find_env()
    key = None
    if env_path and env_path.is_file():
        key = read_key(env_path)
        print(f".env file: {env_path}")
    else:
        print(".env file: not found")
    if not key:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key:
            print("Using ANTHROPIC_API_KEY from the environment instead.")
    if not key:
        print("FAIL: ANTHROPIC_API_KEY is missing or empty.")
        sys.exit(1)

    print(f"Key found: {key[:7]}...{key[-4:]} (length {len(key)})")
    if not key.startswith("sk-ant-"):
        print("Warning: the key does not start with sk-ant-, so it may be the wrong value.")
    if key != key.strip() or any(c in key for c in " \n\r\t\"'"):
        print("Warning: the key has spaces or quotes inside it. Check the .env line.")

    # 1. Authentication check: lists models, costs nothing.
    status, data, rid = call("GET", "/models?limit=100", key)
    if status != 200:
        print("FAIL (authentication check)\n    " + error_text(status, data, rid))
        sys.exit(1)
    ids = [m.get("id", "") for m in data.get("data", [])]
    print(f"PASS: the key authenticates. {len(ids)} models are visible to it.")

    if "--no-message" in args:
        print("Skipped the message test.")
        return

    # 2. Usage check: a tiny real request, a few tokens.
    model = os.environ.get("ANTHROPIC_TEST_MODEL") or (
        DEFAULT_MODEL
        if DEFAULT_MODEL in ids
        else next((i for i in ids if "haiku" in i), ids[0] if ids else DEFAULT_MODEL)
    )
    print(f"Sending a tiny message to {model} ...")
    status, data, rid = call(
        "POST",
        "/messages",
        key,
        {"model": model, "max_tokens": 16, "messages": [{"role": "user", "content": "Reply with the single word: ok"}]},
    )
    if status != 200:
        print("FAIL (message test)\n    " + error_text(status, data, rid))
        print("If the first check passed, the key is valid but usage, billing or the model is the problem.")
        sys.exit(2)
    text = "".join(b.get("text", "") for b in data.get("content", []))
    use = data.get("usage", {})
    print(f"PASS: got a reply: {text!r}")
    print(f"Tokens used: {use.get('input_tokens')} in, {use.get('output_tokens')} out. request-id: {rid}")


if __name__ == "__main__":
    main()
