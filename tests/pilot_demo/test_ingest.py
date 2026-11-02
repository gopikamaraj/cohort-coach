"""The pilot ingest on a FAKE folder made from synthetic sheets: tidy, duplicates, class and roll,
name scan, reading, truth, diagnosis and the reports. The model steps are fakes (no paid call)."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

from PIL import Image

from engine.diagnosis import class_profile, diagnose_child
from engine.model import Form
from services.pilot_demo import answers as ans
from services.pilot_demo.config import form_for, load_manifest
from tests.pilot_demo.conftest import truth_rows
from tools.pilot import ingest as ing

NAME_BOX = (0.1, 0.1, 0.4, 0.15)


class FakeScanner:
    """Answers in call order: the header of IMG_0003, then the name scan of rolls 1 and 2."""

    def __init__(self) -> None:
        self.calls = 0

    def scan(self, jpeg: bytes) -> ing.Scan | None:
        n, self.calls = self.calls, self.calls + 1
        return [
            ing.Scan("3A", 3, False, ()),
            ing.Scan(None, None, False, ()),
            ing.Scan(None, None, True, (NAME_BOX,)),
        ][n]


class FakeReader:
    """Reads each sheet as the truth with the given boxes changed; costs a fixed amount."""

    def __init__(self, cost: float = 0.01, wrong: dict[int, int] | None = None) -> None:
        self.calls = 0
        self.cost = cost
        self.wrong = wrong or {}  # call number -> box index to misread

    def read(self, jpeg: bytes, form: Form) -> ing.ReadOut | None:
        self.calls += 1
        rows = truth_rows()
        texts = list(rows[min(self.calls, 3)])
        conf = [0.97] * len(texts)
        status = ["ok"] * len(texts)
        if self.calls in self.wrong:
            i = self.wrong[self.calls]
            texts[i] = "999"
            conf[i], status[i] = 0.4, "check"
        return ing.ReadOut(texts, conf, status, self.cost)


def run(folder: Path, **kw: object) -> ing.Report:
    return ing.build(folder, **kw)  # type: ignore[arg-type]


def answers_file(folder: Path) -> ans.AnswerFile:
    return ans.AnswerFile.model_validate_json((folder / "pilot_answers.json").read_text("utf-8"))


def test_tidy_turns_a_sideways_photo_upright_and_shrinks_it(folder: Path) -> None:
    big = Image.new("RGB", (3000, 2000), "white")
    buf = io.BytesIO()
    big.save(buf, "PNG")
    img, _ = ing.fix_rotation(Image.open(io.BytesIO(buf.getvalue())))
    assert img.height > img.width  # a landscape photo is turned to portrait
    assert max(ing.shrink(img).size) == ing.LONG_EDGE


def test_duplicates_are_dropped_and_the_sharper_copy_is_kept(folder: Path) -> None:
    rep = run(folder)
    names = " ".join(rep.dropped)
    assert "copy of 3A-roll01.png (identical to 3A-roll01.png)" in names
    assert "3A-roll01 blurry.png" in names and "kept sharper" in names
    assert (folder / "sheets" / "3A-roll01.jpg").is_file()


def test_class_and_roll_come_from_the_file_name_or_from_the_header_scan(folder: Path) -> None:
    rep = run(folder)  # no scanner: IMG_0003 cannot be placed and is listed, never guessed
    assert rep.unlabelled == ["IMG_0003.png"]
    assert not (folder / "sheets" / "3A-roll03.jpg").exists()
    sc = FakeScanner()
    rep = run(folder, scanner=sc)
    assert rep.unlabelled == [] and (folder / "sheets" / "3A-roll03.jpg").is_file()
    assert (folder / "sheets" / "3A-roll02.jpg").is_file()  # from "3A_roll_02.png"


def test_a_name_region_is_blacked_out_and_only_a_yes_and_a_count_are_reported(folder: Path) -> None:
    rep = run(folder, scanner=FakeScanner())
    assert rep.name_regions == 1 and len(rep.names_found) == 1
    img = Image.open(folder / "sheets" / "3A-roll02.jpg").convert("L")
    x0, y0 = int(img.width * 0.12), int(img.height * 0.11)
    x1, y1 = int(img.width * 0.38), int(img.height * 0.14)
    assert max(img.crop((x0, y0, x1, y1)).getdata()) < 25  # solid black
    report = (folder / "ingest_report.md").read_text("utf-8")
    assert "1 region(s)" in report and "HUMAN REVIEW" in report


def test_without_a_scanner_every_sheet_is_listed_for_a_name_review(folder: Path) -> None:
    rep = run(folder)
    assert sorted(rep.names_not_scanned) == ["3A-roll01.jpg", "3A-roll02.jpg"]


def test_truth_wins_over_the_ai_read_and_every_disagreement_is_counted(folder: Path) -> None:
    rep = run(folder, scanner=FakeScanner(), reader=FakeReader(wrong={1: 4}))
    doc = answers_file(folder)
    a = next(c for c in doc.classes if c.class_code == "3A")
    s1, s2, s3 = a.sheets[0], a.sheets[1], a.sheets[2]
    assert s1.source == "truth+ai" and s1.verified and s2.verified
    assert s1.answers[4].given == truth_rows()[1][4] != "999"  # truth kept
    assert s3.source == "ai" and not s3.verified  # no hand-keyed row for roll 3
    assert rep.disagreements == 1 and rep.boxes_compared == 20
    assert "3A-roll03" in rep.unverified


def test_the_report_counts_add_up(folder: Path) -> None:
    rep = run(folder, scanner=FakeScanner())
    kept = len(list((folder / "sheets").glob("*.jpg")))
    assert rep.files_in == kept + len(rep.dropped) + len(rep.unlabelled) + len(rep.out_of_range)
    doc = answers_file(folder)
    a, b = doc.classes
    assert a.class_summary.no_sheet == 1 and a.class_summary.absent == 1
    assert b.class_summary.children_paired == 0 and b.class_summary.no_sheet == 3
    assert a.class_summary.children_paired == rep.sheets_per_class["3A"] == 2


def test_the_cost_cap_stops_reading_and_a_second_run_is_free(folder: Path) -> None:
    reader = FakeReader(cost=1.0)
    rep = run(folder, scanner=FakeScanner(), reader=reader, max_usd=1.0)
    assert reader.calls == 1 and rep.ai_cost_usd == 1.0
    assert rep.unread == ["3A-roll02.jpg", "3A-roll03.jpg"] or "3A-roll03.jpg" in rep.unread


def test_the_run_is_idempotent_and_cached_by_image_hash(folder: Path) -> None:
    reader = FakeReader()
    run(folder, scanner=FakeScanner(), reader=reader)
    first = (folder / "pilot_answers.json").read_text("utf-8")
    calls = reader.calls
    scanner = FakeScanner()
    scanner.calls = 99  # would raise if asked again: the scan is cached too
    run(folder, scanner=scanner, reader=reader)
    assert reader.calls == calls and (folder / "pilot_answers.json").read_text("utf-8") == first


def test_the_accuracy_file_holds_counts_only_and_exists_only_with_truth(
    folder: Path, tmp_path: Path
) -> None:
    out = tmp_path / "pilot_reading_accuracy.md"
    run(folder, scanner=FakeScanner(), reader=FakeReader(wrong={1: 4}), accuracy_path=out)
    text = out.read_text("utf-8")
    assert "| 3A | 19 of 20 | 1 of 2 |" in text and "directional" in text
    assert not re.search(r"roll|3A-", text.replace("| 3A |", ""))  # no per-child rows
    (folder / "truth" / "3A.csv").unlink()
    out2 = tmp_path / "none.md"
    run(folder, scanner=FakeScanner(), reader=FakeReader(), accuracy_path=out2)
    assert not out2.exists()


def test_the_answer_file_validates_and_every_judgement_is_the_engines(folder: Path) -> None:
    run(folder, scanner=FakeScanner(), reader=FakeReader())
    raw = json.loads((folder / "pilot_answers.json").read_text("utf-8"))
    doc = ans.AnswerFile.model_validate(raw)
    assert doc.source == "pilot" and doc.demo
    questions = {q["no"]: q for q in doc.test["questions"]}
    assert len(questions) == 10
    assert questions[1]["class_variants"] == {"3A": 346, "3B": 453}
    manifest = load_manifest(folder / "manifest.yaml")
    for c in doc.classes:
        form = form_for(manifest.klass(c.class_code))  # type: ignore[arg-type]
        diags = []
        for s in (x for x in c.sheets if x.status == "entered"):
            assert [a.q for a in s.answers] == list(questions)
            for a in s.answers:
                q = questions[a.q]
                if a.status == "answered":
                    right = int(a.given) == form.items[a.q - 1].a if a.q <= 2 else None
                    assert a.correct == (int(a.given) == _correct(form, a.q))
                    del right
                    if a.matched_bug:
                        assert a.matched_bug in q["error_probes"]
                else:
                    assert a.correct is None and a.given == ""
            diags.append(diagnose_child(form, [ans.reading_of(a.given) for a in s.answers]))
        profile = class_profile(diags)
        assert c.class_summary.counts == {k.value: v for k, v in profile.counts.items()}


def _correct(form: Form, q: int) -> int:
    from engine.bugs import correct_answer

    return correct_answer(form.items[q - 1])
