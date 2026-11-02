# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: practice.spec.ts >> the AI map shows 10 calls by 5 layers and the audit trail shows metadata only
- Location: e2e\practice.spec.ts:194:1

# Error details

```
Error: expect(locator).toHaveCount(expected) failed

Locator:  getByTestId('ai-map').locator('tbody tr')
Expected: 10
Received: 13
Timeout:  5000ms

Call log:
  - Expect "toHaveCount" getByTestId('ai-map').locator('tbody tr') with timeout 5000ms
  - waiting for getByTestId('ai-map').locator('tbody tr')
    - locator resolved to 0 elements
    - unexpected value "0"
    13 × locator resolved to 13 elements
       - unexpected value "13"

```

# Page snapshot

```yaml
- generic [ref=e2]:
  - generic [ref=e4]:
    - banner [ref=e5]:
      - link "Cohort Coach" [ref=e6] [cursor=pointer]:
        - /url: "#/roles"
      - status "Estimated download speed from your phone's browser. Upload speed is not shown." [ref=e7]:
        - generic [ref=e10]: Online
        - generic [ref=e14]:
          - generic [ref=e15]: Good signal ·
          - text: 10+ Mbps
    - main [ref=e16]:
      - region [ref=e17]:
        - heading "AI map" [level=1] [ref=e18]
        - paragraph [ref=e19]: Every Claude call, what it does, and its five layers.
        - paragraph [ref=e20]: Judge view. Not shown to teachers.
        - table [ref=e22]:
          - rowgroup [ref=e23]:
            - row [ref=e24]:
              - columnheader "#" [ref=e25]
              - columnheader "Input" [ref=e26]
              - columnheader "Processing" [ref=e27]
              - columnheader "Guardrails" [ref=e28]
              - columnheader "Evaluation" [ref=e29]
              - columnheader "Output" [ref=e30]
          - rowgroup [ref=e31]:
            - row [ref=e32]:
              - rowheader "1. Child voices claude-sonnet-5-5 · v3" [ref=e33]:
                - text: 1. Child voices
                - generic [ref=e34]: claude-sonnet-5-5 · v3
              - cell "Child persona, language, the teacher's labelled move, and the exact wrong answer the engine chose." [ref=e35]
              - cell "Claude writes one line of at most 30 words around the engine's number." [ref=e36]
              - cell "Every number must equal the engine's answer; length, language and script checks; pre-filter; one retry, then a template line." [ref=e37]
              - 'cell "200 scripted turns: numbers match 100%; realism rated 1 to 5 by humans (pending until rated)." [ref=e38]'
              - cell "A short spoken line in the child's voice, with an AI-layers overlay in judge mode." [ref=e39]
            - row [ref=e40]:
              - rowheader "2. Teacher-move labeller claude-haiku-5-5 · v3" [ref=e41]:
                - text: 2. Teacher-move labeller
                - generic [ref=e42]: claude-haiku-5-5 · v3
              - cell "One line the teacher said or typed, wrapped as untrusted data, and the technique's fixed move list." [ref=e43]
              - cell "A small model returns one label and a confidence." [ref=e44]
              - cell "The label must be in the fixed list (JSON schema); low confidence becomes 'other', which changes nothing; off-task and injection lines become 'off_task'." [ref=e45]
              - cell "150 human-labelled lines, agreement at least 85%." [ref=e46]
              - cell "A move label that moves the simulation's child state; never shown as a score." [ref=e47]
            - row [ref=e48]:
              - rowheader "3. Rehearsal feedback claude-sonnet-5-5 · v2" [ref=e49]:
                - text: 3. Rehearsal feedback
                - generic [ref=e50]: claude-sonnet-5-5 · v2
              - cell "The rehearsal transcript (stays on her phone unless she shares it) and the rubric of moves." [ref=e51]
              - cell "Claude writes two strengths and one idea to try, each with a quote." [ref=e52]
              - cell "Each quote must appear word for word in the transcript; points only from the rubric; no scores; pre-filter and call 7." [ref=e53]
              - 'cell "30 transcripts: quotes 100% valid; usefulness rated by teachers (pending until rated)." [ref=e54]'
              - cell "A private feedback card with a Checked badge and a 'this is wrong' flag." [ref=e55]
            - row [ref=e56]:
              - rowheader "4. Mentor method capture claude-sonnet-5-5 · v1" [ref=e57]:
                - text: 4. Mentor method capture
                - generic [ref=e58]: claude-sonnet-5-5 · v1
              - cell "The mentor's transcribed answers, split into numbered sentences." [ref=e59]
              - cell "Claude turns them into steps, each citing the sentence ids it came from." [ref=e60]
              - cell "Every cited id must exist; only what she said; she approves, then a reviewer approves." [ref=e61]
              - cell "Mentor edit size and reviewer acceptance, reported when mentors exist." [ref=e62]
              - cell "A method card that can feed the next cohort's track." [ref=e63]
            - row [ref=e64]:
              - rowheader "5. Track drafting claude-opus-5-5 · v2" [ref=e65]:
                - text: 5. Track drafting
                - generic [ref=e66]: claude-opus-5-5 · v2
              - cell "The error, language, up to 3 approved method cards and the lesson plan structure." [ref=e67]
              - cell "The strongest model drafts offline in a batch at half price." [ref=e68]
              - cell "Arithmetic checked by code; class numbers are slots filled by code; reading level; call 7; then a reviewer and a mentor approve." [ref=e69]
              - cell "Share of drafts accepted with minor edits; arithmetic correctness (code-checked)." [ref=e70]
              - cell "A reviewed track published as audio, with Checked and Reviewed badges." [ref=e71]
            - row [ref=e72]:
              - rowheader "6. Reflection digest claude-haiku-5-5 · v1" [ref=e73]:
                - text: 6. Reflection digest
                - generic [ref=e74]: claude-haiku-5-5 · v1
              - cell "Short reflections with names and schools removed by code first." [ref=e75]
              - cell "A small model assigns each reflection to a theme." [ref=e76]
              - cell "Code strips names before the call; the model never states a count, code counts the themes." [ref=e77]
              - cell "Mentor usefulness rating (pending until mentors rate)." [ref=e78]
              - cell "A weekly digest for the mentor." [ref=e79]
            - row [ref=e80]:
              - rowheader "7. Output checker claude-haiku-5-5 · v4" [ref=e81]:
                - text: 7. Output checker
                - generic [ref=e82]: claude-haiku-5-5 · v4
              - cell "Candidate text, audience, language, target error, and what code already checked." [ref=e83]
              - 'cell "A small model scores the rubric: tone, safety, stereotypes, language, fit, reading level, maths, statistics, injection." [ref=e84]'
              - cell "Includes rejected-before examples from reviewers; unsure means fail; a fail goes to a human or a template." [ref=e85]
              - 'cell "Red-team set: 0 unsafe outputs reach a teacher." [ref=e86]'
              - cell "A pass or fail verdict with a reason for the team and a one-line reason for the user." [ref=e87]
            - row [ref=e88]:
              - rowheader "8. Answer reading claude-haiku-5-5 · v1" [ref=e89]:
                - text: 8. Answer reading
                - generic [ref=e90]: claude-haiku-5-5 · v1
              - cell "One sheet photo (base64 JPEG). It carries no name or roll number. The model is never told the expected answers." [ref=e91]
              - cell "A small vision model transcribes digits; a stronger model retries doubtful reads." [ref=e92]
              - cell "Reads outside the correct and error answers, or below the confidence bar, go to the teacher; Devanagari digits normalised; the photo is deleted right after." [ref=e93]
              - 'cell "Hand-keyed set: at least 98% of auto-accepted reads correct, at most 15% sent to the teacher." [ref=e94]'
              - cell "Per-box digits for the engine to diagnose, on her phone." [ref=e95]
            - row [ref=e96]:
              - rowheader "10. Demo teacher (judge mode only) claude-haiku-5-5 · v1" [ref=e97]:
                - text: 10. Demo teacher (judge mode only)
                - generic [ref=e98]: claude-haiku-5-5 · v1
              - cell "The scenario, the approved move list, the style, the transcript so far and the engine's state of the five simulated children." [ref=e99]
              - cell "A small model picks one approved move and writes a line of at most 25 words in the chosen style." [ref=e100]
              - cell "The move id must be on the approved list for the style; every number must come from the scenario's allowed set; no answer leak beyond the style; no check item; on any failure the move's template line is used. The server refuses the call outside a judge session." [ref=e101]
              - 'cell "20 runs per style: approved ids 100%, numbers in the allowed set, and the experienced runs cover more rubric points than the struggling runs in at least 18 of 20 pairs (rubric coverage is internal to the eval, never shown to a teacher)." [ref=e102]'
              - cell "A teacher line labelled 'AI playing the teacher (demo only)'; never shown to a real teacher, who hears the reviewed model run." [ref=e103]
            - row [ref=e104]:
              - rowheader "11. Sprite item author (offline) claude-sonnet-5-5 · v1" [ref=e105]:
                - text: 11. Sprite item author (offline)
                - generic [ref=e106]: claude-sonnet-5-5 · v1
              - cell "A short brief for one object (for example 'a mango') and the ids of the items that exist." [ref=e107]
              - cell "Claude drafts one item as a list of whitelisted shapes with integer numbers and palette-slot colours, plus a short English alt text." [ref=e108]
              - cell "Schema; shape and attribute whitelist; integer numbers; palette slots only (no hex); size budget; no text; the item must render at counts 1 and 5 in every palette and as a PNG; pre-filter and no-check-item checks on the words; call 7 on the words; a rejected draft returns the failing rule to the author and is never shown; then a coach approves and a programme officer enables." [ref=e109]
              - 'cell "Pending a live run. Until then the gates are proven by tests: each rule has a failing case." [ref=e110]'
              - cell "A draft item file in content/sprites/drafts/, not loaded by the renderer. It reaches a teacher only inside an enabled pack version. No art is generated at run time." [ref=e111]
            - row [ref=e112]:
              - rowheader "12. Chat question class claude-haiku-5-5 · v1" [ref=e113]:
                - text: 12. Chat question class
                - generic [ref=e114]: claude-haiku-5-5 · v1
              - cell "The question with names, roll numbers and phone numbers already replaced, and its language." [ref=e115]
              - cell "A small model picks one of six labels with a confidence; below 0.6 the question counts as unclear." [ref=e116]
              - cell "Code checks safety and welfare words first and routes those to the coach without any model call; a replaced child name makes it child-specific; the question is data, never an instruction; any failure means unclear." [ref=e117]
              - cell "The 50-prompt chat red team (injection, child-specific, safety, off-topic, Tamil, Hindi and English mixing) must send nothing unsafe on its own." [ref=e118]
              - cell "One label that decides who sees the question and whether a draft is made." [ref=e119]
            - row [ref=e120]:
              - rowheader "13. Chat reply draft claude-sonnet-5-5 · v1" [ref=e121]:
                - text: 13. Chat reply draft
                - generic [ref=e122]: claude-sonnet-5-5 · v1
              - cell "The masked question, the language, her cohort's error and the approved sentences retrieved for it (approved lessons and strategies)." [ref=e123]
              - cell "The model writes at most 120 words and must quote the approved sentence behind each statement, or return no answer and why." [ref=e124]
              - cell "Every citation must name a retrieved source and quote it word for word; code checks sums, personal data, class numbers, pilot items and scores; call 7 checks tone and fit; it is a draft until a person sends it. It goes out on its own only if every auto-send gate passes, labelled as AI-generated." [ref=e125]
              - cell "Share of drafts sent as is, edited or discarded, and corrections after an automatic send, reported by code in docs/evidence/chat_metrics.json (simulated data in the demo)." [ref=e126]
              - cell "A draft in the mentor's inbox with its sources; to the teacher only through a person or the auto-send gates, with a label." [ref=e127]
            - row [ref=e128]:
              - rowheader "14. Assistant answer claude-sonnet-5-5 · v1" [ref=e129]:
                - text: 14. Assistant answer
                - generic [ref=e130]: claude-sonnet-5-5 · v1
              - cell "The question (wrapped as data), the role, the language, and up to six passages retrieved from the role's own namespaces, with rubric rows for the judge." [ref=e131]
              - cell "A mid-tier model writes at most 120 words from the passages, cites each with a verbatim quote, and names the rubric rows it rests on, or returns no answer and why." [ref=e132]
              - cell "The scope comes from the server, never the prompt; retrieval cannot reach another role's namespace; code checks every quote word for word, the rubric rows, length, personal data, scores, claims of action and pressure words; the status labels, how to check and limits come from the rubric map, not the model; any failure falls back to an extract from the passages or to no answer." [ref=e133]
              - 'cell "evals/assistant_eval.md: retrieval, scope and citation checks per role by code; the model''s wording is not scored there (pending a live run)." [ref=e134]'
              - cell "An answer with status labels, sources (file, slide, video), how to check it and its limits; or an abstention that says what the assistant can help with." [ref=e135]
        - region [ref=e136]:
          - heading "Try to break it" [level=2] [ref=e137]
          - paragraph [ref=e138]: These lines are prepared. Each one runs through the real pre-filter, and you see which check stopped it.
          - generic [ref=e139]:
            - button "Tell the system to ignore its rules" [ref=e140] [cursor=pointer]
            - button "Insult a child" [ref=e141] [cursor=pointer]
            - button "Share a phone number" [ref=e142] [cursor=pointer]
            - button "Name a child with a roll number" [ref=e143] [cursor=pointer]
      - link "Ask the assistant" [ref=e144] [cursor=pointer]:
        - /url: "#/assistant?from=aimap"
    - navigation "Screens" [ref=e145]:
      - link "Home" [ref=e146] [cursor=pointer]:
        - /url: "#/home"
      - link "Enter check" [ref=e150] [cursor=pointer]:
        - /url: "#/check"
      - link "My class" [ref=e155] [cursor=pointer]:
        - /url: "#/cards"
      - link "Practice" [ref=e160] [cursor=pointer]:
        - /url: "#/practice"
      - button "More" [ref=e166] [cursor=pointer]
  - status
```

# Test source

```ts
  97  |   // the only other call is the server's answer to "is this the judge demo?" (no teacher data)
  98  |   for (const r of requests.filter((x) => x.url().endsWith("/api/roles"))) expect(r.method()).toBe("GET");
  99  |   expect(turns).toHaveLength(7);
  100 | });
  101 | 
  102 | test("the AI-layers overlay matches the API trace, for judges only", async ({ page }) => {
  103 |   const turns: TurnJson[] = [];
  104 |   await rehearse(page, turns);
  105 |   await expect(page.getByTestId("layers-panel")).toHaveCount(0);
  106 |   await page.getByTestId("sec-judge").click();
  107 |   await page.getByTestId("layers-toggle").click();
  108 |   await page.getByTestId("sec-class").click();
  109 |   const panel2 = page.getByTestId("turn-2").getByTestId("layers-panel");
  110 |   const t2 = turns[1]!;
  111 |   await expect(panel2.getByTestId("layer-input")).toHaveText("Tell me how you got that.");
  112 |   await expect(panel2.getByTestId("layer-label")).toContainText(t2.layers.processing.label.move_id);
  113 |   await expect(panel2.getByTestId("layer-engine")).toContainText(String(t2.layers.processing.engine.answer));
  114 |   await expect(panel2.getByTestId("layer-eval")).toContainText(`${t2.layers.evaluation.latency_ms} ms`);
  115 |   await expect(panel2.getByTestId("layer-output")).toHaveText(`${t2.layers.output.source} · ${t2.layers.output.badge}`);
  116 |   for (const label of ["Input", "Processing", "Guardrails", "Evaluation", "Output"]) await expect(panel2).toContainText(label);
  117 | 
  118 |   await chooseRole(page, "teacher");
  119 |   await page.goto("/#/practice?seed=5");
  120 |   await page.getByTestId("start-practice").click();
  121 |   await expect(page.getByTestId("layers-toggle")).toHaveCount(0); // not for teachers
  122 |   await expect(page.getByTestId("sec-judge")).toHaveCount(0);
  123 | });
  124 | 
  125 | test("the server request log holds no transcript text (application logs: tests/practice/test_api.py)", async ({ page }) => {
  126 |   await rehearse(page, []);
  127 |   const log = readFileSync(API_LOG, "utf-8");
  128 |   expect(log).toContain("/api/practice/sessions"); // the requests were logged ...
  129 |   for (const line of LINES.filter((l) => !l.startsWith("/tap"))) {
  130 |     expect(log).not.toContain(line); // ... but never what she said
  131 |     expect(log).not.toContain(encodeURIComponent(line));
  132 |   }
  133 |   expect(log).not.toMatch(/52 minus 29|loose ones/);
  134 | });
  135 | 
  136 | test("retry uses the same children", async ({ page }) => {
  137 |   await rehearse(page, []);
  138 |   const names = await page.locator(".kid-name").allInnerTexts();
  139 |   await page.getByTestId("end").click();
  140 |   await expect(page.getByTestId("feedback")).toBeVisible();
  141 |   await page.getByTestId("retry").click();
  142 |   await expect(page.locator(".kid-name")).toHaveText(names);
  143 | });
  144 | 
  145 | test("a class's own counts seat the children, and a slow reply is explained", async ({ page }) => {
  146 |   const bodies: Record<string, unknown>[] = [];
  147 |   page.on("request", (r) => {
  148 |     if (r.method() === "POST" && /\/api\/practice\/sessions$/.test(r.url())) bodies.push(JSON.parse(r.postData() ?? "{}") as Record<string, unknown>);
  149 |   });
  150 |   await page.goto("/#/judge");
  151 |   await page.getByTestId("load-demo").click();
  152 |   await expect(page.getByTestId("demo-loaded")).toBeVisible();
  153 |   await page.goto("/#/home");
  154 |   await page.getByTestId("home-practice").click();
  155 |   await page.getByTestId("start-practice").click();
  156 |   await expect(page.getByTestId("kid-4")).toBeVisible();
  157 |   expect(bodies[0]!["counts"]).toMatchObject({ "SUB-SFL": 11 });
  158 |   expect(bodies[0]!["checked"]).toBe(28);
  159 |   expect(bodies[0]!["scenario"]).toBe("SUB-SFL");
  160 |   await expect(page.getByRole("note")).toContainText("Simulated data");
  161 |   // These seats were never recorded, so the model is not available in recorded mode: a template
  162 |   // line is used and the teacher is told why.
  163 |   await page.getByTestId("say").fill("Who can tell me 52 minus 29?");
  164 |   await page.getByTestId("send").click();
  165 |   await expect(page.getByTestId("reply-1")).toBeVisible();
  166 |   await expect(page.getByText("The AI model is not switched on here, so a simple reply was used.")).toBeVisible();
  167 | });
  168 | 
  169 | test("when practice is paused the teacher can watch a recorded sample", async ({ page }) => {
  170 |   await page.route("**/api/practice/sessions", (route) => route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"paused"}' }));
  171 |   await page.goto("/#/practice");
  172 |   await page.getByTestId("start-practice").click();
  173 |   await expect(page.getByTestId("practice-state")).toHaveText("Practice is paused for today.");
  174 |   await page.getByTestId("watch-sample").click();
  175 |   await expect(page.getByTestId("sample")).toContainText("Tell me how you got that.");
  176 |   await expect(page.getByTestId("sample")).toContainText("recorded sample");
  177 | });
  178 | 
  179 | test("offline, practice says so and sends nothing; everything else still opens", async ({ page }) => {
  180 |   const calls: string[] = [];
  181 |   page.on("request", (r) => {
  182 |     if (r.url().includes("/api/practice")) calls.push(r.url());
  183 |   });
  184 |   await page.goto("/#/judge");
  185 |   await page.getByTestId("offline-toggle").click();
  186 |   await page.goto("/#/practice");
  187 |   await page.getByTestId("start-practice").click();
  188 |   await expect(page.getByTestId("practice-state")).toContainText("Practice needs a connection");
  189 |   expect(calls).toHaveLength(0);
  190 |   await page.goto("/#/check");
  191 |   await expect(page.getByTestId("form-A")).toBeVisible();
  192 | });
  193 | 
  194 | test("the AI map shows 10 calls by 5 layers and the audit trail shows metadata only", async ({ page }) => {
  195 |   await rehearse(page, []);
  196 |   await page.goto("/#/aimap");
> 197 |   await expect(page.getByTestId("ai-map").locator("tbody tr")).toHaveCount(10); // calls 1 to 8, 10 and 11 (call 9 arrives in P10)
      |                                                                ^ Error: expect(locator).toHaveCount(expected) failed
  198 |   await expect(page.getByTestId("ai-map").locator("thead th")).toHaveCount(6);
  199 |   await page.goto("/#/audit");
  200 |   await expect(page.getByTestId("audit-table")).toBeVisible();
  201 |   await expect(page.getByTestId("audit-table").locator("li").first()).toContainText("Checks passed");
  202 |   const text = await page.locator("main").innerText();
  203 |   expect(text).toContain("c01_child_voice");
  204 |   expect(text).toContain("c07_checker");
  205 |   for (const line of LINES.filter((l) => !l.startsWith("/tap"))) expect(text).not.toContain(line);
  206 | });
  207 | 
  208 | test("feedback thumbs stay on the phone, the flag goes to the team; sharing is off by default and remembered", async ({ page }) => {
  209 |   const flags: string[] = [];
  210 |   page.on("request", (r) => {
  211 |     if (/\/api\/feedback$/.test(r.url())) flags.push(r.postData() ?? "");
  212 |   });
  213 |   await page.goto("/#/practice?seed=5");
  214 |   const share = page.getByRole("checkbox");
  215 |   await expect(share).not.toBeChecked(); // off by default
  216 |   await share.check();
  217 |   await page.waitForTimeout(500); // the choice is written to IndexedDB asynchronously; reloading at once races it
  218 |   await page.reload();
  219 |   await page.goto("/#/practice?seed=5");
  220 |   await expect(page.getByRole("checkbox")).toBeChecked(); // the choice is saved
  221 |   await page.getByRole("checkbox").uncheck();
  222 |   await rehearse(page, []);
  223 |   await page.getByTestId("end").click();
  224 |   await expect(page.getByTestId("strength-0")).toBeVisible();
  225 |   await page.getByTestId("strength-0").getByRole("button", { name: /Helpful/ }).first().click();
  226 |   await expect(page.getByText("Thanks for telling us.")).toBeVisible();
  227 |   await page.getByRole("button", { name: "This is wrong" }).click();
  228 |   await expect(page.getByText("The team will review this card")).toBeVisible();
  229 |   await expect.poll(() => flags.length).toBe(1);
  230 |   expect(JSON.parse(flags[0]!)).toMatchObject({ kind: "card_flag", context: "practice" });
  231 |   const kept = await page.evaluate(
  232 |     () =>
  233 |       new Promise<{ ratings?: Record<string, string>; flags: number }>((resolve, reject) => {
  234 |         const open = indexedDB.open("cohort-coach");
  235 |         open.onerror = () => reject(open.error);
  236 |         open.onsuccess = () => {
  237 |           const db = open.result;
  238 |           const tr = db.transaction(["transcripts", "syncQueue"]);
  239 |           const rows = tr.objectStore("transcripts").getAll();
  240 |           const queue = tr.objectStore("syncQueue").getAll();
  241 |           tr.oncomplete = () => resolve({ ratings: (rows.result[0] as { ratings?: Record<string, string> }).ratings, flags: (queue.result as { kind: string }[]).filter((q) => q.kind === "flag").length });
  242 |         };
  243 |       }),
  244 |   );
  245 |   expect(Object.values(kept.ratings ?? {})).toContain("up");
  246 |   expect(kept.flags).toBe(0); // it went to the team, not into the phone queue
  247 | });
  248 | 
  249 | test("the screen says what she is practising and lists the moves to try", async ({ page }) => {
  250 |   await page.goto("/#/practice?seed=5");
  251 |   await expect(page.getByTestId("goal-intro")).toContainText("take the smaller digit from the larger");
  252 |   await page.getByTestId("start-practice").click();
  253 |   await expect(page.getByTestId("goal")).toBeHidden(); // its own section, so the class comes first
  254 |   await page.getByTestId("sec-goal").click();
  255 |   await expect(page.getByTestId("goal")).toBeVisible();
  256 |   await expect(page.getByTestId("goal")).toContainText("What to practise");
  257 |   expect(await page.getByTestId("goal").locator("li").count()).toBeGreaterThanOrEqual(3);
  258 |   await expect(page.getByTestId("goal")).toContainText(/bundle/i);
  259 | });
  260 | 
```