// The "Download audio" button. Nothing is made until it is pressed; then a progress line, a file
// download, and the file's size. It says the voice is AI-generated, and is switched off (with the
// reason) when the phone is offline.
import { useState } from "react";
import { fileName, makeAudio, PackAudioError, saveFile, sizeText, type AudioFailure } from "../lib/packAudio";
import { useApp } from "../state";
import type { Key } from "../i18n";

export function AudioDownload({
  text,
  language,
  code,
  section,
  label,
  testId,
}: {
  text: string;
  language: string;
  code: string;
  section?: string;
  label: Key;
  testId: string;
}) {
  const { tr, online } = useApp();
  const [state, setState] = useState<"idle" | "busy" | "done" | "failed">("idle");
  const [done, setDone] = useState("");
  const [why, setWhy] = useState<AudioFailure>("other");

  async function press() {
    setState("busy");
    try {
      const name = fileName(code, language, section);
      const made = await makeAudio({ text, language, name });
      saveFile(made);
      const s = sizeText(made.bytes);
      setDone(tr("audio.ready", { name: made.filename, size: tr(s.key, { n: s.n }) }));
      setState("done");
    } catch (e) {
      setWhy(e instanceof PackAudioError ? e.kind : "other");
      setState("failed");
    }
  }

  const offline = !online;
  return (
    <div className="audio-dl no-print" data-testid={`${testId}-box`}>
      <button type="button" className="btn btn-secondary" disabled={offline || state === "busy"} aria-describedby={`${testId}-note`} onClick={() => void press()} data-testid={testId}>
        {tr(label)}
      </button>
      <span id={`${testId}-note`} className="muted ai-voice">
        {offline ? tr("audio.offline") : tr("audio.ai_voice")}
      </span>
      {state === "busy" ? (
        <p role="status" data-testid={`${testId}-busy`}>
          {tr("audio.preparing")}
        </p>
      ) : null}
      {state === "done" ? (
        <p role="status" data-testid={`${testId}-done`}>
          {done}
        </p>
      ) : null}
      {state === "failed" ? (
        <p role="alert" data-testid={`${testId}-failed`}>
          {tr(why === "cap" ? "audio.cap" : "audio.failed")}{" "}
          {why !== "cap" ? (
            <button type="button" className="btn btn-secondary" onClick={() => void press()}>
              {tr("audio.retry")}
            </button>
          ) : null}
        </p>
      ) : null}
    </div>
  );
}
