import express from "express";
import { SearchRequest } from "./schemas.js";
import type { PythonClient } from "./python-client.js";

export function createApp(python: PythonClient) {
  const app = express();
  app.use(express.json());

  app.get("/api/body-parts", async (_req, res) => {
    try {
      res.json(await python.bodyParts());
    } catch (error) {
      console.error(error);
      res.status(502).json({ error: "The search service is not available." });
    }
  });

  app.post("/api/search", async (req, res) => {
    const parsed = SearchRequest.safeParse(req.body);
    if (!parsed.success) {
      res
        .status(400)
        .json({ error: "Invalid search.", issues: parsed.error.issues });
      return;
    }
    try {
      res.json(await python.search(parsed.data));
    } catch (error) {
      console.error(error);
      res.status(502).json({ error: "The search service is not available." });
    }
  });

  return app;
}
