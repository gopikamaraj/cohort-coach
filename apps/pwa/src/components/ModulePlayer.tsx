// Listen to a module in the browser. Nothing plays or is made until she presses Listen (no autoplay). The audio is
// the same file Download audio gives (made once by the server from the module's spoken text, then kept on this phone
// so it plays with no signal). Play and pause, a seek bar, the time and the length, three speeds, and Download. The
// first time it is started the server is told (a system fact: the player started; not that she listened to the end).
import { useEffect, useRef, useState } from "react";
import type { Key } from "../i18n";
import { makeAudio, PackAudioError, saveFile, type Made } from "../lib/packAudio";
import { useApp } from "../state";
import { Icon } from "./icons";

const SPEEDS = [0.75, 1, 1.25] as const;
const CACHE = "cc-module-audio";

const clock = (s: number): string => {
  const t = Math.max(0, Math.floor(Number.isFinite(s) ? s : 0));
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
};

async function keptCopy(key: string): Promise<Blob | null> {
  try {
    const hit = await (await caches.open(CACHE)).match(key);
    return hit ? await hit.blob() : null;
  } catch {
    return null; // no Cache API (private window): it is made again when she is online
  }
}

async function keepCopy(key: string, blob: Blob): Promise<boolean> {
  try {
    await (await caches.open(CACHE)).put(key, new Response(blob, { headers: { "Content-Type": "audio/mpeg" } }));
    return true;
  } catch {
    return false;
  }
}

export function ModulePlayer({
  text,
  language,
  stem,
  keyId,
  played,
  onPlayed,
  testId,
}: {
  text: string;
  language: string;
  stem: string; // the file name, without .mp3
  keyId: string; // what identifies this audio on the phone (track, module, language)
  played: boolean;
  onPlayed: () => void | Promise<void>; // told once, the first time it starts
  testId: string;
}) {
  const { tr, online } = useApp();
  const [state, setState] = useState<"idle" | "loading" | "ready" | "failed">("idle");
  const [why, setWhy] = useState<"offline" | "other">("other");
  const [url, setUrl] = useState<string | null>(null);
  const [made, setMade] = useState<Made | null>(null);
  const [kept, setKept] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [now, setNow] = useState(0);
  const [length, setLength] = useState(0);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const audio = useRef<HTMLAudioElement>(null);
  const told = useRef(played);
  const cacheKey = `https://cc.local/module-audio/${keyId}`;

  // a copy kept on this phone is found on arrival: it can be played with no signal (still not started by itself)
  useEffect(() => {
    let live = true;
    void keptCopy(cacheKey).then((b) => {
      if (!live || !b) return;
      setKept(true);
      setMade({ blob: b, filename: `${stem}.mp3`, bytes: b.size, seconds: 0, provider: "", cached: true });
    });
    return () => {
      live = false;
    };
  }, [cacheKey, stem]);

  useEffect(() => {
    if (!made) return;
    const u = URL.createObjectURL(made.blob);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [made]);

  useEffect(() => {
    if (audio.current) audio.current.playbackRate = speed;
  }, [speed, url]);

  async function load(): Promise<void> {
    if (made) {
      setState("ready");
      return;
    }
    setState("loading");
    try {
      const got = await makeAudio({ text, language, name: stem });
      setMade(got);
      setKept(await keepCopy(cacheKey, got.blob));
      setState("ready");
    } catch (e) {
      setWhy(e instanceof PackAudioError && e.kind === "offline" ? "offline" : "other");
      setState("failed");
    }
  }

  const ready = (state === "ready" || (made !== null && state === "idle")) && url !== null;
  const toggle = () => {
    const a = audio.current;
    if (!a) return;
    if (a.paused) void a.play();
    else a.pause();
  };

  return (
    <div className="module-player no-print" role="group" aria-label={tr("player.label")} data-testid={`${testId}-player`}>
      {!ready ? (
        <button type="button" className="btn btn-secondary" disabled={state === "loading" || (!online && !made)} onClick={() => void load()} data-testid={`${testId}-listen`}>
          <Icon name="play" size={18} /> {state === "loading" ? tr("player.loading") : tr("player.listen")}
        </button>
      ) : (
        <>
          <audio
            ref={audio}
            src={url ?? undefined}
            preload="metadata"
            onLoadedMetadata={(e) => setLength(e.currentTarget.duration)}
            onTimeUpdate={(e) => setNow(e.currentTarget.currentTime)}
            onPlay={() => {
              setPlaying(true);
              if (!told.current) {
                told.current = true;
                void onPlayed();
              }
            }}
            onPause={() => setPlaying(false)}
            onEnded={() => setPlaying(false)}
            data-testid={`${testId}-player-audio`}
          />
          <div className="row">
            <button type="button" className="btn btn-primary" onClick={toggle} aria-pressed={playing} aria-label={tr(playing ? "player.pause" : "player.play")} data-testid={`${testId}-toggle`}>
              <Icon name={playing ? "pause" : "play"} size={18} /> {tr(playing ? "player.pause" : "player.play")}
            </button>
            <span className="muted" data-testid={`${testId}-time`} aria-live="off">
              {clock(now)} / {clock(length)}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={Math.max(1, Math.floor(length))}
            step={1}
            value={Math.min(Math.floor(now), Math.max(1, Math.floor(length)))}
            aria-label={tr("player.seek")}
            aria-valuetext={`${clock(now)} / ${clock(length)}`}
            onChange={(e) => {
              if (audio.current) audio.current.currentTime = Number(e.target.value);
            }}
            data-testid={`${testId}-seek`}
          />
          <div className="row" role="radiogroup" aria-label={tr("player.speed")}>
            {SPEEDS.map((s) => (
              <button key={s} type="button" role="radio" aria-checked={speed === s} className={speed === s ? "btn btn-primary" : "btn btn-secondary"} onClick={() => setSpeed(s)} data-testid={`${testId}-speed-${s}`}>
                {s}x
              </button>
            ))}
            {made ? (
              <button type="button" className="btn btn-secondary" onClick={() => saveFile(made)} data-testid={`${testId}-save`}>
                {tr("player.download" as Key)}
              </button>
            ) : null}
          </div>
          {kept ? <p className="muted" data-testid={`${testId}-kept`}>{tr("player.kept")}</p> : null}
        </>
      )}
      <p className="muted ai-voice">{tr("audio.ai_voice")}</p>
      {state === "failed" ? (
        <p role="alert" data-testid={`${testId}-failed`}>
          {tr(why === "offline" ? "player.offline" : "player.failed")}
        </p>
      ) : null}
    </div>
  );
}
