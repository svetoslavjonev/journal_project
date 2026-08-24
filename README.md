# Knowledge Space

Knowledge Space is a private Django application for managing knowledge sources
and the insights captured from them. It supports books, research papers,
articles, and individual podcast episodes through a shared `KnowledgeItem`
model and source-specific detail records.

## Features

- User registration, login, logout, and strictly user-scoped data access.
- A mixed-source library with All, Books, Papers, Articles, and Podcasts views.
- Manual CRUD for books, papers, articles, and podcast episodes.
- Source-specific status wording backed by shared status values.
- Personal summaries, tags, and journal insights for every supported source.
- Paper analysis fields for research questions, findings, methodology, data,
  asset class, journal, DOI, and URL.
- Idempotent bulk paper import from the local paper-manager JSON format.
- Global search across sources, tags, analytical fields, and insights.
- A source-neutral dashboard with counts, in-progress sources, recent sources,
  recent insights, and pinned-insight metrics.
- Server-rendered Django templates with responsive vanilla CSS and JavaScript.

## Supported Sources

All sources store shared fields on `KnowledgeItem`, including title, creator,
status, summary, source URL, dates, archive state, tags, and insights.

### Books

`BookDetail` stores author, genre, ISBN, publisher, page count, publication date,
original language, edition, and optional JSON metadata.

### Papers

`PaperDetail` stores:

- publication year
- journal
- DOI
- asset class
- sample size, data, and source
- methodology and research design
- key research question
- key findings and practical applications

### Articles

`ArticleDetail` stores the publication or site name. Publication date, authors,
URL, status, and personal summary use common `KnowledgeItem` fields.

### Podcast Episodes

One `KnowledgeItem` represents one episode. `PodcastEpisodeDetail` stores the
show name and guests, while hosts use `KnowledgeItem.creator`.

The model reserves source-type values for videos, courses, and miscellaneous
sources, but manual workflows for those types are not currently implemented.

## Statuses

The database uses the same status values for every source:

```text
queued
in_progress
completed
paused
abandoned
```

The interface presents natural labels by source type:

| Source | Queued | In progress | Completed |
|---|---|---|---|
| Book | Want to read | Reading | Finished |
| Paper | To read | Reading | Read |
| Article | To read | Reading | Read |
| Podcast | Queue | Listening | Listened |

Paused and abandoned use their generic labels.

## Paper JSON Import

Open **Library → Papers → Import papers** and upload the JSON file produced by
the separate paper-manager application. The applications do not share a
database, API, or runtime dependency.

The importer accepts a JSON list containing:

```text
title
year
authors
asset class
sample size, data and source
methodology and research design
key research question
key findings and practical applications
```

Imported papers belong to the authenticated user, use status `queued` (`To
read`), and convert `year = 0` to an unknown publication year. The importer does
not automatically create summaries, tags, insights, or reading dates.

Duplicate detection uses a normalized fingerprint of title, publication year,
and authors. It compares only against the current user's papers and records
already accepted in the same upload. Existing matches are skipped and never
updated, so re-importing the same accumulated JSON file is safe.

Malformed records are reported independently without blocking valid records.
Malformed JSON files do not modify the database.

## Architecture

The project is a Django monolith with four main apps:

- `accounts` manages the custom user model and authentication.
- `core` owns the homepage, dashboard, global search, and health check.
- `library` owns sources, detail models, tags, CRUD workflows, and paper import.
- `journal` owns insights linked to `KnowledgeItem`.

The core relationship is:

```text
User
  └── KnowledgeItem
        ├── one source-specific Detail
        ├── Insight[]
        └── KnowledgeItemTag[] ── Tag
```

Selectors scope reads to the authenticated user. Services validate and group
multi-model writes in database transactions. See `docs/architecture.md` for the
current implementation architecture.

## Tech Stack

- Python
- Django 6
- SQLite for local development
- PostgreSQL-ready production configuration
- Vanilla HTML, CSS, and JavaScript
- Django test framework

## Local Setup

1. Create and activate a virtual environment.

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies.

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Apply migrations.

   ```powershell
   python manage.py migrate
   ```

4. Create an admin user.

   ```powershell
   python manage.py createsuperuser
   ```

5. Run the development server.

   ```powershell
   python manage.py runserver
   ```

6. Open `http://127.0.0.1:8000/`. The Django admin is available at
   `http://127.0.0.1:8000/admin/`.

## Testing

Run the full suite with:

```powershell
python manage.py test
```

Coverage includes authentication, migrations, model integrity, all source CRUD
flows, tags, insights, search, dashboard behavior, import idempotency, deletion,
and cross-user permission protection.

## Environment Configuration

Local overrides may be placed in `journal_project/local_settings.py`. Production
configuration should use environment variables:

```text
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=example.com,www.example.com
DATABASE_URL=postgresql://user:password@host:5432/database
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
```

Optional security variables include:

```text
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_USE_X_FORWARDED_PROTO=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_LOG_LEVEL=INFO
DJANGO_DB_CONN_MAX_AGE=60
```

Only enable HSTS after HTTPS is verified.

## Static and Media Files

Source assets live in `staticfiles/`, collected production assets in
`collected_static/`, and uploaded media in `mediafiles/`.

```powershell
python manage.py collectstatic --noinput
```

## Deployment Checks

```powershell
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --noinput
```

Configure HTTPS, secure cookies, allowed hosts, a production secret key, and a
PostgreSQL `DATABASE_URL`. Confirm the public health endpoint at `/health/`.
