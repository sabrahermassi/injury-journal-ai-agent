import type { Message } from "ollama";
import { chat } from "./llm.js";
import { InjurySchema, type Injury } from "./schema.js";

const SYSTEM = `You extract injury data from a personal note.
Return JSON with keys: injury, bodyPart, severity (1-10), cause, date (YYYY-MM-DD).
If a value is not in the note, use null. Never guess.`;

export async function extract(note: string, model?: string): Promise<Injury> {
  const messages: Message[] = [
    { role: "system", content: SYSTEM },
    { role: "user", content: note },
  ];

  const first = await chat(messages, model);
  const r1 = InjurySchema.safeParse(JSON.parse(first));
  if (r1.success) return r1.data;

  messages.push(
    { role: "assistant", content: first },
    {
      role: "user",
      content: `Invalid: ${r1.error.message}. Fix it and return JSON only.`,
    },
  );
  const second = await chat(messages, model);
  return InjurySchema.parse(JSON.parse(second));
}
