import { Note, type AskRequest } from "./schemas.js";

const PYTHON_URL = process.env.PYTHON_URL ?? "http://localhost:8000";

// Project 2: the calls the API makes to the Python service. An interface, so tests can pass a fake.
export interface AskNotesClient {
  // The answer stream's events, as Python sends them (checked by the route). Stops when signal aborts.
  askStream(request: AskRequest, signal: AbortSignal): AsyncIterable<unknown>;
  // One full note, or null if it doesn't exist.
  note(id: number): Promise<Note | null>;
}

// Server-Sent Events: each event is "data: {json}" followed by an empty line.
export async function* readEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<unknown> {
  const decoder = new TextDecoder();
  let buffer = "";
  for await (const bytes of body) {
    buffer += decoder.decode(bytes, { stream: true });
    let end = buffer.indexOf("\n\n");
    while (end !== -1) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      for (const line of block.split("\n")) {
        if (line.startsWith("data: ")) yield JSON.parse(line.slice("data: ".length));
      }
      end = buffer.indexOf("\n\n");
    }
  }
}

export const askNotesClient: AskNotesClient = {
  async *askStream(request, signal) {
    const response = await fetch(`${PYTHON_URL}/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal, // aborting closes the connection, so Python stops the model
    });
    if (!response.ok || response.body === null) {
      throw new Error(`Python service answered ${response.status} on /ask/stream`);
    }
    yield* readEvents(response.body);
  },
  async note(id) {
    const response = await fetch(`${PYTHON_URL}/notes/${id}`);
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`Python service answered ${response.status} on /notes/${id}`);
    return Note.parse(await response.json()); // check Python's answer too
  },
};
