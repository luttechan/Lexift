from __future__ import annotations

# Publisher only: Do not add unverified names.
SPECIAL_THANKS: tuple[tuple[str, str], ...] = (
    # ('Japanese', 'Clone'),
    # ('English', '클로네쨩사랑해'),
)

def get_special_thanks() -> tuple[tuple[str, str], ...]:
    return tuple((language, name) for language, name in SPECIAL_THANKS
                 if language.strip() and name.strip())
