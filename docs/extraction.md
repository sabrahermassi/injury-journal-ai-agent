# Structured extraction

`extract(note, model=None)` in `app/extract.py` turns a messy note into a validated `Injury` object (a Pydantic model).

- **In:** `"Twisted my left ankle playing football yesterday, pain about 7"`
- **Out:** `Injury(injury="twisted ankle", body_part="left ankle", severity=7, cause="football", date=None)`

```text
1. Build messages
   system: rules
   user:   note
        │
        ▼
2. Call the LLM
        │
        ▼
3. Parse JSON + validate with Pydantic
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
6. Parse JSON + validate with Pydantic
        │
     valid? ── yes ──► return Injury ✅
        │
        no ──► raise error ❌
```

## Why a retry?

LLMs sometimes return wrong or broken JSON. Sending the Pydantic error back lets the model fix its own mistake. `model_validate_json` parses and validates in one step, so broken JSON also triggers the retry.
