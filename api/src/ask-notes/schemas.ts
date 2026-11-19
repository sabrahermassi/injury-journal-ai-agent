import { z } from "zod";

// Postgres text can't hold the NUL character: reject it here, before Python.
const noNul = (text: string) => !text.includes("\u0000");
const isoDate = z.iso.date();

// What React sends to POST /api/ask/stream.
export const AskRequest = z.object({
  question: z.string().trim().min(1).max(1000).refine(noNul, "must not contain NUL"),
  filters: z
    .object({
      body_part: z.string().min(1).refine(noNul, "must not contain NUL").optional(),
      min_severity: z.number().int().min(1).max(10).optional(),
      date_from: isoDate.optional(),
      date_to: isoDate.optional(),
    })
    .optional(),
  top_k: z.number().int().min(1).max(20).optional(),
});
export type AskRequest = z.infer<typeof AskRequest>;

// What the Python service sends back.
export const Citation = z.object({
  note_id: z.number().int(),
  chunk_id: z.number().int(),
  start: z.number().int().min(0),
  end: z.number().int().min(0),
  quote: z.string(),
});

export const AskResult = z.object({
  answer: z.string(),
  citations: z.array(Citation),
  refused: z.boolean(),
  scope: z.enum(["in_scope", "out_of_scope", "urgent"]), // out_of_scope and urgent are never searched
});

// One event of the answer stream. Anything else from Python is rejected.
export const StreamEvent = z.discriminatedUnion("type", [
  z.object({ type: z.literal("status"), text: z.string() }),
  z.object({ type: z.literal("answer"), text: z.string() }),
  z.object({ type: z.literal("reset") }),
  z.object({ type: z.literal("done"), result: AskResult }),
  z.object({ type: z.literal("error"), message: z.string() }),
]);
export type StreamEvent = z.infer<typeof StreamEvent>;

export const Note = z.object({
  id: z.number().int(),
  text: z.string(),
  body_part: z.string().nullable(),
  severity: z.number().int().nullable(),
  note_date: z.string().nullable(),
});
export type Note = z.infer<typeof Note>;
