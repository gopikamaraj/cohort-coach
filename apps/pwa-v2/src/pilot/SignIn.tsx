import { useState } from "react";
import { Icon } from "../components/icons";
import type { Key } from "../i18n";
import { jsonInit, pilotFetch, type Session } from "./api";

interface Props {
  tr: (key: Key, params?: Record<string, string | number>) => string;
  online: boolean;
  ended: boolean;
  onSignedIn: (session: Session) => void;
}

export default function SignIn({ tr, online, ended, onSignedIn }: Props) {
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [error, setError] = useState<Key | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!online) {
      setError("pilot.signin.offline");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await pilotFetch("/api/pilot/auth/signin", jsonInit("POST", { name: name.trim(), key }), null);
      if (res.ok) {
        const body = (await res.json()) as { token: string; name: string; roles: string[] };
        onSignedIn({ token: body.token, name: body.name, roles: body.roles });
        return;
      }
      setError(res.status === 429 ? "pilot.signin.wait" : res.status === 401 ? "pilot.signin.bad" : "pilot.signin.error");
    } catch {
      setError("pilot.signin.offline");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="p-page">
      <form className="p-card" onSubmit={submit} data-testid="pilot-signin">
        <h1>{tr("pilot.signin.title")}</h1>
        <p className="p-muted">{tr("pilot.signin.intro")}</p>
        {ended ? (
          <p className="p-msg" role="status">
            <Icon name="info" size={18} />
            {tr("pilot.session_ended")}
          </p>
        ) : null}
        <label className="p-field">
          <span>{tr("pilot.signin.name")}</span>
          <input type="text" value={name} autoComplete="username" autoCapitalize="none" onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="p-field">
          <span>{tr("pilot.signin.key")}</span>
          <input type="password" value={key} autoComplete="current-password" onChange={(e) => setKey(e.target.value)} />
        </label>
        {error ? (
          <p className="p-msg p-bad" role="alert">
            <Icon name="close" size={18} />
            {tr(error)}
          </p>
        ) : null}
        <button type="submit" className="p-btn p-block" disabled={busy || !name.trim() || !key}>
          {tr("pilot.signin.go")}
        </button>
      </form>
    </main>
  );
}
