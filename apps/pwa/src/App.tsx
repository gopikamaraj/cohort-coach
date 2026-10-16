import { useState } from "react";
import { type Lang, t } from "./strings";

export default function App() {
  const [lang, setLang] = useState<Lang>("en");
  return (
    <div style={{ display: "flex", justifyContent: "center", padding: 16, fontFamily: "system-ui, sans-serif" }}>
      <div
        style={{ width: 360, minHeight: 640, border: "8px solid #222", borderRadius: 28, padding: 16, boxSizing: "border-box" }}
      >
        <h1 style={{ fontSize: 22 }}>{t(lang, "title")}</h1>
        <p>{t(lang, "judge")}</p>
        <p style={{ color: "#555" }}>{t(lang, "note")}</p>
        <div style={{ display: "flex", gap: 8 }}>
          {(["en", "hi", "ta"] as Lang[]).map((l) => (
            <button key={l} onClick={() => setLang(l)} style={{ minHeight: 48, minWidth: 48 }}>
              {l}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
