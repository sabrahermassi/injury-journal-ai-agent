import { useState } from "react";
import AskPage from "./ask-notes/AskPage";
import SearchPage from "./semantic-search/SearchPage";

type Page = "search" | "ask";

// One web app for every project: a small menu, one page per project.
function App() {
  const [page, setPage] = useState<Page>("search");
  return (
    <>
      <nav className="menu">
        <button type="button" aria-pressed={page === "search"} onClick={() => setPage("search")}>
          Search
        </button>
        <button type="button" aria-pressed={page === "ask"} onClick={() => setPage("ask")}>
          Ask
        </button>
      </nav>
      {page === "search" ? <SearchPage /> : <AskPage />}
    </>
  );
}

export default App;
