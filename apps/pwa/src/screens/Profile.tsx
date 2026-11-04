// My profile: who I am here (role, language), my classes, my data (storage, backup, data used) and my
// privacy choices. Everything here is about this phone; nothing is sent unless a button says so.
import { dismissConflict, listConflicts, type Conflict } from "../lib/cloudStore";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { IconButton, Icon } from "../components/icons";
import { useToast } from "../components/toast";
import { buildBackup, openBackup, restoreBackup, sealBackup } from "../lib/backup";
import { addClass, deleteClass, listClasses, renameClass, setActive, type ClassItem } from "../lib/classes";
import { setConsent, getConsent, withdrawAll, recordOnServer, type Choices, type Scope, countsOn } from "../lib/consent";
import { clearCloud } from "../lib/cloudStore";
import { clearPhone, db } from "../lib/db";
import { footerAllowed, footerOn, setFooterOn, subscribe } from "../lib/action";
import { costOf, getPrice, getUsage, resetUsage, setPrice, type Usage } from "../lib/meter";
import { persistenceStatus, requestPersistence, type PersistenceStatus } from "../lib/storage";
import { href } from "../lib/router";
import { sendFeedback, type FeedbackKind } from "../lib/feedback";
import { LANG_NAMES, LANGS, isLang } from "../i18n";
import { InstallEntry } from "../components/install";
import { TesterSettings } from "../components/TesterUI";
import { useApp } from "../state";
import { SignInForm } from "../components/SignInForm";
import { useConsent } from "../lib/useConsent";

const mb = (n: number) => (n / 1_000_000).toFixed(1);
const bytes = (n: number) => (n < 1_000_000 ? `${(n / 1000).toFixed(n < 10_000 ? 1 : 0)} KB` : `${(n / 1_000_000).toFixed(2)} MB`);

/** A nickname for this phone: shown after "Viewing as" in the title bar, so two teachers on two phones are told apart. */
function NicknameField() {
  const { tr } = useApp();
  return (
    <section className="panel" aria-labelledby="nick-title" data-testid="nickname-panel">
      <h2 id="nick-title">{tr("signin.title")}</h2>
      <SignInForm testid="nickname-panel-form" />
    </section>
  );
}

function Section({ icon, title, children, id }: { icon: string; title: string; children: React.ReactNode; id: string }) {
  return (
    <section className="panel" aria-labelledby={id} data-testid={id}>
      <h2 id={id}>
        <Icon name={icon} /> <span>{title}</span>
      </h2>
      {children}
    </section>
  );
}

function Classes() {
  const { tr, reload } = useApp();
  const toast = useToast();
  const [items, setItems] = useState<ClassItem[]>([]);
  const [name, setName] = useState("");
  const refresh = useCallback(async () => setItems(await listClasses()), []);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  const after = async () => {
    await refresh();
    await reload();
  };
  return (
    <Section icon="users" title={tr("profile.classes")} id="pf-classes">
      <ul className="plain">
        {items.map((c) => (
          <li key={c.id} className={c.active ? "class-row class-active" : "class-row"} data-testid="class-row">
            <span className="class-name">
              <strong>{c.name}</strong>
              {c.simulated ? <span className="chip">{tr("profile.simulated")}</span> : null}
              {c.active ? <span className="chip chip-positive">{tr("profile.active")}</span> : null}
            </span>
            <span className="row-actions">
              {!c.active ? <IconButton icon="ok" label={tr("profile.use_class")} iconOnly testId="class-use" onClick={() => void setActive(c.id).then(after)} /> : null}
              <IconButton
                icon="edit"
                label={tr("profile.rename")}
                iconOnly
                testId="class-rename"
                onClick={() => {
                  const next = window.prompt(tr("profile.rename"), c.name);
                  if (next) void renameClass(c.id, next).then(after);
                }}
              />
              <IconButton
                icon="trash"
                label={tr("profile.delete_class")}
                iconOnly
                variant="danger"
                testId="class-delete"
                onClick={() => {
                  if (window.confirm(tr("profile.delete_class_confirm", { name: c.name }))) void deleteClass(c.id).then(after).then(() => toast(tr("profile.class_deleted"), "ok"));
                }}
              />
            </span>
          </li>
        ))}
      </ul>
      <form
        className="inline-form"
        onSubmit={(e) => {
          e.preventDefault();
          const wanted = name;
          if (!wanted.trim()) return;
          setName(""); // clear at once, so a quick second entry is not wiped when the first finishes saving
          void addClass(wanted, false).then(after);
        }}
      >
        <label className="sr" htmlFor="new-class">
          {tr("profile.class_name")}
        </label>
        <input id="new-class" value={name} maxLength={40} placeholder={tr("profile.class_name")} onChange={(e) => setName(e.target.value)} data-testid="class-name" />
        <IconButton icon="plus" label={tr("profile.add_class")} type="submit" variant="primary" testId="class-add" />
      </form>
      <p className="muted">{tr("profile.classes_note")}</p>
    </Section>
  );
}

function Storage() {
  const { tr, reload } = useApp();
  const toast = useToast();
  const [st, setSt] = useState<PersistenceStatus | null>(null);
  const [pass, setPass] = useState("");
  const file = useRef<HTMLInputElement>(null);
  const refresh = useCallback(async () => setSt(await persistenceStatus()), []);
  useEffect(() => {
    void refresh();
  }, [refresh]);

  const exportNow = async () => {
    const b = await buildBackup();
    const text = pass ? await sealBackup(b, pass) : JSON.stringify(b);
    const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `cohort-coach-backup-${new Date().toISOString().slice(0, 10)}${pass ? "-sealed" : ""}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast(tr("profile.exported"), "ok");
  };
  const restore = async (f: File) => {
    try {
      const res = await restoreBackup(await openBackup(await f.text(), pass));
      await reload();
      toast(tr("profile.restored", { classes: res.classes, checks: res.checks, rehearsals: res.transcripts }), "ok");
    } catch (e) {
      toast(e instanceof Error && /passphrase/.test(e.message) ? tr("profile.restore_pass") : tr("profile.restore_bad"));
    }
  };

  return (
    <Section icon="database" title={tr("profile.storage")} id="pf-storage">
      <p data-testid="persist-state">
        <Icon name={st?.persisted ? "ok" : "info"} />{" "}
        {!st ? tr("common.loading") : !st.supported ? tr("profile.persist_unsupported") : st.persisted ? tr("profile.persist_on") : tr("profile.persist_off")}
      </p>
      {st?.supported && !st.persisted ? (
        <IconButton icon="lock" label={tr("profile.persist_ask")} testId="persist-ask" onClick={() => void requestPersistence().then(async (ok) => (await refresh(), toast(ok ? tr("profile.persist_on") : tr("profile.persist_refused"), ok ? "ok" : "info")))} />
      ) : null}
      {st && st.supported ? <p className="muted">{tr("profile.storage_used", { used: mb(st.usage), quota: mb(st.quota) })}</p> : null}
      <h3>{tr("profile.backup")}</h3>
      <p className="muted">{tr("profile.backup_note")}</p>
      <label className="field">
        <span>{tr("profile.passphrase")}</span>
        <input type="password" autoComplete="new-password" value={pass} onChange={(e) => setPass(e.target.value)} data-testid="backup-pass" />
      </label>
      <div className="row">
        <IconButton icon="download" label={tr("profile.export")} variant="primary" testId="backup-export" onClick={() => void exportNow()} />
        <IconButton icon="upload" label={tr("profile.restore")} testId="backup-restore" onClick={() => file.current?.click()} />
        <input
          ref={file}
          type="file"
          accept="application/json,.json"
          className="sr"
          aria-label={tr("profile.restore")}
          tabIndex={-1}
          data-testid="backup-file"
          onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = "";
            if (f) void restore(f);
          }}
        />
      </div>
    </Section>
  );
}

function UsageSetting() {
  const { tr } = useApp();
  const on = useSyncExternalStore(subscribe, footerOn);
  if (!footerAllowed()) return null;
  return (
    <label className="check-line">
      <input type="checkbox" checked={on} onChange={(e) => setFooterOn(e.target.checked)} data-testid="usage-setting" />
      <span>{tr("usage.setting")}</span>
    </label>
  );
}

function DataUsed() {
  const { tr } = useApp();
  const toast = useToast();
  const [u, setU] = useState<Usage>(getUsage());
  const [price, setP] = useState(String(getPrice() ?? ""));
  useEffect(() => {
    const t = window.setInterval(() => setU(getUsage()), 1500);
    return () => window.clearInterval(t);
  }, []);
  const cost = costOf(u, Number(price) || undefined);
  return (
    <Section icon="wifi" title={tr("profile.data_used")} id="pf-data">
      <UsageSetting />
      <dl className="stats">
        <div>
          <dt>{tr("profile.sent")}</dt>
          <dd data-testid="data-sent">{bytes(u.sent)}</dd>
        </div>
        <div>
          <dt>{tr("profile.received")}</dt>
          <dd data-testid="data-received">{bytes(u.received)}</dd>
        </div>
        <div>
          <dt>{tr("profile.total")}</dt>
          <dd data-testid="data-total">{bytes(u.sent + u.received)}</dd>
        </div>
      </dl>
      <p className="muted">{tr("profile.data_since", { date: new Date(u.since).toLocaleDateString() })}</p>
      <label className="field">
        <span>{tr("profile.price_per_gb")}</span>
        <input
          inputMode="decimal"
          value={price}
          data-testid="data-price"
          onChange={(e) => {
            setP(e.target.value);
            setPrice(Number(e.target.value) || undefined);
          }}
        />
      </label>
      {cost !== null ? (
        <p data-testid="data-cost">{tr("profile.cost", { cost: cost.toFixed(2) })}</p>
      ) : null}
      <IconButton
        icon="trash"
        label={tr("profile.clear_data_used")}
        testId="data-clear"
        onClick={() => {
          resetUsage();
          setU(getUsage());
          toast(tr("profile.cleared"), "ok");
        }}
      />
      <p className="muted">{tr("profile.data_note")}</p>
    </Section>
  );
}

const CHOICES: { scope: Scope; key: "counts" | "practice" | "share" | "feedback" | "keep" }[] = [
  { scope: "counts", key: "counts" },
  { scope: "practice_ai", key: "practice" },
  { scope: "share_rehearsal", key: "share" },
  { scope: "feedback", key: "feedback" },
  { scope: "keep_sheets", key: "keep" },
];

function Privacy() {
  const { tr, reset } = useApp();
  const toast = useToast();
  const consent = useConsent();
  const change = (scope: Scope, on: boolean) => {
    const before = getConsent();
    const base: Choices = { core: true, counts: countsOn(null), practice_ai: false, share_rehearsal: false, feedback: false, ...(before ?? {}) };
    const after = setConsent({ ...base, core: true, [scope]: on });
    void recordOnServer(before, after);
  };
  return (
    <Section icon="shield" title={tr("profile.privacy")} id="pf-privacy">
      <p>{tr("profile.privacy_intro")}</p>
      <ul className="plain switches">
        {CHOICES.map((c) => (
          <li key={c.scope}>
            <label className="switch">
              <input type="checkbox" checked={c.scope === "counts" ? countsOn(consent) : consent?.[c.scope] === true} onChange={(e) => change(c.scope, e.target.checked)} data-testid={`consent-${c.scope}`} />
              <span>
                <strong>{tr(`consent.${c.key}` as "consent.counts")}</strong>
                <span className="muted">{tr(`consent.${c.key}_why` as "consent.counts_why")}</span>
              </span>
            </label>
          </li>
        ))}
      </ul>
      <p className="muted">{consent ? tr("profile.consent_at", { date: new Date(consent.at).toLocaleString(), v: consent.v }) : tr("profile.consent_none")}</p>
      <div className="row">
        <a className="btn btn-secondary btn-with-icon" href={href("/privacy")} data-testid="privacy-link">
          <Icon name="info" /> <span>{tr("profile.read_notice")}</span>
        </a>
        <IconButton
          icon="close"
          label={tr("profile.withdraw")}
          testId="consent-withdraw"
          onClick={() => {
            const before = getConsent();
            void db.syncQueue.where("kind").equals("feedback").delete(); // anything waiting is dropped, not sent later
            void recordOnServer(before, withdrawAll());
            toast(tr("profile.withdrawn"), "ok");
          }}
        />
      </div>
      <h3>{tr("profile.erase")}</h3>
      <p className="muted">{tr("profile.erase_note")}</p>
      <IconButton
        icon="trash"
        variant="danger"
        label={tr("profile.erase_all")}
        testId="erase-all"
        onClick={() => {
          if (!window.confirm(tr("profile.erase_confirm"))) return;
          void (async () => {
            for (const c of await listClasses()) await deleteClass(c.id);
            await clearCloud();
            await clearPhone();
            resetUsage();
            for (const k of Object.keys(localStorage)) if (k.startsWith("cc.")) localStorage.removeItem(k); // settings, consent, device id
            sessionStorage.clear();
            await reset();
            toast(tr("profile.erased"), "ok");
          })();
        }}
      />
    </Section>
  );
}

function Feedback() {
  const { tr, role, lang, online } = useApp();
  const toast = useToast();
  const consent = useConsent();
  const [kind, setKind] = useState<FeedbackKind>("app");
  const [rating, setRating] = useState(0);
  const [text, setText] = useState("");
  const send = async () => {
    if (!consent?.feedback) {
      toast(tr("feedback.need_consent"));
      return;
    }
    const r = await sendFeedback({ kind, ...(rating ? { rating } : {}), ...(text.trim() ? { text: text.trim() } : {}), language: lang, role }, online);
    if (r === "refused") toast(tr("feedback.refused"));
    else {
      toast(r === "sent" ? tr("feedback.sent") : tr("feedback.queued"), "ok");
      setText("");
      setRating(0);
    }
  };
  return (
    <Section icon="chat" title={tr("profile.feedback")} id="pf-feedback">
      <label className="field">
        <span>{tr("feedback.about")}</span>
        <select value={kind} onChange={(e) => setKind(e.target.value as FeedbackKind)} data-testid="feedback-kind">
          {(["app", "content", "simulation"] as const).map((k) => (
            <option key={k} value={k}>
              {tr(`feedback.${k}` as "feedback.app")}
            </option>
          ))}
        </select>
      </label>
      <div className="stars" role="group" aria-label={tr("feedback.rating")}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" className={n <= rating ? "star star-on" : "star"} aria-pressed={n <= rating} aria-label={tr("feedback.star", { n })} onClick={() => setRating(n === rating ? 0 : n)} data-testid={`star-${n}`}>
            <Icon name="star" />
          </button>
        ))}
      </div>
      <label className="field">
        <span>{tr("feedback.text")}</span>
        <textarea rows={3} maxLength={500} value={text} onChange={(e) => setText(e.target.value)} data-testid="feedback-text" />
      </label>
      <p className="muted">{tr("feedback.note")}</p>
      <IconButton icon="send" label={tr("feedback.send")} variant="primary" testId="feedback-send" onClick={() => void send()} disabled={!rating && !text.trim()} />
    </Section>
  );
}

function ConflictsList() {
  const { tr } = useApp();
  const [rows, setRows] = useState<Conflict[] | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const load = useCallback(() => void listConflicts().then(setRows), []);
  useEffect(load, [load]);
  return (
    <Section icon="refresh" title={tr("sync.conflicts_title")} id="conflicts">
      <p className="muted">{tr("sync.conflicts_hint")}</p>
      {rows && rows.length === 0 ? <p data-testid="conflicts-none">{tr("sync.conflicts_none")}</p> : null}
      <ul className="list">
        {(rows ?? []).map((c) => (
          <li key={c.id} data-testid={`conflict-${c.id}`}>
            <span>{tr("sync.conflict_row", { what: `${c.collection} ${c.doc_id}`, when: new Date(c.at).toLocaleString() })}</span>{" "}
            <button type="button" className="btn btn-secondary" aria-expanded={openId === c.id} onClick={() => setOpenId(openId === c.id ? null : c.id)}>
              {tr("sync.open")}
            </button>{" "}
            <button type="button" className="btn btn-secondary" onClick={() => void dismissConflict(c.id).then(load)}>
              {tr("sync.dismiss")}
            </button>
            {openId === c.id ? <pre className="muted" tabIndex={0}>{JSON.stringify(c.data, null, 2)}</pre> : null}
          </li>
        ))}
      </ul>
    </Section>
  );
}

export default function Profile() {
  const { tr, role, lang, setLang } = useApp();
  return (
    <div data-testid="profile">
      <h1>{tr("profile.title")}</h1>
      <p className="who">
        <Icon name={role} /> <strong>{tr(`role.${role}` as "role.teacher")}</strong> ·{" "}
        <a href={href("/roles")} data-testid="change-role">
          {tr("profile.change_role")}
        </a>
      </p>
      <label className="field">
        <span>
          <Icon name="globe" size={18} /> {tr("common.language")}
        </span>
        <select
          value={lang}
          data-testid="profile-lang"
          onChange={(e) => {
            if (isLang(e.target.value)) setLang(e.target.value);
          }}
        >
          {LANGS.map((l) => (
            <option key={l} value={l}>
              {LANG_NAMES[l]}
            </option>
          ))}
        </select>
      </label>
      <InstallEntry variant="row" />
      <NicknameField />
      <TesterSettings />
      <Classes />
      <ConflictsList />
      <Storage />
      <DataUsed />
      <Privacy />
      <Feedback />
    </div>
  );
}
