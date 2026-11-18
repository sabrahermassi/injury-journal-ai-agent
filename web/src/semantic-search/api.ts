// The shapes the TS API sends back, and the two calls the page makes.

export type Injury = {
  injury: string | null;
  body_part: string | null;
  severity: number | null;
  cause: string | null;
  date: string | null;
};

export type SearchResult = {
  id: string;
  text: string;
  fields: Injury;
  score: number;
};

export type SearchFilters = {
  body_part?: string;
  min_severity?: number;
  date_from?: string;
  date_to?: string;
};

export async function fetchBodyParts(): Promise<string[]> {
  const response = await fetch("/api/body-parts");
  if (!response.ok) throw new Error("Could not load body parts");
  return response.json();
}

export async function searchNotes(
  query: string,
  filters: SearchFilters,
): Promise<SearchResult[]> {
  const response = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, filters }),
  });
  if (!response.ok) throw new Error("Search failed");
  return response.json();
}
