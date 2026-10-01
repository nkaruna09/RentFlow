# API reference

Base URL: `/api/v1`. Interactive docs are served at `/docs` (Swagger) and `/redoc` when the app runs.

> Template — endpoints listed here are planned, not implemented. Keep this file in sync with `backend/app/api/v1/endpoints/`.

## Conventions

- JSON request and response bodies; `snake_case` field names.
- Authentication: `Authorization: Bearer <access_token>`.
- Money is a decimal string (`"1450.00"`) to avoid float rounding.
- Timestamps are ISO 8601 in UTC (`2026-08-06T14:30:00Z`).
- List endpoints accept `?page=1&page_size=25` and return `{ items, total, page, page_size }`.

### Error shape

```json
{
  "detail": "Human-readable message",
  "code": "lease_overlap",
  "field_errors": { "start_date": "must be before end_date" }
}
```

| Status | Meaning |
| --- | --- |
| 400 | Malformed request |
| 401 | Missing or invalid token |
| 403 | Authenticated but not permitted |
| 404 | Not found, or not visible to this user |
| 409 | Conflict (e.g. overlapping lease) |
| 422 | Validation failure |
| 500 | Unhandled server error |

---

## Auth — `/auth`

| Method | Path | Description |
| --- | --- | --- |
| POST | `/auth/register` | Create an account |
| POST | `/auth/login` | Exchange credentials for tokens |
| POST | `/auth/refresh` | Exchange a refresh token for a new access token |
| POST | `/auth/logout` | Revoke the current refresh token |
| GET | `/auth/me` | Current user profile |

## Properties — `/properties`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/properties` | List properties owned by the caller |
| POST | `/properties` | Create a property |
| GET | `/properties/{id}` | Retrieve one |
| PATCH | `/properties/{id}` | Update |
| DELETE | `/properties/{id}` | Delete (cascades to units) |
| GET | `/properties/{id}/units` | Units belonging to a property |

## Units — `/units`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/units` | List, filterable by `property_id` and `status` |
| POST | `/units` | Create |
| GET | `/units/{id}` | Retrieve |
| PATCH | `/units/{id}` | Update |
| DELETE | `/units/{id}` | Delete |

## Tenants — `/tenants`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/tenants` | List |
| POST | `/tenants` | Create |
| GET | `/tenants/{id}` | Retrieve |
| PATCH | `/tenants/{id}` | Update |
| GET | `/tenants/{id}/leases` | Lease history |

## Leases — `/leases`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/leases` | List, filterable by `unit_id`, `tenant_id`, `status` |
| POST | `/leases` | Create — 409 if it overlaps an active lease on the unit |
| GET | `/leases/{id}` | Retrieve |
| PATCH | `/leases/{id}` | Update a draft lease |
| POST | `/leases/{id}/activate` | Move `draft` → `active` |
| POST | `/leases/{id}/renew` | Create a successor lease |
| POST | `/leases/{id}/terminate` | End early with a reason and date |

## Payments — `/payments`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/payments/invoices` | List invoices, filterable by `lease_id` and `status` |
| POST | `/payments/invoices` | Create an ad-hoc invoice |
| GET | `/payments/invoices/{id}` | Retrieve |
| POST | `/payments/invoices/{id}/payments` | Record a payment against an invoice |
| GET | `/payments/arrears` | Outstanding balances across all leases owned by the caller |

Invoice and payment writes are available to landlords and managers. Payment
amounts must be positive and cannot exceed the invoice's outstanding balance.
Arrears are grouped by lease and include a portfolio-wide outstanding total.

## Maintenance — `/maintenance`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/maintenance` | List requests, filterable by `unit_id`, `status`, `priority` |
| POST | `/maintenance` | Submit a request |
| GET | `/maintenance/{id}` | Retrieve |
| PATCH | `/maintenance/{id}` | Update status, priority, assignee |
| POST | `/maintenance/{id}/comments` | Add a comment |

## Documents — `/documents`

Files attached to a lease (signed PDFs), a payment (receipts) or a maintenance
request (photos). Uploads and downloads are proxied through the API; blob URLs are
never returned. Access follows the owning record, and anything the caller can't see is a 404.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/documents?owner_type=&owner_id=` | List documents attached to a record |
| POST | `/documents` | Upload (`multipart/form-data`: `owner_type`, `owner_id`, `file`). PDF/JPEG/PNG/WebP, ≤ 10 MB |
| GET | `/documents/{id}/content` | Download the file (`Content-Disposition: attachment`) |

| `owner_type` | Read | Upload |
| --- | --- | --- |
| `lease` | owning landlord/manager, the lease's tenant | owning landlord/manager |
| `payment` | owning landlord/manager | owning landlord/manager |
| `maintenance_request` | anyone who can see the request | anyone who can see the request |

## Health — `/health`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health/live` | Liveness probe — process is up |
| GET | `/health/ready` | Readiness probe — database reachable |
