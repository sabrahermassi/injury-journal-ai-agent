import { readFile } from "node:fs/promises";
import { extract } from "./extract.js";
import type { Injury } from "./schema.js";

const MODELS = ["llama3.2", "qwen2.5:3b", "qwen2.5:7b"];
const FIELDS = ["injury", "bodyPart", "severity", "cause", "date"] as const;

type TestCase = { note: string; expected: Injury };
const testCases: TestCase[] = JSON.parse(
  await readFile("eval/notes.json", "utf8"),
);

function isMatch(actual: unknown, expected: unknown): boolean {
  if (typeof actual === "string" && typeof expected === "string") {
    const actualText = actual.trim().toLowerCase();
    const expectedText = expected.trim().toLowerCase();
    if (actualText === "" || expectedText === "") return false;
    return (
      actualText.includes(expectedText) || expectedText.includes(actualText)
    );
  }
  return actual === expected;
}

for (const model of MODELS) {
  let correctFields = 0;
  let failedNotes = 0;
  let totalMs = 0;

  for (const testCase of testCases) {
    const startTime = Date.now();
    try {
      const result = await extract(testCase.note, model);
      for (const field of FIELDS) {
        if (isMatch(result[field], testCase.expected[field])) {
          correctFields++;
        }
      }
    } catch {
      failedNotes++;
    }
    totalMs += Date.now() - startTime;
  }

  const totalFields = testCases.length * FIELDS.length;
  const percentCorrect = Math.round((correctFields / totalFields) * 100);
  const secondsPerNote = (totalMs / testCases.length / 1000).toFixed(1);

  console.log(
    `${model} | ${percentCorrect}% correct | ${failedNotes} failed | ${secondsPerNote}s per note`,
  );
}
