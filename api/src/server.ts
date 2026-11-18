import { createApp } from "./app.js";
import { pythonClient } from "./python-client.js";

const PORT = Number(process.env.PORT ?? 3000);

createApp(pythonClient).listen(PORT, () => {
  console.log(`TS API running on http://localhost:${PORT}`);
});
