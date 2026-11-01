// Stage of breakdown for the class, worked out on this phone from the answers she entered. Nothing
// is sent anywhere: the per-child rows stay here, and only the class counts are kept on the card.
// A stage is always "most likely", and every stage line carries a one-minute probe.
import { isEmptyRow, readRow } from "./check";
import { classCounts, classifyChild, type StageCounts } from "./stagecalc";

export type { StageCounts } from "./stagecalc";

/** The class's stage counts. `missed` says, per child position, which concepts she tagged "missed
 *  the teaching on this"; a plain set of positions is the older whole-sheet tag. */
export function stagesFor(
  formKey: string,
  rows: string[][],
  missed: ReadonlySet<number> | ReadonlyMap<number, ReadonlySet<string>>,
): StageCounts | null {
  const tagsOf = (i: number) =>
    missed instanceof Map ? { missed_concepts: [...(missed.get(i) ?? [])] } : { missed: (missed as ReadonlySet<number>).has(i) };
  const results = rows
    .map((row, i) => ({ row, i }))
    .filter(({ row }) => !isEmptyRow(row))
    .map(({ row, i }) => classifyChild(formKey, readRow(row), tagsOf(i)));
  return results.length === 0 ? null : classCounts(results);
}

/** The order the stages read in on the card. */
export const STAGE_ORDER = ["Core", "Input (test)", "Output", "Input (teaching)"] as const;
export const STAGE_KEY: Record<string, string> = {
  Core: "stage.core",
  "Input (test)": "stage.input_test",
  Output: "stage.output",
  "Input (teaching)": "stage.input_teaching",
};
export const PROBE_KEY: Record<string, string> = {
  Core: "stage.probe.core",
  "Input (test)": "stage.probe.input_test",
  Output: "stage.probe.output",
  "Input (teaching)": "stage.probe.input_teaching",
};
