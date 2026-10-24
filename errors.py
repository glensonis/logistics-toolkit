"""Shared error types."""


class UserInputError(ValueError):
    """A validation error whose message is safe to show to end users."""


def finite_float(value) -> float:
    """float() that rejects NaN/inf and overflow with a safe UserInputError."""
    import math

    try:
        n = float(value)
    except OverflowError:
        raise UserInputError("Values are too large") from None
    except (TypeError, ValueError):
        raise UserInputError("Values must be numbers") from None
    if not math.isfinite(n):
        raise UserInputError("Values must be finite numbers")
    return n
