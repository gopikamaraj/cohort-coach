// Stitch pack capture: drives the built PWA in a judge-mode demo session (recorded AI, stub voice)
// and, for every manifest entry, saves the first viewport, scroll slices, horizontal scroll, and a
// JSON file with every visible element, its box, region and style. Image work (long images,
// annotation, contact sheets) and the documents are done by build.py from these files.
// Usage: node capture.mjs <manifest.json> <outDir> <baseUrl> <apiBase>
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const [manifestPath, outDir, baseUrl, apiBase] = process.argv.slice(2);
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "../..");
const req = createRequire(path.join(root, "apps/pwa/package.json"));
const { chromium } = req("playwright-core");

const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const only = process.env.ONLY ? process.env.ONLY.split(",") : null;
const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';
const FIXED_TIME = new Date("2026-10-31T10:00:00+05:30");
const SECRET = /(sk-[A-Za-z0-9_-]{16,}|Api-Subscription-Key|[\w.+-]+@[\w-]+\.[A-Za-z]{2,}|(?<![\d.])\d{10}(?![\d.]))/;
const DEMO_WORD = /demo|simulated|डेमो|नकली|டெமோ|உருவகப்/i;

const log = (...a) => console.log(...a);
const failures = [];
const index = []; // every capture, for build.py

const INIT = `
  Object.defineProperty(navigator, "connection", { configurable: true, value: { downlink: 9.2, effectiveType: "4g", rtt: 50, saveData: false, addEventListener() {}, removeEventListener() {} } });
  document.addEventListener("DOMContentLoaded", () => {
    const s = document.createElement("style");
    s.textContent = "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important;scroll-behavior:auto!important}";
    document.head.appendChild(s);
  });
`;

// ---- in-page helpers (serialised into the page) ------------------------------------------------

function inPageFindContainer() {
  const cands = [...document.querySelectorAll("*")].filter((e) => {
    const s = getComputedStyle(e);
    return (s.overflowY === "auto" || s.overflowY === "scroll") && e.scrollHeight > e.clientHeight + 4 && e.clientHeight > 200;
  });
  cands.sort((a, b) => b.clientHeight - a.clientHeight);
  document.querySelectorAll("[data-sp-container]").forEach((e) => e.removeAttribute("data-sp-container"));
  if (cands[0]) {
    cands[0].setAttribute("data-sp-container", "1");
    const r = cands[0].getBoundingClientRect();
    return { mode: "element", top: r.top, bottom: r.bottom, left: r.left, right: r.right, scrollHeight: cands[0].scrollHeight, clientHeight: cands[0].clientHeight, scrollTop: cands[0].scrollTop };
  }
  const de = document.documentElement;
  if (de.scrollHeight > window.innerHeight + 4) return { mode: "window", top: 0, bottom: window.innerHeight, left: 0, right: window.innerWidth, scrollHeight: de.scrollHeight, clientHeight: window.innerHeight, scrollTop: window.scrollY };
  return { mode: "none", top: 0, bottom: window.innerHeight, left: 0, right: window.innerWidth, scrollHeight: window.innerHeight, clientHeight: window.innerHeight, scrollTop: 0 };
}

function inPageScrollTo(y) {
  const c = document.querySelector("[data-sp-container]");
  if (c) {
    c.scrollTop = y;
    return c.scrollTop;
  }
  window.scrollTo(0, y);
  return window.scrollY;
}

function inPageCollect(cont) {
  const norm = (() => {
    const probe = document.createElement("span");
    probe.style.display = "none";
    document.body.appendChild(probe);
    return (v) => {
      probe.style.color = "";
      probe.style.color = v;
      return getComputedStyle(probe).color;
    };
  })();
  const colorTokens = {};
  const lenTokens = {};
  for (const sheet of document.styleSheets) {
    let rules;
    try {
      rules = sheet.cssRules;
    } catch {
      continue;
    }
    for (const rule of rules) {
      if (!rule.selectorText || !/^:root/.test(rule.selectorText)) continue;
      for (const name of rule.style) {
        if (!name.startsWith("--")) continue;
        const v = rule.style.getPropertyValue(name).trim();
        if (/^#|^rgb/.test(v)) colorTokens[norm(v)] = name;
        else if (/^\d+(\.\d+)?px$/.test(v)) lenTokens[v] = name;
      }
    }
  }
  const tok = (c) => (colorTokens[c] ? ` (${colorTokens[c]})` : "");
  const ltok = (v) => (lenTokens[v] ? ` (${lenTokens[v]})` : "");
  const bgOf = (el) => {
    for (let e = el; e; e = e.parentElement) {
      const c = getComputedStyle(e).backgroundColor;
      if (c && c !== "rgba(0, 0, 0, 0)" && c !== "transparent") return c;
    }
    return "rgb(255, 255, 255)";
  };
  const SEL = "button,a[href],input,select,textarea,summary,[role=tab],[role=switch],[role=checkbox],[role=menuitem],[role=button],[tabindex='0'],h1,h2,h3,h4,label,[role=status],[role=alert],[role=dialog],img,svg[aria-label],[data-testid]:not(main):not(section):not(div):not(ul):not(li):not(aside):not(nav)";
  const nodes = [...document.querySelectorAll(SEL)];
  const out = [];
  const seen = new Set();
  const vh = window.innerHeight;
  const vw = window.innerWidth;
  for (const el of nodes) {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    if (r.width < 6 || r.height < 6 || cs.visibility === "hidden" || cs.display === "none" || Number(cs.opacity) === 0) continue;
    if (r.right < 0 || r.left > vw) continue;
    const inCont = cont.mode !== "none" && r.top >= cont.top - 1 && r.bottom <= cont.bottom + 1 + 0 ? true : cont.mode !== "none" && el.closest("[data-sp-container]") !== null;
    // in the container: must intersect the container's visible band; outside it: must be on screen
    if (inCont) {
      if (r.bottom <= cont.top || r.top >= cont.bottom) continue;
    } else if (r.bottom <= 0 || r.top >= vh) continue;
    // hit test: the element must be what a finger would touch
    const cx = Math.min(Math.max(r.left + r.width / 2, 1), vw - 1);
    const cy = Math.min(Math.max(r.top + Math.min(r.height / 2, 20), 1), vh - 1);
    const hit = document.elementFromPoint(cx, cy);
    if (hit && !el.contains(hit) && !hit.contains(el)) continue;
    const tag = el.tagName.toLowerCase();
    const role = el.getAttribute("role") || ({ a: "link", button: "button", input: el.type === "checkbox" ? "checkbox" : el.type === "radio" ? "radio" : "textbox", select: "combobox", textarea: "textbox", summary: "button", h1: "heading", h2: "heading", h3: "heading", h4: "heading", label: "label", img: "image", svg: "image" }[tag] || "element");
    const text = String(el.innerText || el.value || "").replace(/\s+/g, " ").trim().slice(0, 160);
    const name = (el.getAttribute("aria-label") || el.getAttribute("alt") || (el.labels && el.labels[0] && el.labels[0].innerText) || text || el.getAttribute("placeholder") || el.getAttribute("title") || "").replace(/\s+/g, " ").trim().slice(0, 160);
    if (!name && !["image"].includes(role)) continue;
    const interactive = /^(button|link|textbox|combobox|checkbox|radio|tab|switch|menuitem)$/.test(role) || tag === "summary";
    const key = `${tag}|${name}|${Math.round(r.left)}|${Math.round(r.top)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const region = el.closest("[role=dialog],dialog") ? "dialog" : el.closest("[data-testid=demo-drawer]") ? "drawer" : el.closest(".demo-panel") ? "demo bar" : el.closest("header") ? "header" : el.closest(".strip") ? "language strip" : el.closest("footer") ? "footer" : el.closest("main") ? "main" : r.top >= cont.bottom - 1 && cont.mode !== "none" ? "bottom bar" : el.closest("nav") ? (r.left < 120 && vw > 900 ? "side rail" : "bottom bar") : "main";
    const bg = bgOf(el);
    const color = cs.color;
    const border = cs.borderTopWidth !== "0px" && cs.borderTopStyle !== "none" ? `${cs.borderTopWidth} ${cs.borderTopStyle} ${cs.borderTopColor}${tok(norm(cs.borderTopColor))}` : "none";
    out.push({
      tag,
      role,
      name,
      text,
      testid: el.getAttribute("data-testid") || "",
      href: tag === "a" ? el.getAttribute("href") || "" : "",
      interactive,
      region,
      inContainer: !!(cont.mode !== "none" && el.closest("[data-sp-container]")),
      rect: { x: r.left, y: r.top, w: r.width, h: r.height },
      state: [el.disabled && "disabled", el.getAttribute("aria-selected") === "true" && "selected", el.getAttribute("aria-expanded") === "true" && "expanded", el.getAttribute("aria-expanded") === "false" && "collapsed", el.checked && "checked", el.getAttribute("aria-pressed") === "true" && "pressed", el.getAttribute("aria-current") && "current"].filter(Boolean).join(", "),
      style: {
        font: `${cs.fontSize} / ${cs.fontWeight}`,
        color: color + tok(norm(color)),
        background: bg + tok(norm(bg)),
        border,
        radius: cs.borderTopLeftRadius + ltok(cs.borderTopLeftRadius),
        padding: `${cs.paddingTop} ${cs.paddingRight} ${cs.paddingBottom} ${cs.paddingLeft}`,
      },
    });
  }
  return out;
}

function inPageText(cont) {
  const c = document.querySelector("[data-sp-container]");
  const top = [...document.querySelectorAll("header,.demo-panel,.strip")].map((e) => e.innerText).join("\n");
  const bottom = [...document.querySelectorAll("nav")].map((e) => e.innerText).join("\n");
  return { body: (c || document.body).innerText, chrome: (top + "\n" + bottom).trim() };
}

function inPageHScroll() {
  const els = [...document.querySelectorAll("*")].filter((e) => {
    const s = getComputedStyle(e);
    const r = e.getBoundingClientRect();
    return (s.overflowX === "auto" || s.overflowX === "scroll") && e.scrollWidth > e.clientWidth + 8 && r.width > 100 && r.top < window.innerHeight && r.bottom > 0;
  });
  document.querySelectorAll("[data-sp-h]").forEach((e) => e.removeAttribute("data-sp-h"));
  if (!els[0]) return false;
  els[0].setAttribute("data-sp-h", "1");
  els[0].scrollLeft = els[0].scrollWidth;
  return true;
}

// ---- driver ---------------------------------------------------------------------------------------

async function settle(page) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  for (let i = 0; i < 60; i++) {
    const busy = await page.evaluate(() => [...document.querySelectorAll('[data-testid$="busy"],[class*="skeleton"],[class*="spinner"]')].some((e) => e.getBoundingClientRect().width > 0));
    if (!busy) break;
    await page.waitForTimeout(500);
  }
  await page.waitForTimeout(350);
}

async function step(page, s) {
  const sel = (id) => (id.startsWith("css:") ? page.locator(id.slice(4)).first() : page.getByTestId(id).first());
  if (s.click) {
    try {
      await sel(s.click).click({ timeout: 6000 });
    } catch {
      await sel(s.click).evaluate((e) => e.click()); // covered by a sticky bar: tap it by script
    }
  }
  else if (s.clickText) await page.getByText(s.clickText, { exact: false }).first().click({ timeout: 15000 });
  else if (s.fill) await sel(s.fill[0]).fill(s.fill[1]);
  else if (s.select) await sel(s.select[0]).selectOption(s.select[1]);
  else if (s.goto) {
    await page.goto(baseUrl + "/" + s.goto);
    await page.reload();
  } else if (s.wait) await sel(s.wait).waitFor({ timeout: 30000 });
  else if (s.press) await page.keyboard.press(s.press);
  else if (s.reload) await page.reload();
  else if (s.offline !== undefined) await page.context().setOffline(!!s.offline);
  await page.waitForTimeout(250);
}

const contexts = new Map();
let browser;

async function getPage(v, needData) {
  const key = `${v.role}|${v.lang}|${v.viewport}|${needData}`;
  if (contexts.has(key)) return contexts.get(key);
  const vp = manifest.viewports[v.viewport];
  const context = await browser.newContext({
    viewport: { width: vp.w, height: vp.h },
    deviceScaleFactor: vp.dpr,
    isMobile: vp.mobile,
    hasTouch: vp.mobile,
    reducedMotion: "reduce",
    locale: "en-IN",
    timezoneId: "Asia/Kolkata",
    permissions: ["microphone"],
    serviceWorkers: "block",
    acceptDownloads: true,
  });
  await context.clock.setFixedTime(FIXED_TIME);
  await context.addInitScript(INIT);
  const page = await context.newPage();
  page.on("dialog", (d) => void d.accept());
  await page.goto(baseUrl + "/");
  await page.evaluate(([c, l]) => { localStorage.clear(); localStorage.setItem("cc.consent", c); localStorage.setItem("cc.role", "judge"); localStorage.setItem("cc.lang", l); }, [CONSENT, v.lang]);
  if (needData) {
    await page.goto(baseUrl + "/#/judge");
    await page.reload();
    await page.getByTestId("load-demo").click();
    await page.getByTestId("demo-loaded").waitFor({ timeout: 60000 });
  }
  await page.evaluate((r) => localStorage.setItem("cc.role", r), v.role);
  const entry = { page, context };
  contexts.set(key, entry);
  return entry;
}

async function gotoRoute(page, route) {
  await page.goto(baseUrl + "/#" + route);
  await page.reload();
  await settle(page);
}

function slug(s) {
  return s.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "").toLowerCase();
}

async function capture(page, ctxInfo) {
  // ctxInfo: { dir, base, screen, state, role, lang, viewport, dataLabel }
  const vp = manifest.viewports[ctxInfo.viewport];
  fs.mkdirSync(ctxInfo.dir, { recursive: true });
  await settle(page);
  const cont = await page.evaluate(inPageFindContainer);
  const meta = { ...ctxInfo, dpr: vp.dpr, vw: vp.w, vh: vp.h, container: cont, slices: [], hscroll: null, checks: [] };
  await page.evaluate(inPageScrollTo, 0);
  await page.waitForTimeout(150);
  const file = `${ctxInfo.base}.png`;
  await page.screenshot({ path: path.join(ctxInfo.dir, file), animations: "disabled", caret: "hide" });
  meta.viewportFile = file;
  const texts = await page.evaluate(inPageText, cont);
  meta.text = texts;

  // elements, collected at every scroll position and placed in page coordinates
  const all = new Map();
  const place = (e, scrollTop) => {
    const total = cont.top + cont.scrollHeight + (vp.h - cont.bottom);
    let y = e.rect.y;
    if (e.inContainer) y = e.rect.y - cont.top + scrollTop + cont.top;
    else if (cont.mode !== "none" && e.rect.y >= cont.bottom - 1) y = total - (vp.h - e.rect.y);
    return { x: e.rect.x, y, w: e.rect.w, h: e.rect.h };
  };
  const addAll = (els, scrollTop) => {
    for (const e of els) {
      const pg = place(e, scrollTop);
      const k = `${e.tag}|${e.name}|${Math.round(pg.x)}|${Math.round(pg.y)}`;
      if (!all.has(k)) all.set(k, { ...e, page: pg });
    }
  };
  addAll(await page.evaluate(inPageCollect, cont), 0);

  // slices
  const scrollable = cont.mode !== "none" && cont.scrollHeight > cont.clientHeight + 4;
  if (scrollable) {
    const overlap = 80;
    const band = cont.clientHeight;
    const maxTop = cont.scrollHeight - cont.clientHeight;
    const tops = [];
    for (let y = 0; y < maxTop; y += band - overlap) tops.push(y);
    tops.push(maxTop);
    let n = 0;
    let last = -1;
    for (const y of tops) {
      const actual = await page.evaluate(inPageScrollTo, y);
      if (actual === last) continue;
      last = actual;
      await page.waitForTimeout(150);
      n += 1;
      const f = `${ctxInfo.base}-s${String(n).padStart(2, "0")}.png`;
      await page.screenshot({ path: path.join(ctxInfo.dir, f), animations: "disabled", caret: "hide" });
      meta.slices.push({ file: f, scrollTop: actual });
      addAll(await page.evaluate(inPageCollect, { ...cont, scrollTop: actual }), actual);
    }
    await page.evaluate(inPageScrollTo, 0);
  }

  // horizontal scroll
  if (await page.evaluate(inPageHScroll)) {
    await page.waitForTimeout(150);
    const f = `${ctxInfo.base}-hscroll.png`;
    await page.screenshot({ path: path.join(ctxInfo.dir, f), animations: "disabled", caret: "hide" });
    meta.hscroll = f;
    await page.evaluate(() => { const e = document.querySelector("[data-sp-h]"); if (e) e.scrollLeft = 0; });
  }

  // number the elements top to bottom: interactive first when over the cap
  let list = [...all.values()];
  const CAP = 60;
  if (list.length > CAP) {
    const rank = (e) => (e.interactive ? 0 : e.role === "heading" ? 1 : 2);
    list = list.sort((a, b) => rank(a) - rank(b) || a.page.y - b.page.y).slice(0, CAP);
  }
  list.sort((a, b) => a.page.y - b.page.y || a.page.x - b.page.x);
  list.forEach((e, i) => {
    e.id = `E${i + 1}`;
    e.pct = { x: +((e.rect.x / vp.w) * 100).toFixed(1), y: +((e.rect.y / vp.h) * 100).toFixed(1), w: +((e.rect.w / vp.w) * 100).toFixed(1), h: +((e.rect.h / vp.h) * 100).toFixed(1) };
  });
  meta.elements = list;

  // safety checks on what is on screen
  const bodyText = texts.body + "\n" + texts.chrome;
  if (SECRET.test(bodyText)) meta.checks.push({ rule: "personal-or-secret-pattern", ok: false, detail: bodyText.match(SECRET)[0].slice(0, 30) });
  if (ctxInfo.data && !DEMO_WORD.test(bodyText)) meta.checks.push({ rule: "demo-label-missing", ok: false, detail: "no 'Demo' or 'Simulated' text on a screen with data" });
  for (const c of meta.checks) {
    if ((ctxInfo.known || []).includes(c.rule)) c.known = true; // a gap in the product, reported in the pack, not a capture failure
    else failures.push(`${ctxInfo.base}: ${c.rule} ${c.detail}`);
  }
  fs.writeFileSync(path.join(ctxInfo.dir, `${ctxInfo.base}.json`), JSON.stringify(meta, null, 1));
  index.push({ dir: path.relative(outDir, ctxInfo.dir), base: ctxInfo.base, screen: ctxInfo.screen, state: ctxInfo.state, role: ctxInfo.role, lang: ctxInfo.lang, viewport: ctxInfo.viewport, slices: meta.slices.length, elements: list.length });
  log(`  ${ctxInfo.base}: ${meta.slices.length} slices, ${list.length} elements`);
  return meta;
}

// ---- the Demo Studio sequence ---------------------------------------------------------------------

async function runDemoSequence(screen, dir, order) {
  const v = screen.variants[0];
  const { page } = await getPage({ ...v }, false);
  await page.evaluate(() => localStorage.setItem("cc.role", "judge"));
  await page.goto(baseUrl + "/#/demo?step=1");
  await page.reload();
  await settle(page);
  let n = order;
  const cap = async (state) => {
    n += 1;
    const base = `${String(n).padStart(2, "0")}-${screen.id}_${state}_${v.role}_${v.lang}_${v.viewport}`;
    await capture(page, { dir, base, screen: screen.id, state, role: v.role, lang: v.lang, viewport: v.viewport, data: true });
  };
  const next = async () => { await page.getByTestId("demo-next").click(); await page.waitForTimeout(400); await settle(page); };
  const want = new Set(v.states);
  await page.getByTestId("demo-begin").click();
  await page.waitForURL(/#\/check/);
  await settle(page);
  await page.getByTestId("paper-details").locator("summary").click();
  await page.getByTestId("paper-make").click();
  await page.getByTestId("paper-code").waitFor({ timeout: 60000 });
  if (want.has("s2-paper")) await cap("s2-paper");
  await next();
  await page.getByTestId("demo-make-sheets").click();
  await page.getByTestId("demo-sheet-list").locator("li").nth(19).waitFor({ timeout: 300000 });
  if (want.has("s3-sheets")) await cap("s3-sheets");
  await next();
  await page.getByTestId("demo-use-1").click();
  await page.waitForFunction(() => document.querySelector('[data-testid="demo-roll-1"]')?.getAttribute("data-status") === "needs_review", null, { timeout: 90000 });
  await page.getByTestId("demo-autofill").click();
  await page.getByTestId("demo-entry-msg").waitFor({ timeout: 90000 });
  if (want.has("s4-entry")) await cap("s4-entry");
  await next();
  await page.getByTestId("demo-preview-6").click();
  await page.getByTestId("demo-drawer-img").waitFor();
  if (want.has("s5-drawer")) await cap("s5-drawer");
  await page.keyboard.press("Escape");
  await page.getByTestId("demo-preview-1").click();
  for (let i = 0; i < 25; i++) {
    if ((await page.getByTestId("demo-drawer").count()) === 0) break;
    await page.getByTestId("demo-approve").click();
    await page.waitForTimeout(100);
  }
  if (want.has("s5-approved")) await cap("s5-approved");
  await page.getByTestId("demo-finish").click();
  await page.waitForURL(/step=6/, { timeout: 60000 });
  await settle(page);
  if (want.has("s6-counts")) await cap("s6-counts");
  await page.getByTestId("demo-simulate").click();
  await page.waitForURL(/step=7/, { timeout: 120000 });
  await page.getByTestId("demo-cohorts").waitFor();
  if (want.has("s7-cohorts")) await cap("s7-cohorts");
  await next();
  await page.getByTestId("demo-audio").click();
  await page.getByTestId("demo-audio-badge").waitFor({ timeout: 120000 });
  if (want.has("s8-lesson")) await cap("s8-lesson");
  await next();
  await page.getByTestId("practice-next").waitFor();
  if (want.has("s9-practice")) await cap("s9-practice");
  await next();
  await page.getByTestId("demo-chat-text").fill("How do I help children who take the smaller digit from the bigger one?");
  await page.getByTestId("demo-chat-ask").click();
  await page.getByTestId("demo-chat-thread").locator("li").first().waitFor({ timeout: 90000 });
  if (want.has("s10-chat")) await cap("s10-chat");
  await next();
  await page.getByTestId("demo-coach").waitFor({ timeout: 120000 });
  if (want.has("s11-coach")) await cap("s11-coach");
  await page.getByTestId("demo-tab-officer").click();
  await page.getByTestId("demo-dashboard").waitFor();
  if (want.has("s11-officer")) await cap("s11-officer");
  await next();
  await page.getByTestId("demo-post").click();
  await page.getByTestId("before-after").waitFor({ timeout: 60000 });
  if (want.has("s12-post")) await cap("s12-post");
  return n;
}

// ---- main -------------------------------------------------------------------------------------------

(async () => {
  browser = await chromium.launch({ args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream", "--font-render-hinting=none"] });
  let screenNo = 0;
  for (const screen of manifest.screens) {
    screenNo += 1;
    if (only && !only.includes(screen.id)) continue;
    const dir = path.join(outDir, `${String(screenNo).padStart(2, "0")}-${screen.id}`);
    fs.mkdirSync(dir, { recursive: true });
    log(`${String(screenNo).padStart(2, "0")} ${screen.id}`);
    let order = 0;
    try {
      if (screen.sequence === "demo") {
        order = await runDemoSequence(screen, dir, order);
        continue;
      }
      for (const v of screen.variants) {
        const { page } = await getPage(v, !!screen.data && !screen.id.startsWith("demo"));
        for (const stateId of v.states) {
          order += 1;
          const steps = screen.states?.[stateId] ?? [];
          await gotoRoute(page, screen.route);
          for (const s of steps) {
            try {
              await step(page, s);
            } catch (e) {
              throw new Error(`state ${stateId}, step ${JSON.stringify(s)}: ${String(e.message).split("\n")[0]}`);
            }
          }
          const base = `${String(order).padStart(2, "0")}-${screen.id}_${stateId}_${v.role}_${v.lang}_${v.viewport}`;
          await capture(page, { dir, base, screen: screen.id, state: stateId, role: v.role, lang: v.lang, viewport: v.viewport, data: !!screen.data, known: screen.known_gaps || [] });
          if ((screen.states?.[stateId] ?? []).some((s) => s.offline !== undefined)) await page.context().setOffline(false);
        }
      }
    } catch (e) {
      failures.push(`${screen.id}: ${String(e.message).split("\n")[0]}`);
      log(`  FAILED ${screen.id}: ${String(e.message).split("\n")[0]}`);
    }
  }
  fs.writeFileSync(path.join(outDir, "capture-index.json"), JSON.stringify({ captures: index, failures }, null, 1));
  await browser.close();
  log(`captured ${index.length} states; ${failures.length} failures`);
  process.exit(failures.length ? 1 : 0);
})();
