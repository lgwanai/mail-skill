"""Chinese date expression parser for natural language search."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class DateRange:
    """Represents a date range with inclusive start and end dates."""
    date_from: date
    date_to: date


def parse_date_expression(query: str, reference_date: date | None = None) -> DateRange | None:
    """Parse Chinese date expression to DateRange. To be implemented."""
    raise NotImplementedError("parse_date_expression not yet implemented")


def extract_date_from_query(query: str, reference_date: date | None = None) -> tuple[DateRange | None, str]:
    """Extract date expression from query string. To be implemented."""
    raise NotImplementedError("extract_date_from_query not yet implemented")
