# ElimuNova

ElimuNova: *Reimagining Education. Empowering Every Future.* A modern school management platform for Kenyan schools (primary, junior secondary and senior secondary).
(Formerly ElimuPro. See [docs/BRANDING.md](docs/BRANDING.md) for what was renamed and what deliberately kept its old identifier.)
Multi-school SaaS: every record belongs to a school and the backend enforces that a school can only reach its own data.

> **Honest status.** This is a working *core* (phases 1-3 and the essentials of 4), not the full product. See
> [What is built](#what-is-built-and-what-is-not) before relying on anything.

## Product purpose and target users
- **Students / learners** create their own account, apply for admission, then see a personal dashboard (results, timetable, fees, announcements).
- **Teachers** see only their assigned classes, view class lists, create exams and enter results (learners see marks immediately).
- **Parents / guardians** log in to see each linked child's results, fee balance and payments, timetable and school news (one login can cover several children).
- **School administrators** (admin, principal, deputy) review applications, enrol students, manage classes, streams, subjects, fees and announcements.
- **Bursars** record payments and view balances.
- **Platform super admin** creates schools and activates/deactivates them.
- There is **no attendance module** anywhere, by design.

## The core workflow (implemented end to end)
Student signs up → account + draft application created → student completes 3-step form → submits (gets reference `ELM-2026-XXXXXX`) →
application appears in admin list → admin reviews (start review / request changes / reject / approve) → approval creates the `students` record,
assigns admission number, class and stream, copies guardian details → the same login now shows the student dashboard.
All screens read the same database rows.

## What is built and what is not
**Built and covered by automated tests (backend):** authentication (JWT, bcrypt), roles, school isolation, student signup, admissions workflow,
student dashboard/profile/results/fees/timetable/announcements, teacher accounts and class/subject assignments, teacher dashboard, class lists and result entry (permission-checked per class and subject), parent accounts linked to children through guardians, parent dashboard and per-child results/fees/timetable, admin student management, classes/streams/subjects, exams and result entry,
fee structures/assignment/manual payments, announcements, super-admin school management.

**Built, compiled, but not exercised in a browser or covered by frontend tests:** the React app (public pages, signup, application form,
student portal, admin portal incl. Teachers and Parents pages, teacher portal incl. mark-entry screen, parent portal, platform page, PWA manifest + service worker).

**Not built yet (no placeholder pages were created for them):** report cards
(students can print the results page from the browser), per-student subject assignment, teacher timetable view, class-teacher-specific permissions (the `class_teacher` role currently behaves like `teacher`), timetable *editor UI* (API exists), admin-side result entry and exam management UI (teachers have it; the API allows admins), messages/notifications, library, inventory, boarding, transport, reports and CSV/PDF export, password-reset flow, document
upload (table exists), M-Pesa callback handling, rate limiting, `seed.sql`
(demo data is loaded with `backend/seed.py` because passwords must be hashed).

**M-Pesa:** `backend/app/services/mpesa.py` implements Daraja OAuth and STK Push using environment variables, but it has **never been run against
Safaricom** (no credentials were available). The callback endpoint does not exist yet, so an STK Push cannot update balances. Payments are currently
recorded manually by staff (cash / bank / M-Pesa code).

## Technology
React 18 (JavaScript, React Router 6, plain CSS, `react-scripts`; no Vite) · Flask 3, SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, Flask-Bcrypt, Flask-CORS · PostgreSQL (SQLite is used by tests).

## Project structure
```
<repository>/
  backend/    Flask API (app/models, routes, services, utils, config), tests/, seed.py, export_schema.py
  frontend/   React app (src/pages, layouts, components, context, services, hooks, utils) + public/ (PWA files)
  database/   schema.sql (generated from the models)
  docs/       API.md, DATABASE.md, SETUP.md, DEPLOYMENT.md
```

## Prerequisites
Python 3.10+, Node.js 18+, PostgreSQL 15+ (or Docker Desktop).

## Run with Docker
Copy `.env.example` to `.env`, replace the development-only secrets, then run `docker compose up --build`. The frontend is at
`http://localhost:8080`; the API is at `http://localhost:5000/api/v1`. Compose starts PostgreSQL, applies migrations, then starts the API and frontend.

## Local development
Full setup instructions are in [docs/SETUP.md](docs/SETUP.md). In short:
```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # configure PostgreSQL and generate distinct secrets
flask --app run:app db upgrade
python seed.py              # DEMO data only, into an empty database
python run.py               # http://localhost:5000

# Frontend (new terminal)
cd ../frontend && cp .env.example .env && npm ci && npm start   # http://localhost:3000
```

## Environment variables
Backend (`backend/.env`): `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL` (PostgreSQL), `FRONTEND_URL` (CORS origin), `JWT_ACCESS_HOURS`, `MPESA_*`.
Frontend (`frontend/.env`): `REACT_APP_API_URL`. No `.env` file is shipped; never commit one.

## Tests
```bash
cd backend && pytest -q
```
The backend suite runs against in-memory SQLite. Production schema changes use Flask-Migrate; the PostgreSQL schema reference is generated by `backend/export_schema.py`.
There are no frontend tests.

## Demo accounts (created by `seed.py`, demo data only)
Password for all: `Demo@1234`

| Role | Email |
|---|---|
| Super admin | super@elimupro.demo |
| School admin (Mwangaza Academy) | admin@mwangaza.demo |
| Bursar | bursar@mwangaza.demo |
| Teacher (Grade 7 Maths, English, Science) | teacher@mwangaza.demo |
| Parent of Achieng and Wekesa (two children) | mary.otieno@mwangaza.demo |
| Parent of Baraka | james.mwangi@mwangaza.demo |
| Student (enrolled) | achieng@mwangaza.demo |
| Second school admin (isolation demo) | admin@tumaini.demo |

Three applicants (kiprono@, wanjiru@, zawadi@mwangaza.demo; the last is already "under review") are waiting in the admin list. To wipe and reload the demo data on a development database run `python reset_demo.py` in `backend/`. **Never seed or keep demo accounts in production.**

## API overview
See [docs/API.md](docs/API.md). Canonical base path `/api/v1` (`/api` remains a compatibility alias); responses are `{success, data, message?, meta?}` or `{success:false, message, errors?}`.

## PWA installation
Production builds register a service worker and include a manifest and icons. Open the deployed site over HTTPS in Chrome on Android and choose
"Install app" / "Add to Home screen". The service worker caches the app shell only, never API responses. Installability was not tested on a device.

## Deployment and troubleshooting
See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Vercel, Supabase PostgreSQL, and container hosting guidance.
