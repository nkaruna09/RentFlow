# Database

PostgreSQL 16. Schema managed exclusively through Alembic — no manual DDL against any environment.

## Entity relationships

```
users
  └──< properties            (owner_id)
         └──< units          (property_id)
                ├──< leases  (unit_id, tenant_id)
                │      └──< invoices   (lease_id)
                │             └──< payments (invoice_id)
                └──< maintenance_requests (unit_id, reported_by, assigned_to)
                       └──< maintenance_comments (request_id, author_id)

tenants ──< leases
documents ── polymorphic metadata for blobs in Azure Storage
```

## Tables (planned)

### `users`
| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | PK |
| email | citext | unique |
| hashed_password | text | |
| full_name | text | |
| role | enum | `landlord` · `manager` · `tenant` |
| is_active | bool | default true |
| created_at / updated_at | timestamptz | |

### `properties`
| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | PK |
| owner_id | uuid | FK → users |
| name | text | |
| address_line1 / line2 / city / region / postal_code / country | text | |
| property_type | enum | `single_family` · `multi_family` · `condo` · `commercial` |
| created_at / updated_at | timestamptz | |

### `units`
| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | PK |
| property_id | uuid | FK → properties, cascade delete |
| label | text | e.g. "Unit 2B"; unique per property |
| bedrooms / bathrooms | numeric | |
| square_feet | int | nullable |
| market_rent | numeric(12,2) | |
| status | enum | `vacant` · `occupied` · `unavailable` |

### `tenants`
| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | PK |
| user_id | uuid | FK → users, nullable until the tenant registers |
| full_name / email / phone | text | |
| emergency_contact | jsonb | nullable |

### `leases`
| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | PK |
| unit_id | uuid | FK → units |
| tenant_id | uuid | FK → tenants |
| start_date / end_date | date | |
| rent_amount | numeric(12,2) | |
| deposit_amount | numeric(12,2) | |
| billing_day | int | day of month rent is due, 1–28 |
| status | enum | `draft` · `active` · `expired` · `terminated` |

> Constraint: no two `active` leases may overlap on the same `unit_id`. Enforce with an exclusion constraint on a daterange.

### `invoices`
| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | PK |
| lease_id | uuid | FK → leases |
| period_start / period_end | date | |
| amount_due | numeric(12,2) | |
| late_fee_amount | numeric(12,2) | nullable; non-null once a late fee is applied |
| due_date | date | |
| status | enum | `open` · `paid` · `partial` · `overdue` · `void` |

> Constraint: one invoice per `(lease_id, period_start, period_end)`.

### `payments`
| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | PK |
| invoice_id | uuid | FK → invoices |
| amount | numeric(12,2) | |
| paid_at | timestamptz | |
| method | enum | `bank_transfer` · `card` · `cash` · `check` · `other` |
| reference | text | nullable |

### `maintenance_requests`
| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | PK |
| unit_id | uuid | FK → units |
| reported_by | uuid | FK → users |
| title / description | text | |
| priority | enum | `low` · `medium` · `high` · `emergency` |
| status | enum | `open` · `assigned` · `in_progress` · `resolved` · `closed` |
| assigned_to | uuid | FK → users, nullable |
| resolved_at | timestamptz | nullable |

Maintenance comments are stored in a separate `maintenance_comments` table rather than a
`jsonb` column. Comments are append-oriented API sub-resources with their own author and
timestamps, so a normalized table preserves the audit trail and avoids rewriting the request row.

### `maintenance_comments`
| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | PK |
| request_id | uuid | FK → maintenance_requests, cascade delete |
| author_id | uuid | FK → users |
| body | text | |

### `documents`
| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | PK |
| owner_type / owner_id | enum / uuid | polymorphic link: `lease`, `payment` (receipts), `maintenance_request` (photos); indexed together |
| blob_url | text | Azure Blob Storage, `rentflow-documents/<owner_type>/<owner_id>/<id>/<filename>` |
| filename / content_type / size_bytes | text / text / bigint | original filename; PDF, JPEG, PNG or WebP; max 10 MB |
| uploaded_by | uuid | FK → users |
| created_at | timestamptz | |

`owner_id` has no foreign key because it points at different tables depending on
`owner_type`. `document_service` checks that the owner exists and is visible to the
caller before writing a row. There is no delete endpoint yet; blob soft delete
(7 days) covers accidental deletion in storage.

## Conventions

- Primary keys are UUIDs.
- All money is `numeric(12,2)` — never float.
- All timestamps are `timestamptz` stored in UTC.
- Every table carries `created_at` and `updated_at`.
- Soft deletes only where an audit trail is required; otherwise hard delete with `ON DELETE` rules.

## Indexes to add

- `properties(owner_id)`
- `units(property_id)`, unique `(property_id, label)`
- `leases(unit_id)`, `leases(tenant_id)`, `leases(status)`
- `invoices(lease_id, due_date)`, `invoices(status)`
- `maintenance_requests(unit_id, status)`

## Migrations

```bash
# create a revision after changing models
docker compose exec api alembic revision --autogenerate -m "add leases table"

# apply
docker compose exec api alembic upgrade head

# roll back one
docker compose exec api alembic downgrade -1
```

Every autogenerated revision must be read and edited before merging — Alembic misses constraint and type changes.
