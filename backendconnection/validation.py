FIELDS = (
    "movie_id", "title", "genre", "release_year",
    "director", "content_rating", "synopsis",
)

# Choices for the bulk form; existing create/edit genre fields stay free text.
BULK_GENRES = (
    'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary',
    'Drama', 'Family', 'Fantasy', 'Horror', 'Musical', 'Mystery',
    'Romance', 'Science Fiction', 'Thriller', 'War', 'Western',
)


def validate_movie_genres(movie_ids, genre, versions):
    """Validate the whole request before opening a database connection."""
    if not movie_ids:
        raise ValueError('Select at least one movie.')
    if len(movie_ids) > 25:
        raise ValueError('Select no more than 25 movies at a time.')
    ids = []
    for value in movie_ids:
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ValueError('Movie IDs must be whole numbers.')
        try:
            movie_id = int(value)
        except ValueError:
            raise ValueError('Movie IDs must be whole numbers.') from None
        if not 1 <= movie_id <= 2147483647:
            raise ValueError('Movie IDs must be between 1 and 2147483647.')
        if movie_id in ids:
            raise ValueError('Select each movie only once; duplicate IDs are not allowed.')
        ids.append(movie_id)
    if not isinstance(genre, str) or genre.strip() not in BULK_GENRES:
        raise ValueError('Choose a valid genre from the list.')
    for movie_id in ids:
        version = versions.get(str(movie_id), '')
        if (not isinstance(version, str) or len(version) != 64
                or any(char not in '0123456789abcdef' for char in version)):
            raise ValueError('A movie version is missing or invalid. Refresh the list and select again.')
    return sorted(ids), genre.strip()


def validate_movie(form):
    values = {
        field: form.get(field, "").strip()
        for field in FIELDS
    }
    errors = {}

    for field in FIELDS:
        if not values[field]:
            errors[field] = "This field is required."

    for field, minimum, maximum in (
        ("movie_id", 1, 2147483647),
        ("release_year", 1888, 2100),
    ):
        if values[field]:
            try:
                number = int(values[field])
            except ValueError:
                errors[field] = "Enter a whole number."
            else:
                if not minimum <= number <= maximum:
                    errors[field] = (
                        f"Enter a number from {minimum} to {maximum}."
                    )
                else:
                    values[field] = number

    if values["synopsis"] and not 20 <= len(values["synopsis"]) <= 1000:
        errors["synopsis"] = "Enter between 20 and 1,000 characters."

    return values, errors
