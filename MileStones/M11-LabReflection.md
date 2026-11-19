## M11 - Lab Reflection

This reflection uses my completed MovieVault testing. I have not completed the
separate local S Corp exercises yet.

### 1. Successful and Rejected Requests

In MovieVault, I successfully updated M10 Disposable A (98101) and M10
Disposable B (98102) to Drama after reopening the movie list. The application
reported that both movies were updated, and the PostgreSQL results confirmed
both genres were Drama.

The earlier attempt from an outdated browser tab was rejected. I had edited
movie 98102's synopsis in another tab, so the original selection was stale.
The failed update left the genres as Mystery and Comedy, and the separately
saved `Change in Tab B.` text remained in the database. My screenshots and
before-and-after query results are in [M10.md](M10.md).

### 2. Server-Side Check

The `_lock_current_movie()` function in
[repository_postgres.py](../backendconnection/repository_postgres.py) locks the
current row and compares its version with the version submitted by the form.
A mismatch raises `StaleMovie`. During the bulk update, this causes the entire
transaction to roll back. The Flask route handles that exception as a conflict.

This check belongs on the server because the browser can hold old information,
and someone can change form values or send a request directly. The server must
check the current database record before saving. This protects against stale
updates; it does not establish the user's identity or permission to edit.

### 3. Problem Repaired

After I accidentally closed VS Code, MovieVault stopped loading because Flask
and the SSH tunnel were no longer running. With Codex's help, I restarted Flask
on King's port 5108 and restored the tunnel on local port 55100. The movie list
loaded again, and I completed the successful retry.

### 4. Remaining Limitation

MovieVault does not currently have application sign-in, user roles, record-level
permissions, or CSRF protection for its forms. Its validation, parameterized SQL,
and version checks protect different parts of a request, but they do not replace
account security. The project currently runs through my King's SSH connection.

### 5. Next Action

Before the final project review, I need to complete the separate S Corp exercises,
review my README and saved evidence, and commit and push the intended source and
documentation files. Codex reran the MovieVault suite: all 52 tests passed with
no skips. Those tests use mocked database calls; the M10 results provide the
separate actual PostgreSQL evidence.

AI-use note: I used Codex to help explain the server checks, rerun the project
tests, update documentation, and organize this reflection. I performed the
MovieVault browser tests. S Corp outcomes in my lesson notes are expectations,
not completed tests.
