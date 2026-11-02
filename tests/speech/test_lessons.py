"""Lesson audio: sentence splitting (English, Hindi, Tamil, with sums and decimals), chunking and
re-splitting, stitching and the timing map, the chunk cache, retry, whole-lesson fallback, the
round-trip check, and regenerating one sentence. Generated tones only; no network."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from services.speech import audio, lessons, textnorm
from services.speech.chain import ProviderChain
from services.speech.provider import Audio, Capabilities, Transcript
from services.speech.sarvam import SpeechError

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")


class Scripted:
    """A provider whose audio lasts `per_char` seconds per character, and whose transcription
    returns the last text it voiced (or `heard_as` when set). It can fail on chosen calls."""

    def __init__(
        self,
        name: str,
        *,
        per_char: float = 0.02,
        fail_on: set[int] | None = None,
        heard_as: str | None = None,
        configured: bool = True,
    ) -> None:
        self.name = name
        self.per_char = per_char
        self.fail_on = fail_on or set()
        self.heard_as = heard_as
        self._configured = configured
        self.said: list[str] = []
        self.heard: list[bytes] = []
        self._last_text = ""
        self.calls = 0

    def configured_for(self, function: str) -> bool:
        return self._configured

    @property
    def capabilities(self) -> Capabilities:
        return Capabilities(30.0, frozenset({"wav"}), 300)

    def synthesize(self, text: str, language: str, voice: str, style: str | None) -> Audio:
        self.calls += 1
        if self.calls in self.fail_on:
            raise SpeechError("unavailable", 503)
        self.said.append(text)
        self._last_text = text
        wav = audio.tone(max(0.05, len(text) * self.per_char), 300, rate=24000)
        return Audio(wav, "wav", 24000, 0.0, len(text), self.name, "r")

    def transcribe(self, wav: bytes, language: str) -> Transcript:
        self.heard.append(wav)
        return Transcript(
            self.heard_as if self.heard_as is not None else self._last_text,
            audio.wav_seconds(wav),
            self.name,
        )


class Speech:
    def __init__(self, *providers: Scripted) -> None:
        names = [p.name for p in providers]
        self.chain = ProviderChain({p.name: p for p in providers}, order=lambda f, lang: names)


class Store:
    """A dict standing in for the private bucket."""

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


@pytest.fixture(autouse=True)
def quick_mp3(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("real_audio") is None:
        monkeypatch.setattr(lessons, "encode_mp3", lambda wav, kbps: b"ID3" + wav[44:200])


SCRIPT = (
    "Today we look at 52 - 29. Meena writes 37.\n"
    "Ask her to show it with bundles of ten. What happens to the 2 loose sticks?\n\n"
    "Next week we check by adding back. 23 + 29 = 52, so the answer holds."
)


# --- sentences and chunks ----------------------------------------------------------------------


def test_english_sentences_keep_sums_and_decimals_whole_and_sections_count() -> None:
    s = lessons.split_sentences(
        "Take 703 − 468 slowly. It is 3.5 times bigger! Is it?\n\nNew part."
    )
    assert [x.text for x in s] == [
        "Take 703 − 468 slowly.",
        "It is 3.5 times bigger!",
        "Is it?",
        "New part.",
    ]
    assert [x.section for x in s] == [0, 0, 0, 1]


def test_hindi_sentences_end_at_the_danda() -> None:
    s = lessons.split_sentences("आज हम 52 − 29 देखेंगे। मीना 37 लिखती है। क्या यह सही है?")
    assert [x.text for x in s] == ["आज हम 52 − 29 देखेंगे।", "मीना 37 लिखती है।", "क्या यह सही है?"]


def test_tamil_sentences_end_at_a_full_stop_and_keep_numbers() -> None:
    s = lessons.split_sentences("இன்று 52 - 29 பார்ப்போம். மீனா 37 எழுதுகிறாள். இது 3.5 மடங்கு.")
    assert len(s) == 3 and s[2].text == "இது 3.5 மடங்கு."


def test_chunks_hold_one_or_two_sentences_of_one_section_within_the_limits() -> None:
    sentences = lessons.split_sentences(SCRIPT)
    chunks = lessons.make_chunks(sentences, target=120, maximum=300)
    assert all(1 <= len(c.sentences) <= 2 for c in chunks)
    assert all(len(c.text) <= 300 for c in chunks)
    for c in chunks:
        assert len({sentences[i].section for i in c.sentences}) == 1
    assert [i for c in chunks for i in c.sentences] == list(range(len(sentences)))


def test_a_sentence_over_the_maximum_is_cut_into_pieces() -> None:
    long = "Count, " * 70 + "and stop."
    chunks = lessons.make_chunks(lessons.split_sentences(long), target=220, maximum=300)
    assert len(chunks) >= 2 and all(len(c.text) <= 300 for c in chunks)
    assert all(c.sentences == (0,) for c in chunks)


# --- voicing, stitching, timing -------------------------------------------------------------------


def test_stitched_length_is_the_sum_of_the_chunks_and_the_gaps_and_the_timing_map_matches() -> None:
    p = Scripted("bodhan")
    got = lessons.generate(SCRIPT, "en", Speech(p), Store())
    chunk_seconds = sum(c["seconds"] for c in got.chunks)
    sections = [c for c in got.chunks]
    gaps = 0.0
    sec_of = {i: s for i, s in enumerate(got.sections)}
    for a, b in zip(sections, sections[1:], strict=False):
        gaps += 0.5 if sec_of[b["sentences"][0]] != sec_of[a["sentences"][0]] else 0.25
    assert got.seconds == pytest.approx(chunk_seconds + gaps, abs=0.01)
    starts = [t["start"] for t in got.timing]
    assert starts == sorted(starts) and got.timing[0]["start"] == 0.0
    assert got.timing[-1]["end"] == pytest.approx(got.seconds, abs=0.01)
    assert [t["i"] for t in got.timing] == list(range(len(got.sentences)))
    assert got.provider == "bodhan" and got.voice == "Kavya" and got.style == "educational lecture"


def test_a_chunk_longer_than_28_seconds_is_split_and_made_again() -> None:
    p = Scripted("bodhan", per_char=0.2)  # two sentences of ~80 characters = 32 s
    script = "A" * 79 + ". " + "B" * 79 + "."
    got = lessons.generate(script, "en", Speech(p), Store())
    assert len(got.chunks) == 2 and all(c["seconds"] <= 28 for c in got.chunks)


def test_a_repeated_lesson_makes_no_provider_call() -> None:
    p, store = Scripted("bodhan"), Store()
    lessons.generate(SCRIPT, "en", Speech(p), store)
    voiced, heard = len(p.said), len(p.heard)
    again = lessons.generate(SCRIPT, "en", Speech(p), store)
    assert len(p.said) == voiced and len(p.heard) == heard and again.from_cache


def test_the_cache_key_changes_with_the_voice_the_style_the_text_and_the_pipeline() -> None:
    v = lessons.Voicer("bodhan", "Kavya", "news", "indic-speak", True, lambda t: b"")
    base = lessons.chunk_key(v, "hi", "नमस्ते।")
    assert lessons.chunk_key(v, "hi", "नमस्ते।  ") == base  # spacing is normalised
    for other in (
        lessons.Voicer("bodhan", "Suhani", "news", "indic-speak", True, lambda t: b""),
        lessons.Voicer("bodhan", "Kavya", None, "indic-speak", True, lambda t: b""),
        lessons.Voicer("sarvam", "Kavya", "news", "indic-speak", True, lambda t: b""),
    ):
        assert lessons.chunk_key(other, "hi", "नमस्ते।") != base
    assert lessons.chunk_key(v, "ta", "நன்றி.") != base


def test_the_pipeline_version_is_part_of_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    v = lessons.Voicer("bodhan", "Kavya", None, "indic-speak", True, lambda t: b"")
    before = lessons.chunk_key(v, "en", "Hello.")
    monkeypatch.setattr(lessons, "PIPELINE_VERSION", "lesson-audio-2")
    assert lessons.chunk_key(v, "en", "Hello.") != before


def test_a_failed_chunk_is_retried_once() -> None:
    p = Scripted("bodhan", fail_on={2})
    got = lessons.generate(SCRIPT, "en", Speech(p), Store())
    assert got.provider == "bodhan" and not got.fallbacks


def test_if_a_chunk_still_fails_the_whole_lesson_is_made_with_the_next_provider() -> None:
    bodhan = Scripted("bodhan", fail_on={2, 3})  # chunk 2 fails twice
    sarvam = Scripted("sarvam")
    got = lessons.generate(SCRIPT, "en", Speech(bodhan, sarvam), Store())
    assert got.provider == "sarvam" and got.voice == "ritu" and got.style is None
    assert got.fallbacks and got.fallbacks[0].startswith("bodhan")
    n_chunks = len(got.chunks)
    assert len(sarvam.said) >= n_chunks  # every chunk, in the one voice


def test_when_every_provider_fails_the_lesson_is_text_only() -> None:
    with pytest.raises(lessons.LessonAudioUnavailable) as e:
        lessons.generate(
            SCRIPT,
            "en",
            Speech(
                Scripted("bodhan", fail_on=set(range(1, 99))),
                Scripted("sarvam", fail_on=set(range(1, 99))),
            ),
            Store(),
        )
    assert set(e.value.reasons) == {"bodhan", "sarvam"}


def test_a_cached_lesson_plays_with_every_provider_down() -> None:
    store = Store()
    lessons.generate(SCRIPT, "hi", Speech(Scripted("bodhan")), store)
    down = Speech(Scripted("bodhan", configured=False), Scripted("sarvam", configured=False))
    got = lessons.generate(SCRIPT, "hi", down, store)
    assert got.provider == "bodhan" and got.from_cache


# --- the round trip ------------------------------------------------------------------------------


def test_chunks_that_come_back_different_are_made_again_once_then_flagged() -> None:
    p = Scripted("bodhan", heard_as="something else entirely")
    got = lessons.generate(SCRIPT, "en", Speech(p), Store())
    n = len(got.chunks)
    assert len(p.said) == 2 * n  # each made once more
    assert all(c["flagged"] for c in got.checks)
    assert got.summary == {
        "sentences": len(got.sentences),
        "checked": len(got.sentences),
        "passed": 0,
        "flagged": len(got.sentences),
    }


def test_chunks_that_come_back_right_pass() -> None:
    got = lessons.generate(SCRIPT, "en", Speech(Scripted("bodhan")), Store())
    assert got.summary["flagged"] == 0 and got.summary["passed"] == len(got.sentences)


def test_numbers_said_as_words_still_match() -> None:
    assert (
        textnorm.cer("52 - 29 = 23.", "fifty two minus twenty nine equals twenty three", "en") > 0
    )
    assert textnorm.normalise("Fifty-two and 29!", "en") == "52 and 29"
    assert textnorm.normalise("बावन में से उनतीस", "hi") == "52 में से 29"
    assert textnorm.normalise("तीन सौ छियालीस", "hi") == "346"
    assert textnorm.normalise("முன்னூற்று நாற்பத்து ஆறு", "ta") == "346"
    assert textnorm.normalise("இருபத்து மூன்று", "ta") == "23"
    assert textnorm.normalise("३४६ and ௨௩", "en") == "346 and 23"
    assert textnorm.cer("मीना 37 लिखती है।", "मीना सैंतीस लिखती है", "hi") == 0.0
    assert textnorm.cer("Meena writes 37.", "meena writes thirty seven", "en") == 0.0


def test_the_hindi_word_list_covers_0_to_100() -> None:
    assert len(textnorm._HI_1_100) == 101
    assert textnorm.HI["निन्यानवे"] == 99 and textnorm.HI["सौ"] == 100


def test_a_lesson_without_transcription_is_marked_unchecked() -> None:
    class NoEars(Scripted):
        def configured_for(self, function: str) -> bool:
            return function == "tts"

    got = lessons.generate(SCRIPT, "en", Speech(NoEars("bodhan")), Store())
    assert got.summary["checked"] == 0 and all(c["cer"] is None for c in got.checks)


# --- regenerate one sentence ----------------------------------------------------------------------


def test_regenerating_one_sentence_makes_only_its_chunk_again() -> None:
    p, store = Scripted("bodhan"), Store()
    first = lessons.generate(SCRIPT, "en", Speech(p), store)
    before = len(p.said)
    chunk = lessons.chunk_of_sentence(SCRIPT, 3)
    again = lessons.generate(SCRIPT, "en", Speech(p), store, fresh={chunk}, only_provider="bodhan")
    assert len(p.said) == before + 1  # just that chunk
    assert (
        p.said[-1]
        == [c for c in lessons.make_chunks(lessons.split_sentences(SCRIPT)) if c.index == chunk][
            0
        ].text
    )
    assert again.provider == first.provider and len(again.timing) == len(first.timing)


# --- the real encoder ----------------------------------------------------------------------------


@pytest.mark.real_audio
@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe not on PATH")
def test_the_lesson_file_is_a_valid_mono_mp3_at_48_kbps(tmp_path) -> None:  # type: ignore[no-untyped-def]
    got = lessons.generate(SCRIPT, "en", Speech(Scripted("bodhan", per_char=0.05)), Store())
    f = tmp_path / "lesson.mp3"
    f.write_bytes(got.mp3)
    done = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(f)],
        capture_output=True,
        check=True,
    )
    info = json.loads(done.stdout)
    stream = info["streams"][0]
    assert stream["codec_name"] == "mp3" and stream["channels"] == 1
    assert abs(int(stream["bit_rate"]) - 48000) <= 2000
    assert float(info["format"]["duration"]) == pytest.approx(got.seconds, abs=0.2)
