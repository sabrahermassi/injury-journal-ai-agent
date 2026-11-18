import { z } from "zod";

// A real calendar date in YYYY-MM-DD: 2026-02-30 and 2026-13-01 are rejected.
const isoDate = z.iso.date();

// What React sends to POST /api/search.
export const SearchRequest = z.object({
  query: z.string().trim().min(1),
  filters: z
    .object({
      body_part: z.string().min(1).optional(),
      min_severity: z.number().int().min(1).max(10).optional(),
      date_from: isoDate.optional(),
      date_to: isoDate.optional(),
    })
    .optional(),
  top_k: z.number().int().min(1).max(50).optional(),
});
export type SearchRequest = z.infer<typeof SearchRequest>;

// What the Python service sends back.
export const Injury = z.object({
  injury: z.string().nullable(),
  body_part: z.string().nullable(),
  severity: z.number().int().nullable(),
  cause: z.string().nullable(),
  date: z.string().nullable(),
});

export const SearchResult = z.object({
  id: z.string(),
  text: z.string(),
  fields: Injury,
  score: z.number(),
});
export type SearchResult = z.infer<typeof SearchResult>;

export const SearchResults = z.array(SearchResult);
export const BodyParts = z.array(z.string());
