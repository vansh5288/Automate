# Architecture

## Request lifecycle

```mermaid
sequenceDiagram
    participant U as Employee
    participant API as FastAPI Backend
    participant AI as AI Service
    participant DE as Decision Engine
    participant N as Notion
    participant M as Manager
    participant EXT as Email (external action)

    U->>API: POST /api/requests (or webhook)
    API->>API: validate + hash for idempotency
    API->>AI: extract_purchase_details(text)
    AI-->>API: item, qty, amount, risk, confidence
    API->>DE: decide(extraction)
    alt low risk, high confidence
        DE-->>API: auto_process
        API->>EXT: send procurement email
        EXT-->>API: action id / failure
        API->>N: write Run Log + update status
    else needs human
        DE-->>API: approval_required
        API->>N: create Approval Queue row
        API->>N: write Run Log (ROUTED_TO_APPROVAL)
        loop background poll
            API->>N: query Approval Queue for non-Pending rows
        end
        M->>N: set Approved / Rejected / Override
        N-->>API: poller reads decision
        API->>API: block if approver == requester
        alt approved/override
            API->>EXT: send procurement email
        end
        API->>N: write Run Log (HUMAN_DECISION, EXTERNAL_ACTION)
    end
```

## Failure isolation

Each external dependency (AI provider, Notion, SMTP) fails independently without taking down the request:

- AI failure → status `NEEDS_REVIEW`, routed to a human, Run Log records `AI_CLASSIFIED / FAILURE`.
- Notion failure → retried 3x with exponential backoff; if still failing, the *local* Run Log records the failure and the workflow continues (the request isn't blocked on Notion being reachable).
- Email failure → status `ACTION_FAILED`, never `COMPLETED`; retryable via `POST /api/requests/{id}/retry`.

## Data model

- `requests` — one row per purchase request, the source of truth for current status.
- `approvals` — one row per approval cycle (supports retries/overrides without losing history).
- `run_logs` — append-only, one row per workflow event, mirrored into the Notion Run Log database.
