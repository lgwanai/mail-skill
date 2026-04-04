"""Natural language query parser for email search."""
from __future__ import annotations

from dataclasses import dataclass

from .date_parser import DateRange


@dataclass
class ParsedQuery:
    """Represents a parsed natural language query."""
    original_query: str
    date_range: DateRange | None
    sender: str | None
    keywords: str


def parse_natural_query(query: str, reference_date=None) -> ParsedQuery:
    """Parse natural language query to ParsedQuery. To be implemented."""
    raise NotImplementedError("parse_natural_query not yet implemented")


def match_senders(query_sender: str, sender_list: list[str]) -> list[str]:
    """Match sender pattern against sender list. To be implemented."""
    raise NotImplementedError("match_senders not yet implemented")
