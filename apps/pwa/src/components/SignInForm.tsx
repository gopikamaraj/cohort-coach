// The nickname is the user id. A new nickname is registered (refused with a clear message when taken); an
// existing one is signed in with. There is no password, and the form says so.
import { useState, useSyncExternalStore } from "react";
import type { Key } from "../i18n";
import { getUser, register, signIn, signOut, type SignInResult } from "../lib/identity";
import { setNickname } from "../lib/tester";
import { useApp } from "../state";

const subscribe = (cb: () => void) => {
  window.addEventListener("cc:identity", cb);
  return () => window.removeEventListener("cc:identity", cb);
};

export function SignInForm({ onDone, testid = "signin" }: { onDone?: () => void; testid?: string }) {
  const { tr } = useApp();
  const user = useSyncExternalStore(subscribe, getUser, getUser);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<Extract<SignInResult, { ok: false }>["code"] | null>(null);

  const go = async (how: "register" | "signin") => {
    setBusy(true);
    setProblem(null);
    const res = await (how === "register" ? register(name) : signIn(name));
    setBusy(false);
    if (res.ok) {
      setNickname(res.user.nickname); // the title bar shows it
      onDone?.();
    } else setProblem(res.code);
  };

  if (user) {
    return (
      <div className="stack" data-testid={`${testid}-current`}>
        <p>{tr("signin.as", { name: user.nickname })}</p>
        <button type="button" className="btn btn-secondary" onClick={() => { signOut(); setNickname(""); }} data-testid={`${testid}-switch`}>
          {tr("signin.switch")}
        </button>
        <p className="muted">{tr("signin.note")}</p>
      </div>
    );
  }
  return (
    <div className="stack" data-testid={testid}>
      <label className="field">
        <span>{tr("signin.label")}</span>
        <input type="text" value={name} maxLength={30} onChange={(e) => setName(e.target.value)} autoComplete="off" data-testid={`${testid}-input`} />
      </label>
      {problem ? (
        <p role="alert" data-testid={`${testid}-problem`}>
          {tr(`signin.${problem}` as Key)}
        </p>
      ) : null}
      <div className="row">
        <button type="button" className="btn btn-primary" disabled={busy || name.trim().length < 3} onClick={() => void go("register")} data-testid={`${testid}-register`}>
          {tr("signin.register")}
        </button>
        <button type="button" className="btn btn-secondary" disabled={busy || name.trim().length < 1} onClick={() => void go("signin")} data-testid={`${testid}-signin`}>
          {tr("signin.signin")}
        </button>
      </div>
      <p className="muted">{tr("signin.note")}</p>
    </div>
  );
}
