// Testing only (DEV_TESTING=1): "Download all audios" makes and saves the audio of every module made so far,
// one after the other, so the voice can be checked without opening each module. It does not mark a module
// downloaded. Hidden unless the caller shows it.
import { useState } from "react";
import type { TrackView } from "../lib/modules";
import { exportStem, makeAudio, saveFile } from "../lib/packAudio";
import { useApp } from "../state";

export function DevAudioAll({ track, code }: { track: TrackView | null; code: string }) {
  const { tr, online } = useApp();
  const [state, setState] = useState<"idle" | "busy" | "done" | "failed">("idle");
  const [at, setAt] = useState(0);
  const [saved, setSaved] = useState(0);
  const mods = (track?.modules ?? []).filter((m) => m.spoken);

  async function press() {
    setState("busy");
    setSaved(0);
    try {
      for (const [i, m] of mods.entries()) {
        setAt(i + 1);
        const language = m.language ?? track?.language ?? "en";
        saveFile(await makeAudio({ text: m.spoken as string, language, name: exportStem(code, language, `Improvement-Track-Module-${m.number}`) }));
        setSaved(i + 1);
      }
      setState("done");
    } catch {
      setState("failed");
    }
  }

  return (
    <div className="audio-dl no-print" data-testid="pack-audio-all-box">
      <button type="button" className="btn btn-secondary" disabled={!online || state === "busy" || mods.length === 0} onClick={() => void press()} data-testid="pack-audio-all">
        {tr("audio.dev_all")}
      </button>
      {mods.length === 0 ? <span className="muted pack-note">{tr("audio.dev_all_none")}</span> : null}
      {state === "busy" ? (
        <p role="status" data-testid="pack-audio-all-busy">
          {tr("audio.dev_all_progress", { n: at, total: mods.length })}
        </p>
      ) : null}
      {state === "done" ? (
        <p role="status" data-testid="pack-audio-all-done">
          {tr("audio.dev_all_done", { n: saved })}
        </p>
      ) : null}
      {state === "failed" ? (
        <p role="alert" data-testid="pack-audio-all-failed">
          {tr("audio.failed")}
        </p>
      ) : null}
    </div>
  );
}
