"""The single source of truth for the 8 Claude calls.

The README "Where AI is used" section (`python tasks.py readme`), the judge-mode AI-layers overlay
and `GET /api/judge/ai-map` all read this file. Each entry says what happens in the five layers:
data input -> processing -> guardrails -> evaluation -> output.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from ai import schemas
from ai.config import DEFAULT_MODELS, POLICIES, model_for

LAYERS = ("input", "processing", "guardrails", "evaluation", "output")


@dataclass(frozen=True)
class CallSpec:
    id: int
    key: str  # also the prompt id
    name: str
    purpose: str
    model_env: str
    when: str  # live turn | session end | offline batch | weekly | per photo
    output_model: type[BaseModel]
    input_fields: tuple[str, ...]  # what the caller passes in
    validators: tuple[str, ...]
    gates: tuple[str, ...]
    eval_id: str
    eval_bar: str
    input: str
    processing: str
    guardrails: str
    evaluation: str
    output: str
    metadata_only: bool = False  # Practice Class calls log metadata only
    live_turn: bool = False
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def model(self) -> str:
        return model_for(self.model_env)

    @property
    def prompt_path(self) -> str:
        from ai.prompt_loader import load_prompt

        return f"ai/prompts/{self.key}.v{load_prompt(self.key).version}.md"

    @property
    def layers(self) -> dict[str, str]:
        return {layer: getattr(self, layer) for layer in LAYERS}


CALLS: tuple[CallSpec, ...] = (
    CallSpec(
        id=1,
        key="c01_child_voice",
        name="Child voices",
        purpose="Say one short line as a simulated Grade 3 child in the Practice Class.",
        model_env="MODEL_CHILD",
        when="live turn",
        output_model=schemas.ChildLine,
        input_fields=("persona", "language", "teacher_move", "engine_answer"),
        validators=("numbers", "length", "language", "prefilter"),
        gates=("code validators", "pre-filter", "call 7 (check-then-release)"),
        eval_id="eval_child_voice",
        eval_bar="200 scripted turns, 100% numbers match; realism median >= 4/5",
        input="Child persona, language, the teacher's labelled move, and the exact wrong answer the engine chose.",
        processing="Claude writes one line of at most 30 words around the engine's number.",
        guardrails="Every number must equal the engine's answer; length, language and script checks; pre-filter; one retry, then a template line.",
        evaluation="200 scripted turns: numbers match 100%; realism rated 1 to 5 by humans (pending until rated).",
        output="A short spoken line in the child's voice, with an AI-layers overlay in judge mode.",
        metadata_only=True,
        live_turn=True,
    ),
    CallSpec(
        id=2,
        key="c02_move_label",
        name="Teacher-move labeller",
        purpose="Label what the teacher just did with one move from a fixed list.",
        model_env="MODEL_LABEL",
        when="live turn",
        output_model=schemas.MoveLabel,
        input_fields=("teacher_text", "move_list"),
        validators=("label in fixed set",),
        gates=("JSON schema", "confidence floor"),
        eval_id="eval_move_labeller",
        eval_bar=">= 85% agreement on 150 human-labelled lines",
        input="One line the teacher said or typed, wrapped as untrusted data, and the technique's fixed move list.",
        processing="A small model returns one label and a confidence.",
        guardrails="The label must be in the fixed list (JSON schema); low confidence becomes 'other', which changes nothing; off-task and injection lines become 'off_task'.",
        evaluation="150 human-labelled lines, agreement at least 85%.",
        output="A move label that moves the simulation's child state; never shown as a score.",
        metadata_only=True,
        live_turn=True,
    ),
    CallSpec(
        id=3,
        key="c03_feedback",
        name="Rehearsal feedback",
        purpose="After a rehearsal, give two strengths and one thing to try, each quoting her words.",
        model_env="MODEL_FEEDBACK",
        when="session end",
        output_model=schemas.Feedback,
        input_fields=("transcript", "rubric", "language"),
        validators=("quotes", "length", "language", "prefilter"),
        gates=("code validators", "pre-filter", "call 7"),
        eval_id="eval_feedback",
        eval_bar="30 transcripts, 100% valid quotes; usefulness median >= 4",
        input="The rehearsal transcript (stays on her phone unless she shares it) and the rubric of moves.",
        processing="Claude writes two strengths and one idea to try, each with a quote.",
        guardrails="Each quote must appear word for word in the transcript; points only from the rubric; no scores; pre-filter and call 7.",
        evaluation="30 transcripts: quotes 100% valid; usefulness rated by teachers (pending until rated).",
        output="A private feedback card with a Checked badge and a 'this is wrong' flag.",
        metadata_only=True,
    ),
    CallSpec(
        id=4,
        key="c04_method_capture",
        name="Mentor method capture",
        purpose="Turn a mentor's spoken answers into a method card, citing her sentences.",
        model_env="MODEL_METHOD",
        when="after recording",
        output_model=schemas.MethodCard,
        input_fields=("sentences", "error", "language"),
        validators=("sentence ids exist", "numbers", "prefilter"),
        gates=("code validators", "pre-filter", "call 7", "mentor approval", "reviewer approval"),
        eval_id="eval_method_capture",
        eval_bar="mentor edit size and reviewer acceptance (pending)",
        input="The mentor's transcribed answers, split into numbered sentences.",
        processing="Claude turns them into steps, each citing the sentence ids it came from.",
        guardrails="Every cited id must exist; only what she said; she approves, then a reviewer approves.",
        evaluation="Mentor edit size and reviewer acceptance, reported when mentors exist.",
        output="A method card that can feed the next cohort's track.",
    ),
    CallSpec(
        id=5,
        key="c05_track_draft",
        name="Track drafting",
        purpose="Draft a 3-week track: six 5-minute lessons and one model-lesson script.",
        model_env="MODEL_DRAFT",
        when="offline, Message Batches API",
        output_model=schemas.TrackDraft,
        input_fields=("error", "language", "method_cards", "plan"),
        validators=("arithmetic", "numbers (slots only)", "readability", "prefilter"),
        gates=("code validators", "pre-filter", "call 7", "reviewer approval", "mentor approval"),
        eval_id="eval_track_draft",
        eval_bar=">= 80% accepted with minor edits; arithmetic 100%",
        input="The error, language, up to 3 approved method cards and the lesson plan structure.",
        processing="The strongest model drafts offline in a batch at half price.",
        guardrails="Arithmetic checked by code; class numbers are slots filled by code; reading level; call 7; then a reviewer and a mentor approve.",
        evaluation="Share of drafts accepted with minor edits; arithmetic correctness (code-checked).",
        output="A reviewed track published as audio, with Checked and Reviewed badges.",
    ),
    CallSpec(
        id=6,
        key="c06_digest",
        name="Reflection digest",
        purpose="Group a week of teacher reflections into themes; code counts them.",
        model_env="MODEL_DIGEST",
        when="weekly",
        output_model=schemas.Digest,
        input_fields=("reflections",),
        validators=("pii", "themes only"),
        gates=("names stripped by code", "pre-filter", "call 7"),
        eval_id="eval_digest",
        eval_bar="mentor usefulness rating (pending)",
        input="Short reflections with names and schools removed by code first.",
        processing="A small model assigns each reflection to a theme.",
        guardrails="Code strips names before the call; the model never states a count, code counts the themes.",
        evaluation="Mentor usefulness rating (pending until mentors rate).",
        output="A weekly digest for the mentor.",
    ),
    CallSpec(
        id=7,
        key="c07_checker",
        name="Output checker",
        purpose="Check anything headed to a teacher against the rubric and return a structured verdict.",
        model_env="MODEL_CHECK",
        when="everything headed to a teacher",
        output_model=schemas.Verdict,
        input_fields=("text", "audience", "language", "target_error", "code_checks"),
        validators=("verdict schema",),
        gates=("gate 2",),
        eval_id="eval_redteam",
        eval_bar="red-team set: 0 unsafe outputs reach a teacher",
        input="Candidate text, audience, language, target error, and what code already checked.",
        processing="A small model scores the rubric: tone, safety, stereotypes, language, fit, reading level, maths, statistics, injection.",
        guardrails="Includes rejected-before examples from reviewers; unsure means fail; a fail goes to a human or a template.",
        evaluation="Red-team set: 0 unsafe outputs reach a teacher.",
        output="A pass or fail verdict with a reason for the team and a one-line reason for the user.",
        live_turn=True,
    ),
    CallSpec(
        id=8,
        key="c08_answer_reading",
        name="Answer reading",
        purpose="Read the digits a child wrote on an answer-sheet photo, blind.",
        model_env="MODEL_READ",
        when="per sheet photo",
        output_model=schemas.SheetRead,
        input_fields=("photo",),
        validators=("digits only", "reads in expected set", "confidence floor"),
        gates=("read outside expected answers goes to the teacher",),
        eval_id="eval_answer_reading",
        eval_bar=">= 98% of auto-accepted reads correct; <= 15% sent to the teacher",
        input="One sheet photo (base64 JPEG). It carries no name or roll number. The model is never told the expected answers.",
        processing="A small vision model transcribes digits; a stronger model retries doubtful reads.",
        guardrails="Reads outside the correct and error answers, or below the confidence bar, go to the teacher; Devanagari digits normalised; the photo is deleted right after.",
        evaluation="Hand-keyed set: at least 98% of auto-accepted reads correct, at most 15% sent to the teacher.",
        output="Per-box digits for the engine to diagnose, on her phone.",
        metadata_only=True,
    ),
)

BY_ID: dict[int, CallSpec] = {c.id: c for c in CALLS}
BY_KEY: dict[str, CallSpec] = {c.key: c for c in CALLS}

assert set(DEFAULT_MODELS) >= {c.model_env for c in CALLS}
assert set(POLICIES) == set(BY_KEY)


def get_call(call: int | str) -> CallSpec:
    return BY_ID[call] if isinstance(call, int) else BY_KEY[call]
