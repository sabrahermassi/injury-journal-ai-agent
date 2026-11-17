# Structured extraction

`extract(note, model?)` turns a messy note into a validated `Injury` object.

- **In:** `"Twisted my left ankle playing football yesterday, pain about 7"`
- **Out:** `{ injury: "twisted ankle", bodyPart: "left ankle", severity: 7, cause: "football", date: null }`

```text
1. Build messages
   system: rules
   user:   note
        │
        ▼
2. Call the LLM
        │
        ▼
3. Parse JSON + validate with Zod
        │
     valid? ── yes ──► return Injury ✅
        │
        no
        ▼
4. Add 2 messages
   assistant: the wrong answer
   user:      "Invalid: <error>. Fix it."
        │
        ▼
5. Call the LLM again
        │
        ▼
6. Parse JSON + validate with Zod
        │
     valid? ── yes ──► return Injury ✅
        │
        no ──► throw error ❌
```

## Why a retry?

LLMs sometimes return wrong JSON. Sending the Zod error back lets the model fix its own mistake.
