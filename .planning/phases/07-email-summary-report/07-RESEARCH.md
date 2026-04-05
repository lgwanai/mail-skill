# Phase 7: Email Summary Report - Research

**Researched:** 2026-04-05
**Domain:** Email summarization, LLM-powered reporting, Markdown generation
**Confidence:** HIGH

## Summary

Phase 7 introduces an email summary report feature that aggregates emails by sender within a specified time period, generates individual email summaries using LLM, and produces a comprehensive digest report in Markdown format. This phase builds heavily on existing infrastructure: the LLM client from Phase 6, database queries from Phase 1-2, and Markdown formatting patterns from Phase 5.

**Primary recommendation:** Leverage existing `LLMClient`, `MailDatabase.search_emails()`, and `detail.py` formatting patterns. Create a new `summary_report.py` module that orchestrates email grouping, LLM summarization, and report generation. Use structured prompts for consistent output format.

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SUMMARY-01 | Group emails by sender for given recipient and time period | `db.search_emails()` supports date_from/date_to filters; Python `itertools.groupby` for sender grouping |
| SUMMARY-02 | Generate individual email summaries with key info and action items | `LLMClient` from Phase 6; prompt engineering for structured summary extraction |
| SUMMARY-03 | Create overall summary with action items list | LLM aggregation of individual summaries; structured prompt for consolidated output |
| SUMMARY-04 | Format output as readable Markdown with export support | Existing `detail.py` patterns; Python `markdown` library already used in CLI |

</phase_requirements>

## Standard Stack

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | 2.14.0 | LLM API for summarization | Already configured via LLMClient from Phase 6 |
| sqlite3 | stdlib | Email retrieval and filtering | Existing `MailDatabase` class |
| datetime | stdlib | Date range parsing | Standard for date handling |
| itertools | stdlib | Grouping emails by sender | `groupby` for efficient grouping |

### Supporting (Already Available)

| Library | Purpose | When to Use |
|---------|---------|-------------|
| markdown | HTML conversion for export | SUMMARY-04 if HTML export needed |
| jinja2 | Template rendering | SUMMARY-04 for report formatting |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LLMClient | Direct OpenAI API | LLMClient provides abstraction and testing hooks |
| itertools.groupby | Pandas groupby | itertools is stdlib, no new dependency |
| Markdown formatting | HTML formatting | Markdown is more readable in CLI, already used |

**Installation:**
No new dependencies required. All infrastructure already in place.

## Architecture Patterns

### Recommended Project Structure

```
scripts/mail_manager/
├── summary_report.py        # NEW - main report generation module
├── llm/
│   ├── client.py            # EXISTING - use for summarization
│   └── prompts.py           # EXTEND - add summary prompts
├── db.py                    # EXISTING - use search_emails()
├── detail.py                # EXISTING - use formatting patterns
└── ...
```

### Pattern 1: Email Grouping by Sender

**What:** Group filtered emails by sender for per-sender summary sections
**When to use:** SUMMARY-01 for organizing report structure

```python
# Source: Python stdlib pattern
from __future__ import annotations

from datetime import date, datetime
from itertools import groupby
from typing import Any


def group_emails_by_sender(
    emails: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group emails by sender email address.

    Args:
        emails: List of email dictionaries with 'sender' field.

    Returns:
        Dict mapping sender to list of their emails, sorted by date.
    """
    # Sort by sender first (required for groupby)
    sorted_emails = sorted(emails, key=lambda e: e.get("sender", ""))

    grouped: dict[str, list[dict[str, Any]]] = {}
    for sender, group in groupby(sorted_emails, key=lambda e: e.get("sender", "")):
        if sender:
            # Sort each group by date
            grouped[sender] = sorted(
                list(group),
                key=lambda e: e.get("date") or "",
            )

    return grouped


def filter_emails_by_recipient_and_date(
    db: "MailDatabase",
    recipient: str,
    date_from: date,
    date_to: date,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Filter emails by recipient and date range.

    Args:
        db: MailDatabase instance.
        recipient: Email address of recipient (user's email).
        date_from: Start date inclusive.
        date_to: End date inclusive.
        limit: Maximum emails to retrieve.

    Returns:
        List of email dictionaries matching criteria.
    """
    return db.search_emails(
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        limit=limit,
    )
```

### Pattern 2: Individual Email Summary Generation

**What:** Use LLM to generate structured summary for each email
**When to use:** SUMMARY-02 for per-email summarization

```python
# Source: Project pattern from thread_manager.py and reply_assistant.py
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mail_manager.llm.client import LLMClient


@dataclass
class EmailSummary:
    """Structured summary of a single email."""

    subject: str
    key_points: list[str]
    action_items: list[str]
    deadline: str | None
    priority: str  # high, medium, low
    one_liner: str  # Single sentence summary


# Prompt for individual email summary (add to prompts.py)
EMAIL_SUMMARY_PROMPT = """Analyze this email and provide a structured summary.

Email:
From: {sender}
Subject: {subject}
Date: {date}
Body:
{body}

Provide your response in this exact JSON format:
{{
    "key_points": ["point 1", "point 2", "point 3"],
    "action_items": ["action 1", "action 2"],
    "deadline": "YYYY-MM-DD or null",
    "priority": "high|medium|low",
    "one_liner": "Single sentence summary of the email"
}}

Focus on:
1. What is this email about?
2. What action is requested or implied?
3. Are there any deadlines mentioned?
4. How important/urgent does this seem?
"""


def summarize_email(
    llm_client: "LLMClient",
    email: dict[str, Any],
) -> EmailSummary:
    """Generate structured summary for a single email.

    Args:
        llm_client: LLM client for generation.
        email: Email dictionary with sender, subject, date, body_text.

    Returns:
        EmailSummary with structured information.
    """
    import json

    # Truncate body if too long
    body = email.get("body_text", "") or ""
    if len(body) > 2000:
        body = body[:2000] + "..."

    prompt = EMAIL_SUMMARY_PROMPT.format(
        sender=email.get("sender", "Unknown"),
        subject=email.get("subject", "No Subject"),
        date=email.get("date", "Unknown"),
        body=body,
    )

    response = llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,  # Lower temperature for structured output
        max_tokens=500,
    )

    # Parse JSON response
    try:
        # Extract JSON from response (handle markdown code blocks)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        # Fallback if JSON parsing fails
        data = {
            "key_points": [response.content[:200]],
            "action_items": [],
            "deadline": None,
            "priority": "medium",
            "one_liner": response.content[:100],
        }

    return EmailSummary(
        subject=email.get("subject", "No Subject"),
        key_points=data.get("key_points", []),
        action_items=data.get("action_items", []),
        deadline=data.get("deadline"),
        priority=data.get("priority", "medium"),
        one_liner=data.get("one_liner", ""),
    )
```

### Pattern 3: Overall Summary Generation

**What:** Aggregate all summaries into overall digest with consolidated action items
**When to use:** SUMMARY-03 for final report generation

```python
# Source: Project pattern from reply_assistant.py aggregation
OVERALL_SUMMARY_PROMPT = """You are analyzing a collection of email summaries to create an executive summary.

Here are the email summaries grouped by sender:

{sender_summaries}

Provide your response in this exact JSON format:
{{
    "overview": "2-3 sentence overview of all emails",
    "key_themes": ["theme 1", "theme 2", "theme 3"],
    "all_action_items": [
        {{"item": "action description", "sender": "sender email", "priority": "high|medium|low"}},
        ...
    ],
    "upcoming_deadlines": [
        {{"date": "YYYY-MM-DD", "description": "what is due", "sender": "sender email"}},
        ...
    ],
    "recommended_priority": [
        "Most urgent item to address",
        "Second most urgent",
        "Third most urgent"
    ]
}}

Focus on:
1. What are the main themes across all emails?
2. What actions need to be taken?
3. What deadlines are approaching?
4. What should be prioritized?
"""


@dataclass
class OverallSummary:
    """Overall summary of all emails."""

    overview: str
    key_themes: list[str]
    all_action_items: list[dict[str, str]]
    upcoming_deadlines: list[dict[str, str]]
    recommended_priority: list[str]


def generate_overall_summary(
    llm_client: "LLMClient",
    sender_summaries: dict[str, list[EmailSummary]],
) -> OverallSummary:
    """Generate overall summary from sender-grouped summaries.

    Args:
        llm_client: LLM client for generation.
        sender_summaries: Dict mapping sender to their EmailSummary list.

    Returns:
        OverallSummary with consolidated information.
    """
    import json

    # Format sender summaries for prompt
    summaries_text: list[str] = []
    for sender, summaries in sender_summaries.items():
        summaries_text.append(f"\n### Sender: {sender}")
        for i, s in enumerate(summaries, 1):
            summaries_text.append(f"\n{i}. {s.subject}")
            summaries_text.append(f"   Summary: {s.one_liner}")
            if s.action_items:
                summaries_text.append(f"   Actions: {', '.join(s.action_items)}")
            if s.deadline:
                summaries_text.append(f"   Deadline: {s.deadline}")

    prompt = OVERALL_SUMMARY_PROMPT.format(
        sender_summaries="\n".join(summaries_text),
    )

    response = llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1000,
    )

    # Parse JSON response
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        data = {
            "overview": response.content[:300],
            "key_themes": [],
            "all_action_items": [],
            "upcoming_deadlines": [],
            "recommended_priority": [],
        }

    return OverallSummary(
        overview=data.get("overview", ""),
        key_themes=data.get("key_themes", []),
        all_action_items=data.get("all_action_items", []),
        upcoming_deadlines=data.get("upcoming_deadlines", []),
        recommended_priority=data.get("recommended_priority", []),
    )
```

### Pattern 4: Markdown Report Formatting

**What:** Format all summaries as readable Markdown document
**When to use:** SUMMARY-04 for output formatting

```python
# Source: Project pattern from detail.py
from datetime import datetime
from typing import Any


def format_summary_report(
    recipient: str,
    date_from: date,
    date_to: date,
    sender_summaries: dict[str, list[tuple[dict[str, Any], EmailSummary]]],
    overall: OverallSummary,
) -> str:
    """Format complete summary report as Markdown.

    Args:
        recipient: Email address of the recipient.
        date_from: Report start date.
        date_to: Report end date.
        sender_summaries: Dict mapping sender to list of (email, EmailSummary) tuples.
        overall: OverallSummary object.

    Returns:
        Markdown-formatted report string.
    """
    sections: list[str] = []

    # Header
    sections.append(f"# Email Summary Report")
    sections.append(f"")
    sections.append(f"**Recipient:** {recipient}")
    sections.append(f"**Period:** {date_from} to {date_to}")
    sections.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    sections.append(f"")

    # Overview section
    sections.append(f"## Overview")
    sections.append(f"")
    sections.append(overall.overview)
    sections.append(f"")

    # Key themes
    if overall.key_themes:
        sections.append(f"### Key Themes")
        for theme in overall.key_themes:
            sections.append(f"- {theme}")
        sections.append(f"")

    # Recommended priority
    if overall.recommended_priority:
        sections.append(f"### Recommended Priority")
        for i, item in enumerate(overall.recommended_priority, 1):
            sections.append(f"{i}. {item}")
        sections.append(f"")

    # All action items
    if overall.all_action_items:
        sections.append(f"## All Action Items")
        sections.append(f"")
        sections.append(f"| Priority | Action | Sender |")
        sections.append(f"|----------|--------|--------|")
        for item in sorted(
            overall.all_action_items,
            key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "medium"), 1),
        ):
            sections.append(
                f"| {item.get('priority', 'medium').upper()} | {item.get('item', '')} | {item.get('sender', '')} |"
            )
        sections.append(f"")

    # Upcoming deadlines
    if overall.upcoming_deadlines:
        sections.append(f"## Upcoming Deadlines")
        sections.append(f"")
        sections.append(f"| Date | Description | Sender |")
        sections.append(f"|------|-------------|--------|")
        for dl in sorted(overall.upcoming_deadlines, key=lambda x: x.get("date", "")):
            sections.append(
                f"| {dl.get('date', '')} | {dl.get('description', '')} | {dl.get('sender', '')} |"
            )
        sections.append(f"")

    # Per-sender sections
    sections.append(f"## Emails by Sender")
    sections.append(f"")

    total_emails = sum(len(emails) for emails in sender_summaries.values())
    sections.append(f"*Total emails: {total_emails} from {len(sender_summaries)} senders*")
    sections.append(f"")

    for sender, email_summaries in sender_summaries.items():
        sections.append(f"### {sender}")
        sections.append(f"")

        for email, summary in email_summaries:
            # Email header
            subject = email.get("subject", "No Subject")
            date = (email.get("date") or "")[:10]
            sections.append(f"#### {subject}")
            sections.append(f"*Date: {date}*")
            sections.append(f"")

            # One-liner
            sections.append(f"> {summary.one_liner}")
            sections.append(f"")

            # Key points
            if summary.key_points:
                sections.append(f"**Key Points:**")
                for point in summary.key_points:
                    sections.append(f"- {point}")
                sections.append(f"")

            # Action items
            if summary.action_items:
                sections.append(f"**Action Items:**")
                for action in summary.action_items:
                    sections.append(f"- [ ] {action}")
                sections.append(f"")

            # Deadline
            if summary.deadline:
                sections.append(f"**Deadline:** {summary.deadline}")
                sections.append(f"")

            sections.append(f"---")
            sections.append(f"")

    return "\n".join(sections)
```

### Anti-Patterns to Avoid

- **Summarizing all emails in one LLM call:** Context window limits will cause truncation; process per-sender batches
- **No caching:** Re-summarizing same emails wastes API calls; consider caching summaries in database
- **Unstructured LLM output:** Without JSON format, parsing becomes fragile; always request structured output
- **Ignoring LLM failures:** JSON parsing errors will crash the report; always have fallback handling

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM API calls | Custom HTTP client | LLMClient (Phase 6) | Handles retries, errors, timeouts |
| Email filtering | Custom SQL queries | db.search_emails() | Already supports date filtering |
| Date parsing | Regex on strings | datetime.strptime() | Standard library handles edge cases |
| Grouping | Manual loops | itertools.groupby | More efficient, cleaner code |
| Markdown formatting | String concatenation | detail.py patterns | Consistent formatting style |
| JSON parsing | Regex extraction | json.loads() with fallback | Handles edge cases better |

**Key insight:** All infrastructure is already in place. Focus on orchestrating existing components with appropriate prompts for the summarization use case.

## Common Pitfalls

### Pitfall 1: LLM Rate Limiting with Large Email Volumes

**What goes wrong:** Summarizing 50+ emails hits rate limits, report generation fails halfway
**Why it happens:** Each email requires an LLM call; rate limits are per-minute
**How to avoid:**
- Batch emails (max 10 per batch with delays)
- Show progress indicator during generation
- Implement retry with exponential backoff
- Consider caching summaries for repeated reports
**Warning signs:** 429 errors, partial reports, long wait times

### Pitfall 2: JSON Parsing Failures

**What goes wrong:** LLM occasionally outputs malformed JSON, crashing report generation
**Why it happens:** LLM output is probabilistic; JSON format may not be followed exactly
**How to avoid:**
- Use lower temperature (0.3) for structured outputs
- Request JSON in markdown code blocks for easier extraction
- Always have fallback parsing (regex, partial extraction)
- Log failures for debugging
**Warning signs:** JSONDecodeError exceptions, empty summary fields

### Pitfall 3: Empty Date Range Results

**What goes wrong:** No emails found for specified date range, empty report
**Why it happens:** Wrong date format, no emails in period, incorrect recipient
**How to avoid:**
- Validate date range before processing
- Show clear error if no emails found
- Suggest broader date range or check filters
**Warning signs:** Empty sender_summaries dict, "No emails found" message

### Pitfall 4: Memory Issues with Large Email Bodies

**What goes wrong:** Processing emails with large attachments or bodies causes memory issues
**Why it happens:** Email body_text can be large; copying into prompts consumes memory
**How to avoid:**
- Truncate body_text to 2000 characters before sending to LLM
- Skip emails with empty body_text
- Process emails in batches, not all at once
**Warning signs:** Memory errors, slow processing, large context windows

### Pitfall 5: Inconsistent Summary Quality

**What goes wrong:** Some summaries are detailed, others are vague or missing key information
**Why it happens:** Email content varies; prompts may not handle all cases
**How to avoid:**
- Use consistent prompt structure with examples
- Lower temperature for more consistent output
- Include formatting instructions in prompt
- Validate summary has required fields before using
**Warning signs:** Empty action_items, generic one_liners, missing deadlines

## Code Examples

### Main Report Generation Function

```python
# Source: Project pattern for CLI commands
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mail_manager.db import MailDatabase
    from mail_manager.llm.client import LLMClient

logger = logging.getLogger(__name__)


def generate_email_summary_report(
    db: "MailDatabase",
    llm_client: "LLMClient",
    recipient: str,
    date_from: date | None = None,
    date_to: date | None = None,
    days_back: int = 7,
    limit: int = 100,
    output_path: str | None = None,
) -> str:
    """Generate complete email summary report.

    Args:
        db: MailDatabase instance.
        llm_client: LLM client for summarization.
        recipient: Email address of the recipient.
        date_from: Start date (default: days_back from today).
        date_to: End date (default: today).
        days_back: Number of days to look back if date_from not specified.
        limit: Maximum emails to process.
        output_path: Optional path to save report as file.

    Returns:
        Markdown-formatted report string.
    """
    # Set default date range
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=days_back)

    logger.info(f"Generating report for {recipient} from {date_from} to {date_to}")

    # Step 1: Fetch emails
    emails = filter_emails_by_recipient_and_date(
        db=db,
        recipient=recipient,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )

    if not emails:
        return f"No emails found for {recipient} between {date_from} and {date_to}."

    logger.info(f"Found {len(emails)} emails")

    # Step 2: Group by sender
    sender_groups = group_emails_by_sender(emails)
    logger.info(f"Grouped into {len(sender_groups)} senders")

    # Step 3: Generate summaries per sender
    sender_summaries: dict[str, list[tuple[dict[str, Any], EmailSummary]]] = {}
    all_summaries: dict[str, list[EmailSummary]] = {}

    for sender, sender_emails in sender_groups.items():
        sender_summaries[sender] = []
        all_summaries[sender] = []

        for email in sender_emails:
            try:
                summary = summarize_email(llm_client, email)
                sender_summaries[sender].append((email, summary))
                all_summaries[sender].append(summary)
                logger.debug(f"Summarized: {email.get('subject', '')[:50]}")
            except Exception as e:
                logger.warning(f"Failed to summarize email {email.get('message_id')}: {e}")
                continue

    # Step 4: Generate overall summary
    overall = generate_overall_summary(llm_client, all_summaries)

    # Step 5: Format report
    report = format_summary_report(
        recipient=recipient,
        date_from=date_from,
        date_to=date_to,
        sender_summaries=sender_summaries,
        overall=overall,
    )

    # Step 6: Save to file if path provided
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"Report saved to {output_path}")

    return report
```

### CLI Integration

```python
# Add to mail_cli.py

def cmd_summary_report(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Generate email summary report."""
    from mail_manager.summary_report import generate_email_summary_report
    from mail_manager.llm.client import LLMClient

    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)
    isolated_db = MailDatabase(paths["db_path"])
    llm_client = LLMClient()

    # Parse date arguments
    date_from = None
    date_to = None
    if args.date_from:
        date_from = datetime.strptime(args.date_from, "%Y-%m-%d").date()
    if args.date_to:
        date_to = datetime.strptime(args.date_to, "%Y-%m-%d").date()

    try:
        report = generate_email_summary_report(
            db=isolated_db,
            llm_client=llm_client,
            recipient=client.email,
            date_from=date_from,
            date_to=date_to,
            days_back=args.days,
            limit=args.limit,
            output_path=args.output,
        )

        if args.output:
            print(json.dumps(success_response(
                message=f"Report saved to {args.output}",
                data={"emails_processed": len(report.split("---")) - 1},
            )))
        else:
            print(report)

    except Exception as e:
        print(json.dumps(error_response(ErrorCodes.INTERNAL_ERROR, str(e))))


# Add to main() argument parser:
# summary-report command
summary_p = subparsers.add_parser(
    "summary-report",
    help="Generate email summary report by sender"
)
summary_p.add_argument("--account", help="Account to use")
summary_p.add_argument(
    "--date-from",
    help="Start date (YYYY-MM-DD, default: 7 days ago)",
)
summary_p.add_argument(
    "--date-to",
    help="End date (YYYY-MM-DD, default: today)",
)
summary_p.add_argument(
    "--days",
    type=int,
    default=7,
    help="Days to look back if date-from not specified",
)
summary_p.add_argument(
    "--limit",
    type=int,
    default=100,
    help="Maximum emails to process",
)
summary_p.add_argument(
    "--output",
    help="Output file path (prints to stdout if not specified)",
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual email reading | AI-summarized digests | 2023+ | 10x faster comprehension |
| Flat email lists | Grouped by sender | 2024+ | Better context understanding |
| Unstructured summaries | JSON-structured with action items | 2024+ | Actionable insights |
| CLI output only | Markdown with export | 2025+ | Shareable reports |

**Deprecated/outdated:**
- Keyword extraction without context: Use LLM for semantic understanding
- Simple subject line summaries: Use full body analysis for meaningful summaries
- Static report formats: Use structured output that can be reformatted

## Open Questions

1. **Should summaries be cached in the database?**
   - What we know: LLM calls are expensive; emails don't change once received
   - What's unclear: Cache invalidation strategy, storage overhead
   - Recommendation: Store summaries in a new `email_summaries` table with `message_id` as key; regenerate on demand or after 30 days

2. **How to handle very large email volumes (500+ emails)?**
   - What we know: Rate limits and context window limits exist
   - What's unclear: Optimal batching strategy, user experience
   - Recommendation: Limit to 100 emails by default; show progress; offer --all flag for power users

3. **Should the report support different output formats?**
   - What we know: Markdown is primary; HTML export available via markdown library
   - What's unclear: PDF, JSON export needs
   - Recommendation: Start with Markdown + HTML; add JSON export for programmatic use

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest with pytest-mock |
| Config file | pyproject.toml (pytest.ini_options) |
| Quick run command | `pytest tests/test_summary_report.py -v -x` |
| Full suite command | `pytest --cov=scripts --cov-report=term-missing` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| SUMMARY-01 | Group emails by sender | unit | `pytest tests/test_summary_report.py::TestGroupEmailsBySender -x` | Wave 0 |
| SUMMARY-02 | Generate individual email summaries | unit | `pytest tests/test_summary_report.py::TestSummarizeEmail -x` | Wave 0 |
| SUMMARY-02 | Extract action items from email | unit | `pytest tests/test_summary_report.py::TestExtractActionItems -x` | Wave 0 |
| SUMMARY-03 | Generate overall summary | unit | `pytest tests/test_summary_report.py::TestGenerateOverallSummary -x` | Wave 0 |
| SUMMARY-03 | Consolidate action items | unit | `pytest tests/test_summary_report.py::TestConsolidateActionItems -x` | Wave 0 |
| SUMMARY-04 | Format Markdown report | unit | `pytest tests/test_summary_report.py::TestFormatSummaryReport -x` | Wave 0 |
| SUMMARY-04 | Export to file | integration | `pytest tests/test_summary_report.py::TestExportReport -x` | Wave 0 |
| All | End-to-end report generation | integration | `pytest tests/test_cli.py::test_cmd_summary_report -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_summary_report.py -v --cov=scripts/mail_manager/summary_report`
- **Per wave merge:** `pytest --cov=scripts --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_summary_report.py` - covers SUMMARY-01~04
- [ ] `tests/conftest.py` extension - fixtures for sample email groups, mock LLM summary responses
- [ ] `scripts/mail_manager/summary_report.py` - new module to implement
- [ ] `scripts/mail_manager/llm/prompts.py` - extend with summary prompts

### Mock Strategies

**LLM Summary Mock:**
```python
# In conftest.py
@pytest.fixture
def mock_llm_summary_response():
    """Mock LLM response for email summarization."""
    from unittest.mock import MagicMock, patch

    with patch("scripts.mail_manager.llm.client.LLMClient") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client

        # Mock chat response with JSON summary
        mock_response = MagicMock()
        mock_response.content = '''```json
{
    "key_points": ["Point 1", "Point 2"],
    "action_items": ["Action 1", "Action 2"],
    "deadline": "2026-04-10",
    "priority": "high",
    "one_liner": "This is a test email summary."
}
```'''
        mock_client.chat.return_value = mock_response

        yield mock_client


@pytest.fixture
def sample_email_group():
    """Sample emails grouped by sender for testing."""
    return {
        "alice@example.com": [
            {
                "message_id": "msg-1",
                "sender": "alice@example.com",
                "subject": "Project Update",
                "date": "2026-04-01",
                "body_text": "Please review the attached project plan by Friday.",
            },
            {
                "message_id": "msg-2",
                "sender": "alice@example.com",
                "subject": "Re: Meeting",
                "date": "2026-04-02",
                "body_text": "Let's meet tomorrow at 2pm.",
            },
        ],
        "bob@example.com": [
            {
                "message_id": "msg-3",
                "sender": "bob@example.com",
                "subject": "Budget Approval",
                "date": "2026-04-03",
                "body_text": "Need your approval on the Q2 budget by end of week.",
            },
        ],
    }
```

## Sources

### Primary (HIGH confidence)

- Project codebase analysis: `scripts/mail_manager/db.py`, `scripts/mail_manager/llm/client.py`, `scripts/mail_manager/detail.py`, `scripts/mail_manager/thread_manager.py`, `scripts/mail_manager/reply_assistant.py`
- Existing test infrastructure: `tests/conftest.py`, `tests/test_llm_client.py`, `tests/test_thread_manager.py`, `tests/test_reply_assistant.py`
- Existing prompts: `scripts/mail_manager/llm/prompts.py`

### Secondary (MEDIUM confidence)

- Python stdlib patterns for grouping and date handling (standard, well-documented)
- LLM prompt engineering for structured output (established best practices)

### Tertiary (LOW confidence)

- Specific summary format preferences - may need user feedback iteration
- Optimal LLM parameters for summary quality - may need tuning

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All packages already installed, familiar patterns from Phase 6
- Architecture: HIGH - Building on existing patterns (LLMClient, db.search_emails, detail formatting)
- Pitfalls: MEDIUM - LLM integration edge cases well-known from Phase 6 experience
- Test strategy: HIGH - Following existing pytest patterns from conftest.py and test files

**Research date:** 2026-04-05
**Valid until:** 30 days (stable libraries, established patterns)
