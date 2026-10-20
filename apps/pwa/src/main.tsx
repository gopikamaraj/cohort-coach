import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { API_BASE } from "./lib/api";
import { installMeter } from "./lib/meter";
import "./styles.css";

installMeter(API_BASE);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
