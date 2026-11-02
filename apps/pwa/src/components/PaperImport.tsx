// Create a paper from a PDF or an answered sheet. The AI only reads the printed questions; the
// server computes every answer, probe and coverage cell; a person confirms. The side panel asks for
// what is missing, one question at a time, and its answers go through the same whitelisted edit as a
// typed change, tagged "Assistant changed this" and undoable. It never confirms or assigns.
import { useEffect, useRef, useState } from "react";
import type { Key } from "../i18n";
import { editFor, HubError, hblob, hcall, type DraftItem, type HubIdentity, type ImportView, type OpenQuestion } from "../lib/paperHub";
import { useApp } from "../state";
import { isAiOff, useAiMode } from "../lib/aiMode";
import { Busy } from "./Busy";
import { AiOffNote, RecordedChip } from "./parts";
import { Icon, IconButton } from "./icons";
import { isKeyFile, MAX_KEY_BYTES, parseKeyFile, type ParsedKey } from "../lib/keyfile";

type Role = "paper" | "guide" | "other";
type Picked = { file: File; role: Role; key?: ParsedKey };
const MAX_UPLOADS = 6;
/** A number is typed in a plain text box (no stepper arrows): digits only, as many as a paper uses. */
const DIGITS = { type: "text", inputMode: "numeric" as const, pattern: "[0-9]*", maxLength: 3, autoComplete: "off", onInput: (e: React.FormEvent<HTMLInputElement>) => { e.currentTarget.value = e.currentTarget.value.replace(/\D/g, ""); } };

export function PaperImport({ who, kind, onConfirmed }: { who: HubIdentity; kind: string; onConfirmed: (paperId: string) => void }) {
  const { tr } = useApp();
  const aiOff = isAiOff(useAiMode());
  const [view, setView] = useState<ImportView | null>(null);
  const [busy, setBusy] = useState<string>("");
  const [msg, setMsg] = useState<{ text: string; bad?: boolean } | null>(null);
  const [page, setPage] = useState<string | null>(null);
  const [skipped, setSkipped] = useState<string[]>([]);
  const pageUrl = useRef<string | null>(null);
  const [picked, setPicked] = useState<Picked[]>([]);
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!view || view.status !== "draft") return;
    let gone = false;
    void hblob(`/imports/${view.id}/page/1`, who)
      .then((b) => {
        if (gone) return;
        if (pageUrl.current) URL.revokeObjectURL(pageUrl.current);
        pageUrl.current = URL.createObjectURL(b);
        setPage(pageUrl.current);
      })
      .catch(() => undefined);
    return () => {
      gone = true;
    };
  }, [view?.id, view?.status]);

  const fail = (e: unknown) => setMsg({ text: e instanceof HubError && e.explanation ? e.explanation : tr("ph.err"), bad: true });

  // Files are collected first, each marked as the question paper, the teacher's guide or other.
  async function addFiles(list: FileList | null) {
    if (!list?.length) return;
    setMsg(null);
    const added: Picked[] = [];
    for (const file of Array.from(list)) {
      if (isKeyFile(file.name)) {
        // a text file is an answer key: read here, and only its questions and answers are kept
        try {
          if (file.size > MAX_KEY_BYTES) throw new Error("it is too large");
          const key = parseKeyFile(file.name, await file.text());
          added.push({ file, role: "other", key });
        } catch (e) {
          setMsg({ text: tr("ph.key_bad", { name: file.name, why: e instanceof Error ? e.message : "" }), bad: true });
        }
      } else added.push({ file, role: "paper" });
    }
    // the first picture or PDF is taken to be the question paper, the next ones the teacher's guide; she can change each
    setPicked((cur) => {
      let seen = cur.filter((x) => !x.key).length;
      const next = added.map((x) => (x.key ? x : { ...x, role: (seen++ === 0 ? "paper" : "guide") as Role }));
      const keep = next.some((x) => x.key) ? cur.filter((x) => !x.key) : cur; // one answer key: a new one replaces it
      return [...keep, ...next].slice(0, MAX_UPLOADS);
    });
  }

  async function upload() {
    if (picked.length === 0) return;
    if (!picked.some((x) => !x.key && x.role === "paper")) {
      setMsg({ text: tr("ph.need_paper_file"), bad: true });
      return;
    }
    setBusy("ph.reading");
    setMsg(null);
    try {
      const form = new FormData();
      picked.forEach((x) => {
        if (x.key) return; // an answer key is sent as its numbers only, never as a file
        form.append("files", x.file, x.file.name);
        form.append("roles", x.role);
      });
      const key = picked.find((x) => x.key);
      if (key?.key) form.append("key_json", JSON.stringify({ answers: key.key.answers }));
      if (note.trim()) form.append("note", note.trim());
      form.append("kind", kind); // chosen above, on the Papers page
      const v = await hcall<ImportView>("/imports", who, { form });
      setView(v);
      setPicked([]);
      setSkipped([]);
    } catch (e) {
      fail(e);
    } finally {
      setBusy("");
    }
  }

  async function apply(edits: { field: string; value: string | number | boolean }[], via: "user" | "assistant", id = view?.id) {
    if (!id || edits.length === 0) return;
    try {
      setView(await hcall<ImportView>(`/imports/${id}/edit`, who, { body: { edits, via } }));
    } catch (e) {
      fail(e);
    }
  }

  async function undo() {
    if (!view) return;
    try {
      setView(await hcall<ImportView>(`/imports/${view.id}/undo`, who, { method: "POST" }));
    } catch (e) {
      fail(e);
    }
  }

  async function confirm() {
    if (!view) return;
    setBusy("ph.confirm");
    try {
      const paper = await hcall<{ id: string }>(`/imports/${view.id}/confirm`, who, { body: {} });
      setMsg({ text: tr("ph.confirmed") });
      setView(null);
      onConfirmed(paper.id);
    } catch (e) {
      fail(e);
    } finally {
      setBusy("");
    }
  }

  async function abandon() {
    if (!view) return;
    await hcall(`/imports/${view.id}`, who, { method: "DELETE" }).catch(() => undefined);
    setView(null);
    setPage(null);
  }

  if (!view) {
    return (
      <section className="stack" data-testid="import-upload" aria-labelledby="import-title">
        <h3 id="import-title">{tr("ph.route_pdf")}</h3>
        <p className="muted" data-testid="import-note">
          {tr("ph.upload_note")}
        </p>
        <AiOffNote text={tr("ai.off.import")} testId="import-ai-off" />
        <fieldset className="stack" data-testid="import-files">
          <legend>{tr("ph.files_title")}</legend>
          <p className="muted">{tr("ph.files_limit")}</p>
          <p className="muted">{tr("ph.key_note")}</p>
          {picked.length > 0 ? (
            <ul className="plain stack" data-testid="import-file-list">
              {picked.map((x, k) => (
                <li key={`${x.file.name}-${k}`} className="file-row">
                  <div className="file-info">
                    <span className="file-name">{x.file.name}</span>
                    {x.key ? (
                      <span className="muted" data-testid={`import-key-${k}`}>
                        {tr("ph.role_key")} · {tr("ph.key_n", { n: x.key.items })}
                      </span>
                    ) : null}
                    <label className="file-role" hidden={!!x.key}>
                      <span className="sr">{tr("ph.role_label")}</span>
                      <select value={x.role} onChange={(e) => setPicked((cur) => cur.map((y, m) => (m === k ? { ...y, role: e.target.value as Role } : y)))} data-testid={`import-role-${k}`}>
                        <option value="paper">{tr("ph.role_paper")}</option>
                        <option value="guide">{tr("ph.role_guide")}</option>
                        <option value="other">{tr("ph.role_other")}</option>
                      </select>
                    </label>
                  </div>
                  <IconButton icon="trash" iconOnly variant="secondary" label={tr("ph.remove_file", { name: x.file.name })} onClick={() => setPicked((cur) => cur.filter((_, m) => m !== k))} testId={`import-remove-${k}`} />
                </li>
              ))}
            </ul>
          ) : null}
          <label className={aiOff || picked.length >= MAX_UPLOADS ? "btn btn-secondary is-disabled" : "btn btn-secondary"} aria-disabled={aiOff || picked.length >= MAX_UPLOADS || undefined}>
            {tr("ph.add_files")}
            <input type="file" multiple accept="application/pdf,image/png,image/jpeg,.json,.csv,.txt,application/json,text/csv,text/plain" className="sr" disabled={!!busy || aiOff || picked.length >= MAX_UPLOADS} onChange={(e) => { void addFiles(e.target.files); e.target.value = ""; }} data-testid="import-file" />
          </label>
          <label className="field">
            <span>{tr("ph.note_label")}</span>
            <textarea rows={4} maxLength={500} value={note} placeholder={tr("ph.note_hint")} onChange={(e) => setNote(e.target.value)} disabled={aiOff} data-testid="import-note-text" />
          </label>
          <button type="button" className="btn btn-primary" disabled={!!busy || aiOff || picked.length === 0} onClick={() => void upload()} data-testid="import-read">
            {tr("ph.read_files")}
          </button>
        </fieldset>
        {busy ? <Busy ai={busy === "ph.reading"} text={tr(busy as Key)} testId="import-busy" /> : null}
        {msg ? (
          <p role={msg.bad ? "alert" : "status"} data-testid="import-msg">
            {msg.text}
          </p>
        ) : null}
      </section>
    );
  }

  const d = view.draft;
  const changes = d.changes ?? {};
  const blocking = view.blocking.length;
  const asked = d.open_questions.filter((q) => !skipped.includes(q.id));
  const current = asked.find((q) => q.blocking) ?? asked[0] ?? null;
  const tag = (field: string) => {
    const c = changes[field];
    return c && c.via === "assistant" ? (
      <span className="chip" data-testid={`changed-${field}`}>
        {tr("ph.changed_by")} · {tr("ph.was", { value: String(c.old ?? "-") })}
      </span>
    ) : null;
  };

  return (
    <section className="stack" aria-labelledby="review-title" data-testid="import-review">
      <h3 id="review-title">
        {tr("ph.review_title")} <RecordedChip testId="import-recorded" />
      </h3>
      <p className="muted">{view.note}</p>
      {page ? <img className="import-page" src={page} alt={tr("ph.page_alt", { n: 1 })} data-testid="import-page" /> : null}

      <div style={{ overflowX: "auto" }}>
        <table data-testid="import-table">
          <thead>
            <tr>
              <th scope="col">{tr("ph.col_item")}</th>
              <th scope="col">{tr("ph.col_op")}</th>
              <th scope="col" className="import-num">{tr("ph.col_a")}</th>
              <th scope="col" className="import-num">{tr("ph.col_b")}</th>
              <th scope="col">{tr("ph.col_key")}</th>
              <th scope="col">{tr("ph.col_include")}</th>
            </tr>
          </thead>
          <tbody>
            {d.items.map((it) => (
              <ItemRow key={it.n} it={it} apply={apply} tag={tag} />
            ))}
          </tbody>
        </table>
      </div>

      <h4>{tr("ph.coverage_title")}</h4>
      <ul className="plain" data-testid="import-coverage">
        {Object.entries(d.coverage).map(([code, ns]) => (
          <li key={code}>{tr("ph.coverage_items", { code, items: ns.length ? ns.join(", ") : "-" })}</li>
        ))}
      </ul>
      {d.coverage_warnings.map((c) => (
        <p key={c} className="muted" data-testid={`coverage-warn-${c}`}>
          {tr("ph.coverage_warn", { code: c })}
        </p>
      ))}

      <aside className="card stack" aria-labelledby="ask-title" data-testid="import-assistant">
        <h4 id="ask-title">{tr("ph.q_title")}</h4>
        {current ? <Ask key={current.id} q={current} items={d.items} onAnswer={(edits) => void apply(edits, "assistant")} onSkip={() => setSkipped((s) => [...s, current.id])} /> : <p data-testid="ask-none">{tr("ph.q_none")}</p>}
      </aside>

      {view.reuses && view.reuses.length > 0 ? (
        <p role="alert" data-testid="import-reuses">
          {tr("ph.reuses", { codes: view.reuses.join(", ") })}
        </p>
      ) : null}
      {msg ? (
        <p role={msg.bad ? "alert" : "status"} data-testid="import-msg">
          {msg.text}
        </p>
      ) : null}
      {busy ? <Busy text={tr(busy as Key)} testId="import-busy" /> : null}
      <div className="row">
        <button type="button" className="btn btn-primary" disabled={blocking > 0 || !!busy} onClick={() => void confirm()} data-testid="import-confirm">
          {tr("ph.confirm")}
        </button>
        <button type="button" className="btn btn-secondary" disabled={!view.can_undo} onClick={() => void undo()} data-testid="import-undo">
          {tr("ph.undo")}
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => void abandon()} data-testid="import-abandon">
          {tr("ph.abandon")}
        </button>
      </div>
      {blocking > 0 ? (
        <p className="muted" data-testid="import-blocked">
          {tr("ph.confirm_blocked", { n: blocking })}
        </p>
      ) : null}
    </section>
  );
}

function ItemRow({ it, apply, tag }: { it: DraftItem; apply: (e: { field: string; value: string | number | boolean }[], via: "user" | "assistant") => Promise<void>; tag: (f: string) => React.ReactNode }) {
  const { tr } = useApp();
  // What the reader should look at on this row, in words; the row is highlighted when there is any.
  const notes: string[] = [];
  if (it.unsure) notes.push(tr("ph.obs_unsure"));
  if (it.disagreement) notes.push(tr("ph.obs_disagree"));
  if (it.key_file !== undefined && it.key_mismatch) {
    notes.push(it.from_guide && it.a !== null && it.a !== it.key_file ? tr("ph.obs_key_guide", { guide: it.a, key: it.key_file }) : tr("ph.obs_key", { key: it.key_file, code: it.correct ?? "-" }));
  } else if (it.key_mismatch) notes.push(tr("ph.obs_printed"));
  if (!it.supported && it.operation !== "dictate") notes.push(tr("ph.obs_unsupported"));
  const num = (field: "a" | "b", cur: number | null) => (
    <input
      {...DIGITS}
      className="import-num-input"
      aria-label={`${tr(field === "a" ? "ph.col_a" : "ph.col_b")} ${it.n}`}
      defaultValue={cur ?? ""}
      key={`${it.n}-${field}-${cur}`}
      disabled={it.operation === "other" || (field === "b" && it.operation === "dictate")}
      onBlur={(e) => e.target.value !== "" && Number(e.target.value) !== cur && void apply([{ field: `items.${it.n}.${field}`, value: Number(e.target.value) }], "user")}
      data-testid={`item-${it.n}-${field}`}
    />
  );
  return (
    <tr data-testid={`item-row-${it.n}`} className={notes.length > 0 ? "row-warn" : undefined} data-warn={notes.length > 0 ? "true" : undefined}>
      <th scope="row">{it.n}</th>
      <td>
        <span className="op-cell">
          {tr(`ph.op_${it.operation}` as Key)}
          {notes.length > 0 ? (
            <span className="obs">
              <button type="button" className="obs-btn" aria-label={`${tr("ph.obs_title", { n: it.n })}: ${notes.join(" ")}`} aria-describedby={`obs-${it.n}`} data-testid={`item-${it.n}-warn`}>
                <Icon name="warning" size={18} />
              </button>
              <span role="tooltip" id={`obs-${it.n}`} className="obs-tip" data-testid={`item-${it.n}-warn-text`}>
                {notes.map((t) => (
                  <span key={t}>{t}</span>
                ))}
              </span>
            </span>
          ) : null}
        </span>
      </td>
      <td>
        {num("a", it.a)}
        {it.from_key ? <small className="muted" data-testid={`item-${it.n}-from-key`}>{tr("ph.from_key")}</small> : it.from_guide ? <small className="muted" data-testid={`item-${it.n}-guide`}>{tr("ph.from_guide")}</small> : null}
        {tag(`items.${it.n}.a`)}
      </td>
      <td>{num("b", it.b)}</td>
      <td data-testid={`item-${it.n}-key`}>{it.correct ?? "-"}</td>
      <td>
        <label className="tick">
          <input type="checkbox" checked={it.include} disabled={!it.supported} onChange={(e) => void apply([{ field: `items.${it.n}.include`, value: e.target.checked }], "user")} aria-label={`${tr("ph.col_include")} ${it.n}`} data-testid={`item-${it.n}-include`} />
        </label>
        {tag(`items.${it.n}.include`)}
      </td>
    </tr>
  );
}

/** One open question: why it matters, answer chips or a box, and "I don't know". */
function Ask({ q, items, onAnswer, onSkip }: { q: OpenQuestion; items: DraftItem[]; onAnswer: (e: { field: string; value: string | number | boolean }[]) => void; onSkip: () => void }) {
  const { tr } = useApp();
  const [text, setText] = useState("");
  const [b, setB] = useState("");
  const [hand, setHand] = useState(false);
  const [op, setOp] = useState<"add" | "subtract">("add");
  const n = Number(q.id.split("-")[1] ?? 0);
  const label = (): string => {
    const id = q.id.split("-")[0] ?? "";
    const code = q.id.startsWith("coverage-") ? q.id.slice(9) : "";
    return tr(`ph.q_${id === "no" ? "no_items" : id}` as Key, { n, code });
  };
  const optionLabel = (o: string): string => (["pre", "post", "termly"].includes(o) ? tr(`check.kind.${o}` as Key) : o === "A" || o === "B" ? o : tr(`ph.opt_${o}` as Key));
  const unsureItem = items.find((i) => i.n === n);
  return (
    <div className="stack" data-testid={`ask-${q.id}`}>
      <p>
        <strong>{label()}</strong>
      </p>
      <p className="muted">{tr("ph.q_why", { why: q.why })}</p>
      {hand ? (
        <div className="row" data-testid="ask-hand">
          <select value={op} onChange={(e) => setOp(e.target.value as "add" | "subtract")} aria-label={tr("ph.col_op")} data-testid="ask-op">
            <option value="add">{tr("ph.op_add")}</option>
            <option value="subtract">{tr("ph.op_subtract")}</option>
          </select>
          <input {...DIGITS} aria-label={tr("ph.col_a")} onChange={(e) => setText(e.target.value)} data-testid="ask-a" />
          <input {...DIGITS} aria-label={tr("ph.col_b")} onChange={(e) => setB(e.target.value)} data-testid="ask-b" />
          <button
            type="button"
            className="btn btn-secondary"
            disabled={text === "" || b === ""}
            onClick={() =>
              onAnswer([
                { field: `items.${n}.operation`, value: op },
                { field: `items.${n}.a`, value: Number(text) },
                { field: `items.${n}.b`, value: Number(b) },
              ])
            }
            data-testid="ask-send"
          >
            {tr("ph.q_answer")}
          </button>
        </div>
      ) : q.options ? (
        <div className="chips">
          {q.options.map((o) => (
            <button key={o} type="button" className="chip-btn" disabled={o === "add_item"} onClick={() => (o === "continue" ? onSkip() : o === "enter_by_hand" ? setHand(true) : onAnswer(editFor(q, o)))} data-testid={`ask-opt-${o}`}>
              {optionLabel(o)}
            </button>
          ))}
        </div>
      ) : q.id.startsWith("unsure-") ? (
        <div className="row">
          <input {...DIGITS} aria-label={tr("ph.col_a")} defaultValue={unsureItem?.a ?? ""} onChange={(e) => setText(e.target.value)} data-testid="ask-a" />
          <input {...DIGITS} aria-label={tr("ph.col_b")} defaultValue={unsureItem?.b ?? ""} onChange={(e) => setB(e.target.value)} data-testid="ask-b" />
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              const edits: { field: string; value: number }[] = [];
              if (text !== "") edits.push({ field: `items.${n}.a`, value: Number(text) });
              if (b !== "") edits.push({ field: `items.${n}.b`, value: Number(b) });
              if (edits.length === 0 && unsureItem) {
                if (unsureItem.a !== null) edits.push({ field: `items.${n}.a`, value: unsureItem.a });
              }
              onAnswer(edits);
            }}
            data-testid="ask-send"
          >
            {tr("ph.q_answer")}
          </button>
        </div>
      ) : (
        <div className="row">
          <input value={text} onChange={(e) => setText(e.target.value)} aria-label={tr("ph.q_answer")} data-testid="ask-text" />
          <button type="button" className="btn btn-secondary" disabled={!text.trim()} onClick={() => onAnswer([{ field: q.field, value: q.field.endsWith(".a") ? Number(text) : text.trim() }])} data-testid="ask-send">
            {tr("ph.q_answer")}
          </button>
        </div>
      )}
      <button type="button" className="chip-btn" onClick={onSkip} data-testid="ask-skip">
        {tr("ph.q_dont_know")}
      </button>
      <p className="muted">{tr("ph.q_skipped")}</p>
    </div>
  );
}
