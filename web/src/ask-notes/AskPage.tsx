import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  fetchNote,
  InvalidQuestionError,
  MAX_QUESTION_LENGTH,
  streamAnswer,
  type Citation,
  type Note,
  type Scope,
  type StreamEvent,
} from "./api";
import "./AskPage.css";

type Phase = "idle" | "streaming" | "done" | "lost";

// Project 2: ask a question, watch the answer arrive, click a citation to see it in its note.
export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState(""); // the question being answered, for Retry
  const [phase, setPhase] = useState<Phase>("idle");
  const [status, setStatus] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [refused, setRefused] = useState(false);
  const [scope, setScope] = useState<Scope>("in_scope");
  const [error, setError] = useState("");
  const [opened, setOpened] = useState<{
    note: Note;
    citation: Citation;
  } | null>(null);
  const controller = useRef<AbortController | null>(null);
  const lookup = useRef(0); // number of the latest citation lookup: older answers are ignored

  // Leaving the page (switching to Search, closing the tab) stops the answer on the server too.
  useEffect(() => () => controller.current?.abort(), []);

  function handleEvent(event: StreamEvent) {
    if (event.type === "status") setStatus(event.text);
    if (event.type === "answer") setAnswer((text) => text + event.text);
    if (event.type === "reset") setAnswer("");
    if (event.type === "done") {
      setAnswer(event.result.answer); // the checked answer replaces the streamed one
      setCitations(event.result.citations);
      setRefused(event.result.refused);
      setScope(event.result.scope);
      setPhase("done");
    }
    if (event.type === "error") {
      setAnswer(""); // a cut-off answer was never checked: don't leave it on screen
      setError(event.message);
      setPhase("lost");
    }
  }

  async function ask(text: string) {
    controller.current?.abort(); // a new question stops the previous answer
    const current = new AbortController();
    controller.current = current;
    setAsked(text);
    setPhase("streaming");
    setStatus("");
    setAnswer("");
    setCitations([]);
    setRefused(false);
    setScope("in_scope");
    setError("");
    setOpened(null);
    lookup.current += 1; // a citation lookup still loading belongs to the old question

    let finished = false;
    try {
      await streamAnswer(
        text,
        (event) => {
          if (event.type === "done" || event.type === "error") finished = true;
          handleEvent(event);
        },
        current.signal,
      );
      if (!finished) throw new Error("stream ended early"); // the connection dropped mid-answer
    } catch (error) {
      if (current.signal.aborted) return; // we stopped it on purpose
      if (error instanceof InvalidQuestionError) {
        setError(
          "The question was rejected. Check it isn't empty or longer than 1000 characters.",
        );
        setPhase("idle"); // no Retry: the same question would be rejected again
        return;
      }
      if (!finished) {
        setAnswer(""); // a cut-off answer was never checked: don't leave it on screen
        setError("Connection lost.");
        setPhase("lost");
      }
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const text = question.trim();
    if (text && text.length <= MAX_QUESTION_LENGTH) void ask(text);
  }

  async function openCitation(citation: Citation) {
    const thisLookup = ++lookup.current;
    try {
      const note = await fetchNote(citation.note_id);
      if (thisLookup === lookup.current) setOpened({ note, citation }); // still the latest click
    } catch {
      if (thisLookup === lookup.current) setError("Could not load that note.");
    }
  }

  function stop() {
    controller.current?.abort(); // closes the connection: the model stops on the server
    setAnswer(""); // the cut-off answer was never checked
    setPhase("idle");
  }

  function closeNote() {
    lookup.current += 1; // a lookup still loading must not reopen it
    setOpened(null);
  }

  return (
    <main>
      <h1>Ask your notes</h1>
      <p className="subtitle">
        Answers come only from your notes, with quotes checked word for word.
      </p>

      <form onSubmit={handleSubmit} className="search-row">
        <input
          type="search"
          placeholder="e.g. did I need an X-ray for my ankle?"
          value={question}
          maxLength={MAX_QUESTION_LENGTH}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <button type="submit" disabled={!question.trim()}>
          Ask
        </button>
        {phase === "streaming" && (
          <button type="button" className="secondary" onClick={stop}>
            Stop
          </button>
        )}
      </form>

      {phase === "streaming" && (
        <p className="status">{status || "Starting"}…</p>
      )}

      {(answer || phase === "done") && (
        <section
          className={`answer ${scope === "urgent" ? "urgent" : refused ? "refused" : ""}`}
        >
          <p>
            {answer}
            {phase === "done" &&
              citations.map((citation, index) => (
                <button
                  key={index}
                  type="button"
                  className="cite"
                  onClick={() => void openCitation(citation)}
                >
                  [{index + 1}]
                </button>
              ))}
          </p>
          {phase === "streaming" && (
            <p className="hint">
              Not checked yet: quotes are checked when the answer is finished.
            </p>
          )}
        </section>
      )}

      {phase === "lost" && (
        <p className="error">
          {error}{" "}
          <button type="button" onClick={() => void ask(asked)}>
            Retry
          </button>
        </p>
      )}
      {phase !== "lost" && error && <p className="error">{error}</p>}

      {opened && (
        <section className="note">
          <h2>
            Note {opened.note.note_date ?? ""}{" "}
            {opened.note.body_part ? `· ${opened.note.body_part}` : ""}
          </h2>
          <p>
            {opened.note.text.slice(0, opened.citation.start)}
            <mark>
              {opened.note.text.slice(
                opened.citation.start,
                opened.citation.end,
              )}
            </mark>
            {opened.note.text.slice(opened.citation.end)}
          </p>
          <button type="button" className="secondary" onClick={closeNote}>
            Close
          </button>
        </section>
      )}
    </main>
  );
}
