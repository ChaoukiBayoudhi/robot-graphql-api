# Robot GraphQL API

Django + Strawberry GraphQL API for robot fleet management.

## Tech stack

- Python 3
- Django
- Strawberry GraphQL
- django-cors-headers
- psycopg2 (PostgreSQL)
- Database: PostgreSQL

## Project structure

- `robot_graphql_api/`: project settings and root URLs
- `api/`: Django app
- Tests: `api/tests.py`

## Data model

| Model | App | Fields |
|---|---|---|
| `Robot` | `api` | id, name, serial_number, battery_level, max_speed, is_active, created_at |
| `Drone` | `api` | id, name, serial_number, max_altitude, payload_capacity, battery_level, is_autonomous |
| `TechnicalSpecification` | `api` | robot, drone, cpu, memory_gb, firmware_version |
| `Mission` | `api` | id, name, description, start_time, end_time, status |
| `Task` | `api` | mission, title, priority, is_completed |
| `MissionParticipation` | `api` | mission, agent_id, role, assigned_at |
| `TelemetryRecord` | `api` | agent_id, timestamp, data |

## URL routes

Declared in `urls.py`:

- `/health/`
- `/graphql/`
- `/api/`

## How to run

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

`settings.py` is configured for PostgreSQL: create the database and use your own credentials before running `migrate`.

Copy `.env.example` to `.env` and fill in your own values.

Then open `http://127.0.0.1:8000/`.

---

Author: [Chaouki Bayoudhi](https://github.com/ChaoukiBayoudhi)
