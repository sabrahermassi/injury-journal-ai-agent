import { Ollama, type Message } from "ollama";
import { requireEnv } from "./env.js";

const ollama = new Ollama({ host: requireEnv("OLLAMA_URL") });

export async function chat(
  messages: Message[],
  model = requireEnv("LLM_MODEL"),
): Promise<string> {
  const res = await ollama.chat({
    model,
    messages,
    format: "json",
    options: { temperature: 0 },
  });
  return res.message.content;
}
