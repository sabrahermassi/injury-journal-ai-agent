# Structured extraction

`extract(note, model?)` turns a messy note into a validated `Injury` object.

- **In:** `"Twisted my left ankle playing football yesterday, pain about 7"`
- **Out:** `{ injury: "twisted ankle", bodyPart: "left ankle", severity: 7, cause: "football", date: null }`

```mermaid
flowchart TD
    A["Build messages<br/>system: rules · user: note"]
    B["Call the LLM"]
    C["Parse JSON + validate with Zod"]
    D{"Valid?"}
    E["Return Injury ✅"]
    F["Add 2 messages<br/>assistant: wrong answer<br/>user: 'Invalid: error. Fix it.'"]
    G["Call the LLM again"]
    H["Parse JSON + validate with Zod"]
    I{"Valid?"}
    J["Throw error ❌"]

    A --> B --> C --> D
    D -- yes --> E
    D -- no --> F --> G --> H --> I
    I -- yes --> E
    I -- no --> J
```

## Why a retry?

LLMs sometimes return wrong JSON. Sending the Zod error back lets the model fix its own mistake.
