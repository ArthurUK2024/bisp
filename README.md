# Ijara

Ijara is a peer-to-peer rental marketplace for Tashkent. Owners list items
(tools, electronics, event gear, vehicles, and more), renters browse and
book by date and time, and the booking moves through a nine-state
workflow from request to completion. Cash on pickup is the default
payment method, with Stripe wired in as an optional online path.

The stack is Nuxt 3 on the front end, Django 5.2 with Django REST
Framework on the back end, and PostgreSQL 16 underneath. Everything runs
under Docker Compose, so a fresh clone reaches a working demo with one
command on Linux, macOS, and Windows.

---

## Quick start

You need Docker Desktop (Windows or macOS) or Docker Engine 24+ with
Compose v2.22+ on Linux. Nothing else — no Python, Node, or Postgres
on the host.

```bash
git clone https://github.com/ArthurUK2024/bisp.git ijara
cd ijara
docker compose up --build -d
```

That is the whole setup. The first build takes a few minutes while the
base images pull and dependencies install. Subsequent boots take roughly
ten seconds.

When the three containers report healthy, open:

- Front end: http://localhost:3000
- API root: http://localhost:8000/api/v1/
- Health check: http://localhost:8000/api/v1/health/
- Django admin: http://localhost:8000/admin/

The database is automatically migrated on first boot, and a demo seed
populates four users, eighteen listings across seven categories, photos
for every listing, and eight bookings spread across the workflow states
so dashboards look populated immediately.

To watch the boot in real time:

```bash
docker compose logs -f
```

To stop the stack:

```bash
docker compose down
```

To wipe the database and start fresh:

```bash
docker compose down -v
docker compose up --build -d
```

---

## Demo accounts

Every seeded account uses the same password: `zx7mnp45`.

| Email                            | Role                              |
| -------------------------------- | --------------------------------- |
| `aziz.karimov@ijara.demo`        | Owner of most listings, also staff (Django admin access) |
| `dilnoza.tursunova@ijara.demo`   | Renter                            |
| `rustam.yuldashev@ijara.demo`    | Owner / renter                    |
| `malika.abdullaeva@ijara.demo`   | Owner / renter                    |

Sign in at http://localhost:3000/login with any of the above.

To reset the demo data without rebuilding the whole stack:

```bash
docker compose exec api python manage.py seed_demo --reset
```

---

## Walkthrough

A short tour to confirm the prototype works end to end:

1. Open http://localhost:3000/listings. Type `drll` (with the typo) into
   the search box — the cordless drill resolves via trigram similarity.
   Use the category and price filters to narrow the feed.
2. Click into a listing. The detail page shows a gallery, description,
   owner card, and a sticky pricing panel.
3. Sign in as `dilnoza.tursunova@ijara.demo`. Pick a date and time
   window on the listing page; the price quote refreshes live. Submit
   the booking, then go to `/dashboard/bookings`.
4. Open a second browser and try to book the same listing for an
   overlapping window. The submit fails with an overlap error coming
   from a Postgres exclusion constraint, not an application-level
   guard.
5. Sign out and sign in as `aziz.karimov@ijara.demo`. From
   `/dashboard/bookings` (As owner), accept the request, mark it picked
   up, mark it returned, then complete it. Each step is recorded with
   actor and timestamp.
6. The same account doubles as a Django admin login at
   http://localhost:8000/admin/, where every model and the booking
   transition log are visible.

---

## Services

| Container | Image base                  | Purpose                                       |
| --------- | --------------------------- | --------------------------------------------- |
| `db`      | `postgres:16-alpine`        | PostgreSQL with `pg_trgm`, `unaccent`, and `btree_gist` loaded on first boot |
| `api`     | `python:3.12-slim-bookworm` | Django 5.2 + Django REST Framework + JWT auth |
| `web`     | `node:22-bookworm-slim`     | Nuxt 3 with Nuxt UI v3 and Pinia              |

All three live on a private `ijara` Docker network. The `web` container
talks to `api` over Docker DNS, while the browser talks to `api` over
the host's `localhost:8000` mapping. The dual-URL split is configured
through Nuxt's `runtimeConfig`, so server-side rendering and client-side
fetches both work without CORS detours.

The healthcheck chain is strict: `db` must report `pg_isready` before
`api` boots, and `api` must return 200 on `/api/v1/health/` before `web`
starts. This gives deterministic cold-start ordering without any
application-level retry code.

---

## API surface

A summary of the most useful endpoints. Everything is namespaced under
`/api/v1/`.

### Authentication

| Method | Path                          | Purpose                                    |
| ------ | ----------------------------- | ------------------------------------------ |
| POST   | `/auth/register`              | Create an account                          |
| POST   | `/auth/login`                 | Exchange credentials for an access token   |
| POST   | `/auth/refresh`               | Rotate the refresh cookie, return access   |
| POST   | `/auth/logout`                | Blacklist the refresh token                |
| GET    | `/auth/me`                    | The signed-in user's profile               |
| GET    | `/auth/users/me/profile/`     | Editable profile fields                    |
| PATCH  | `/auth/users/me/profile/`     | Update display name, phone, or bio         |
| POST   | `/auth/users/me/avatar/`      | Upload an avatar (JPEG, PNG, or WebP)      |

The access token lives in memory; the refresh token is an HttpOnly,
Secure, SameSite=Lax cookie at path `/api/auth/`. Browser JavaScript
cannot read the refresh cookie, which closes the most common token-
exfiltration vector.

### Listings

| Method | Path                                  | Purpose                                |
| ------ | ------------------------------------- | -------------------------------------- |
| GET    | `/listings/`                          | Browse with filters and search         |
| POST   | `/listings/`                          | Create a listing (owner)               |
| GET    | `/listings/<id>/`                     | Listing detail (anonymous OK)          |
| PATCH  | `/listings/<id>/`                     | Update a listing (owner only)          |
| DELETE | `/listings/<id>/`                     | Soft-delete                            |
| POST   | `/listings/<id>/photos/`              | Upload a photo (multipart)             |
| DELETE | `/listings/<id>/photos/<pk>/`         | Remove a photo                         |

Filters: `category`, `district`, `q` (search), `unit`, `min_price`,
`max_price`. Search runs against a persistent `SearchVectorField`
(title weight A, description weight B) and falls back to trigram
word-similarity for typos.

### Bookings

| Method | Path                                | Purpose                                  |
| ------ | ----------------------------------- | ---------------------------------------- |
| GET    | `/bookings/?role=renter`            | Bookings I have made                     |
| GET    | `/bookings/?role=owner`             | Bookings on my listings                  |
| POST   | `/bookings/`                        | Create a booking (renter)                |
| POST   | `/bookings/quote/`                  | Price preview, no save                   |
| GET    | `/bookings/<id>/`                   | Booking detail with full timeline        |
| PATCH  | `/bookings/<id>/`                   | Move the booking to a new state          |

The booking workflow has nine states: `requested`, `accepted`,
`rejected`, `cancelled`, `paid`, `picked_up`, `returned`, `completed`,
`disputed`. Allowed transitions and the actor who can drive each one
(owner, renter, system, admin) are enforced in a single service
function. Every transition is recorded in a separate audit table.

Three database-level invariants protect data integrity:

1. **No double bookings.** A Postgres exclusion constraint over the
   `(start_at, end_at)` time range, filtered to active states, blocks
   two bookings from sharing a window on the same listing.
2. **No direct state writes.** A grep for `booking.state = ...`
   outside the booking service finds zero hits.
3. **Pricing snapshot.** Unit, unit price, quantity, and total are
   locked at booking creation. Owner edits to listing prices have
   zero effect on existing bookings.

---

## Project layout

```
.
├── backend/                — Django 5.2 + Django REST Framework
│   ├── ijara/              — project package (settings, urls)
│   ├── apps/
│   │   ├── accounts/       — custom user model, JWT auth, profiles
│   │   ├── catalog/        — listings, photos, demo seed command
│   │   ├── bookings/       — booking workflow with FSM and pricing
│   │   ├── payments/       — Stripe integration (optional)
│   │   ├── search/         — full-text search helpers
│   │   └── common/         — health endpoint, shared utilities
│   ├── scripts/            — entrypoint.sh and Postgres init SQL
│   ├── pyproject.toml      — pinned Python dependency set
│   └── Dockerfile
├── frontend/               — Nuxt 3 application
│   ├── pages/              — public listings, dashboard, auth
│   ├── components/         — reusable Vue components
│   ├── composables/        — useApi, useListings, useBookings, ...
│   ├── server/api/auth/    — Nitro proxy routes (BFF for auth)
│   ├── nuxt.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Common commands

Run the backend test suite (pytest):

```bash
docker compose exec api pytest
```

Run the frontend unit tests (Vitest):

```bash
docker compose exec web npx vitest run --config vitest.unit.config.ts
```

Run the end-to-end tests (Playwright):

```bash
docker compose exec web npx playwright test
```

Open a Django shell:

```bash
docker compose exec api python manage.py shell
```

Open a Postgres shell:

```bash
docker compose exec db psql -U ijara -d ijara
```

Apply migrations after a model change:

```bash
docker compose exec api python manage.py makemigrations
docker compose exec api python manage.py migrate
```

Reset the demo data:

```bash
docker compose exec api python manage.py seed_demo --reset
```

---

## Troubleshooting

### Port already in use

If `docker compose up` fails with "port is already allocated", another
process on the host is holding 3000, 5432, or 8000:

```bash
# macOS / Linux
lsof -i :3000 -i :5432 -i :8000

# Windows (PowerShell)
Get-NetTCPConnection -LocalPort 3000,5432,8000
```

Stop the offending process or change the host port mapping in
`docker-compose.yml`.

### Health badge stays red on the front page

The badge goes red when the Nuxt server cannot reach the API across the
Docker network. Three checks narrow the cause:

```bash
docker compose ps
docker compose logs api --tail 40
curl -fsS http://localhost:8000/api/v1/health/
```

If `api` is healthy and the host curl returns 200, the Nuxt server-side
base URL has drifted from the Docker DNS name. The default value is
`http://api:8000/api/v1/`.

### Demo data did not appear

The seed only runs on a fresh database (no users yet). To force a reseed
on top of an existing database:

```bash
docker compose exec api python manage.py seed_demo --reset
```

To wipe the database completely and let the entrypoint reseed on next
boot:

```bash
docker compose down -v
docker compose up --build -d
```

### Windows-specific notes

- Use Docker Desktop with the WSL 2 backend — the Linux backend is the
  one this stack is tested against.
- File-watch updates (live reload) are slower under WSL 2 than on a
  native Linux host, but the stack functions correctly. Restart the
  affected container if a change does not show up after a few seconds.
- Line endings are pinned to LF for shell scripts via `.gitattributes`,
  so `entrypoint.sh` boots cleanly even on a Windows checkout.

---

## License

This repository is the code artefact for a final-year university
project. It is published for academic and portfolio purposes. The
seeded photos are fetched from `picsum.photos` at seed time and are
covered by their respective licenses; the placeholder fallback is
generated locally with Pillow.
