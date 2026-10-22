# AI gaps: report (22 Oct 2026)

Goal: every AI claim points to a file, and nothing is claimed that is not built. Product behaviour is unchanged; this work touched docs, specs, two scripts and one test.

## Step 0: what the docs confirmed or contradicted

All facts read from platform.claude.com on 22 Oct and recorded with URLs in `docs/build/DECISIONS.md` (two entries dated 22 Oct).

| Question | Finding | Matches CLAUDE.md and BUILD_PROMPTS? |
| --- | --- | --- |
| Citations request and document types | `citations.enabled` on each document; plain text (`char_location`), PDF (`page_location`), custom content (`content_block_location`, 0-indexed, end exclusive, blocks used as-is) | New, no conflict |
| Models | Opus 5.5, Sonnet 5.5 and Haiku 5.5 are active; "all active models support citations" | New, no conflict |
| Citations with structured output | **Not combinable: the API returns a 400.** Re-confirmed live by `scripts/ai_proof.py` | **Contradicts** the kit's "every call uses structured outputs"; fixed (two passes) |
| Citations in batches and with caching | Documented only as one general sentence ("work in conjunction with ... prompt caching, token counting, and batch processing"); source documents can be cached, the response's citation blocks cannot | New. Citations inside a batch are not tested separately: first use in P09 falls back to a synchronous pass if refused |
| Cache minimum and usage fields | 512 tokens on all three models; `cache_creation_input_tokens` and `cache_read_input_tokens` in `usage`; 0.05x read price on Opus and Sonnet | Matches |
| Thinking and effort | `thinking: {type: adaptive}`; effort `output_config.effort` with five levels; defaults Opus medium, Sonnet high, Haiku medium; Opus 5.5 cannot disable thinking | Matches |

## Files changed

- New: `AI_USAGE.md`, `scripts/ai_proof.py`, `scripts/gen_ai_usage.py`, `tests/test_ai_usage_doc.py`, `docs/evidence/ai_usage_proof.json` (written by the script), this report.
- Edited (docs only): `CLAUDE.md` (call 4 and 5 rows, the citations exception to "use structured outputs", rule 16, repo map), `docs/design/cohort-coach-design.md` (calls 4 and 5, a "Citations" note), `docs/build/BUILD_PROMPTS.md` (P03, P09, P11, P16 blocks and acceptance), `docs/build/DECISIONS.md`, `docs/build/PROGRESS.md`, `README.md` (one pointer), `.claude/agents/judge-reviewer.md`, `.claude/agents/integrity-auditor.md`.
- Not edited: `ai/registry.py`. Its entries for calls 4 and 5 must not claim citations until the code parses them (tasks C4-3 and C5-4).

## The design in one paragraph

Call 4 pass A sends the mentor's corrected transcript as a custom-content document, one block per sentence, so a citation's block index is our sentence id; no schema, a fixed line format; code rebuilds the lines from the text blocks and citations and fills the card; a line with no valid citation is rejected and logged. Call 5 pass 1 is the structured draft; pass 2 adds "Why this move" lines with citations over six cached evidence documents, and the page shown comes from a code table, never from model text; uncited lines are dropped; IDR and APU citations are labelled opinion. The old validators and call 7 stay as the independent check.

## Capability status (from `AI_USAGE.md`)

| Capability | Status |
| --- | --- |
| Vision (call 8) | Verified |
| Structured outputs | Verified |
| Prompt caching | Verified |
| LLM-simulated children (1, 2) | Built |
| Classification into a fixed taxonomy (2) | Built |
| LLM as checker (7) | Built |
| Reflective feedback (3) | Built |
| Model tiering | Built |
| Effort and thinking settings | Built |
| Untrusted-text tagging | Built |
| Speech in and out | Built |
| Claude Code with subagents (used to build) | Built |
| Citations API (calls 4, 5) | Specified (the API-level check passed; the product code is not built) |
| Message Batches (call 5) | Specified (the API-level check passed; `batch_draft` is not built) |
| Meshy MCP | Specified (parked; authoring time only) |

## The proof run

`python scripts/ai_proof.py` on 22 Oct (about USD 0.10, synthetic inputs): caching PASS (2,114 tokens written, then read), structured output PASS (calls 2, 7 and 8, no retry), citations PASS (sentence ids 0 to 3 all resolved; the structured-output refusal observed), batches PASS (a 2-request batch ended with 2 succeeded; the first run timed out at 120 s and the second resumed the same batch), image input PASS (10 of 10 boxes read with confidence on `SIM_COV_H06.jpg`, none differing from the manifest truth). Details and ids: `docs/evidence/ai_usage_proof.json`.

## What I could not verify, and why

- Citations inside a Message Batch: the docs say it in one general sentence and the batch page is silent; not tested here (no call 5 pass 2 exists yet). The fallback is a synchronous pass.
- Citation quality on real mentor speech: the proof used four made-up sentences. Real mentor transcripts arrive with P11 round 4; until then the claim is the request shape and the code rules, not accuracy.
- The red-team and eval results for call 7 and call 10 are pending P13, so `AI_USAGE.md` does not call them Verified.
- The cost-per-teacher script and assumptions file named in the design do not exist yet (P13); section 8 of `AI_USAGE.md` says so.
