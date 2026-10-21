# CS256 individual project starter

This is a small starting point, not a completed assignment. Use your own project,
brand, and lecture database. Read the current lesson and Moodle assignment first.

## Lessons 1–3: no server required

1. Extract the ZIP into a normal folder (not inside the ZIP viewer).
2. Open `templates/mockup.html` in a browser and the folder in your editor.
3. Complete `PROPOSAL.md`, sketch three screens, and change `templates/brand.css`.
4. Give each screen a useful heading and label. Test at a narrow window width.

## Lesson 4: run Flask locally

Use an approved Python 3.10 or newer installation. Lightsail uses Python 3.12;
if a campus machine only offers an older Python, ask for the approved current
interpreter rather than changing its system installation.

Windows PowerShell, opened in this extracted folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe backendconnection/app.py
```

macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python backendconnection/app.py
```

Open http://127.0.0.1:5001. Stop with Ctrl+C. You do not need to activate the
virtual environment, change PowerShell execution policy, or deploy publicly.
These instructions describe the original Lesson 4 local setup. For Milestone 5, the temporary Python list has been replaced with a parameterized PostgreSQL query. The current server startup instructions are documented below.


## Lesson 5: MovieVault PostgreSQL Integration

### Project Overview

MovieVault is a Flask web application that reads movie records from PostgreSQL and displays them using a Jinja HTML template.

The project currently uses two related database tables:

- `cs256_m05_movievault.movies` — stores movie records.
- `cs256_m05_movievault.reviews` — stores reviews associated with movies.

The `movies.movie_id` primary key connects to the `reviews.movie_id` foreign key, creating a one-to-many relationship.

The Milestone 5 Flask page currently queries the movies table. It uses a parameterized title filter and displays the returned title and genre.

### Project File Locations

GitHub repository structure:

- `backendconnection/app.py` — Flask application and PostgreSQL query.
- `templates/index.html` — Jinja template displaying movie records.
- `templates/brand.css` — Website styling.

King's College server structure:

- Server: `cs256.kings.edu`
- Username: `antonioscialpi`
- Project folder: `/home/antonioscialpi/cs256-project`
- Server Flask application: `~/cs256-project/app.py`
- Server template: `~/cs256-project/templates/index.html`
- Python environment: `~/cs256-project/.venv-kings`

The GitHub and server folder structures are slightly different. The application now detects the templates directory in either layout; no source change is required when uploading.

### PostgreSQL Configuration

- Database: `antonioscialpi`
- Database role: `antonioscialpi`
- Schema: `cs256_m05_movievault`
- Connection: PostgreSQL Unix socket on the King's server
- Socket directory: `/var/run/postgresql`
- Environment variable: `DATABASE_DSN`

The Python application accesses its connection configuration through `os.environ['DATABASE_DSN']`.

The database connection uses the following non-secret setting on the King's server:

```bash
export DATABASE_DSN="dbname=$(whoami)"
```

No passwords, private keys, or secret configuration values are stored in this repository.

### Connect to King's Server

From Windows PowerShell:

```powershell
ssh antonioscialpi@cs256.kings.edu
```

### Start the Flask Application

In the King's Linux terminal:

```bash
cd ~/cs256-project
export DATABASE_DSN="dbname=$(whoami)"
PYTHONDONTWRITEBYTECODE=1 .venv-kings/bin/python -m flask --app app:app --no-debug run --host 127.0.0.1 --port 5108 --no-debugger --no-reload
```

Keep this terminal open while using the application.

The Flask application runs on the King's server, not on the Windows computer.

### Create the SSH Tunnel

Open a second terminal on Windows, outside the King's SSH session.

Run:

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:55100:127.0.0.1:5108 antonioscialpi@cs256.kings.edu
```

Keep the SSH tunnel open.

In the Windows web browser, visit:

http://127.0.0.1:55100

The browser connects through the SSH tunnel to Flask running on the King's server.

### Verify the Database Connection

In the King's Linux project folder:

```bash
cd ~/cs256-project
export DATABASE_DSN="dbname=$(whoami)"
PYTHONDONTWRITEBYTECODE=1 .venv-kings/bin/python check_connection.py
```

### Test the PostgreSQL Query

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-kings/bin/python check_read.py
```

The tested query returns two sample movie records:

1. Sample Film: Lantern Harbor — Mystery
2. Sample Film: Orbit Picnic — Comedy

The results match the records displayed on the Flask webpage.

### Security and Version Control

Do not commit Python virtual environments, `.env` files, passwords, database credentials, private keys, or local secret configuration files.

The GitHub repository does not automatically synchronize with the King's server. Changes must be transferred or deployed separately.

## Lesson 6: Form Validation and Database Write

See [M06_SETUP.md](M06_SETUP.md) for exact upload/startup commands and the browser
and PostgreSQL checks required for the submission.

- `/movies/new` displays the form on GET and validates submitted fields on POST.
- `backendconnection/validation.py` checks required fields, integer IDs, release
  years (1888–2100), and synopsis length (20–1,000 characters).
- `backendconnection/repository_postgres.py` inserts bound parameter values,
  commits the row, and retrieves saved movies by their primary keys.
- Success redirects with HTTP 303 to `/movies/<movie_id>`. Refreshing this GET
  page does not repeat the INSERT. Duplicate IDs return a field error.
- The homepage now includes all movie titles and links to creation and details.

Movie IDs are entered manually because the existing database has no default
for `movie_id`. No database schema changes are required.
