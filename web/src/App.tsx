import { useEffect, useState, type FormEvent } from "react";
import {
  fetchBodyParts,
  searchNotes,
  type SearchFilters,
  type SearchResult,
} from "./api";
import "./App.css";

function App() {
  const [query, setQuery] = useState("");
  const [bodyParts, setBodyParts] = useState<string[]>([]);
  const [bodyPart, setBodyPart] = useState("");
  const [minSeverity, setMinSeverity] = useState(0); // 0 means "any"
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [results, setResults] = useState<SearchResult[] | null>(null); // null = no search yet
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Fill the body part dropdown once, when the page opens.
  useEffect(() => {
    fetchBodyParts()
      .then(setBodyParts)
      .catch(() =>
        setError("Could not reach the API. Are all 3 services running?"),
      );
  }, []);

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;

    // Only send the filters that are set.
    const filters: SearchFilters = {};
    if (bodyPart) filters.body_part = bodyPart;
    if (minSeverity > 0) filters.min_severity = minSeverity;
    if (dateFrom) filters.date_from = dateFrom;
    if (dateTo) filters.date_to = dateTo;

    setLoading(true);
    setError("");
    try {
      setResults(await searchNotes(query, filters));
    } catch {
      setError("Search failed. Are all 3 services running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Injury notes search</h1>
      <p className="subtitle">
        Search your notes by meaning, and filter by the fields the LLM
        extracted.
      </p>

      <form onSubmit={handleSearch}>
        <div className="search-row">
          <input
            type="search"
            placeholder="e.g. pain after running"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? "Searching…" : "Search"}
          </button>
        </div>

        <div className="filters">
          <label>
            Body part
            <select
              value={bodyPart}
              onChange={(event) => setBodyPart(event.target.value)}
            >
              <option value="">Any</option>
              {bodyParts.map((part) => (
                <option key={part} value={part}>
                  {part}
                </option>
              ))}
            </select>
          </label>

          <label>
            Min severity: {minSeverity === 0 ? "any" : minSeverity}
            <input
              type="range"
              min={0}
              max={10}
              value={minSeverity}
              onChange={(event) => setMinSeverity(Number(event.target.value))}
            />
          </label>

          <label>
            From
            <input
              type="date"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
            />
          </label>

          <label>
            To
            <input
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
            />
          </label>
        </div>
      </form>

      {error && <p className="error">{error}</p>}

      {results !== null && results.length === 0 && (
        <p className="empty">No matching notes.</p>
      )}

      <ul className="results">
        {results?.map((result) => (
          <li key={result.id}>
            <div className="result-top">
              <p className="note">{result.text}</p>
              <span className="score">{result.score.toFixed(2)}</span>
            </div>
            <dl className="fields">
              <Field label="Injury" value={result.fields.injury} />
              <Field label="Body part" value={result.fields.body_part} />
              <Field label="Severity" value={result.fields.severity} />
              <Field label="Cause" value={result.fields.cause} />
              <Field label="Date" value={result.fields.date} />
            </dl>
          </li>
        ))}
      </ul>
    </main>
  );
}

function Field({
  label,
  value,
}: {
  label: string;
  value: string | number | null;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value ?? "—"}</dd>
    </div>
  );
}

export default App;
