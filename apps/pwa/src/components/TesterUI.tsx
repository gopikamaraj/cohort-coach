// Tester stats, the parts a person sees: the first-run name sheet, the Feedback button and sheet,
// the settings block, and the quiet tracker that turns route and role changes into events.
// All decisions (consent, queueing, sending) live in lib/tester.ts; nothing here can block a screen.
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import type { Key } from "../i18n";
import {
  TAGS, captureInvite, changeNickname, declineSharing, deleteMyData, durationBucket, getPrefs,
  giveConsent, markJudge, needsFirstRun, pauseSharing, queueFeedback, sharing, subscribePrefs, testerConfig, track, flush,
} from "../lib/tester";
import { useOnline } from "../lib/net";
import { useRoute } from "../lib/router";
import { useApp } from "../state";
import { getUser } from "../lib/identity";
import { SignInForm } from "./SignInForm";
import { Icon } from "./icons";
import { useToast } from "./toast";

const usePrefs = () => useSyncExternalStore(subscribePrefs, getPrefs, getPrefs);

function useEnabled(): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    let live = true;
    void testerConfig().then((c) => live && setOn(c.enabled));
    return () => {
      live = false;
    };
  }, []);
  return on;
}

function Sheet({ open, onClose, labelId, children, testid }: { open: boolean; onClose: () => void; labelId: string; children: React.ReactNode; testid: string }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} className="sheet" aria-labelledby={labelId} onClose={onClose} onClick={(e) => e.target === ref.current && onClose()} data-testid={testid}>
      {open ? <div className="sheet-body">{children}</div> : null}
    </dialog>
  );
}

function FirstRun({ onDone }: { onDone: () => void }) {
  const { tr } = useApp();
  const [name, setName] = useState("");
  const [share, setShare] = useState(true);
  const [pub, setPub] = useState(false);
  const ok = share && name.trim().length >= 1;
  const skip = () => {
    declineSharing();
    onDone();
  };
  return (
    <Sheet open onClose={skip} labelId="tester-first-title" testid="tester-first">
      <div className="sheet-head">
        <h2 id="tester-first-title">{tr("tester.first.title")}</h2>
      </div>
      <label className="field">
        <span>{tr("tester.first.name")}</span>
        <input type="text" value={name} maxLength={30} onChange={(e) => setName(e.target.value)} placeholder={tr("tester.first.name_hint")} data-testid="tester-name" autoComplete="off" />
      </label>
      <label className="switch">
        <input type="checkbox" checked={share} onChange={(e) => setShare(e.target.checked)} data-testid="tester-consent" />
        <span>{tr("tester.first.share")}</span>
      </label>
      <label className="switch">
        <input type="checkbox" checked={pub} onChange={(e) => setPub(e.target.checked)} data-testid="tester-public" />
        <span>{tr("tester.first.public")}</span>
      </label>
      <p className="muted">{tr("tester.first.warn")}</p>
      <div className="sheet-actions">
        <button
          type="button"
          className="m-btn m-btn-filled"
          disabled={!ok}
          onClick={() => {
            giveConsent(name, pub);
            onDone();
          }}
          data-testid="tester-save"
        >
          {tr("tester.first.save")}
        </button>
        <button type="button" className="m-btn m-btn-tonal" onClick={skip} data-testid="tester-skip">
          {tr("tester.first.skip")}
        </button>
      </div>
    </Sheet>
  );
}

function FeedbackSheet({ open, onClose, role, screen }: { open: boolean; onClose: () => void; role: string; screen: string }) {
  const { tr } = useApp();
  const online = useOnline();
  const prefs = usePrefs();
  const toast = useToast();
  const [rating, setRating] = useState(0);
  const [tags, setTags] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const on = sharing(prefs);
  useEffect(() => {
    if (open) {
      setRating(0);
      setTags([]);
      setComment("");
    }
  }, [open]);
  const toggle = (t: string) => setTags((cur) => (cur.includes(t) ? cur.filter((x) => x !== t) : cur.length < 3 ? [...cur, t] : cur));
  const send = () => {
    queueFeedback({ rating, tags, comment: comment.trim() || undefined, role, screen_id: screen });
    toast(tr(online ? "tester.fb.thanks" : "tester.fb.thanks_queued"), "ok");
    onClose();
  };
  return (
    <Sheet open={open} onClose={onClose} labelId="tester-fb-title" testid="tester-fb-sheet">
      <div className="sheet-head">
        <h2 id="tester-fb-title">{tr("tester.fb.title")}</h2>
      </div>
      {!on ? (
        <>
          <p role="status">{tr("tester.fb.off")}</p>
          <div className="sheet-actions">
            <button type="button" className="m-btn m-btn-tonal" onClick={onClose}>
              {tr("common.close")}
            </button>
          </div>
        </>
      ) : (
        <>
          <fieldset className="fb-group">
            <legend>{tr("tester.fb.rating")}</legend>
            <div className="fb-stars">
              {[1, 2, 3, 4, 5].map((n) => (
                <button key={n} type="button" className={rating === n ? "fb-star fb-on" : "fb-star"} aria-pressed={rating === n} aria-label={tr("tester.fb.star", { n })} onClick={() => setRating(n)} data-testid={`tester-star-${n}`}>
                  {n}
                </button>
              ))}
            </div>
          </fieldset>
          <fieldset className="fb-group">
            <legend>{tr("tester.fb.tags")}</legend>
            <div className="fb-tags">
              {TAGS.map((t) => (
                <button key={t} type="button" className={tags.includes(t) ? "fb-tag fb-on" : "fb-tag"} aria-pressed={tags.includes(t)} onClick={() => toggle(t)} data-testid={`tester-tag-${t}`}>
                  {tr(`tester.tag.${t}` as Key)}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="field">
            <span>{tr("tester.fb.comment")}</span>
            <textarea value={comment} maxLength={500} rows={3} onChange={(e) => setComment(e.target.value)} data-testid="tester-comment" />
          </label>
          <p className="muted">{tr("tester.first.warn")}</p>
          <div className="sheet-actions">
            <button type="button" className="m-btn m-btn-filled" disabled={rating === 0} onClick={send} data-testid="tester-fb-send">
              {tr("tester.fb.send")}
            </button>
            <button type="button" className="m-btn m-btn-tonal" onClick={onClose}>
              {tr("common.close")}
            </button>
          </div>
        </>
      )}
    </Sheet>
  );
}

/** Mounted once in the shell. Renders nothing at all unless the server has the feature on. */
/** The nickname pop-up: opens on the role picker until a nickname is set, and from the title bar's nickname button. */
const subscribeIdentity = (cb: () => void) => {
  window.addEventListener("cc:identity", cb);
  return () => window.removeEventListener("cc:identity", cb);
};

export function NicknameRoot() {
  const { tr } = useApp();
  const route = useRoute();
  const user = useSyncExternalStore(subscribeIdentity, getUser, getUser);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const show = () => setOpen(true);
    document.addEventListener("cc:nickname", show);
    return () => document.removeEventListener("cc:nickname", show);
  }, []);
  useEffect(() => {
    if (route !== "/roles" || user) return;
    let asked = false;
    try {
      asked = sessionStorage.getItem("cc.nick.asked") === "1";
    } catch {
      /* no storage: ask again next time */
    }
    if (asked) return;
    try {
      sessionStorage.setItem("cc.nick.asked", "1");
    } catch {
      /* ignore */
    }
    setOpen(true);
  }, [route, user]);
  const done = () => setOpen(false);
  if (!open) return null;
  return (
    <Sheet open onClose={done} labelId="nick-pop-title" testid="nickname-popup">
      <div className="sheet-head">
        <h2 id="nick-pop-title">{tr("signin.title")}</h2>
      </div>
      <SignInForm onDone={done} testid="nickname-popup" />
      {user ? null : (
        <div className="sheet-actions">
          <button type="button" className="m-btn m-btn-tonal" onClick={done} data-testid="nickname-popup-later">
            {tr("profile.nickname_later")}
          </button>
        </div>
      )}
    </Sheet>
  );
}

export function TesterRoot() {
  const enabled = useEnabled();
  const { role, lang } = useApp();
  const route = useRoute();
  const prefs = usePrefs();
  const online = useOnline();
  const [first, setFirst] = useState(false);
  const [fb, setFb] = useState(false);
  const entered = useRef({ screen: "", at: Date.now() });
  const started = useRef(Date.now());
  const sawRole = useRef(false);
  const lastRole = useRef<string | null>(null);
  const wasOffline = useRef(false);

  useEffect(() => {
    captureInvite();
    const again = () => captureInvite(); // an invite link opened in a page that is already running
    window.addEventListener("hashchange", again);
    return () => window.removeEventListener("hashchange", again);
  }, []);
  useEffect(() => {
    if (!enabled) return;
    void needsFirstRun().then(setFirst);
  }, [enabled]);
  useEffect(() => {
    if (role === "judge") markJudge();
  }, [role]);
  useEffect(() => {
    const open = () => setFirst(true); // "Turn on sharing" in My profile
    document.addEventListener("cc:tester-first-run", open);
    return () => document.removeEventListener("cc:tester-first-run", open);
  }, []);

  // Screen views carry the time spent on the screen, so one event is sent when the person leaves it.
  useEffect(() => {
    if (!enabled) return;
    const screen = route.slice(1);
    if (entered.current.screen && entered.current.screen !== screen) {
      track("screen_viewed", { screen_id: entered.current.screen, role, value: { t: durationBucket(Date.now() - entered.current.at) } });
    }
    if (entered.current.screen !== screen) entered.current = { screen, at: Date.now() };
    if (!sawRole.current && screen !== "roles" && screen !== "judge") {
      sawRole.current = true;
      track("role_selected", { role });
    }
  }, [route, enabled, role]);
  useEffect(() => {
    if (!enabled) return;
    if (lastRole.current !== null && lastRole.current !== role) {
      sawRole.current = true;
      track(route === "/roles" ? "role_selected" : "view_as_role", { role });
    }
    lastRole.current = role;
  }, [role, enabled, route]);
  useEffect(() => {
    if (!online) wasOffline.current = true;
  }, [online]);

  // Session end: on hide or close. The batch goes with keepalive so it survives the tab closing.
  useEffect(() => {
    if (!enabled) return;
    const end = () => {
      if (document.visibilityState !== "hidden") return;
      const { screen, at } = entered.current;
      if (screen) track("screen_viewed", { screen_id: screen, role, value: { t: durationBucket(Date.now() - at) } });
      track("offline_session", { value: { offline: wasOffline.current } });
      track("session_end", { value: { d: durationBucket(Date.now() - started.current) } });
      void flush(undefined, undefined, true);
    };
    document.addEventListener("visibilitychange", end);
    return () => document.removeEventListener("visibilitychange", end);
  }, [enabled, role]);
  useEffect(() => {
    if (enabled && online) void flush();
  }, [enabled, online, prefs.consent]);
  useEffect(() => {
    if (enabled && sharing()) track("session_start", { value: { lang } });
    // once per page load, after the choice is known
  }, [enabled]);

  if (!enabled) return null;
  return (
    <>
      {first ? <FirstRun onDone={() => setFirst(false)} /> : null}
      <FeedbackButton onOpen={() => setFb(true)} />
      <FeedbackSheet open={fb} onClose={() => setFb(false)} role={role} screen={route.slice(1)} />
    </>
  );
}

function FeedbackButton({ onOpen }: { onOpen: () => void }) {
  const { tr } = useApp();
  return (
    <button type="button" className="fb-fab" onClick={onOpen} data-testid="tester-fb-open">
      <Icon name="chat" size={20} />
      <span>{tr("tester.fb.button")}</span>
    </button>
  );
}

/** The settings block on My profile. */
export function TesterSettings() {
  const { tr } = useApp();
  const enabled = useEnabled();
  const prefs = usePrefs();
  const toast = useToast();
  const [name, setName] = useState(prefs.nickname);
  const [pub, setPub] = useState(prefs.isPublic);
  const [confirm, setConfirm] = useState(false);
  if (!enabled) return null;
  const stateKey: Key = prefs.consent !== "yes" ? "tester.set.off" : prefs.paused ? "tester.set.paused" : "tester.set.on";
  return (
    <section className="panel" aria-labelledby="tester-set-title" data-testid="tester-settings">
      <h2 id="tester-set-title">
        <Icon name="info" /> <span>{tr("tester.set.title")}</span>
      </h2>
      <p role="status">{tr(stateKey)}</p>
      {prefs.consent === "yes" ? (
        <>
          <label className="field">
            <span>{tr("tester.first.name")}</span>
            <input type="text" value={name} maxLength={30} onChange={(e) => setName(e.target.value)} data-testid="tester-set-name" />
          </label>
          <label className="switch">
            <input type="checkbox" checked={pub} onChange={(e) => setPub(e.target.checked)} />
            <span>{tr("tester.first.public")}</span>
          </label>
          <div className="stack">
            <button type="button" className="btn btn-secondary" disabled={!name.trim()} onClick={() => changeNickname(name, pub)} data-testid="tester-set-save">
              {tr("tester.set.update")}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => pauseSharing(!prefs.paused)} data-testid="tester-pause">
              {tr(prefs.paused ? "tester.set.resume" : "tester.set.pause")}
            </button>
          </div>
        </>
      ) : (
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => {
            setName(prefs.nickname);
            document.dispatchEvent(new CustomEvent("cc:tester-first-run"));
          }}
          data-testid="tester-turn-on"
        >
          {tr("tester.set.start")}
        </button>
      )}
      <button
        type="button"
        className="btn btn-secondary"
        onClick={() => {
          if (!confirm) return setConfirm(true);
          setConfirm(false);
          void deleteMyData().then((r) => toast(tr(r === "deleted" ? "tester.set.deleted" : "tester.set.deleted_device"), "ok"));
        }}
        data-testid="tester-delete"
      >
        {confirm ? tr("tester.set.delete_confirm") : tr("tester.set.delete")}
      </button>
    </section>
  );
}
