// /dev/styleguide: every v2 component in every state, for review and for the screenshot loop.
// A developer page reached from judge mode; the sample words are English on purpose (they show
// shapes, not product copy). Presentation only.
import { useState } from "react";
import { useApp } from "../state";
import { useToast } from "../components/toast";
import {
  Avatar,
  AudioPlayer,
  BarChart,
  BigNumber,
  BottomSheet,
  Button,
  Callout,
  Card,
  CardGrid,
  Chip,
  Dialog,
  EmptyState,
  FormGrid,
  List,
  ListRow,
  ProgressMeter,
  Segmented,
  SelectField,
  Skeleton,
  StatusPill,
  StepFlow,
  Table,
  TextField,
  Toggle,
  TopBar,
} from "../ui";

const SWATCHES = ["paper", "surface", "chalk", "tonal", "pen", "pen-container", "good-container", "warn-container", "margin-container", "ink", "muted", "outline"];

export default function StyleGuide() {
  const { tr } = useApp();
  const toast = useToast();
  const [seg, setSeg] = useState("week");
  const [on, setOn] = useState(true);
  const [pressed, setPressed] = useState(false);
  const [dlg, setDlg] = useState(false);
  const [sheet, setSheet] = useState(false);
  return (
    <section aria-labelledby="sg-title" data-testid="styleguide">
      <TopBar title="Style guide">
        <StatusPill tone="info">v2 components</StatusPill>
      </TopBar>
      <p className="muted" id="sg-title">
        Every component in every state. Tokens: src/styles/tokens.css. Rules: docs/design/STYLEGUIDE.md.
      </p>

      <h2>Colour tokens</h2>
      <div className="ui-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(8rem, 1fr))" }}>
        {SWATCHES.map((s) => (
          <div key={s} style={{ display: "grid", gap: "var(--s1)" }}>
            <span style={{ height: 48, background: `var(--${s})`, border: "1px solid var(--outline)", borderRadius: "var(--r-btn)" }} />
            <span className="muted">--{s}</span>
          </div>
        ))}
      </div>

      <h2>Type scale (five sizes)</h2>
      <div style={{ display: "grid", gap: "var(--s1)" }}>
        <span style={{ fontSize: "var(--text-2xl)", fontWeight: 700 }}>2xl · 32 · the one big number</span>
        <span style={{ fontSize: "var(--text-xl)", fontWeight: 700 }}>xl · 24 · page title</span>
        <span style={{ fontSize: "var(--text-lg)", fontWeight: 700 }}>lg · 20 · section title</span>
        <span style={{ fontSize: "var(--text-md)" }}>md · 18 · body text</span>
        <span style={{ fontSize: "var(--text-sm)" }}>sm · 16 · labels, captions, navigation</span>
      </div>

      <h2>Buttons</h2>
      <div className="ui-card__foot">
        <Button>Filled</Button>
        <Button variant="tonal">Tonal</Button>
        <Button variant="outlined">Outlined</Button>
        <Button variant="text">Text</Button>
        <Button variant="danger">This is wrong</Button>
        <Button icon="mic">With icon</Button>
        <Button disabled>Disabled</Button>
        <Button loading>Loading</Button>
      </div>

      <h2>Chips and status</h2>
      <div className="ui-card__foot">
        <Chip>Plain chip</Chip>
        <Chip pressed={pressed} onClick={() => setPressed(!pressed)}>
          Filter chip
        </Chip>
        <StatusPill>Online</StatusPill>
        <StatusPill tone="good">Checked</StatusPill>
        <StatusPill tone="warn">Waiting to send</StatusPill>
        <StatusPill tone="bad">Held back</StatusPill>
      </div>

      <h2>Form fields</h2>
      <FormGrid>
        <TextField label="Class name" help="Only you see this name." placeholder="Grade 3 A" />
        <TextField label="Number of children" error="Enter a number from 1 to 60." defaultValue="0" />
        <SelectField label="Error" help="The mistake your pupils make most.">
          <option>PV-HEARD</option>
          <option>SUB-SFL</option>
        </SelectField>
        <TextField label="Note" multiline placeholder="What happened?" />
      </FormGrid>
      <Toggle label="Share this session to improve the simulator" checked={on} onChange={setOn} />
      <Segmented
        label="Range"
        value={seg}
        onChange={setSeg}
        options={[
          { value: "week", label: "This week" },
          { value: "term", label: "This term" },
          { value: "all", label: "All terms" },
        ]}
      />

      <h2>Cards, numbers and progress</h2>
      <CardGrid>
        <Card title="Next step" icon="practice" focus footer={<Button variant="tonal">Start rehearsal</Button>}>
          <p>Rehearse with five pretend children before you try it in class.</p>
        </Card>
        <Card title="My class" icon="users">
          <BigNumber value="11 of 28" label="children show this error" />
          <ProgressMeter value={2} max={6} label="2 of 6 lessons done" />
        </Card>
        <Card title="A list" icon="cards">
          <List>
            <ListRow title="Lesson 1" sub="Show it with bundles" icon="speaker" href="#/styleguide" />
            <ListRow title="Lesson 2" sub="Ask the child to explain" icon="speaker" onClick={() => toast("Opened lesson 2", "ok")} />
            <ListRow title="Lesson 3" icon="speaker" trailing={<StatusPill tone="good">Done</StatusPill>} />
          </List>
        </Card>
      </CardGrid>

      <h2>Callouts</h2>
      <div style={{ display: "grid", gap: "var(--s2)" }}>
        <Callout>Simulated data: this class and these children are made up for the demo.</Callout>
        <Callout tone="warning">No signal. Your answers will be sent when you are back online.</Callout>
        <Callout tone="success">Saved. You can close this page.</Callout>
        <Callout tone="error">The photo could not be read. Take it again in better light.</Callout>
      </div>

      <h2>Empty, loading</h2>
      <CardGrid>
        <Card>
          <EmptyState title="Nothing here yet" text="Enter this term's check to see what your class gets wrong." action={<Button>Enter the check</Button>} />
        </Card>
        <Card>
          <Skeleton label="Loading" lines={4} />
        </Card>
      </CardGrid>

      <h2>Flow, chart, table, audio, avatar</h2>
      <Card>
        <StepFlow
          current={1}
          steps={[
            { label: "Photograph", icon: "camera" },
            { label: "Review", icon: "check" },
            { label: "Class card", icon: "cards" },
            { label: "Practise", icon: "practice" },
          ]}
        />
      </Card>
      <CardGrid>
        <Card title="Children by error (simulated)">
          <BarChart
            label="Children by error"
            rows={[
              { label: "PV-HEARD", value: 11 },
              { label: "SUB-SFL", value: 7 },
              { label: "ADD-NOCARRY", value: 4 },
            ]}
            caption="Simulated data. Counts of children, from the check."
          />
        </Card>
        <Card title="Voice lesson">
          <AudioPlayer script="Today we show the number with bundles of ten. Ask: how many tens, how many ones?" scriptLabel="Read the script" />
        </Card>
        <Card title="Pretend children">
          <div className="ui-card__foot">
            {[1, 2, 3, 4, 5].map((n) => (
              <Avatar key={n} seed={n} label={`Child ${n}`} />
            ))}
          </div>
        </Card>
      </CardGrid>
      <Table
        caption="Cohorts"
        columns={["Cohort", "Teachers", "Status"]}
        rows={[
          ["PV-HEARD · Block A", "18", <StatusPill key="a" tone="good">Active</StatusPill>],
          ["SUB-SFL · Block B", "15", <StatusPill key="b" tone="warn">Proposed</StatusPill>],
        ]}
      />

      <h2>Toast, dialog, bottom sheet</h2>
      <div className="ui-card__foot">
        <Button variant="tonal" onClick={() => toast("Saved on this phone", "ok")}>
          Show a toast
        </Button>
        <Button variant="outlined" onClick={() => setDlg(true)}>
          Open a dialog
        </Button>
        <Button variant="outlined" onClick={() => setSheet(true)}>
          Open a bottom sheet
        </Button>
      </div>
      <Dialog open={dlg} onClose={() => setDlg(false)} title="Delete this class?" closeLabel={tr("common.close")}>
        <p>Deleting a class also asks our server to erase its counts.</p>
        <Button variant="danger" onClick={() => setDlg(false)}>
          Delete class
        </Button>
      </Dialog>
      <BottomSheet open={sheet} onClose={() => setSheet(false)} title="Keep the app on your phone" closeLabel={tr("common.close")}>
        <p>Opens fast, uses little data, and works without signal.</p>
      </BottomSheet>
    </section>
  );
}
