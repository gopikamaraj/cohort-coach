import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { API_BASE } from "./lib/api";
import "./lib/install"; // listens from the first moment: the browser offers installing only once, early
import { installIdentity } from "./lib/identity";
import { installMeter } from "./lib/meter";
import "./theme.css"; // the look: every colour, corner and size (docs/design-system.md)
import "./styles.css";

document.documentElement.dataset["theme"] = (import.meta.env["VITE_THEME"] as string | undefined) ?? "m3";

installIdentity(); // every call to our API carries the signed-in user
installMeter(API_BASE);

void import("./App").then(({ default: Root }) => {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <Root />
    </StrictMode>,
  );
});
