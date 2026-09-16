# My CS256 project

- Project name and brand: TBD (Movie Explorer for Users)

- Intended user and one useful task: Movie enthusiests, to help advertise movies

- Three screens and the path between them: Home Page, Forum Page, Submission Page, Blog Page
![Home Page Draft](image-1.png)

- Colors, typography, and why they support the user: red, black, and white. These colors create a movie-style design and make the website easy to read.

- Two related lecture tables and the primary/foreign keys: 
    movies (movie_id VARCHAR(100) PRIMARY KEY);
    reviews (review_id VARCHAR(100) PRIMARY KEY, movie_id FOREIGN KEY);

- Fields the browser will collect/display (and fields it must not expose): Users can enter movie searches, ratings, and reviews. The website displays movie titles, genres, ratings, and reviews. It must not expose passwords, private user information, or API keys.

- One reporting question answered by a join/aggregate: What movies have the highest average user rating? (use tables movies, reviews)

- Smallest working create/read/update/delete workflow: Users can add, view, edit, and delete movie reviews.

- Scope I am deliberately saving for later: I will save user accounts, movie trailers, advanced recommendations, and an admin dashboard for later.

Attach a wireframe with labels, empty results, errors, success, and delete confirmation.

## Weekly progress note

Milestone: M01 / Date:

1. What works (file or screenshot): ![One Facility, Many Reports](image.png)
2. One result I can explain: The 2 page sketches for website UI. (First page is forum page, second page is Home page)
3. What is blocked: No Blockers at the moment
4. My next action: Create a Skeleton.md and plan more of the workflow
5. AI tools used and how I checked/changed the output, or “none”: Codex, Copilot

S Corp observations
Task for Employee- Employees are tasked with filling out a forum (Report an Injury)
Task for Manager- Managers are tasked with filter claims and interpreting data (Manager Dashboard)
