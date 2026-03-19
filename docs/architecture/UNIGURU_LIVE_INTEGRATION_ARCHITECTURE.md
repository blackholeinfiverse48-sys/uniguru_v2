# UniGuru Live Integration Architecture

```mermaid
flowchart LR
    A[Frontend Chat] --> B[Node Backend<br/>/api/v1/chat/query]
    G[Gurukul Backend] --> C[Node Backend<br/>/api/v1/gurukul/query]
    B --> D[UniGuru API<br/>POST /ask]
    C --> D
    D --> E[Conversation Router]
    E --> F[Deterministic Rule Engine]
    E --> H[Safety / Governance]
    E --> I[Bucket Telemetry]
```

## Request Contracts

### Product Chat to UniGuru
```json
{
  "query": "What is a qubit?",
  "context": {
    "caller": "bhiv-assistant"
  }
}
```

### Gurukul to UniGuru
```json
{
  "query": "Explain Pythagoras theorem",
  "context": {
    "caller": "gurukul-platform",
    "student_id": "S-102"
  }
}
```
