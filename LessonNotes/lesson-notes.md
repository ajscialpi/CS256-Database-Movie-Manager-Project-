## Build the page structure with HTML
9/16/26

The <!doctype html> line tells the browser to use modern HTML. The html element has lang="en" to identify the document language. Inside head, title supplies the browser-tab text and the stylesheet link loads ../templates/brand.css. The viewport setting helps the page use the available screen width on a phone.

A link takes the user somewhere. A button performs an action, such as submitting a form. Give either one words that explain the result: “View report” is more useful than “Click here.” A div is a general container for grouping content. It does not describe a user action or a document section by itself.

A table is useful for records that readers compare by column. A caption says what the table contains. A th cell identifies a heading and a td cell contains an ordinary value. scope="col" marks a column heading; scope="row" marks the label that identifies one row. The code example in this section is a sample table for your mockup. Activity 3 adapts its headings and sample values to your project.

## Connecting Flask to front end
9/30/26

browser GET / → app.py: home → templates/index.html → HTML response

- browser GET / → app.py: home:
  The browser requests the homepage (/), which causes Flask to run the home() function in app.py.

- app.py: home → templates/index.html:
  The home() function uses render_template() to load index.html and pass the rows data to the template.

- templates/index.html → HTML response:
  Jinja processes the template and loops through the rows. The completed HTML is then returned to the browser.

## Test your application and explain its protections - M11

### S Corp guided work - expected outcomes, not tested

I have not performed these local S Corp exercises. These notes describe the
expected behavior from the lesson, not observed results.

1. Different employee's report: After creating reports for E0001234 and E0005678,
   selecting E0001234 should prevent access to E0005678's report through its
   saved detail URL. The second report should still exist. `owned_report()`
   checks the report against the scope supplied by `owner_scope()` on the
   server. The freely selected local demo employee is not an authenticated user.
2. Server checks: `establish_demo_role()` checks the session's CSRF token,
   `owned_report()` checks record scope, and `execute(sql, parameters)` keeps
   values separate from SQL structure. These checks do different jobs. A valid
   CSRF token does not grant access to another employee's report, and browser
   controls can be bypassed by sending requests directly.
3. Ordinary suite: The expected outcome is that the ordinary tests pass and the
   four optional PostgreSQL integration tests are skipped when their disposable
   database settings are absent. No actual S Corp pass count, failure count,
   or skip messages have been recorded. Those require running the suite.
4. Source folder: The expected submission includes source, templates, styles,
   requirements, and setup instructions, with private configuration, keys, and
   virtual environments excluded. This needs checking against the actual files.

### MovieVault project checks - actual results

Codex ran `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v`
from the project root on November 18, 2026. All 52 tests passed with no skips.
The suite uses mocked database calls; these are not new live database tests.

| Check | Actual result | Evidence type |
| --- | --- | --- |
| Normal read | Movie list and both disposable movies displayed. | Manual browser testing during M10. |
| Normal write | Both test movie genres changed to Drama, preserving the synopsis. | Browser success and actual PostgreSQL results in [M10](../MileStones/M10.md). |
| Empty search | The no-match case displayed the empty-results message. | Passing mocked search route test. |
| Invalid value | Invalid create input returned 400 without calling the insert function. | Passing mocked create route test. |
| Missing record | Missing movie routes returned 404 without calling update or delete. | Passing mocked CRUD route tests. |
| Cancel | Delete confirmation and Cancel navigation did not call delete. | Passing mocked CRUD route test. |
| Conflict | Stale bulk request preserved both original genres and the saved Tab B synopsis. | Browser conflict and actual PostgreSQL results in M10. |

Problem repaired: Restarting Flask and the SSH tunnel restored MovieVault after
VS Code closed. During the submission review, Codex also found that the README
referred to two helper scripts missing from the repository and replaced those
steps with direct PostgreSQL commands.

Source review: The application, repository module, validation module, templates,
stylesheet, requirements, and README are present. `.venv/` and `.env` are ignored.
A tracked-filename check found no virtual environment, `.env`, or private-key
filenames. This filename check does not prove that every file is free of secrets.

Limitation: MovieVault has no application authentication, roles, record ownership
checks, or CSRF protection. Server validation and stale-version checking do not
provide those protections. SSH access to King's is separate from application
user identity.

The short submission reflection is in
[M11-LabReflection.md](../MileStones/M11-LabReflection.md).

AI-use note: Codex helped interpret the lesson, ran the MovieVault tests, reviewed
the source layout, and drafted these notes. The S Corp section records expected
behavior only; those exercises have not been completed.
