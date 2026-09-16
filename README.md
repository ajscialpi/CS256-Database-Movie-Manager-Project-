# CS256 individual project starter

This is a small starting point, not a completed assignment. Use your own project,
brand, and lecture database. Read the current lesson and Moodle assignment first.

## Lessons 1–3: no server required

1. Extract the ZIP into a normal folder (not inside the ZIP viewer).
2. Open `mockup.html` in a browser and the folder in your editor.
3. Complete `PROPOSAL.md`, sketch three screens, and change `static/brand.css`.
4. Give each screen a useful heading and label. Test at a narrow window width.

## Lesson 4: run Flask locally

Use an approved Python 3.10 or newer installation. Lightsail uses Python 3.12;
if a campus machine only offers an older Python, ask for the approved current
interpreter rather than changing its system installation.

Windows PowerShell, opened in this extracted folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Open http://127.0.0.1:5001. Stop with Ctrl+C. You do not need to activate the
virtual environment, change PowerShell execution policy, or deploy publicly.
The Python list in app.py is temporary mock content, not a database.

## Lesson 5 onward: your lecture database

`repository_postgres_example.py` shows a parameterized join. The names `item`
and `category` are illustrative; adapt them to tables you designed with Professor Haczewski.
Set DATABASE_DSN locally using the connection details your instructor provides;
never commit it or show a password in a screenshot. For example, after replacing
the placeholders (keep these commands off your submitted screenshots):

```powershell
$env:DATABASE_DSN = 'host=YOUR_HOST dbname=YOUR_DATABASE user=YOUR_USER'
```

Use your approved password/secret method; a DSN may omit a password and use
PostgreSQL's protected password file. Import and call your query from app.py,
then adapt the template to its actual column names. Continue through validation,
create, search, update/delete, and a joined report. Do not load S Corp's full data
into your personal database as an automatic replacement for your own project.

## Practice copy versus individual project

The separate `SCORP_LOCAL_EXAMPLE.zip` is the worked example. Run it on port 5000
using its LOCAL_SETUP guide. Its small CSV adapter lets you inspect web behavior;
it is not the final PostgreSQL requirement. Mutation experiments belong in your
local practice copy, using disposable synthetic reports.

`api_example.js` is an optional DevTools example for that local S Corp copy.
Use the functions only after reading the JSON/API lesson.

## Submit

Follow the lesson's checklist and the assignment posted in Moodle. Include source,
README, results, and your progress/AI-use note. Exclude .venv, passwords, keys,
private connection files, and unrelated data. Moodle controls deadlines and grades.
