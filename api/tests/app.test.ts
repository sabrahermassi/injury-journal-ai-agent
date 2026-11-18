import request from "supertest";
import { describe, expect, it } from "vitest";
import { createApp } from "../src/app.js";
import type { PythonClient } from "../src/python-client.js";
import type { SearchRequest } from "../src/schemas.js";

const RESULT = {
  id: "abc",
  text: "knee pain after running",
  fields: {
    injury: "knee pain",
    body_part: "knee",
    severity: 5,
    cause: "running",
    date: null,
  },
  score: 0.71,
};

function fakePython(): PythonClient & { received: SearchRequest[] } {
  const received: SearchRequest[] = [];
  return {
    received,
    async search(searchRequest) {
      received.push(searchRequest);
      return [RESULT];
    },
    async bodyParts() {
      return ["ankle", "knee"];
    },
  };
}

describe("TS API", () => {
  it("passes a valid search to Python and returns the results", async () => {
    const python = fakePython();
    const body = {
      query: "running injury",
      filters: { body_part: "knee", min_severity: 3 },
    };

    const response = await request(createApp(python))
      .post("/api/search")
      .send(body);

    expect(response.status).toBe(200);
    expect(response.body).toEqual([RESULT]);
    expect(python.received).toEqual([body]);
  });

  it("rejects an empty query with 400 and never calls Python", async () => {
    const python = fakePython();
    const response = await request(createApp(python))
      .post("/api/search")
      .send({ query: "  " });
    expect(response.status).toBe(400);
    expect(python.received).toEqual([]);
  });

  it("rejects a badly formatted date", async () => {
    const response = await request(createApp(fakePython()))
      .post("/api/search")
      .send({ query: "knee", filters: { date_from: "15/10/2026" } });
    expect(response.status).toBe(400);
  });

  it("returns 502 when Python is down", async () => {
    const python = fakePython();
    python.search = async () => {
      throw new Error("connection refused");
    };
    const response = await request(createApp(python))
      .post("/api/search")
      .send({ query: "knee" });
    expect(response.status).toBe(502);
  });

  it("lists body parts", async () => {
    const response = await request(createApp(fakePython())).get(
      "/api/body-parts",
    );
    expect(response.body).toEqual(["ankle", "knee"]);
  });
});
