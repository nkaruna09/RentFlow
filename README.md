# RentFlow

Property and rent management for small-to-mid landlords: properties, units, tenants, leases, rent collection, and maintenance requests in one place.

> **Status: in active development.** Auth, properties, units, tenants, leases, and billing (invoicing, payments, arrears, late fees) are implemented and tested. Maintenance, documents, notifications, and the Azure deployment are still stubs marked `TODO`.

---

## Stack

| Layer     | Choice                                              |
| --------- | --------------------------------------------------- |
| Frontend  | Next.js (App Router) · React · TypeScript · Tailwind CSS |
| Backend   | FastAPI (Python 3.12) · SQLAlchemy · Alembic        |
| Database  | PostgreSQL 16                                        |
| Cloud     | Azure (Container Apps, PostgreSQL Flexible Server, Blob Storage, Key Vault) |
| DevOps    | Docker · Docker Compose · GitHub Actions             |

---

## Architecture

Solid lines are implemented. Dashed lines are designed (Bicep templates exist in `infra/`) but not deployed yet.

```mermaid
flowchart LR
    Browser([Browser])

    subgraph Web["Next.js 15 · App Router (port 3000)"]
        direction TB
        Pages["(auth) login · register<br/>(dashboard) properties · units ·<br/>tenants · leases · payments"]
        Client["lib/api/client.ts<br/>typed apiFetch + Bearer token"]
        Pages --> Client
    end

    subgraph API["FastAPI · /api/v1 (port 8000)"]
        direction TB
        Endpoints["Endpoints<br/>auth · properties · units · tenants ·<br/>leases · payments · health"]
        Deps["Dependencies<br/>get_current_user · require_role · get_db"]
        Services["Services<br/>business rules"]
        Repos["Repositories<br/>SQLAlchemy async queries"]
        Endpoints --> Deps
        Endpoints --> Services --> Repos
    end

    subgraph Jobs["Scheduled jobs · workers/scheduler.py"]
        direction TB
        Invoicing["monthly-invoicing"]
        Sweep["overdue-sweep<br/>$20 late fee"]
    end

    DB[("PostgreSQL 16<br/>Alembic migrations")]

    subgraph Azure["Azure (planned)"]
        direction TB
        Blob[("Blob Storage<br/>leases · receipts")]
        KV["Key Vault<br/>secrets"]
        Insights["Application Insights<br/>JSON logs"]
    end

    Browser --> Pages
    Client -- "JSON over HTTPS<br/>Authorization: Bearer JWT" --> Endpoints
    Repos --> DB
    Invoicing --> Services
    Sweep --> Services
    Services -.-> Blob
    API -.-> KV
    API -.-> Insights
```

### Backend layering

Dependencies point inward. Each layer only calls the one below it:

| Layer | Directory | Responsibility |
|---|---|---|
| Endpoints | `app/api/v1/endpoints` | HTTP only: validation, status codes, auth dependencies |
| Services | `app/services` | The only layer with business rules |
| Repositories | `app/repositories` | Query construction and persistence, no business rules |
| Models / Schemas | `app/models`, `app/schemas` | SQLAlchemy tables / Pydantic DTOs at the API boundary |

### Request flow: login and an authenticated call

```mermaid
sequenceDiagram
    autonumber
    actor U as Landlord
    participant W as Next.js
    participant A as FastAPI
    participant S as auth_service / security
    participant DB as PostgreSQL

    U->>W: Submit email + password
    W->>A: POST /api/v1/auth/login
    A->>S: authenticate_user()
    S->>DB: SELECT user by email
    S->>S: verify_password (hash)
    S-->>A: access token + refresh token (HS256 JWT)
    A-->>W: TokenPair
    W->>W: Save session in localStorage

    U->>W: Open /properties
    W->>A: GET /api/v1/properties<br/>Authorization: Bearer access_token
    A->>S: get_current_user() decodes JWT, checks blocklist
    A->>A: require_role(LANDLORD, MANAGER)
    alt role not allowed
        A-->>W: 403 AuthorizationError
    else allowed
        A->>DB: Query scoped to current user's properties
        A-->>W: 200 JSON
    end

    Note over W,A: When the access token expires, POST /auth/refresh swaps the refresh token for a new pair and blocklists the old one (by jti).<br/>POST /auth/logout blocklists the refresh token.
```

### Request flow: recording a rent payment

```mermaid
sequenceDiagram
    autonumber
    actor U as Landlord
    participant A as POST /payments/invoices/{id}/payments
    participant P as payment_service
    participant DB as PostgreSQL

    U->>A: amount (Decimal)
    A->>A: require_role(LANDLORD, MANAGER)
    A->>P: record_payment()
    P->>DB: SELECT invoice ... FOR UPDATE (row lock, owner-scoped)
    alt not found / void
        P-->>A: 404 NotFound / 409 Conflict
    end
    P->>DB: SUM(payments) for this invoice
    alt paid + amount > amount_due
        P-->>A: 422 ValidationError (overpayment)
    else
        P->>P: status = PAID if fully paid, otherwise PARTIAL
        P->>DB: INSERT payment, UPDATE invoice, COMMIT
        P-->>A: Payment
        A-->>U: 201 Created
    end
```

The row lock stops two payments recorded at the same moment from both passing the balance check, so an invoice can't be overpaid.

### Scheduled jobs

```mermaid
flowchart LR
    Cron["Azure Container Apps job<br/>(cron schedule)"] --> CLI["python -m app.workers.scheduler &lt;job&gt; [--date]"]
    CLI -->|monthly-invoicing| MI["For each billable lease with a period starting this month:<br/>billing_service.generate_invoice()<br/>(prorated, one invoice per lease + period)"]
    CLI -->|overdue-sweep| OS["billing_service.apply_late_fees()<br/>unpaid & past due → OVERDUE + $20.00 fee"]
    MI --> DB[(PostgreSQL)]
    OS --> DB
```

Both jobs are **idempotent**, so a failed run can simply be retried. A unique constraint on (lease, period) stops duplicate invoices. The late fee is only applied while `late_fee_amount` is null, so running the sweep twice never charges twice. `--date` lets you re-run a missed day. The design reasoning is in [ADR 0002](docs/adr/0002-use-container-apps-jobs-for-scheduled-work.md).

### CI/CD

```mermaid
flowchart LR
    Push["push / PR"] --> FE["CI · Frontend<br/>npm ci → lint → typecheck → vitest → next build"]
    Push --> BE["CI · Backend<br/>ruff → ruff format → mypy → alembic upgrade → pytest + coverage<br/>(against a real Postgres 16 service)"]
    Push -->|main| CD["CD · Azure<br/>OIDC login → build & push images → run migrations → update Container Apps"]
    style CD stroke-dasharray: 5 5
```

The frontend and backend workflows only run when their own folder changes. CD authenticates with OIDC federated credentials, so no long-lived Azure secrets are stored. Its steps are written but commented out until the infrastructure is provisioned.

---

## Repository layout

```
RentFlow/
├── .github/
│   ├── workflows/          CI and deployment pipelines
│   └── ISSUE_TEMPLATE/     Issue and PR templates
├── backend/                FastAPI service
│   ├── app/
│   │   ├── api/v1/         Route handlers, grouped by resource
│   │   ├── core/           Config, security, logging, exceptions
│   │   ├── db/             Engine, session, declarative base
│   │   ├── models/         SQLAlchemy ORM tables
│   │   ├── schemas/        Pydantic request/response models
│   │   ├── repositories/   Data-access layer
│   │   ├── services/       Business rules
│   │   ├── workers/        Scheduled jobs
│   │   └── utils/          Date and money helpers
│   ├── alembic/            Database migrations
│   └── tests/
├── frontend/               Next.js app
│   ├── src/app/            App Router routes
│   ├── src/components/     UI primitives, layout, forms, tables
│   ├── src/lib/            API client and utilities
│   ├── src/hooks/          React hooks
│   ├── src/types/          Shared TypeScript types
│   └── tests/
├── infra/                  Azure infrastructure as code (Bicep)
├── docs/                   Architecture, API, database, deployment
├── scripts/                Developer helper scripts
└── docker-compose.yml      Local dev: web + api + postgres
```

---

## Domain model (planned)

```
User ──< Property ──< Unit ──< Lease >── Tenant
                                │
                                ├──< Invoice ──< Payment
                                └──< MaintenanceRequest
```

See [`docs/database.md`](docs/database.md) for the full schema.

---

## Getting started locally

### Prerequisites

- Python 3.12+
- Node.js 18+
- npm
- Docker Desktop or Docker Engine (for the local Postgres service)

### 1) Start the database

From the repo root:

```powershell
docker compose up -d db
```

This starts PostgreSQL on `localhost:5432`.

### 2) Start the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API should be available at:

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health checks:
  - http://localhost:8000/api/v1/health/live
  - http://localhost:8000/api/v1/health/ready

> Important: start Uvicorn from the `backend` folder so Python resolves the `app` package correctly. Running it from the repo root may fail with `ModuleNotFoundError: No module named 'app'`.

### 3) Start the frontend

In a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

The frontend should be available at:

- Frontend: http://localhost:3000

### 4) Verify the app is running

| Service  | URL                            |
| -------- | ------------------------------ |
| Frontend | http://localhost:3000          |
| API      | http://localhost:8000          |
| API docs | http://localhost:8000/docs     |
| Liveness | http://localhost:8000/api/v1/health/live |
| Readiness | http://localhost:8000/api/v1/health/ready |
| Postgres | localhost:5432                 |

### Optional: run everything together with Docker Compose

```powershell
docker compose up --build
```

This starts the database, API, and web app together. If you want to run the backend and frontend manually for active development, keep them separate as shown above.

---

## Documentation

- [Architecture](docs/architecture.md) — system design and request flow
- [API](docs/api.md) — REST endpoint reference
- [Database](docs/database.md) — schema and migrations
- [Deployment](docs/deployment.md) — Azure environments and pipelines
- [Contributing](CONTRIBUTING.md) — branch, commit and review conventions
- [ADRs](docs/adr/) — architecture decision records

---

## Roadmap

- [ ] **M1 — Foundations:** repo scaffold, Docker Compose, CI green
- [ ] **M2 — Auth:** registration, login, JWT, role-based access
- [ ] **M3 — Core CRUD:** properties, units, tenants, leases
- [ ] **M4 — Billing:** invoice generation, payment recording, arrears view
- [ ] **M5 — Maintenance:** request submission, assignment, status tracking
- [ ] **M6 — Azure:** infrastructure provisioned, CD pipeline deploying
- [ ] **M7 — Polish:** notifications, documents, reporting

---

## License

MIT — see [LICENSE](LICENSE).
