# RentFlow

Property and rent management for small-to-mid landlords: properties, units, tenants, leases, rent collection, and maintenance requests in one place.

> **Status: scaffolding.** This repository currently contains the file structure and documentation only. Source files are stubs marked `TODO` — no implementation has been written yet.

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

## Getting started (once implemented)

```bash
git clone https://github.com/nkaruna09/RentFlow.git
cd RentFlow

cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

docker compose up --build
```

| Service  | URL                            |
| -------- | ------------------------------ |
| Frontend | http://localhost:3000          |
| API      | http://localhost:8000          |
| API docs | http://localhost:8000/docs     |
| Postgres | localhost:5432                 |

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
