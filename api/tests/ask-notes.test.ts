import request from "supertest";
import { describe, expect, it } from "vitest";
import { createApp } from "../src/app.js";
import { readEvents, type AskNotesClient } from "../src/ask-notes/python-client.js";
import type { AskRequest } from "../src/ask-notes/schemas.js";
import type { SemanticSearchClient } from "../src/semantic-search/python-client.js";

const search: SemanticSearchClient = { search: async () => [], bodyParts: async () => [] };

const DONE = {
  type: "done",
  result: {
    answer: "No X-ray was needed.",
    citations: [{ note_id: 5, chunk_id: 9, start: 10, end: 40, quote: "no X-ray was needed" }],
    refused: false,
  },
};

const NOTE = { id: 5, text: "Saw Dr. Lambert.", body_part: "ankle", severity: 4, note_date: "2026-04-06" };

function fakePython(events: unknown[]): AskNotesClient & { received: AskRequest[] } {
  const received: AskRequest[] = [];
  return {
    received,
    async *askStream(askRequest) {
      received.push(askRequest);
      yield* events;
    },
    async note(id) {
      return id === 5 ? NOTE : null;
    },
  };
}

function app(python: AskNotesClient) {
  return createApp({ semanticSearch: search, askNotes: python });
}

function eventsIn(text: string): unknown[] {
  return text
    .split("\n")
    .filter((line) => line.startsWith("data: "))
    .map((line) => JSON.parse(line.slice("data: ".length)));
}

describe("Ask notes API", () => {
  it("streams Python's events to the browser", async () => {
    const events = [{ type: "status", text: "Searching your notes" }, { type: "answer", text: "No X-ray" }, DONE];
    const python = fakePython(events);
    const response = await request(app(python)).post("/api/ask/stream").send({ question: "X-ray?" });
    expect(response.status).toBe(200);
    expect(response.headers["content-type"]).toContain("text/event-stream");
    expect(eventsIn(response.text)).toEqual(events);
    expect(python.received).toEqual([{ question: "X-ray?" }]);
  });

  it("rejects an empty question or a NUL character with 400 and never calls Python", async () => {
    const python = fakePython([DONE]);
    for (const body of [{ question: "  " }, { question: "knee\u0000" }, { question: "knee", filters: { body_part: "a\u0000" } }]) {
      expect((await request(app(python)).post("/api/ask/stream").send(body)).status).toBe(400);
    }
    expect(python.received).toEqual([]);
  });

  it("stops with an error event when Python sends something unexpected", async () => {
    const response = await request(app(fakePython([{ type: "hacked" }, DONE])))
      .post("/api/ask/stream")
      .send({ question: "knee" });
    expect(eventsIn(response.text)).toEqual([{ type: "error", message: "The AI service sent something unexpected." }]);
  });

  it("sends 'connection lost' when the Python stream drops", async () => {
    const python = fakePython([]);
    python.askStream = async function* () {
      yield { type: "answer", text: "No" };
      throw new Error("socket hang up");
    };
    const response = await request(app(python)).post("/api/ask/stream").send({ question: "knee" });
    expect(eventsIn(response.text)).toEqual([
      { type: "answer", text: "No" },
      { type: "error", message: "Connection to the AI service was lost." },
    ]);
  });

  it("returns one note, 404 for an unknown one, 400 for a bad id", async () => {
    const python = fakePython([]);
    expect((await request(app(python)).get("/api/notes/5")).body).toEqual(NOTE);
    expect((await request(app(python)).get("/api/notes/6")).status).toBe(404);
    expect((await request(app(python)).get("/api/notes/abc")).status).toBe(400);
  });

  it("reads Server-Sent Events even when they arrive cut into pieces", async () => {
    const text = 'data: {"type":"reset"}\n\ndata: {"type":"answer","text":"hi"}\n\n';
    const bytes = new TextEncoder().encode(text);
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        for (let i = 0; i < bytes.length; i += 7) controller.enqueue(bytes.slice(i, i + 7));
        controller.close();
      },
    });
    const events: unknown[] = [];
    for await (const event of readEvents(body)) events.push(event);
    expect(events).toEqual([{ type: "reset" }, { type: "answer", text: "hi" }]);
  });
});
