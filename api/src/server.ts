import { createApp } from "./app.js";
import { askNotesClient } from "./ask-notes/python-client.js";
import { semanticSearchClient } from "./semantic-search/python-client.js";

const PORT = Number(process.env.PORT ?? 3000);

createApp({ semanticSearch: semanticSearchClient, askNotes: askNotesClient }).listen(PORT, () => {
  console.log(`TS API running on http://localhost:${PORT}`);
});
