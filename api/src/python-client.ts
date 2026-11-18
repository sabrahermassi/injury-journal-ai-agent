import {
  BodyParts,
  SearchResults,
  type SearchRequest,
  type SearchResult,
} from "./schemas.js";

const PYTHON_URL = process.env.PYTHON_URL ?? "http://localhost:8000";

// The two calls the API makes to the Python service. An interface, so tests can pass a fake.
export interface PythonClient {
  search(request: SearchRequest): Promise<SearchResult[]>;
  bodyParts(): Promise<string[]>;
}

async function callPython(path: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(`${PYTHON_URL}${path}`, init);
  if (!response.ok) {
    throw new Error(`Python service answered ${response.status} on ${path}`);
  }
  return response.json();
}

export const pythonClient: PythonClient = {
  async search(request) {
    const body = await callPython("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    return SearchResults.parse(body); // check Python's answer too
  },
  async bodyParts() {
    return BodyParts.parse(await callPython("/body-parts"));
  },
};
