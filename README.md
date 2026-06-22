# Knowledge Space

Knowledge Space is a private Django web application for tracking knowledge
sources and the insights that come from them. The current version is
book-focused: users can manage a private library, record reading progress, add
metadata, organize sources with tags, and keep separate journal insights such as
quotes, notes, ideas, questions, reflections, and summaries.

The project was built as an AI-Assisted Development final exam project. Its first release is
intentionally scoped like a digital Moleskine for books, while the data model is
kept flexible enough to support articles, podcasts, videos, academic papers, and
other source types later.

## Features

- User registration, login, and logout.
- Private dashboard for each authenticated user.
- Book CRUD: create, view, edit, and delete books.
- Book metadata: title, author, genre, publication date, reading status,
  publisher, ISBN, page count, summary, and optional JSON metadata.
- Separate insights linked to knowledge sources.
- Insight CRUD with multiple insight types.
- Tags for organizing knowledge items.
- Search and filtering across books, tags, and insights.
- User-scoped data access: users cannot view or modify another user's records.
- Server-rendered Django templates with vanilla CSS and JavaScript.
- Production-ready settings through environment variables.

## Architecture

The application is a simple Django monolith.

Main apps:

- `accounts` handles the custom user model, signup, login, and logout.
- `core` owns the homepage, dashboard, search page, and health check.
- `library` owns knowledge sources, book details, tags, and book workflows.
- `journal` owns insights and journal workflows.

Core model design:

- `KnowledgeItem` is the generic source model. In v1, most items are books.
- `BookDetail` stores book-specific metadata for a `KnowledgeItem`.
- `Insight` stores user-created notes, quotes, questions, ideas, reflections,
  and summaries linked to a `KnowledgeItem`.
- `Tag` and `KnowledgeItemTag` organize sources privately per user.

This means books are represented as:

```text
KnowledgeItem(source_type="book")
  -> BookDetail
  -> Insight[]
  -> Tag[]
```

The `Insight` model links to `KnowledgeItem`, not directly to `BookDetail`, so
future source types can reuse the same journal system.

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

6. Open the app.

   ```text
   http://127.0.0.1:8000/
   ```

The Django admin is available at:

```text
http://127.0.0.1:8000/admin/
```

## Testing

Run the full test suite with:

```powershell
python manage.py test
```

The tests cover:

- Authentication flows.
- Model validation.
- Book CRUD.
- Insight CRUD.
- Tags.
- Search and filtering.
- Delete behavior.
- Cross-user permission protection.

Permission tests are especially important because every user's library and
journal data must remain private.

## Environment Configuration

Local machine-specific overrides can be placed in:

```text
journal_project/local_settings.py
```

Use this only for local development. Production configuration should use
environment variables.

Important production variables:

```text
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=example.com,www.example.com
DATABASE_URL=postgresql://user:password@host:5432/database
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
```

Optional security and deployment variables:

```text
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_USE_X_FORWARDED_PROTO=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_LOG_LEVEL=INFO
DJANGO_DB_CONN_MAX_AGE=60
```

Only enable HSTS after HTTPS is verified for the deployed domain.

## Static and Media Files

Source static assets live in:

```text
staticfiles/
```

Collected production assets are written to:

```text
collected_static/
```

Future uploaded media belongs in:

```text
mediafiles/
```

For deployment, run:

```powershell
python manage.py collectstatic --noinput
```

## Deployment Checklist

- Set `DJANGO_DEBUG=False`.
- Set `DJANGO_SECRET_KEY` outside source control.
- Set `DJANGO_ALLOWED_HOSTS`.
- Set `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Use PostgreSQL through `DATABASE_URL`.
- Run migrations.
- Run `collectstatic`.
- Create an admin user for the production database.
- Serve static files at `/static/`.
- Enable HTTPS and secure cookies.
- Confirm the health endpoint works at `/health/`.

Useful production checks:

```powershell
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --noinput
```

## Project Structure

```text
journal_project/
  accounts/
  core/
  journal/
  library/
  settings.py
  urls.py
templates/
staticfiles/
manage.py
requirements.txt
```

## Current Scope and Future Work

Current scope is book-first. The architecture is ready for broader knowledge
sources, but article, podcast, video, paper, and course detail models are not
implemented yet.

Planned future improvements include:

- Additional source types.
- Collections.
- Richer search.
- Import workflows.
- More advanced insight linking.
