-- One result row per movie, including movies without reviews.
-- Count the review primary key, not the placeholder row from the LEFT JOIN.
SELECT m.movie_id, m.title, m.genre, m.release_year,
       COUNT(r.review_id) AS total_reviews,
       ROUND(AVG(r.rating), 2) AS average_rating
FROM cs256_m05_movievault.movies AS m
LEFT JOIN cs256_m05_movievault.reviews AS r
       ON r.movie_id = m.movie_id
GROUP BY m.movie_id, m.title, m.genre, m.release_year
ORDER BY total_reviews DESC, m.title ASC, m.movie_id ASC;
