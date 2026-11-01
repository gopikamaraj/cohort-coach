import { useEffect, useRef, useState } from "react";
import { useApp } from "../state";
import { saveLesson, savedBlob, sentenceAt, sizeLabel, type AudioInfo } from "../lib/lessonAudio";

/** A lesson's audio player with one extra tap: keep it on this phone so it plays with no signal.
 * With `info`, it says the voice is AI-generated, shows the file size on the Save button, and
 * highlights each sentence of the lesson as it is said (times come from the server). */
export function LessonAudio({ url, info }: { url: string; info?: AudioInfo | null }) {
  const { tr } = useApp();
  const [local, setLocal] = useState<string | null>(null);
  const [state, setState] = useState<"idle" | "saving" | "failed">("idle");
  const [now, setNow] = useState<number | null>(null);
  const player = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    let made: string | null = null;
    let live = true;
    setLocal(null);
    setState("idle");
    void savedBlob(url).then((blob) => {
      if (blob && live) {
        made = URL.createObjectURL(blob);
        setLocal(made);
      }
    });
    return () => {
      live = false;
      if (made) URL.revokeObjectURL(made);
    };
  }, [url]);

  async function save() {
    setState("saving");
    if (await saveLesson(url)) {
      const blob = await savedBlob(url);
      if (blob) setLocal(URL.createObjectURL(blob));
      setState("idle");
    } else setState("failed");
  }

  const follow = info && info.sentences.length > 0 && info.timing.length > 0;
  return (
    <div>
      {info?.ai_voice ? (
        <p className="muted ai-voice" data-testid="flow-ai-voice">
          {tr("flow.ai_voice")}
        </p>
      ) : null}
      <audio
        ref={player}
        controls
        preload="none"
        src={local ?? url}
        data-testid="flow-audio"
        style={{ width: "100%" }}
        onTimeUpdate={() => follow && setNow(sentenceAt(info.timing, player.current?.currentTime ?? 0))}
        onEnded={() => setNow(null)}
      />
      {follow ? (
        <div className="say-along" data-testid="flow-sentences">
          {info.sentences.map((s, i) => (
            <span key={i} className={now === i ? "say say-on" : "say"} aria-current={now === i ? "true" : undefined} data-testid={`flow-sentence-${i}`}>
              {s}{" "}
            </span>
          ))}
        </div>
      ) : null}
      {local ? (
        <p className="muted" data-testid="flow-audio-saved">{tr("flow.saved_offline")}</p>
      ) : (
        <button type="button" className="btn btn-secondary" disabled={state === "saving"} onClick={() => void save()} data-testid="flow-audio-save">
          {state === "saving" ? tr("flow.saving") : info?.bytes ? tr("flow.save_offline_size", { size: sizeLabel(info.bytes) }) : tr("flow.save_offline")}
        </button>
      )}
      {state === "failed" ? <p role="alert" className="muted">{tr("flow.save_failed")}</p> : null}
    </div>
  );
}
