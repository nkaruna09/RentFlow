# Architecture

> Template. Fill in as decisions are made; record anything contested as an ADR in [`adr/`](adr/).

## 1. Overview

RentFlow is a two-tier web application: a Next.js frontend and a FastAPI backend over PostgreSQL, both containerised and deployed to Azure Container Apps.

```
Browser
   │  HTTPS
   ▼
Next.js (App Router)          ── Azure Container Apps
   │  JSON over HTTPS
   ▼
FastAPI                       ── Azure Container Apps
   │
   ├── PostgreSQL             ── Azure Database for PostgreSQL Flexible Server
   ├── Blob Storage           ── lease PDFs, receipts, photos
   ├── Key Vault              ── secrets and connection strings
   └── Communication Services ── email / SMS notifications
```

## 2. Frontend

- **Rendering** — Server Components by default; Client Components only where interactivity demands it.
- **Routing** — App Router with route groups: `(auth)` for unauthenticated screens, `(dashboard)` for the authenticated shell.
- **Styling** — Tailwind CSS with design tokens as CSS custom properties in `globals.css`.
- **Data access** — all backend calls go through `src/lib/api/client.ts`; no component calls `fetch` directly.
- **State** — server state via the query provider; client-only UI state in `src/store`.

**TODO:** confirm the server-state library, form library, and component primitive approach.

## 3. Backend

Layered, with dependencies pointing inward:

| Layer          | Directory              | Responsibility                                    |
| -------------- | ---------------------- | ------------------------------------------------- |
| API            | `app/api/v1/endpoints` | HTTP concerns: validation, status codes, auth deps |
| Services       | `app/services`         | Business rules; the only layer with domain logic   |
| Repositories   | `app/repositories`     | Query construction and persistence                 |
| Models         | `app/models`           | SQLAlchemy tables                                  |
| Schemas        | `app/schemas`          | Pydantic DTOs at the API boundary                  |

Rules:
- Endpoints never touch the ORM directly — they call services.
- Services never return ORM objects across the API boundary — they return schemas.
- Repositories never contain business rules.

## 4. Authentication and authorisation

- JWT access tokens plus refresh tokens issued by the backend.
- Roles: `landlord`, `manager`, `tenant`.
- Authorisation is enforced in FastAPI dependencies (`app/api/deps`), not in the frontend. The frontend hides UI; the backend is the authority.

**TODO:** decide between backend-issued JWTs alone and Azure Entra ID as the identity provider.

## 5. Background jobs

`app/workers/scheduler.py` owns recurring work:
- monthly invoice generation
- overdue-rent sweep and late-fee application
- lease-expiry notifications

**TODO:** choose the execution mechanism (Container Apps job, in-process scheduler, or task queue).

## 6. Cross-cutting concerns

| Concern         | Approach                                                     |
| --------------- | ------------------------------------------------------------ |
| Configuration   | Pydantic Settings from env vars; secrets from Key Vault in Azure |
| Logging         | Structured JSON logs to Application Insights                 |
| Error handling  | Domain exceptions in `core/exceptions.py` mapped to HTTP responses |
| Migrations      | Alembic, one revision per schema change, reviewed in PR       |
| Money           | `Decimal` end to end; never floats                            |
| Time            | UTC in storage and transport; localised only for display      |

## 7. Open questions

- Multi-tenancy: single database with an owner column, or schema per organisation?
- Payment processing: integrate a provider, or record payments manually first?
- File uploads: direct-to-blob with SAS tokens, or proxied through the API?
