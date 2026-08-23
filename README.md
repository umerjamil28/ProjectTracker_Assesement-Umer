# Organization Project & Task Tracker

## Setup instructions

This is a Python 3.12+ / Django 5 + DRF backend and a Vue 3 frontend. The Postgres database is already migrated and seeded. A `DATABASE_URL` is provided with this submission — put that in `.env`. You do not need to create tables or dummy data.

Work from two folders:

- **Backend, tests** — repo root (the folder that contains `manage.py`)
- **Frontend** — `frontend/`

### 1. Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and set `DATABASE_URL` to the connection string provided with this submission. Leave the other values as they are (`SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`).

Start the API from the repo root, with the virtualenv active:

```powershell
python manage.py runserver
```

- API: `http://127.0.0.1:8000`
- Health: `GET http://127.0.0.1:8000/api/health/`

### 2. Frontend

Second terminal:

```powershell
cd frontend
npm install
npm run dev
```

UI: `http://127.0.0.1:5173`

Vite proxies `/api` to Django, so the browser only needs port 5173. Keep both processes running.

### 3. Tests

From the repo root, virtualenv active:

```powershell
python manage.py test
```

Three tests, as requested: one permission, one API, one model validation. They run on in-memory SQLite and do not write to the shared database. Each test prints what it did.

### Demo login

Password for every user: `DemoPass123!`

| User | Role |
|---|---|
| `alice` | Acme admin, Globex member |
| `bob` | Acme member |
| `carol` | Acme viewer (read-only) |
| `dave` | Globex admin |
| `eve` | Globex member |

Use `alice` to switch organizations and create projects. Use `carol` to confirm viewers cannot write. Use `dave` to confirm Globex cannot see Acme.

---

## Key design decisions

**Django’s built-in user, one `api` app.** The brief asked to use Django’s user model. A custom user or extra apps would have added migrations without changing the product. Organization, Membership, Project, and Task live in `api/models.py`. Users belong to many organizations through Membership (`admin` / `member` / `viewer`). A project belongs to exactly one organization. A task belongs to one project and must be assigned to a member of that same organization.

**ORM only.** Tables come from migrations. Queries use `filter`, `annotate`, `prefetch_related`, and `Count`. No raw SQL. Indexes sit on `(organization, is_active)`, `(project, status)`, and `(project, assigned_to)`.

**Token authentication.** We used DRF token auth. Login returns a token; the Vue app sends `Authorization: Token <token>` on each request; logout deletes it. We chose this because the frontend is a separate Vite app, so a token is simpler than session cookies and CSRF, and we did not need JWT refresh or expiry for this demo.

**Tenancy through membership, not a header.** Every project and task is loaded only if the caller belongs to that organization. Guessing another org’s id returns `403` / `404`. Admins create projects. Members create and update tasks. Viewers are read-only. Checks live in `api/permissions.py`.

**Assignee rule in two places.** `Task.clean()` / `save()` reject a non-member even from the shell or admin. The serializer rejects the same case on the API with a field error.

**Performance on the project list.** `GET /api/v1/organizations/<id>/projects/` returns `open_task_count` and assignee usernames. That is one `annotate(Count)` plus a prefetch of tasks with `select_related("assigned_to")`. No N+1.

**Tests stay off the shared database.** `manage.py test` forces in-memory SQLite so the suite never creates or mutates the provided Postgres.

**Frontend.** Vue 3 covers login, org switch, projects, task filters, create/update/delete/done, and pagination. It is enough to exercise the APIs. It does not try to wrap every route.

---

## Optional enhancements

The brief said pick 1–2 if time allowed. We shipped four:

1. **API versioning** — application routes live under `/api/v1/`.
2. **Pagination** — task lists use page size 5 (`?page=2`).
3. **Soft deletes** — `DELETE /api/v1/tasks/<id>/` sets `deleted_at`. Those rows are hidden from lists and from open-task counts. There is no restore endpoint.
4. **Caching** — the Vue app keeps orgs, projects, and task pages in memory. Switching back shows the last result immediately, then refreshes. In-flight requests are aborted when you change org or project. We cache that because those lists are hit on every switch, and a second network trip to Postgres is the slow part. This is not Django cache or Redis.

---

## Tradeoffs you made

**No project update API.** The brief asked for list + create (admins only). PATCH on projects would have been easy and unused.

**Soft delete is one-way.** Keeping the row is useful for review. Building restore, a deleted-items list, and UI for it would have been a second product.

**No Django cache / Redis.** The project list is already one annotated query. A shared server cache would hide bugs more than it would help at this size. Caching lives in the frontend instead (see Optional enhancements).

**Page size 5.** Small on purpose so a second page shows up in the demo without a huge seed.

**Remote Postgres latency.** The first request to the provided database can feel slow. That is network and SSL, not query shape.

**One app at the repo root.** A `backend/` wrapper would only move `manage.py` and `.env`. The usual Django layout is repo root = project, `frontend/` = UI.

**Quality over coverage.** Three high-value tests, not a full suite. That matches the brief.

---

## What you’d improve with more time

- A time tracker on tasks: start/stop a timer, log hours, and see time spent per task and per person
- Stronger user permissions: invite and remove members from the UI, let admins change roles, and let members edit only tasks assigned to them
- More permission coverage: cross-org access, and a viewer trying to mark a task done
- Restore for soft-deleted tasks, and an admin-only view of them
- An audit log of who changed a task
- A due-date reminder (management command or background job)
- Clearer empty and error states on the frontend
