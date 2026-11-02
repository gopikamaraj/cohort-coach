import { useEffect, useState } from "react";
import { useApp } from "../state";
import { saveLesson, savedBlob } from "../lib/lessonAudio";

/** A lesson's audio player with one extra tap: keep it on this phone so it plays with no signal. */
export function LessonAudio({ url }: { url: string }) {
  const { tr } = useApp();
  const [local, setLocal] = useState<string | null>(null);
  const [state, setState] = useState<"idle" | "saving" | "failed">("idle");

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

  return (
    <div>
      <audio controls preload="none" src={local ?? url} data-testid="flow-audio" style={{ width: "100%" }} />
      {local ? (
        <p className="muted" data-testid="flow-audio-saved">{tr("flow.saved_offline")}</p>
      ) : (
        <button type="button" className="btn btn-secondary" disabled={state === "saving"} onClick={() => void save()} data-testid="flow-audio-save">
          {state === "saving" ? tr("flow.saving") : tr("flow.save_offline")}
        </button>
      )}
      {state === "failed" ? <p role="alert" className="muted">{tr("flow.save_failed")}</p> : null}
    </div>
  );
}
