# Sahal Notary System

A Django web application for managing notarized documents in Somalia, with a
Somali-language interface across three roles — **Macmiil** (Client),
**Notaayo** (Notary), and **Maamule** (Admin) — plus a public, no-login
document verification page.

## Features

- **Client portal** — view your documents, track status (Sugaya / La saxiixay
  / Dhammaystiran), and download the official PDF.
- **Notary workflow** — a guided wizard to generate documents from reusable
  templates (one-party or two-party, with optional witnesses), and a
  completion action that:
  - confirms all required client/witness signatures are on file,
  - embeds the notary's stamp into the final PDF,
  - hashes the generated PDF (SHA-256) for integrity verification,
  - flips the document from **Sugaya** (Pending) to **Dhammaystiran**
    (Completed),
  - records the action in an audit log.
- **Digital signatures** — clients capture a signature once (via an in-browser
  canvas signature pad) and it's automatically embedded into any document
  generated for them, replacing `{{client_signature}}`-style placeholders in
  the template body.
- **Admin panel** — manage clients and notaries, capture/update client
  signatures, and view reporting on document volume per notary.
- **Public QR verification** — every generated document gets a QR code
  linking to a public page that displays its details and content hash, no
  login required.
- **PDF generation** — documents render to PDF (via `xhtml2pdf`) with
  embedded signatures, notary seal, and a verification hash footer.

## Tech stack

- Python / Django 5.2
- `django-formtools` (multi-step document creation wizard)
- `xhtml2pdf` (PDF rendering)
- `qrcode` + `Pillow` (QR codes, image handling)
- SQLite (development database)

## Getting started

```bash
# from the project root
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo      # creates demo admin/notaries/clients/templates
python manage.py runserver
```

Then visit `http://127.0.0.1:8000/`.

### Demo accounts (from `seed_demo`)

All demo accounts use the temporary password `123` and will be prompted to
change it on first login.

| Username          | Role   |
|--------------------|--------|
| `admin`            | Admin  |
| `maxamed.daahir`   | Notary |
| `amina.yusuf`      | Client |

## Running tests

```bash
python manage.py test
```

## Project structure

```
accounts/   custom User model, login/password-change views, role decorators
portal/     core domain: clients, notaries, document templates, documents,
            the notary creation wizard, admin views, public verification,
            and the audit log
notary/     Django project settings/urls
```

Uploaded files (client signatures, notary seals) are stored under `media/`,
which is not version-controlled.
