# CivicLens AI: SDLC and interview walkthrough

This guide explains how to work on the project like a software team, from a user need through a monitored release. The app is a portfolio prototype: use test data, never real sensitive citizen information.

## 1. Understand the problem and users

Start with the problem statement: residents need a clear way to report local issues and follow progress; city staff need a manageable queue and a traceable workflow.

Identify roles and outcomes before coding:

- **Resident:** create an account, submit a report with a location, and follow status updates.
- **Staff:** review reports, filter the queue, assign a department/owner, and record a resolution.
- **Administrator:** provision staff accounts and manage access.

For each change, write a small acceptance criterion. Example: “A resident can select Traffic Signals, submit a report, and see that category in their report details.”

## 2. Explore and plan

Before editing:

1. Read the relevant model, view, template, API serializer, and tests.
2. Search where a behavior is used so every surface stays consistent.
3. Break work into a small issue or pull request. Keep one coherent change per PR.
4. Decide how the change will be tested and whether it needs a database migration.

Useful repository areas:

- `complaints/models.py` — report categories, status, priority, history.
- `complaints/forms.py` and `templates/` — resident and staff web flows.
- `ai_engine/services.py` — the current small synthetic text classifier and advisory priority rules.
- `analytics/views.py` — dashboards and role-specific workflows.
- `static/app.js`, `static/style.css` — interactive maps, charts, and UI.
- `docs/` — product and deployment guidance.

## 3. Develop locally

```bash
git switch main
git pull --ff-only
git switch -c feat/short-description
source venv/bin/activate
```

Make a focused change. Do not put database URLs, passwords, Django secrets, or personal data in source files or commits. Use local environment variables or an ignored `.env` file.

Run the relevant checks before asking for review:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

If models change, create and review a migration:

```bash
python manage.py makemigrations
python manage.py migrate
```

For user-facing changes, also manually try the resident and staff journeys at desktop and mobile widths. Check keyboard navigation, validation errors, permissions, and empty states.

## 4. Version control and code review

Review the diff, stage only intended files, and commit with an intent-focused message:

```bash
git status --short
git diff
git add complaints/ ai_engine/ templates/ static/
git commit -m "feat: add civic issue categories"
git push -u origin feat/short-description
```

Open a GitHub pull request. Describe the user need, implementation, migration impact, test results, UI screenshots, and rollback considerations. Review the diff yourself and ask a reviewer to check correctness, security, accessibility, and maintainability.

The GitHub Actions workflow runs Django checks, migration consistency, and tests for pull requests and pushes to `main`. Fix failed checks rather than bypassing them. Merge only after the PR is reviewed and green.

## 5. Deploy safely

Vercel deploys the connected GitHub branch. Pull requests/branches can be previewed; merging to `main` triggers the production deployment.

Production needs these environment variables in Vercel settings:

- `DATABASE_URL` — the managed PostgreSQL URL (keep secret).
- `DJANGO_SECRET_KEY` — a private, unique Django secret.
- `DJANGO_DEBUG=False`.
- `DJANGO_SECURE_SSL_REDIRECT=True` when HTTPS forwarding is configured.

After changing environment variables, redeploy so the new values are applied. Apply Django migrations once against the correct production database using a secure, authenticated workflow; do not print secrets or commit pulled environment files. Verify the deployment status and test the public page, resident sign-up/report flow, and staff queue. Use `/healthz/` to verify the app and database are responding.

For production database changes, make a backup first and know the rollback plan. Avoid running destructive migrations against real data without review.

## 6. Monitor and learn

Check Vercel deployment/build logs and the app health endpoint after release. Watch for elevated 4xx/5xx errors, slow database requests, and broken user flows. Record an issue for anything unexpected, fix it on a branch, and ship another reviewed release.

## 7. AI boundaries in this prototype

The current category model is a small TF-IDF + Logistic Regression baseline trained from synthetic examples. Its suggestions and rule-based priority are not validated for city operations. Keep human review mandatory, measure errors on representative held-out data before making quality claims, and avoid sending private resident descriptions to an unapproved provider.

The in-app quick guide is an offline walkthrough, not a conversational LLM. A real LLM-based guide would need a chosen provider, explicit budget/privacy approval, server-side key handling, rate limits, prompt-injection safeguards, and tests. Do not add a paid model or claim the guide is generative AI until that is implemented and evaluated.

## 8. Suggested live demo (5–7 minutes)

1. Show the public landing page and explain the two roles.
2. Sign in as a resident, take the quick guide, submit a fictional report in one of the new categories, and pin a location.
3. Open the report and explain that residents see their own reports only.
4. Sign in as staff, inspect the queue, use filters and the map, review the AI suggestion, then assign/update the fictional report.
5. Show the audit history and explain that staff decisions remain authoritative.
6. Open GitHub: show the feature branch/PR, CI checks, commit history, and migration.
7. Open Vercel: show the production deployment and health check.
8. Explain one limitation honestly: synthetic training data, no durable photo upload on this deployment, and no LLM provider configured.

Use the demo account only for a controlled presentation. Change its password after use and never put credentials in slides, screenshots, source code, or a public README.

## 9. Interview explanation

Use a concise structure:

- **Problem:** “I built a role-specific civic issue reporting prototype.”
- **Design:** “Django serves the web and API; PostgreSQL persists reports; Leaflet and Chart.js show location and workload.”
- **Reliability/security:** “Resident queries are owner-scoped, staff actions are role-checked, and important report changes are audited.”
- **Delivery:** “A GitHub Actions workflow checks configuration, migrations, and tests; Vercel builds from GitHub.”
- **Trade-off:** “The model is advisory and synthetic-data-only. I chose transparency and human review instead of claiming production-grade AI.”
- **Next step:** “Evaluate on representative data, add browser-level tests, and measure resolution outcomes before expanding automation.”
