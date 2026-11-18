import { createApp } from "./app.js";
import { semanticSearchClient } from "./semantic-search/python-client.js";

const PORT = Number(process.env.PORT ?? 3000);

createApp({ semanticSearch: semanticSearchClient }).listen(PORT, () => {
  console.log(`TS API running on http://localhost:${PORT}`);
});
