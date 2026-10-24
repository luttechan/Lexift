from __future__ import annotations

# Publisher only: Do not add unverified names.
SPECIAL_THANKS: tuple[tuple[str, str], ...] = (
    ('Translation (JP) & QA', '루노'),
)

def get_special_thanks() -> tuple[tuple[str, str], ...]:
    return tuple((language, name) for language, name in SPECIAL_THANKS
                 if language.strip() and name.strip())
