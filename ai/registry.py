"""The single source of truth for the Claude calls.

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
    CallSpec(
        id=10,
        key="c10_demo_teacher",
        name="Demo teacher (judge mode only)",
        purpose="Play the teacher in a Practice Class Watch run, in an experienced or a struggling style, so a visitor can compare.",
        model_env="MODEL_DEMO_TEACHER",
        when="live Watch run in judge mode",
        output_model=schemas.DemoTeacherTurn,
        input_fields=("scenario", "style", "approved_moves", "transcript", "engine_state"),
        validators=(
            "move id approved",
            "length",
            "numbers from the scenario",
            "no answer leak",
            "no check item",
            "prefilter",
        ),
        gates=("code validators", "pre-filter", "judge session only"),
        eval_id="eval_demo_teacher",
        eval_bar="20 runs per style: 100% approved move ids; 0 numbers outside the allowed set; experienced beats struggling in >= 18 of 20 pairs",
        input="The scenario, the approved move list, the style, the transcript so far and the engine's state of the five simulated children.",
        processing="A small model picks one approved move and writes a line of at most 25 words in the chosen style.",
        guardrails="The move id must be on the approved list for the style; every number must come from the scenario's allowed set; no answer leak beyond the style; no check item; on any failure the move's template line is used. The server refuses the call outside a judge session.",
        evaluation="20 runs per style: approved ids 100%, numbers in the allowed set, and the experienced runs cover more rubric points than the struggling runs in at least 18 of 20 pairs (rubric coverage is internal to the eval, never shown to a teacher).",
        output="A teacher line labelled 'AI playing the teacher (demo only)'; never shown to a real teacher, who hears the reviewed model run.",
        metadata_only=True,
        live_turn=True,
    ),
    CallSpec(
        id=11,
        key="c11_sprite_author",
        name="Sprite item author (offline)",
        purpose="Draft the JSON spec of one new sprite item (a counted object) for a topic pack, at authoring time only.",
        model_env="MODEL_SPRITE",
        when="offline authoring",
        output_model=schemas.SpriteItemDraft,
        input_fields=("brief", "existing_item_ids"),
        validators=(
            "id not taken",
            "grammar whitelist",
            "size budget",
            "no text",
            "palette slots only",
            "contact tile renders",
            "prefilter",
            "no check item",
        ),
        gates=(
            "code validators",
            "pre-filter",
            "call 7 (words)",
            "coach approval",
            "officer enablement",
        ),
        eval_id="eval_sprite_author",
        eval_bar="pending: no live run yet; every draft must pass all code gates before a coach sees it",
        input="A short brief for one object (for example 'a mango') and the ids of the items that exist.",
        processing="Claude drafts one item as a list of whitelisted shapes with integer numbers and palette-slot colours, plus a short English alt text.",
        guardrails="Schema; shape and attribute whitelist; integer numbers; palette slots only (no hex); size budget; no text; the item must render at counts 1 and 5 in every palette and as a PNG; pre-filter and no-check-item checks on the words; call 7 on the words; a rejected draft returns the failing rule to the author and is never shown; then a coach approves and a programme officer enables.",
        evaluation="Pending a live run. Until then the gates are proven by tests: each rule has a failing case.",
        output="A draft item file in content/sprites/drafts/, not loaded by the renderer. It reaches a teacher only inside an enabled pack version. No art is generated at run time.",
    ),
    CallSpec(
        id=12,
        key="c12_chat_classify",
        name="Chat question class",
        purpose="Decide what kind of question a teacher asked her mentor, so the right people see it first.",
        model_env="MODEL_CHAT_CLASS",
        when="when a teacher ticks AI help and sends a question",
        output_model=schemas.ChatClass,
        input_fields=("language", "masked_question"),
        validators=("schema", "confidence floor", "safety words in code first"),
        gates=("names masked before the call", "safety and welfare words never reach the model"),
        eval_id="eval_chat_redteam",
        eval_bar="red team: 0 unsafe answers sent on their own; safety words always reach the coach",
        input="The question with names, roll numbers and phone numbers already replaced, and its language.",
        processing="A small model picks one of six labels with a confidence; below 0.6 the question counts as unclear.",
        guardrails="Code checks safety and welfare words first and routes those to the coach without any model call; a replaced child name makes it child-specific; the question is data, never an instruction; any failure means unclear.",
        evaluation="The 50-prompt chat red team (injection, child-specific, safety, off-topic, Tamil, Hindi and English mixing) must send nothing unsafe on its own.",
        output="One label that decides who sees the question and whether a draft is made.",
    ),
    CallSpec(
        id=13,
        key="c13_chat_reply",
        name="Chat reply draft",
        purpose="Draft a short reply to a teacher's question from approved material only, for her mentor to send, change or replace.",
        model_env="MODEL_CHAT",
        when="when a teacher ticks AI help and the question is about teaching",
        output_model=schemas.ChatReply,
        input_fields=("language", "error", "sources", "masked_question"),
        validators=(
            "citations present and verbatim",
            "at most 120 words",
            "arithmetic",
            "no personal data",
            "no class numbers",
            "no pilot test item",
            "no scores",
        ),
        gates=(
            "code validators",
            "pre-filter",
            "call 7",
            "mentor or coach sends it, or the auto-send gates pass",
        ),
        eval_id="eval_chat_redteam",
        eval_bar="red team: 0 unsafe answers sent on their own; arithmetic 100%; every citation verbatim",
        input="The masked question, the language, her cohort's error and the approved sentences retrieved for it (approved lessons and strategies).",
        processing="The model writes at most 120 words and must quote the approved sentence behind each statement, or return no answer and why.",
        guardrails="Every citation must name a retrieved source and quote it word for word; code checks sums, personal data, class numbers, pilot items and scores; call 7 checks tone and fit; it is a draft until a person sends it. It goes out on its own only if every auto-send gate passes, labelled as AI-generated.",
        evaluation="Share of drafts sent as is, edited or discarded, and corrections after an automatic send, reported by code in docs/evidence/chat_metrics.json (simulated data in the demo).",
        output="A draft in the mentor's inbox with its sources; to the teacher only through a person or the auto-send gates, with a label.",
    ),
    CallSpec(
        id=14,
        key="c14_assistant_answer",
        name="Assistant answer",
        purpose="Answer one question for one role from the passages that role may read, with sources, or say there is no answer.",
        model_env="MODEL_ASSIST",
        when="when a user types a free-text question to the assistant (suggested questions are pre-written)",
        output_model=schemas.AssistantAnswer,
        input_fields=("role", "language", "passages", "question"),
        validators=(
            "citations present and verbatim",
            "rubric rows offered",
            "at most 120 words",
            "no personal data",
            "no scores or ranking",
            "no claim of an action",
            "no pressure words",
        ),
        gates=(
            "scope set by the server from the authenticated role",
            "retrieval only inside the role's namespaces",
            "code validators",
        ),
        eval_id="eval_assistant",
        eval_bar="per role: 10 on-scope, 3 leak probes, 3 out-of-scope; judge: 30 rubric-aligned; 0 leaks; every citation verbatim",
        input="The question (wrapped as data), the role, the language, and up to six passages retrieved from the role's own namespaces, with rubric rows for the judge.",
        processing="A mid-tier model writes at most 120 words from the passages, cites each with a verbatim quote, and names the rubric rows it rests on, or returns no answer and why.",
        guardrails="The scope comes from the server, never the prompt; retrieval cannot reach another role's namespace; code checks every quote word for word, the rubric rows, length, personal data, scores, claims of action and pressure words; the status labels, how to check and limits come from the rubric map, not the model; any failure falls back to an extract from the passages or to no answer.",
        evaluation="evals/assistant_eval.md: retrieval, scope and citation checks per role by code; the model's wording is not scored there (pending a live run).",
        output="An answer with status labels, sources (file, slide, video), how to check it and its limits; or an abstention that says what the assistant can help with.",
    ),
)

BY_ID: dict[int, CallSpec] = {c.id: c for c in CALLS}
BY_KEY: dict[str, CallSpec] = {c.key: c for c in CALLS}

assert set(DEFAULT_MODELS) >= {c.model_env for c in CALLS}
assert set(POLICIES) == set(BY_KEY)


def get_call(call: int | str) -> CallSpec:
    return BY_ID[call] if isinstance(call, int) else BY_KEY[call]
