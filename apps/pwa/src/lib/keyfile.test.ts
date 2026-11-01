import { describe, expect, it } from "vitest";
import { isKeyFile, KeyFileError, parseKeyFile } from "./keyfile";

// Made-up files only: no pilot data is copied into the repository.
describe("answer key files", () => {
  it("reads a list of question numbers and answers, and ignores everything else in the file (no child rows are kept)", () => {
    const list = parseKeyFile("key.json", JSON.stringify([{ question_no: 1, answer: 346 }, { question_no: 3, answer: 85 }]));
    expect(list.answers).toEqual({ 1: 346, 3: 85 });
    const wrapped = JSON.stringify({
      test: { questions: [{ no: 1, correct_answer: 305, class_variants: { "3B": 346 } }, { no: 2, correct_answer: 496 }] },
      classes: [{ class_code: "3A", sheets: [{ roll: 1, answers: [{ q: 1, given: "999" }] }] }],
    });
    const key = parseKeyFile("pilot_answers.json", wrapped);
    expect(key.answers).toEqual({ 1: 305, 2: 496 }); // class variants are not used
    expect(JSON.stringify(key)).not.toContain("999");
  });
  it("reads a table, a list, csv and txt", () => {
    expect(parseKeyFile("k.json", '{"1": 346, "2": "728"}').answers).toEqual({ 1: 346, 2: 728 });
    expect(parseKeyFile("k.json", '[{"n": 3, "answer": 85}]').answers).toEqual({ 3: 85 });
    expect(parseKeyFile("k.csv", "question,answer\n1,346\n2,728\n").answers).toEqual({ 1: 346, 2: 728 });
    expect(parseKeyFile("k.txt", "# key\n1: 346\n2) 728\n3 = 85\n4 - 74\n").answers).toEqual({ 1: 346, 2: 728, 3: 85, 4: 74 });
  });
  it("says what is wrong, in plain words", () => {
    expect(() => parseKeyFile("k.txt", "1: 346\nhello")).toThrow("line 2 is not a question number and an answer");
    expect(() => parseKeyFile("k.json", "{")).toThrow(KeyFileError);
    expect(() => parseKeyFile("k.json", '{"1": 12345}')).toThrow("whole-number answer from 0 to 999");
    expect(() => parseKeyFile("k.json", '{"99": 5}')).toThrow("not a question number");
    expect(() => parseKeyFile("k.csv", "")).toThrow("no question and answer pairs");
    expect(() => parseKeyFile("k.docx", "x")).toThrow("use a .json, .csv or .txt file");
  });
  it("tells key files from pictures and PDFs", () => {
    expect(isKeyFile("a.CSV")).toBe(true);
    expect(isKeyFile("a.pdf")).toBe(false);
  });
});
