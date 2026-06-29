# Sahal Notary System

A Django web application for managing notarized documents in Somalia, with a
bilingual (Somali / English) interface across three roles — **Macmiil**
(Client), **Notaayo** (Notary), and **Maamule** (Admin) — plus a public,
no-login document verification page reached by scanning a QR code.

> **Note on stack accuracy:** this README documents what is actually
> implemented in the codebase as of this writing. The project currently runs
> on **SQLite**, not PostgreSQL — see [Database](#database) and
> [Technology Stack](#technology-stack) for details and what switching to
> Postgres would require.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation Guide](#installation-guide)
- [Environment Variables](#environment-variables)
- [Database](#database)
- [User Roles](#user-roles)
- [Workflow](#workflow)
- [Main Modules](#main-modules)
- [URL Routes](#url-routes)
- [Static Files](#static-files)
- [Security Features](#security-features)
- [Reports](#reports)
- [PDF / Printing](#pdf--printing)
- [Signature System](#signature-system)
- [Screenshots](#screenshots)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Future Improvements](#future-improvements)
- [License](#license)
- [Author](#author)
- [Version](#version)
- [Support](#support)

---

## Overview

Sahal Notary System digitizes the lifecycle of a notarized document:

1. A **Notary** picks a client and a reusable **document template** through a
   guided, multi-step wizard, optionally adding a second party and witnesses.
2. The system renders the template body, substituting placeholders
   (`{{client_name}}`, `{{date}}`, `{{client_signature}}`, etc.) with real
   data and the client's captured signature image.
3. Once all required signatures are on file, the notary **completes** the
   document: it's hashed (SHA-256), rendered to PDF with an embedded
   verification QR code, and locked.
4. The **Client** can log in at any time to see their documents and download
   the PDF.
5. Anyone — no account required — can scan the QR code (or open its URL) to
   **verify** the document's authenticity and content hash.
6. An **Admin** manages the client and notary roster and reviews activity
   through a reporting dashboard.

## Key Features

| Feature | Status | Notes |
|---|---|---|
| Authentication | ✅ Implemented | Custom session-based login (username + password), "remember me", forced password change on first login (temp password), Somali-localized error messages |
| Forgot / Reset Password | ❌ Not Implemented | The login page shows a static message directing users to contact the System Administrator; there is no self-service email reset flow |
| Role-Based Access Control | ✅ Implemented | `accounts.User.Role` (`CLIENT` / `NOTARY` / `ADMIN`) enforced by a `role_required` decorator and a middleware that pins users with a temporary password to the change-password page |
| Dashboard | ✅ Implemented | Per-role landing page: client document list + status counts, notary activity overview, admin reports |
| Client Management | ✅ Implemented | Admin-side create / edit / delete for clients, with phone & national-ID uniqueness validation |
| Officer (Notary) Management | ✅ Implemented | Admin-side create / edit / delete for notaries; notaries also have a self-service profile page (phone, bio, stamp image) |
| Document Management | ✅ Implemented | Create (via wizard), list, detail view, edit (while still `PENDING`), complete, PDF download |
| Document Templates | ✅ Implemented | Title, free-text category, one-party/two-party type, witness requirement, placeholder-driven body, usage counter; delete blocked once a template has been used |
| Categories | ⚠️ Partial | `category` is a free-text field on `DocumentTemplate` used to build a filter dropdown — **not** a dedicated `Category` model/CRUD |
| Rich Text Editor | ❌ Not Implemented | Template body is a plain `<textarea>` |
| Digital Signature | ✅ Implemented | In-browser canvas signature pad; a client's signature is captured once and reused on every document; notaries also have a signature + stamp image |
| PDF Generation | ✅ Implemented | `xhtml2pdf` renders the document (with embedded signatures, notary seal, and QR code) to a downloadable PDF |
| Verification Workflow | ✅ Implemented | Public, login-free `/verify/<uuid>/` page showing document details and content hash, plus a generated QR PNG |
| Search | ⚠️ Partial | Client-side, instant text filtering of on-page lists (`live_filter.js`) — not a server-side/database full-text search |
| Reports | ✅ Implemented | Stat cards, monthly trend chart, notary activity bar chart, per-notary performance trend chart, and a day/month/custom-range date filter driving all of it |
| Notifications | ❌ Not Implemented | |
| Audit Logs | ⚠️ Partial | `AuditLog` model records "document completed" events; viewable via Django Admin only — no dedicated front-end page |
| User Profile | ⚠️ Partial | Notaries/Admins have a self-service profile page; clients do **not** — their record is managed by an Admin |
| Settings | ❌ Not Implemented | No dedicated settings page beyond password change |
| Internationalization | ✅ Implemented | English + Somali, runtime language switcher, `.po`/`.mo` catalogs under `locale/` |
| Demo Data Seeding | ✅ Implemented | `python manage.py seed_demo` management command |

## Technology Stack

**Backend**
- Python 3 / [Django](https://www.djangoproject.com/) `5.2.8`
- [`django-formtools`](https://django-formtools.readthedocs.io/) — powers the multi-step document creation wizard (`SessionWizardView`)

**Frontend**
- Server-rendered Django templates (no SPA framework)
- Vanilla JavaScript, no bundler — small per-page scripts (sidebar toggle, signature pad, live filter, date-filter bar, charts)
- [Chart.js 4.4.1](https://www.chartjs.org/) loaded from a CDN — used only on the admin Reports page
- A hand-written CSS design system in `portal/static/css/main.css` (CSS custom properties for color/spacing/typography) — no Tailwind/Bootstrap

**Database**
- **SQLite** (`db.sqlite3`) — the only database currently configured (`notary/settings.py`)
- **PostgreSQL: Not Implemented.** There is no `psycopg2`/`psycopg`, no `dj-database-url`, and no environment-driven `DATABASES` dict in this codebase. Moving to Postgres would mean adding a driver package, setting `DATABASES['default']['ENGINE']` to `django.db.backends.postgresql`, and supplying connection details (ideally via environment variables, mirroring how email settings are already done).

**Libraries / Packages** (pinned in `requirements.txt`)

| Package | Version | Purpose |
|---|---|---|
| Django | 5.2.8 | Web framework |
| django-formtools | 2.5.1 | Multi-step document creation wizard |
| xhtml2pdf | 0.2.16 | HTML → PDF rendering |
| qrcode | 7.4.2 | QR code generation |
| Pillow | 11.0.0 | Image handling (signatures, stamps, QR PNGs) |
| python-dotenv | 1.2.2 | Loads `.env` into the process environment for `settings.py` |

**Third-party integrations**
- Chart.js (CDN script tag, reports page only — no npm/build step)
- SMTP email configuration exists in `settings.py` (configured via environment variables, with a console-backend fallback in development) but nothing in the app currently sends email — there is no self-service password reset; users who forget their password must contact a System Administrator

## Project Structure

```
sahal-notary/
├── accounts/                  Custom user model & authentication
│   ├── models.py              User (AbstractUser + role, must_change_password)
│   ├── views.py                login / logout / password change
│   ├── forms.py                SomaliAuthenticationForm
│   ├── middleware.py           ForcePasswordChangeMiddleware
│   ├── decorators.py           role_required
│   ├── urls.py
│   └── templates/accounts/     login, password_change
│
├── portal/                    Core domain app
│   ├── models.py               ClientProfile, NotaryProfile, DocumentTemplate,
│   │                           Document, Witness, AuditLog
│   ├── views_admin.py          Admin: clients/notaries CRUD, reports + date filter
│   ├── views_notary.py         Notary: overview, templates CRUD, documents, profile
│   ├── views_client.py         Client: dashboard, PDF download
│   ├── views_public.py         Public: home redirect, document verification, QR image
│   ├── wizard.py                Multi-step document creation wizard
│   ├── forms.py                 All portal-side forms
│   ├── utils.py                 PDF rendering, QR generation, helpers
│   ├── admin.py                 Django Admin registrations
│   ├── templatetags/icons.py    Inline SVG icon system
│   ├── static/                  css/main.css, js/*, img/
│   ├── templates/portal/        base layouts + admin/notary/client/public/pdf templates
│   └── tests/                   Model, view, util, and wizard tests
│
├── notary/                     Django project (settings, root urls, wsgi/asgi)
├── locale/                     en / so translation catalogs
├── media/                      Uploaded signatures & stamp images (gitignored)
├── .env.example                Template for required environment variables
├── requirements.txt
└── manage.py
```

## Installation Guide

```bash
# 1. Clone the project
git clone https://github.com/casaradda-spec/sahal-notary.git
cd sahal-notary

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment variables
copy .env.example .env           # Windows
# cp .env.example .env           # macOS / Linux
# then edit .env with real values (see Environment Variables below)

# 6. Apply database migrations
python manage.py migrate

# 7. Create an administrator account
python manage.py createsuperuser
# — or seed realistic demo data instead (see below) —
python manage.py seed_demo

# 8. Run the development server
python manage.py runserver
```

Then visit `http://127.0.0.1:8000/`.

### Demo accounts (from `seed_demo`)

All seeded accounts use the temporary password `123` and are forced to
change it on first login.

| Username | Role |
|---|---|
| `admin` | Admin (Maamule) |
| `maxamed.daahir` | Notary (Notaayo) |
| `amina.yusuf` | Client (Macmiil) |

### Running tests

```bash
python manage.py test
```

## Environment Variables

Read via `os.environ` in `notary/settings.py` (loaded from `.env` through
`python-dotenv`). All have defaults except none are required to *run* the
app — without SMTP credentials, the app falls back to printing emails to the
console.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `EMAIL_HOST` | No | `smtp.gmail.com` | SMTP server host |
| `EMAIL_PORT` | No | `587` | SMTP server port |
| `EMAIL_HOST_USER` | No | *(empty)* | SMTP username; if empty, `EMAIL_BACKEND` falls back to the console backend |
| `EMAIL_HOST_PASSWORD` | No | *(empty)* | SMTP password / app password |
| `DEFAULT_FROM_EMAIL` | No | `noreply@sahal.com` | "From" address on password-reset emails |
| `EMAIL_BACKEND` | No | auto-selected | Explicit override of Django's email backend, if needed |

See `.env.example` for a ready-to-copy template — **never commit real
credentials to that file**; put them in `.env` instead, which is
git-ignored.

> ⚠️ `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` are currently **hardcoded** in
> `notary/settings.py` rather than environment-driven. This is fine for local
> development but must be addressed before any production deployment — see
> [Deployment](#deployment).

## Database

**Engine:** SQLite (`db.sqlite3`, file-based, no separate server process).
PostgreSQL is **not configured** in this project (see
[Technology Stack](#technology-stack)).

**Main models** (`portal/models.py` and `accounts/models.py`):

| Model | Key fields | Notes |
|---|---|---|
| `accounts.User` | `role` (`CLIENT`/`NOTARY`/`ADMIN`), `must_change_password` | Extends Django's `AbstractUser`; `role_home_url()` routes each role to its landing page |
| `ClientProfile` | `user` (1:1), `national_id`, `phone`, `city`, `address`, `signature` | `doc_count` property sums documents as party 1 and party 2 |
| `NotaryProfile` | `user` (1:1), `license_number`, `region`, `phone`, `signature`, `seal_image`, `rating`, `bio` | |
| `DocumentTemplate` | `title`, `category`, `party_type` (`ONE`/`TWO`), `requires_witnesses`, `body`, `times_used` | `body` supports `{{client_name}}`, `{{client2_name}}`, `{{date}}`, `{{city}}`, `{{notary_name}}`, `{{notary_license}}`, `{{ref}}`, and signature placeholders |
| `Document` | `ref`, `template` (FK), `notary` (FK), `client`/`client2` (FK), `status` (`PENDING`/`SIGNED`/`COMPLETED`), `rendered_body`, `content_hash`, `pdf_hash`, `qr_token` | `ref` is auto-generated as `SNS-<n>`; `finalize()` snapshots and hashes the rendered body |
| `Witness` | `document` (FK), `name`, `phone`, `order` | Up to 5 per document (formset `max_num`) |
| `AuditLog` | `user`, `action` (`DOCUMENT_COMPLETED`), `document`, `details`, `created_at` | Currently the only logged action is document completion |

## User Roles

Defined by `accounts.User.Role`:

| Role (code) | Somali label | Landing page | Can do |
|---|---|---|---|
| `ADMIN` | Maamule | `/admin-panel/reports/` | Manage clients & notaries, view reports; also has notary-level access (template/document management, since `role_required` lists often include both `NOTARY` and `ADMIN`) |
| `NOTARY` | Notaayo | `/notary/` | Create documents via the wizard, manage templates, view/edit/complete documents, manage own profile |
| `CLIENT` | Macmiil | `/app/` | View own documents (as party 1 or 2), download PDFs |

Access control is enforced by the `role_required(*roles)` decorator on every
view (it 403s via `PermissionDenied` for the wrong role, and requires login
via Django's `login_required`). `ForcePasswordChangeMiddleware` additionally
redirects any authenticated user with `must_change_password=True` to
`/password-change/` regardless of role, except for the logout path.

## Workflow

1. **Login** (`/login/`) with username + password. First-time/seeded users
   are redirected to `/password-change/` until they set a real password.
2. **Role redirect** sends the user to their landing page
   (`role_home_url()`).
3. **Notary creates a document** via the wizard at `/notary/create/`:
   - Step 1 — select a client (blocked if the client's profile is missing
     required fields, e.g. no signature on file)
   - Step 2 — select a template
   - Step 3 *(if the template is two-party)* — select the second party
   - Step 4 *(if the template requires witnesses)* — enter 0–5 witnesses
   - Step 5 — review a live preview, then confirm
   - On confirm, the `Document` is created with status `PENDING`, its body
     rendered and hashed, and the template's `times_used` incremented.
4. **Notary completes the document** once every required signature is on
   file: status moves `PENDING → SIGNED → COMPLETED`, a PDF is rendered and
   SHA-256-hashed, `signed_at` is stamped, and an `AuditLog` entry is created.
5. **Client** logs in, sees the document on their dashboard (filterable by
   status), and downloads the PDF.
6. **Anyone** can scan the document's embedded QR code to open
   `/verify/<uuid>/`, a public page showing the document's details and
   content hash with no login required.

## Main Modules

- **`accounts`** — custom `User` model, login/logout, forced first-login
  password change, role decorator, password-change-enforcement middleware.
  There is no self-service password reset; the login page directs users to
  contact a System Administrator.
- **`portal` (admin)** — `views_admin.py`: client & notary CRUD, client
  signature capture, and the Reports dashboard.
- **`portal` (notary)** — `views_notary.py` + `wizard.py`: document template
  CRUD, the document creation wizard, document list/detail/edit/complete,
  and the notary's own profile.
- **`portal` (client)** — `views_client.py`: status-filterable document
  dashboard and PDF download.
- **`portal` (public)** — `views_public.py`: root redirect, QR-driven
  document verification page, and QR PNG generation.
- **`portal.utils`** — PDF rendering (`xhtml2pdf`), QR code generation
  (`qrcode`), signature decoding, username generation, and shared helpers.

## URL Routes

| Route | Name | View | Notes |
|---|---|---|---|
| `/` | `home` | `views_public.home_redirect` | Redirects to role landing page or login |
| `/login/` | `login` | `accounts.login_view` | |
| `/logout/` | `logout` | `accounts.logout_view` | |
| `/password-change/` | `password_change` | `accounts.password_change_view` | |
| `/app/` | `client_dashboard` | `views_client.dashboard` | Client only |
| `/app/documents/<ref>/pdf/` | `client_document_pdf` | `views_client.document_pdf` | Client only |
| `/notary/` | `notary_overview` | `views_notary.overview` | Notary only |
| `/notary/templates/` | `notary_templates` | `views_notary.template_list` | Notary, Admin |
| `/notary/create/` | `notary_create` | `wizard.CreateDocumentWizard` | Notary, Admin |
| `/notary/documents/` | `notary_documents` | `views_notary.all_documents` | Notary, Admin |
| `/notary/documents/<ref>/` | `notary_document_detail` | `views_notary.document_detail` | Notary, Admin |
| `/notary/documents/<ref>/complete/` | `notary_document_complete` | `views_notary.document_complete` | Notary, Admin |
| `/notary/profile/` | `notary_profile` | `views_notary.profile` | Notary, Admin |
| `/admin-panel/clients/` | `admin_clients` | `views_admin.clients_view` | Admin (Notary can view) |
| `/admin-panel/notaries/` | `admin_notaries` | `views_admin.notaries_view` | Admin only |
| `/admin-panel/reports/` | `admin_reports` | `views_admin.reports` | Admin only |
| `/verify/<uuid>/` | `verify` | `views_public.verify` | Public |
| `/verify/<uuid>/qr.png` | `qr_image` | `views_public.qr_image` | Public |
| `/admin/` | — | Django Admin | Staff/superuser only |
| `/i18n/setlang/` | — | Django's built-in language switcher | |

*(Full list, including edit/delete sub-routes, is in `portal/urls.py` and `accounts/urls.py`.)*

## Static Files

- `STATIC_URL = 'static/'`, `STATIC_ROOT = BASE_DIR / 'staticfiles'` — run
  `python manage.py collectstatic` before deploying.
- `MEDIA_URL = 'media/'`, `MEDIA_ROOT = BASE_DIR / 'media'` — stores client
  signatures and notary stamp images; served by Django only when
  `DEBUG=True` (see `notary/urls.py`). `media/` is git-ignored.
- App static files live under `portal/static/`: `css/main.css` (the design
  system), and `js/sidebar.js`, `js/signature_pad.js`, `js/live_filter.js`.

## Security Features

- **Role-based access control** via `role_required`, enforced on every
  protected view (raises `PermissionDenied` for the wrong role).
- **Forced password change** for any account still on its temporary
  password, enforced server-side by `ForcePasswordChangeMiddleware` (not
  just a UI nudge).
- **Password validation** via Django's standard validators
  (`UserAttributeSimilarityValidator`, `MinimumLengthValidator`,
  `CommonPasswordValidator`, `NumericPasswordValidator`).
- **No self-service password reset**: a lost password can only be reset by a
  System Administrator (e.g. via Django Admin or `manage.py changepassword`),
  removing the attack surface of an email-based reset flow entirely.
- **CSRF protection** and **clickjacking protection**
  (`XFrameOptionsMiddleware`) via Django's standard middleware stack.
- **Secrets kept out of source control**: real SMTP credentials belong in
  `.env` (git-ignored); `.env.example` should contain placeholders only.
- **Uploaded files validated as images** (`ImageField` for signatures and
  stamps, via Pillow) rather than arbitrary file uploads.

> Production hardening still needed: `SECRET_KEY` is hardcoded, `DEBUG=True`,
> and `ALLOWED_HOSTS=[]` — see [Deployment](#deployment).

## Reports

The admin Reports page (`/admin-panel/reports/`) includes:

- **Stat cards** — Documents / Clients / Notaries counts for the active
  filter period.
- **Date filter bar** — switch between **Day**, **Month**, and **Custom
  range**; every chart, stat, and list on the page re-queries against the
  selected range (default: the current month).
- **Monthly Trends chart** (Chart.js) — documents/clients/notaries created
  per sub-period, bucketed daily (ranges ≤ ~62 days) or monthly (longer
  ranges), with month-over-month-style growth percentages compared to the
  immediately preceding period of equal length.
- **Notary Activity** — a horizontal bar chart of document counts per
  notary for the selected range.
- **Notary Performance Trend** (Chart.js) — one line per active notary
  showing their document throughput over the same sub-periods.
- **Recent Activity** — the latest documents within the selected range.

## PDF / Printing

- Rendering is done by **`xhtml2pdf`** (`pisa.CreatePDF`) against an HTML
  template (`portal/templates/portal/pdf/document.html`), via
  `utils.render_pdf` / `utils.render_pdf_bytes`.
- A custom `link_callback` resolves `/media/` and `/static/` URLs to real
  filesystem paths, since `xhtml2pdf` can't fetch them over HTTP from inside
  the Django process.
- The verification QR code is embedded as a base64 data URI (not a live
  HTTP link) for the same reason.
- On completion, the rendered PDF's bytes are SHA-256-hashed and stored as
  `Document.pdf_hash` for integrity verification.
- Both clients (`/app/documents/<ref>/pdf/`) and notaries/admins
  (`/notary/documents/<ref>/pdf/`) can download the PDF.

## Signature System

- Clients and notaries capture a signature once using an in-browser
  `<canvas>` pad (`portal/static/portal/js/signature_pad.js`), submitted as a
  base64 data URL and decoded server-side (`utils.decode_signature_data_url`)
  into an `ImageField`.
- A client's stored signature is automatically substituted into any document
  generated for them — the template body's `{{client_signature}}` /
  `{{client1_signature}}` / `{{client2_signature}}` tokens are replaced with
  the actual signature `<img>` (or a "no signature on file" warning if
  missing) by `Document.render_body()`.
- Notaries additionally have a `seal_image` (stamp), editable from their
  profile page, embedded into the rendered PDF.

## Screenshots

> Screenshots are not included in this repository. Add your own below.

### Login
(Add Screenshot)

### Dashboard
(Add Screenshot)

### Client Module
(Add Screenshot)

### Notary — Document Wizard
(Add Screenshot)

### Admin — Reports
(Add Screenshot)

### Public Verification Page
(Add Screenshot)

## Deployment

This project is currently configured for **local development only**. Before
deploying anywhere public, you would need to:

- Move `SECRET_KEY` out of `notary/settings.py` into an environment variable
  (currently hardcoded — **Not Implemented** as env-driven).
- Set `DEBUG = False` and populate `ALLOWED_HOSTS` (currently `[]`).
- Choose and configure a production database — SQLite is fine for small/
  single-process deployments, but PostgreSQL is recommended and **not yet
  wired up** in this codebase.
- Run `python manage.py collectstatic` and serve `STATIC_ROOT` via a real
  web server / CDN (or `django.contrib.staticfiles` + whitenoise-style
  middleware — neither is currently configured).
- Serve `MEDIA_ROOT` (signatures, stamps) via a proper file store in
  production — Django only serves it itself when `DEBUG=True`.
- Set real `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` in the deployment
  environment (never in `.env.example` or any committed file).
- Put the app behind HTTPS — `request.build_absolute_uri()` (used for reset
  links and QR verification URLs) will then naturally produce `https://` URLs.
- Run under a production WSGI/ASGI server (`notary.wsgi.application` /
  `notary.asgi.application` already exist; gunicorn/uvicorn etc. are not
  included in `requirements.txt`).

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `DisallowedHost` error when scripting requests (e.g. in a shell or test script) | `ALLOWED_HOSTS = []` by default | Add your host, or use `django.test.utils.override_settings(ALLOWED_HOSTS=['*'])` for local scripting/tests |
| Password-reset emails don't appear to send | No `EMAIL_HOST_USER` configured | This is expected — the app falls back to the console email backend and prints the email to the terminal running `runserver` |
| A document can't be completed | One or more required signatures (client/witnesses) are missing | The error message lists exactly what's missing; capture the signature(s) or add witnesses first |
| A client/notary can't be deleted | They have documents/templates attached | This is enforced intentionally (`doc_count > 0` / `times_used > 0` checks) to avoid orphaning historical documents |
| `accounts.tests.LoginViewTests.test_already_authenticated_user_redirected_away_from_login` fails | A known stale assertion expecting the old post-login admin redirect target (`/admin-panel/clients/`); the redirect target was intentionally changed to `/admin-panel/reports/` | Update the assertion in `accounts/tests.py` to expect `/admin-panel/reports/` |

## Future Improvements

Based on the current architecture, realistic next steps include:

- PostgreSQL support via environment-driven `DATABASES` configuration
- A REST/JSON API layer (e.g. Django REST Framework) for mobile or
  third-party integrations
- In-app notifications (status changes, completion alerts)
- A rich text editor for document template bodies
- Server-side/full-text search instead of client-side list filtering
- A dedicated audit-log UI for admins (today it's Django-Admin-only)
- Self-service client profile editing
- Two-factor authentication
- Containerization (Dockerfile / docker-compose) and a CI pipeline (tests +
  linting on push)
- A proper category model for document templates instead of a free-text field

## License

This project is licensed under the MIT License — see the `LICENSE` file for
details.

```
MIT License

Copyright (c) [year] [Author Name]

Permission is hereby granted, free of charge, to any person obtaining a copy...
```

*(Add a full `LICENSE` file at the project root if one does not already exist.)*

## Author

- **Name:**
- **Email:**
- **GitHub:**
- **Company:**

## Version

**1.0.0**

## Support

For questions, issues, or contributions, please open an issue on the
project's GitHub repository.
