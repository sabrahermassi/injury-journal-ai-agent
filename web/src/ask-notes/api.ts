// The shapes the TS API sends back, and the two calls the Ask page makes.

export type Citation = {
  note_id: number;
  chunk_id: number;
  start: number; // where the quote is in the note's text
  end: number;
  quote: string;
};

export type AskResult = {
  answer: string;
  citations: Citation[];
  refused: boolean;
};

export type StreamEvent =
  | { type: "status"; text: string }
  | { type: "answer"; text: string }
  | { type: "reset" }
  | { type: "done"; result: AskResult }
  | { type: "error"; message: string };

export type Note = {
  id: number;
  text: string;
  body_part: string | null;
  severity: number | null;
  note_date: string | null;
};

export const MAX_QUESTION_LENGTH = 1000; // the API rejects longer questions

// The API rejected the question itself (too long, empty...): retrying the same question won't help.
export class InvalidQuestionError extends Error {}

// Ask a question and call onEvent for each event as it arrives (Server-Sent Events).
// Aborting the signal closes the connection, which stops the model on the server.
export async function streamAnswer(
  question: string,
  onEvent: (event: StreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch("/api/ask/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  if (response.status === 400)
    throw new InvalidQuestionError("The question was rejected.");
  if (!response.ok || response.body === null)
    throw new Error(`Ask failed: ${response.status}`);

  const decoder = new TextDecoder();
  const reader = response.body.getReader();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });
    let end = buffer.indexOf("\n\n");
    while (end !== -1) {
      const line = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      if (line.startsWith("data: "))
        onEvent(JSON.parse(line.slice("data: ".length)));
      end = buffer.indexOf("\n\n");
    }
  }
}

export async function fetchNote(id: number): Promise<Note> {
  const response = await fetch(`/api/notes/${id}`);
  if (!response.ok) throw new Error("Could not load the note");
  return response.json();
}
