"""Live check of "Download audio" through Bodhan AI, inside the autopilot caps.

Prints the estimated cost first and makes no call unless --go is given. It sends one English section
of the pack (the text the page shows: "Why it happens" and the two-minute check for SUB-SFL) through
the real endpoint, then checks the MP3 in code: it exists, ffprobe's duration is close to the length
the text should take, it is not silent, and (STT seconds permitting) a round trip through Bodhan's
speech to text gives back text close to the source. Keys come from the environment and are
never printed.

    python scripts/verify_pack_audio_live.py [--go]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai.config import load_env  # noqa: E402

load_env()
load_env(str(ROOT / ".env.local"))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from services.api.db import Base, make_engine  # noqa: E402
from services.api.main import create_app  # noqa: E402
from services.api.practice import get_speech  # noqa: E402
from services.api.profiles import get_session  # noqa: E402
from services.content import error_content as ec  # noqa: E402
from services.media.storage import get_audio_store  # noqa: E402
from services.speech import audio, lessons, textnorm  # noqa: E402
from services.speech.service import default_service  # noqa: E402


class DictStore:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.data[key] = data

    def get(self, key: str) -> bytes:
        return self.data[key]

    def size(self, key: str) -> int | None:
        return len(self.data[key]) if key in self.data else None

    def delete(self, key: str) -> None:
        self.data.pop(key, None)


def section_text() -> str:
    ex = ec.explanations()["errors"]["SUB-SFL"]
    iv = ec.intervention()["errors"]["SUB-SFL"]
    return "\n\n".join(
        [
            "Why it happens.\n" + ex["why"]["en"],
            "A two-minute check.\n" + iv["two_minute_check"]["en"],
        ]
    )


def ffprobe_seconds(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    return float(json.loads(out.stdout)["format"]["duration"])


def mean_volume_db(path: Path) -> float:
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    )  # fmt: skip
    for line in out.stderr.splitlines():
        if "mean_volume" in line:
            return float(line.split("mean_volume:")[1].split("dB")[0])
    return -91.0


def main(argv: list[str]) -> int:
    text = section_text()
    est = lessons.estimate(text, "en", "bodhan")
    cap_tts = int(os.environ.get("AUTOPILOT_MAX_TTS_CHARS", "20000"))
    cap_stt = float(os.environ.get("AUTOPILOT_MAX_STT_SECONDS", "300"))
    expected_s = est["chars"] / 15.0
    print(
        f"text: {int(est['chars'])} characters (cap {cap_tts}); about {expected_s:.0f} s of speech"
    )
    print(
        f"estimated cost (text to speech plus round trip): INR {est['cost_inr']} "
        "(unverified prices)"
    )
    if est["chars"] > cap_tts or expected_s > cap_stt:
        print("over a cap: not calling")
        return 2
    if "--go" not in argv:
        print("dry run: add --go to call Bodhan")
        return 0
    if not (os.environ.get("BODHAN_SPEAK_API_KEY") or os.environ.get("BODHAN_API_KEY")):
        print("no Bodhan speak key in the environment")
        return 3

    engine = make_engine(f"sqlite:///{Path(tempfile.mkdtemp()) / 'v.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session():  # type: ignore[no-untyped-def]
        with factory() as s:
            yield s

    speech = default_service()
    store = DictStore()
    app = create_app()
    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_speech] = lambda: speech
    app.dependency_overrides[get_audio_store] = lambda: store
    client = TestClient(app)
    client.post("/api/users/register", json={"nickname": "pack audio check"})
    head = {"X-Role": "teacher", "X-User": "pack audio check"}
    r = client.post(
        "/api/audio/pack",
        json={"text": text, "language": "en", "name": "intervention-sub-sfl-check-en"},
        headers=head,
    )
    print("status", r.status_code, "provider", r.headers.get("x-audio-provider"),
          "seconds", r.headers.get("x-audio-seconds"), "bytes", len(r.content))  # fmt: skip
    if r.status_code != 200:
        print("detail:", r.text[:200])
        return 1
    out = Path(tempfile.mkdtemp()) / "intervention-sub-sfl-check-en.mp3"
    out.write_bytes(r.content)
    dur = ffprobe_seconds(out)
    vol = mean_volume_db(out)
    print(
        f"ffprobe duration {dur:.1f} s (expected about {expected_s:.0f} s); "
        f"mean volume {vol:.1f} dB"
    )
    ok = 0.4 * expected_s <= dur <= 2.5 * expected_s and vol > -50.0
    print("duration and not-silent checks:", "PASS" if ok else "FAIL")
    again = client.post("/api/audio/pack", json={"text": text, "language": "en"}, headers=head)
    print("repeat press cached:", again.headers.get("x-audio-cached") == "1")

    if dur <= cap_stt:
        wav = audio.to_wav_16k_mono(r.content)
        pieces = audio.split_for_stt(wav)
        heard = " ".join(speech.chain.transcribe(p, "en").text for p in pieces)  # type: ignore[attr-defined]
        cer = textnorm.cer(text.replace("\n", " "), heard, "en")
        wer = textnorm.wer(text.replace("\n", " "), heard, "en")
        print(
            f"round trip through Bodhan speech to text: {len(pieces)} piece(s), "
            f"CER {cer:.3f}, WER {wer:.3f}"
        )
        print("round trip:", "PASS" if wer <= 0.25 else "REVIEW")  # fmt: skip
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
