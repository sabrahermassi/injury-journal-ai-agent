# How we talk to LLMs: messages and roles

## What `messages` is

`messages` is the **script of a conversation**. The model reads the whole script, then writes the **next line**.

Each message has two parts:

- `role`: who is speaking
- `content`: what they said

```python
messages = [
    {"role": "system", "content": "You extract injury data. Use null, never guess."},
    {"role": "user", "content": "Twisted my ankle, pain 7"},
]
```

Almost every LLM API uses this format. OpenAI made it popular, and Ollama, Mistral, Groq and others copy it. Anthropic's API is almost the same, except the system prompt goes in a separate `system` field.

## The roles

| Role        | Who it is          | Plain English                                                  |
| ----------- | ------------------ | -------------------------------------------------------------- |
| `system`    | You, the developer | "Here are your job and your rules." It's set once, at the top. |
| `user`      | The person asking  | "Here is my question or input."                                |
| `assistant` | The model          | "Here's what I answered."                                      |
| `tool`      | A tool's result    | Used for tool calling (later projects).                        |

## The mental model

```text
┌──────────────────────────────────────┐
│ system:    "Extract injury data...   │  ← rules (you)
│             use null, never guess"   │
├──────────────────────────────────────┤
│ user:      "Twisted my ankle, pain 7"│  ← input
└──────────────────┬───────────────────┘
                   │  send the whole script
                   ▼
             ┌───────────┐
             │   MODEL   │  reads everything, writes the next line
             └─────┬─────┘
                   ▼
        assistant: '{"injury": "twisted ankle", ...}'
```

## The model has no memory

Every call starts from zero. To continue a conversation, you send the **whole history** again, every time. ChatGPT does the same thing behind the scenes.

## Why the retry adds an `assistant` message

When the model's answer is invalid, you rebuild the conversation as it actually happened, then add your correction:

```text
┌───────────────────────────────────────────┐
│ system:    rules                          │
│ user:      the note                       │
│ assistant: '{"injury": "twisted ankle"}'  │  ← what the model said (wrong)
│ user:      "Invalid: 4 fields missing.    │  ← your correction
│             Fix it."                      │
└─────────────────────┬─────────────────────┘
                      ▼
                  ┌───────┐
                  │ MODEL │
                  └───┬───┘
                      ▼
        assistant: '{"injury": "...", "body_part": ..., ...}'  ✅
```

- **`assistant` for the wrong answer:** it's the model's own line. The model sees it as "what I said", so it understands that its own answer was wrong.
- **`user` for the error:** it's you replying, "that's wrong, here's why".
- **Without the `assistant` message,** the model would get "Invalid: fix it" without knowing what "it" is.

It works like ChatGPT: you ask, it answers, you say "that's wrong", and it fixes its answer.

In code (`app/extract.py`):

```python
messages.append({"role": "assistant", "content": first})
messages.append({"role": "user", "content": f"Invalid: {error}. Fix it and return JSON only."})
```

## The rules

1. `system` first, once, with the rules.
2. Then `user` and `assistant` take turns.
3. The model always writes the next `assistant` message.
4. Send the whole history on every call, because the model has no memory.

## Other settings in our call

```python
client.chat(
    model="qwen2.5:3b",          # which model answers
    messages=messages,           # the script
    format="json",               # force a JSON reply
    options={"temperature": 0},  # same answer every time, no creativity
)
```

## Read more

- Ollama, "Generate a chat completion": https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion
- Ollama Python library: https://github.com/ollama/ollama-python
- OpenAI, Chat Completions (the original format): https://platform.openai.com/docs/api-reference/chat/create
- Anthropic, Messages API (`system` as a separate field): https://platform.claude.com/docs/en/api/messages
