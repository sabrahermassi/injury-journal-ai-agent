import { Router, type Response } from "express";
import { AskRequest, StreamEvent } from "./schemas.js";
import type { AskNotesClient } from "./python-client.js";

function send(res: Response, event: StreamEvent): void {
  res.write(`data: ${JSON.stringify(event)}\n\n`);
}

// Project 2 routes: /api/ask/stream and /api/notes/:id.
export function askNotesRoutes(python: AskNotesClient): Router {
  const router = Router();

  router.post("/api/ask/stream", async (req, res) => {
    const parsed = AskRequest.safeParse(req.body);
    if (!parsed.success) {
      res.status(400).json({ error: "Invalid question.", issues: parsed.error.issues });
      return;
    }

    // The user left (tab closed, new question, page changed): stop the Python stream too.
    const controller = new AbortController();
    res.on("close", () => controller.abort());

    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    });
    try {
      for await (const raw of python.askStream(parsed.data, controller.signal)) {
        const event = StreamEvent.safeParse(raw); // check every event from Python
        if (!event.success) {
          send(res, { type: "error", message: "The AI service sent something unexpected." });
          break;
        }
        send(res, event.data);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        console.error(error);
        send(res, { type: "error", message: "Connection to the AI service was lost." });
      }
    }
    res.end();
  });

  router.get("/api/notes/:id", async (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id < 1) {
      res.status(400).json({ error: "Invalid note id." });
      return;
    }
    try {
      const note = await python.note(id);
      if (note === null) {
        res.status(404).json({ error: "Note not found." });
        return;
      }
      res.json(note);
    } catch (error) {
      console.error(error);
      res.status(502).json({ error: "The notes service is not available." });
    }
  });

  return router;
}
