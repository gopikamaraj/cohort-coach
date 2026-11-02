// The "Download audio" button. Nothing is made until it is pressed; then a progress line, a file
// download, and the file's size. It says the voice is AI-generated, and is switched off (with the
// reason) when the phone is offline.
import { useState } from "react";
import { runAction } from "../lib/action";
import { exportStem, fileName, makeAudio, PackAudioError, saveFile, sizeText, type AudioFailure, type AudioRequest, type Made } from "../lib/packAudio";
import { useApp } from "../state";
import type { Key } from "../i18n";

export function AudioDownload({
  request,
  language,
  code,
  section,
  label,
  note,
  testId,
  stem,
  onDone,
}: {
  request: Omit<AudioRequest, "name" | "language">; // her edited text, or the error and counts for the server to script
  language: string;
  code: string;
  section?: string;
  label: Key;
  note?: string; // what is in the file, under the button
  testId: string;
  stem?: string; // the file name when it is not the error's (a module's own)
  onDone?: (made: Made) => void | Promise<void>; // after the file is saved (a failure here never marks the audio failed)
}) {
  const { tr, online } = useApp();
  const [state, setState] = useState<"idle" | "busy" | "done" | "failed">("idle");
  const [done, setDone] = useState("");
  const [why, setWhy] = useState<AudioFailure>("other");

  async function press() {
    setState("busy");
    try {
      const name = stem ?? (section ? fileName(code, language, section) : exportStem(code, language));
      // one action: the click to the saved file, and every call the server made for it
      const made = await runAction("download_audio", async () => {
        const got = await makeAudio({ ...request, language, name });
        saveFile(got);
        return got;
      });
      try {
        await onDone?.(made);
      } catch {
        /* the file is saved; recording it can be tried again by the next press */
      }
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
        {state === "busy" ? tr("audio.preparing") : tr(label)}
      </button>
      {note ? <span className="muted pack-note">{note}</span> : null}
      <span id={`${testId}-note`} className="muted ai-voice">
        {offline ? tr("audio.offline") : tr("audio.ai_voice")}
      </span>
      {state === "busy" ? (
        <p role="status" className="sr-only" data-testid={`${testId}-busy`}>
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
