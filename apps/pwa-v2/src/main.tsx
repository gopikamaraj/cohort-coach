import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { API_BASE } from "./lib/api";
import "./lib/install"; // listens from the first moment: the browser offers installing only once, early
import { installMeter } from "./lib/meter";
import { detectPilot } from "./pilot/mode";
import "./styles/tokens.css"; // the look: every colour, corner, size and motion value
import "./styles.css"; // layout of the screens
import "./styles/base.css"; // v2: raw elements, forms, focus, reduced motion
import "./styles/components.css"; // v2: the component set and the app shell

document.documentElement.dataset["theme"] = (import.meta.env["VITE_THEME"] as string | undefined) ?? "m3";

installMeter(API_BASE);

// Pilot mode (the server's PILOT_MODE=1, or a pilot build) starts the pilot app, which imports no
// other screen. Otherwise the full app starts, exactly as before.
void detectPilot().then(async (pilot) => {
  const { default: Root } = pilot ? await import("./pilot/PilotApp") : await import("./App");
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <Root />
    </StrictMode>,
  );
});
