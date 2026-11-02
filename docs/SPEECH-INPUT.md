# Speech input: what the voice-script call is sent

The call that writes the text sent to TTS (call 18, `ai/prompts/c18_module_narration.v2.md`) is sent an input built by code from the same module the screen shows. Code: `services/modules/speech_input.py`. Checks and fallback: `services/modules/speech_check.py`. Report of every built input: `docs/build/reports/SPEECH-INPUTS.md` (`python scripts/speech_inputs_report.py`, no AI or network call).

## The input

```
<facts>
{"language": "en", "title": "...", "module_number": 1, "module_count": 2, "step_count": 3}
</facts>
<module>
[purpose] What this does
...
</module>
```

- Facts, in this key order: language, title, module_number, module_count, step_count. `module_number` and `module_count` are the "Module n of N" label's own numbers and are both left out when unknown. `step_count` is present only when there are steps. The model call renders the facts with sorted keys (`ai/client.py`), so the model sees them in alphabetical order; the built text and the hash use the order above.
- Sections, in the order the screen shows them, only those with text: smaller_step, purpose, materials, steps, example, check. Each starts with `[tag] Heading`, the heading being the screen's heading in the module's language. Steps are one per line with no numbering. An unknown tag, a missing title, an unsupported language, or a module with neither purpose nor steps raises `SpeechInputError`; nothing partial is sent. Worked examples are not built for Hindi and Tamil (they are shown in English only).
- Cleaning of every field: markdown, HTML, emoji and other pictographs, zero-width and control characters are removed; link text is kept; spaces collapse; quotation marks, colons, plus, minus, equals, less-than, greater-than and digits stay. `<module>`, `</module>`, `<facts>`, `</facts>` are removed from content. Text such as "ignore previous instructions" is left as data. No UI-only strings were found in module text, so none are removed.
- Length: the limit is 4000 characters (longest today 933); longer raises, never truncates.
- Hash: SHA-256 of the text, the prompt version and the model id.

## Digit by digit

`content/speech/digit_readings.v1.yaml` lists, per module id (`PV-HEARD:ask_explain`), digit strings read digit by digit ("six zero two"). Whole-number matches are wrapped as `{digits:602}` in the text sent to the model (6020 and 1602 are not). Every other number is said as an ordinary number. To add an entry, add the module id and the exact string; an entry that matches nothing in the English module raises (stale). Only 602 in the explain-her-steps module is listed; the report lists every digit number and whether it is marked.

## Checks and fallback

- `check_speech_output(text, speech_input)` returns codes: digits, quotes, brackets, markup, pause_count, step_count, digits_reading, length (1.0 to 1.6 times the section words), opening ("first of two modules").
- `template_script` builds the English fallback from the same sections. Other languages have none.
- Today's wiring: the call returns one text per section and `narration.validate` checks it (parts present in order, numbers said in words, none added, length, no markup); `narration.run` retries once, then runs the pre-filter and call 7, then the code-built script is used. `check_speech_output` and `template_script` are built and tested but not wired, because the call does not return a whole script with `[pause]`.

## Not covered

Non-English fallback and number rules (Hindi and Tamil keep digits and the code script); content-owner review of which numbers are digit by digit; any listening test.
