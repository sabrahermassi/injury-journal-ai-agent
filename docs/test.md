```mermaid
flowchart LR
    UI["React (TypeScript)"]
    API["API layer (TypeScript)"]
    AI["AI service (Python)"]
    OL["Ollama"]

    UI -->|public endpoints| API
    API -->|internal endpoints| AI
    AI --> OL
```

```mermaid
flowchart TB
    N["Messy note"]

    subgraph BOTH["SIDE BY SIDE"]
        E["LLM extraction"]
        V["Embedding model"]
    end

    S["notes.json"]

    N --> E
    N --> V
    E -->|fields| S
    V -->|vector| S
```

```mermaid
flowchart LR
    Q["Search + filters"]
    F["Filter by fields"]
    V["Embed search"]
    C["Cosine similarity"]
    T["Top 5 notes"]

    Q --> F
    F --> V
    V --> C
    C --> T
```
