# Local Setup

## 1. Project Overview

MovieVault currently lists movies, accepts a validated new-movie form, saves it
to PostgreSQL, and displays the saved record. It uses Python, Flask, Jinja HTML
templates, CSS, and Psycopg. Editing/deleting movies and working community reviews
are not implemented in the current Flask routes.

| Location | Purpose |
| --- | --- |
| `backendconnection/app.py` | Flask routes and application startup |
| `backendconnection/repository_postgres.py` | Database inserts and detail queries |
| `backendconnection/validation.py` | Form fields and validation rules |
| `templates/` | Working Flask pages and `brand.css` |
| `html/`, `css/` | Separate static prototypes, including the forum |
| `requirements.txt`, `tests/` | Python dependencies and automated checks |

Follow sections 2–8 in order. Commands use **Windows PowerShell** unless marked
otherwise. After cloning, run shell commands from the repository root (the folder
containing `requirements.txt`). Run SQL only inside `psql`, as indicated.

## 2. Prerequisites

1. Install [Git](https://git-scm.com/downloads/) and
   [Python](https://www.python.org/downloads/). The repository specifies Python
   **3.10 or newer**; use a supported release such as **3.13** for a new setup.
   Ensure the Windows Python launcher (`py`) is installed.
2. Install PostgreSQL using the installer linked on the
   [official Windows download page](https://www.postgresql.org/download/windows/).
   Include the server and command-line tools (`psql`). Record your installation
   directory, port, and the password you choose for the `postgres` administrator.
   This guide uses port **5432**; substitute your port if different. The repository
   does not specify a minimum PostgreSQL version; use a supported stable release.
3. Add your PostgreSQL installation's `bin` directory to your Windows user `Path`
   through **Edit environment variables for your account**, then reopen PowerShell.
   Use the actual installation path, not a guessed versioned directory.
4. Verify the tools:

   ```powershell
   git --version
   py -3 --version
   psql --version
   ```

On macOS/Linux, use the [PostgreSQL downloads page](https://www.postgresql.org/download/)
for your platform and `python3` instead of `py -3`. Database service startup and
administrator authentication depend on the installer; use its documented steps.

## 3. Clone the Repository

In PowerShell, first navigate to the parent folder where you keep projects, then:

```powershell
git clone https://github.com/ajscialpi/CS256-Database-Movie-Manager-Project-.git
cd CS256-Database-Movie-Manager-Project-
```

If you already have this repository, open PowerShell in its root and skip cloning.

## 4. Install Dependencies

From the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The declared dependencies are `Flask>=3.1,<4` and `psycopg[binary]>=3.2,<4`.
Jinja is installed with Flask. Node.js, npm, and a frontend build are not required.

Optional activation:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activation is unnecessary for this guide: every Python command explicitly uses
the virtual environment. If PowerShell blocks activation, continue without it.

macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# Optional:
source .venv/bin/activate
```

For subsequent Python commands on macOS/Linux, replace
`.\.venv\Scripts\python.exe` with `.venv/bin/python`.

## 5. Database Setup

**Missing setup assets:** the repository contains no schema export, migration,
database initialization script, or seed-data file. The README mentions a `reviews`
table, but its full definition is absent and the running app never queries it.
The SQL below is a **minimal local reconstruction** derived from the current movie
queries and validator, not a verified copy of the college database. Original text
column lengths and additional database constraints remain unknown. The early
`PROPOSAL.md` mentions text IDs, but the implemented routes and validator use integers.

`movievault_local` and `movievault_app` below are **example names you create locally**,
not existing repository settings. You may substitute your own names consistently.
The schema/table name **`cs256_m05_movievault.movies` must stay unchanged** because
it is explicitly used in the Python SQL.

1. Confirm PostgreSQL is running:

   ```powershell
   Get-Service -Name '*postgres*'
   ```

   If its status is `Stopped`, open Windows **Services**, find that PostgreSQL
   service, and select **Start** (administrator permission may be required).
   If no service appears, check that the PostgreSQL server was installed.

2. From PowerShell, connect as the local administrator. Enter the administrator
   password selected during installation:

   ```powershell
   psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -W
   ```

3. At the `postgres=#` prompt, run these commands individually. `\password`
   prompts for a new application-user password without putting it in SQL history:

   ```sql
   CREATE ROLE movievault_app LOGIN;
   \password movievault_app
   CREATE DATABASE movievault_local OWNER movievault_app;
   \q
   ```

   These creation steps are for a fresh database. If a name already exists,
   confirm it belongs to your local project before reusing it.

4. Back in PowerShell, connect as the new application user using its new password:

   ```powershell
   psql -h 127.0.0.1 -p 5432 -U movievault_app -d movievault_local -W
   ```

5. At the `movievault_local=>` prompt, create the schema and table:

   ```sql
   CREATE SCHEMA cs256_m05_movievault AUTHORIZATION movievault_app;

   CREATE TABLE cs256_m05_movievault.movies (
       movie_id INTEGER PRIMARY KEY,
       title TEXT NOT NULL,
       genre TEXT NOT NULL,
       release_year INTEGER NOT NULL,
       director TEXT NOT NULL,
       content_rating TEXT NOT NULL,
       synopsis TEXT NOT NULL
   );

   SELECT COUNT(*) FROM cs256_m05_movievault.movies;
   \q
   ```

   Expect a count of `0`. The application user owns the schema/table, so no extra
   grants are needed. IDs are entered manually; no sequence is required. No data
   import is necessary: section 8 creates your first movie through the form.
   Flask does not automatically create these database objects.

## 6. Environment Configuration

In the same PowerShell terminal you will use to start Flask, from the repository root:

```powershell
$env:DATABASE_DSN = & .\.venv\Scripts\python.exe -c "from getpass import getpass; from psycopg.conninfo import make_conninfo; print(make_conninfo(host='127.0.0.1', port=5432, dbname='movievault_local', user='movievault_app', password=getpass('Application database password: ')))"
$env:PROJECT_SECRET_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Enter the password set by `\password movievault_app`. The first command constructs
and captures the connection string, safely handling special characters in the
password. Adjust its database/user/port if you chose different local values.

| Variable | Meaning |
| --- | --- |
| `DATABASE_DSN` | Required PostgreSQL connection string; conceptually `host=127.0.0.1 port=5432 dbname=YOUR_DATABASE user=YOUR_USER password=YOUR_PASSWORD` |
| `PROJECT_SECRET_KEY` | Optional Flask secret; the source defaults to `local-practice-only`. The command above generates a session-specific value. |

These variables last only for this terminal session. Repeat this section in a new
terminal. The application does **not** load `.env` files itself. Keep credentials
out of source files and Git. The college server's socket connection and SSH tunnel
instructions in `M06_SETUP.md` are not needed for this local setup.

macOS/Linux equivalents:

```bash
export DATABASE_DSN="$(.venv/bin/python -c "from getpass import getpass; from psycopg.conninfo import make_conninfo; print(make_conninfo(host='127.0.0.1', port=5432, dbname='movievault_local', user='movievault_app', password=getpass('Application database password: ')))")"
export PROJECT_SECRET_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"
```

Before starting Flask, confirm Python can connect and read the table:

```powershell
.\.venv\Scripts\python.exe -c "import os, psycopg; conn = psycopg.connect(os.environ['DATABASE_DSN']); print(conn.execute('SELECT COUNT(*) FROM cs256_m05_movievault.movies').fetchone()); conn.close()"
```

Expect `(0,)` for the new empty database. An error here must be resolved before
the homepage can load.

## 7. Running the Application Locally

From the repository root, in the terminal configured in section 6:

```powershell
.\.venv\Scripts\python.exe backendconnection/app.py
```

Keep this terminal open. The code starts Flask in development/debug mode at
**http://127.0.0.1:5001/**. Stop it with **Ctrl+C**. Visit the URL through Flask;
opening a template directly as a file will not run Python or query PostgreSQL.

macOS/Linux:

```bash
.venv/bin/python backendconnection/app.py
```

## 8. Verifying the Setup

1. Confirm the terminal reports `Running on http://127.0.0.1:5001`.
2. Open **http://127.0.0.1:5001/**. The page should show Movie Vault and
   `No matching records yet.` for an empty database. Loading this page successfully
   confirms Flask can query PostgreSQL.
3. Select **Add a movie**, or open **http://127.0.0.1:5001/movies/new**. Enter:

   | Field | Example value |
   | --- | --- |
   | Movie ID | `9001` (must be unused) |
   | Title | `Sample Film: Midnight Library` |
   | Genre | `Mystery` |
   | Release year | `2026` |
   | Director | `Jordan Example` |
   | Content rating | `PG` |
   | Synopsis | `A fictional librarian discovers a hidden room full of clues.` |

4. Click **Save movie**. Expect `/movies/9001` to display the saved details.
   Select **Back to movies** and confirm the title appears on the homepage.
5. To independently confirm persistence, open another PowerShell terminal and run:

   ```powershell
   psql -h 127.0.0.1 -p 5432 -U movievault_app -d movievault_local -W -c "SELECT * FROM cs256_m05_movievault.movies WHERE movie_id = 9001;"
   ```

   Expect one row matching your form. Refreshing the detail page should not create
   another record. A new form with an unused ID and synopsis `Short` should show a
   validation error and save nothing.
6. Optional automated checks, from the repository root:

   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   ```

   These tests mock database calls. They do not replace the real database checks
   above. `tests/verify_m06_server.py` targets the college deployment and assumes
   specific existing records; it is not a fresh-local-setup script.

**Verification limits:** the 11 existing unit tests and Flask route discovery
passed while preparing this guide. No local `psql` command or PostgreSQL Windows
service was detected, so database creation and the complete local save flow were
not executed here. The reconstructed schema must be checked using the steps above.
The README's `check_connection.py` and `check_read.py` are also absent from this
repository; use the inline connection check in section 6 instead.

## 9. Common Errors and Troubleshooting

| Symptom | Fix |
| --- | --- |
| `py` or `psql` is not recognized | Verify installation and `Path`, then reopen PowerShell. If Python is available as `python`, use `python -m venv .venv`. |
| Activation is blocked | Use the explicit `.venv` Python commands; activation is optional. |
| `No module named flask` or `psycopg` | From the root, rerun `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and launch using that same interpreter. |
| `KeyError: 'DATABASE_DSN'` | Repeat section 6 in the terminal that starts Flask; a different terminal does not inherit those settings. |
| Connection refused | Start PostgreSQL and confirm the configured host and installation port. |
| Password authentication failed | Use the application user's password, not the `postgres` administrator password; repeat section 6 with the correct values. |
| Database does not exist / relation does not exist | Complete section 5 and verify the DSN points to that database. Keep the exact schema and table names. |
| Permission denied for schema/table | Ensure section 5's schema and table were created while connected as `movievault_app`. |
| Port 5001 is already in use | Stop your previous Flask process with Ctrl+C, or use the alternative command below. |
| Form rejects a movie | All fields are required. ID: 1–2147483647 and unused; year: 1888–2100; synopsis: 20–1000 characters. |
| Homepage returns HTTP 500 | Check the Flask terminal error and run section 6's connection check; Flask starting alone does not establish a database connection. |
| Jinja braces show in the browser | Visit the Flask URL instead of opening `templates/*.html` as files. |

To use port 5002, from the repository root with section 6's environment configured:

```powershell
.\.venv\Scripts\python.exe -m flask --app backendconnection/app.py run --host 127.0.0.1 --port 5002
```

Then open **http://127.0.0.1:5002/**.

## 10. Your everyday commands: open the app and work on it

Use these steps for **your existing King's server setup**, where the database
and `.venv-kings` environment are already configured. Edit files in VS Code on
your computer; Flask and PostgreSQL run on King's.

1. **Open a PowerShell terminal in VS Code and connect to King's:**

   ```powershell
   ssh antonioscialpi@cs256.kings.edu
   ```

2. **In that same terminal, now connected to King's, start the app:**

   ```bash
   cd ~/cs256-project
   export DATABASE_DSN="dbname=$(whoami)"
   PYTHONDONTWRITEBYTECODE=1 .venv-kings/bin/python -m flask --app app:app --no-debug run --host 127.0.0.1 --port 5108 --no-debugger --no-reload
   ```

   Leave this terminal running. If port 5108 is already in use by your earlier
   Flask session, reuse that session or stop it with **Ctrl+C** before restarting.

3. **Open a second PowerShell terminal on your computer and run:**

   ```powershell
   ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:55100:127.0.0.1:5108 antonioscialpi@cs256.kings.edu
   ```

   Enter your SSH password if prompted. Leave this terminal running too. It may
   show no output after connecting; that is normal. If this tunnel is already
   running in another terminal, reuse it.

4. **Open the website in your browser:**

   - Movie list: **http://127.0.0.1:55100/**
   - Add a movie: **http://127.0.0.1:55100/movies/new**

5. **Make and save your changes in VS Code.** Edit `templates/add_movie.html`
   for the form, `templates/brand.css` for styling, or the Python files in
   `backendconnection/` for app behavior. Local edits must be uploaded before
   they appear on this server-hosted website.

6. **To display your changes, stop Flask with Ctrl+C in the first terminal.**
   Keep the tunnel in the second terminal running. Open a **third PowerShell
   terminal on your computer** and upload your saved files:

   ```powershell
   cd "C:\Users\ajsci\OneDrive - King's College\Desktop\CS256-Database-Movie-Manager-Project-"
   scp .\backendconnection\app.py .\backendconnection\validation.py .\backendconnection\repository_postgres.py antonioscialpi@cs256.kings.edu:~/cs256-project/
   scp .\templates\index.html .\templates\add_movie.html .\templates\movie_detail.html .\templates\brand.css antonioscialpi@cs256.kings.edu:~/cs256-project/templates/
   ```

   These commands replace the matching server files with your local copies.
   Wait for both uploads to finish successfully.

7. **Return to the first terminal and restart Flask:**

   ```bash
   cd ~/cs256-project
   export DATABASE_DSN="dbname=$(whoami)"
   PYTHONDONTWRITEBYTECODE=1 .venv-kings/bin/python -m flask --app app:app --no-debug run --host 127.0.0.1 --port 5108 --no-debugger --no-reload
   ```

   Refresh the browser. Use **Ctrl+F5** if old styling remains. Repeat steps 5–7
   whenever you want to view new changes.

8. **When finished:** press **Ctrl+C** in the Flask terminal and in the tunnel
   terminal. In the first terminal, type `exit` to disconnect from King's.
