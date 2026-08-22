# API use cases

All application routes are under `/api/v1/`. After login, send:

```
Authorization: Token <token>
```

---

## Authentication

| Use case | Method | Endpoint |
|---|---|---|
| Log in | `POST` | `/api/v1/auth/login/` |
| Log out | `POST` | `/api/v1/auth/logout/` |
| Current user and memberships | `GET` | `/api/v1/auth/me/` |

Login body:

```json
{ "username": "alice", "password": "DemoPass123!" }
```

Login response: `{ "token": "...", "user": { ... } }`.  
Logout does not need a body. It deletes the token (`204`).

---

## Organizations

| Use case | Method | Endpoint |
|---|---|---|
| List organizations the user belongs to | `GET` | `/api/v1/organizations/` |

Each org includes the caller’s `role` (`admin` / `member` / `viewer`).  
A user only sees orgs they are a member of.

---

## Projects

| Use case | Method | Endpoint |
|---|---|---|
| List projects in an organization | `GET` | `/api/v1/organizations/<id>/projects/` |
| Create a project (admins only) | `POST` | `/api/v1/organizations/<id>/projects/` |

Create body:

```json
{ "name": "New Project" }
```

Members and viewers get `403` on create.

The list is also the performance endpoint. Each project includes:

- `open_task_count` — open tasks that are not soft-deleted
- `assignees` — unique usernames

---

## Tasks

| Use case | Method | Endpoint |
|---|---|---|
| List tasks for a project | `GET` | `/api/v1/projects/<id>/tasks/` |
| Filter by status | `GET` | `/api/v1/projects/<id>/tasks/?status=open` |
| Filter by assignee | `GET` | `/api/v1/projects/<id>/tasks/?assignee=bob` |
| Filter by assignee id | `GET` | `/api/v1/projects/<id>/tasks/?assignee=2` |
| Create a task | `POST` | `/api/v1/projects/<id>/tasks/` |
| Update a task | `PATCH` | `/api/v1/tasks/<id>/` |
| Mark a task as done | `POST` | `/api/v1/tasks/<id>/done/` |

`status` values: `open`, `in_progress`, `done`.  
`assignee` accepts a username or a user id.

Create / update body:

```json
{
  "title": "Draft homepage",
  "description": "Optional",
  "assigned_to": 2,
  "status": "open",
  "due_date": "2026-08-30"
}
```

Task lists are paginated (`page_size` 5). Use `?page=2`.

Viewers can list and filter. They cannot create, update, or mark done (`403`).

---

## Extra endpoints

Not in the required list. Used by the UI.

| Use case | Method | Endpoint |
|---|---|---|
| List org members (assignee dropdown) | `GET` | `/api/v1/organizations/<id>/members/` |
| Soft-delete a task | `DELETE` | `/api/v1/tasks/<id>/` |
| Health check | `GET` | `/api/health/` |

Soft-delete sets `deleted_at`. The task disappears from lists and from open-task counts.

---

## Who can call what

| Role | Projects | Tasks |
|---|---|---|
| Admin | List + create | List, create, update, mark done, delete |
| Member | List | List, create, update, mark done, delete |
| Viewer | List | List only |
| Non-member | `403` / `404` | `403` / `404` |

`400` invalid input · `401` missing or bad token · `403` wrong role · `404` missing or out of scope.
