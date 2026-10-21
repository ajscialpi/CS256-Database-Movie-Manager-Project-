FIELDS = (
    "movie_id", "title", "genre", "release_year",
    "director", "content_rating", "synopsis",
)


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