// A toast: a short message that appears over the screen and goes by itself. It is announced to screen
// readers (role="status") and can be closed with a tap. Used for "not yet" notes and quiet confirmations,
// so the page does not fill with sentences.
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import { useApp } from "../state";
import { Icon } from "./icons";

interface Toast {
  id: number;
  text: string;
  tone: "info" | "ok";
}

const Ctx = createContext<(text: string, tone?: Toast["tone"]) => void>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const { tr } = useApp();
  const [toasts, setToasts] = useState<Toast[]>([]);
  const next = useRef(1);
  const close = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const show = useCallback(
    (text: string, tone: Toast["tone"] = "info") => {
      const id = next.current++;
      setToasts((t) => [...t.slice(-2), { id, text, tone }]);
      window.setTimeout(() => close(id), 4500);
    },
    [close],
  );
  return (
    <Ctx.Provider value={show}>
      {children}
      <div className="toasts" role="status" aria-live="polite" data-testid="toasts">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.tone}`} data-testid="toast">
            <Icon name={t.tone === "ok" ? "ok" : "info"} />
            <span>{t.text}</span>
            <button type="button" className="toast-close" aria-label={tr("common.close")} onClick={() => close(t.id)}>
              <Icon name="close" size={18} />
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useToast(): (text: string, tone?: Toast["tone"]) => void {
  return useContext(Ctx);
}
