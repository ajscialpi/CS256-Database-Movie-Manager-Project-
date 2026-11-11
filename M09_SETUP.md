# M09: run, review, and submit the report

No schema changes or new runtime dependencies are needed. The report query is
stored in `sql/m09_movie_review_report.sql`; upload that directory along with
the Python and template changes. The normal King's app has not been updated by
the automated verification.

## Local tests

From the repository root in Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

All 38 tests passed during implementation. These tests use mocked database
calls. They do not write records. The separate script below uses PostgreSQL.

## Upload to the normal King's application

After reviewing the changes, stop the existing Flask process with Ctrl+C in its
own terminal. From Windows PowerShell in the repository root:

```powershell
ssh antonioscialpi@cs256.kings.edu 'mkdir -p ~/cs256-project/sql'
scp .\backendconnection\app.py .\backendconnection\repository_postgres.py .\backendconnection\validation.py antonioscialpi@cs256.kings.edu:~/cs256-project/
scp .\templates\index.html .\templates\movie_review_report.html .\templates\brand.css antonioscialpi@cs256.kings.edu:~/cs256-project/templates/
scp .\sql\m09_movie_review_report.sql antonioscialpi@cs256.kings.edu:~/cs256-project/sql/
scp .\tests\verify_m09_server.py antonioscialpi@cs256.kings.edu:~/cs256-project/
ssh antonioscialpi@cs256.kings.edu
```

Keep the existing M06/M08 templates on the server. In the King's terminal:

```bash
cd ~/cs256-project
export DATABASE_DSN="dbname=$(whoami)"
.venv-kings/bin/python -B verify_m09_server.py
psql -X -v ON_ERROR_STOP=1 -d "$USER" -f sql/m09_movie_review_report.sql
.venv-kings/bin/python -B -m flask --app app:app --no-debug run --host 127.0.0.1 --port 5108 --no-debugger --no-reload
```

The verification script performs read-only queries and GET requests, prints
one movie's independent check, and does not create test records. Its synthetic
CTE cases exercise the same report SQL in PostgreSQL. The final `PASS` means
its assertions completed; it does not replace your personal browser review.

In another Windows PowerShell terminal, reuse the existing SSH tunnel or start:

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:55100:127.0.0.1:5108 antonioscialpi@cs256.kings.edu
```

Open <http://127.0.0.1:55100/>, follow **Movie review report**, and check
<http://127.0.0.1:55100/reports/movie-reviews>. Compare movie ID 1 with the
independent SQL in [M09.md](MileStones/M09.md). Check the table at a narrow
window width, follow a movie detail link, and return home. Update the AI-use
note only after completing your own review.

## Commit and obtain the direct submission link

No commit or push was created automatically. The initial working tree was
clean. `.gitignore` excludes `.venv/`, `.env`, `__pycache__/`, and `*.pyc`.
Stage only the M09 files listed here; do not use `git add .`.

From the repository root in Windows PowerShell, after your review:

```powershell
git diff --check
git diff
git status --short
git add -- backendconnection/app.py backendconnection/repository_postgres.py templates/index.html templates/brand.css templates/movie_review_report.html sql/m09_movie_review_report.sql tests/test_movie_review_report.py tests/verify_m09_server.py MileStones/M09.md MileStones/M09-verification.json M09_SETUP.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git status --short
git commit -m "Add M09 movie review report and verification"
$m09Commit = git rev-parse HEAD
$m09Branch = git branch --show-current
git push -u origin $m09Branch
"https://github.com/ajscialpi/CS256-Database-Movie-Manager-Project-/commit/$m09Commit"
```

Inspect the staged diff before committing; it must contain only the intended
files and no secrets. Stop if a command fails. After the push succeeds, open
the printed URL and confirm it shows the M09 changes. Submit that specific
commit URL to the professor, not the repository homepage. You can also open
the repository's commit history on GitHub, select the M09 commit, and copy its URL.
