"""
validators.py - Input validation helpers (user-defined module 1).

Every function either returns a cleaned value or raises ValidationError
with a message that is safe to show directly to the user.
"""
import re
import pandas as pd


class ValidationError(ValueError):
    """Raised when user input is missing or malformed."""


def require_text(value, field, max_len=80):
    """Return stripped text; reject empty or over-long input."""
    text = str(value if value is not None else "").strip()
    if not text:
        raise ValidationError(f"{field} cannot be empty.")
    if len(text) > max_len:
        raise ValidationError(f"{field} must be at most {max_len} characters.")
    return text


def parse_positive_int(value, field):
    """Return an int >= 1 or raise ValidationError."""
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a whole number.")
    if number < 1:
        raise ValidationError(f"{field} must be at least 1.")
    return number


def parse_date(value, field="Date", allow_empty=False):
    """Parse a strict YYYY-MM-DD string into a pandas Timestamp."""
    text = str(value if value is not None else "").strip()
    if not text:
        if allow_empty:
            return None
        raise ValidationError(f"{field} cannot be empty (use YYYY-MM-DD).")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValidationError(f"{field} must be in YYYY-MM-DD format.")
    try:
        return pd.Timestamp(text)
    except ValueError:
        raise ValidationError(f"{field} is not a real calendar date.")


def validate_email(value):
    """Email is optional; if given it must look like name@domain.tld."""
    text = str(value if value is not None else "").strip()
    if text and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text):
        raise ValidationError("Email address looks invalid.")
    return text


def validate_range(start, end, field="Date range"):
    """Ensure start <= end when both are present."""
    if start is not None and end is not None and start > end:
        raise ValidationError(f"{field}: start date is after end date.")
