import { describe, it, expect } from "vitest";
import { requireEnv } from "./env.js";

describe("requireEnv", () => {
  it("returns the value when set", () => {
    process.env.TEST_VAR = "hello";
    expect(requireEnv("TEST_VAR")).toBe("hello");
  });

  it("throws when missing", () => {
    delete process.env.MISSING_VAR;
    expect(() => requireEnv("MISSING_VAR")).toThrow(
      "Missing environment variable: MISSING_VAR",
    );
  });
});
