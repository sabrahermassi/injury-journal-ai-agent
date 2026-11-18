import express from "express";
import { semanticSearchRoutes } from "./semantic-search/routes.js";
import type { SemanticSearchClient } from "./semantic-search/python-client.js";

// The Python clients each project needs. Tests pass fakes.
export type Clients = {
  semanticSearch: SemanticSearchClient;
};

// One TS API for every project: each project adds its own routes here.
export function createApp(clients: Clients) {
  const app = express();
  app.use(express.json());
  app.use(semanticSearchRoutes(clients.semanticSearch));
  return app;
}
