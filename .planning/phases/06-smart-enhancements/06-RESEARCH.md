# Phase 6: Smart Enhancements - Research

**Researched:** 2026-04-05
**Domain:** LLM integration, document parsing, email threading
**Confidence:** HIGH

## Summary

Phase 6 introduces three intelligent features: email thread association with timeline view, attachment content parsing for enhanced search, and AI-powered reply composition. This phase requires integration with LLM APIs and document parsing libraries while maintaining the project's existing architecture patterns (SQLite + ChromaDB, unified error handling, pytest testing).

**Primary recommendation:** Use OpenAI Python SDK (already installed v2.14.0) for LLM features with a thin abstraction layer; use PyMuPDF (v1.26.3), openpyxl (v3.1.5), and python-pptx (v1.0.2) for document parsing (already installed). Follow existing mocking patterns for external dependencies.

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| THREAD-01 | Fetch email and auto-retrieve related correspondence | `in_reply_to`, `references` headers already stored in DB; existing `get_thread_timeline()` method |
| THREAD-02 | Timeline view with full/summary display | Use existing `detail.py` formatting patterns; add summary generation via LLM |
| THREAD-03 | Show sent/received emails in thread | Query by sender/recipient matching; leverage existing `search_emails()` |
| ATTACH-AI-01 | Parse Excel/doc/PPT/PDF/txt/md for indexing | PyMuPDF, openpyxl, python-pptx already installed; add text extraction module |
| ATTACH-AI-02 | Parse images with vision API | OpenAI Vision API via existing OpenAI SDK; requires image encoding |
| REPLY-AI-01 | AI-polished reply composition | OpenAI SDK for chat completions; context from thread timeline |
| REPLY-AI-02 | User confirmation before sending | Integrate with existing `send_email()` in client.py |
| REPLY-AI-03 | Learn from feedback history | Store feedback in SQLite; few-shot examples in LLM prompts |

</phase_requirements>

## Standard Stack

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | 2.14.0 | LLM API integration | Official SDK, already in environment, supports chat completions and vision |
| PyMuPDF | 1.26.3 | PDF text extraction | Fast, comprehensive PDF parsing, already installed |
| openpyxl | 3.1.5 | Excel file reading | Standard for .xlsx files, already installed |
| python-pptx | 1.0.2 | PowerPoint parsing | Standard for .pptx files, already installed |
| chromadb | 0.4.0+ | Vector search for parsed content | Already used for email search, extend for attachments |

### Supporting (May Need Addition)

| Library | Purpose | When to Use |
|---------|---------|-------------|
| python-docx | Word document parsing | Only if .docx attachments are common |
| Pillow | Image processing for vision API | Required for ATTACH-AI-02 (images) |
| tiktoken | Token counting | Optional, for context window management |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| OpenAI SDK | Anthropic SDK | Project already uses OpenAI for embeddings; single provider simpler |
| PyMuPDF | pdfplumber | PyMuPDF faster and already installed |
| python-pptx |unoconv | python-pptx pure Python, no LibreOffice dependency |

**Installation:**
```bash
pip install python-docx Pillow tiktoken  # Only if needed
```

## Architecture Patterns

### Recommended Project Structure

```
scripts/mail_manager/
├── llm/                    # LLM integration (NEW)
│   ├── __init__.py
│   ├── client.py           # LLM client abstraction
│   └── prompts.py          # Prompt templates
├── attachment_parser/      # Document parsing (NEW)
│   ├── __init__.py
│   ├── base.py             # Parser protocol
│   ├── pdf_parser.py       # PyMuPDF wrapper
│   ├── excel_parser.py     # openpyxl wrapper
│   ├── pptx_parser.py      # python-pptx wrapper
│   └── image_parser.py     # Vision API wrapper
├── thread_manager.py       # Thread enhancement (NEW)
├── reply_assistant.py      # AI reply composition (NEW)
├── client.py               # Existing - add reply methods
├── db.py                   # Existing - add attachment content storage
├── detail.py               # Existing - extend for thread view
└── ...
```

### Pattern 1: LLM Client Abstraction

**What:** Thin wrapper around OpenAI SDK for consistent interface and easy testing
**When to use:** All LLM operations (reply composition, attachment summarization, thread summaries)

```python
# Source: Project pattern from db.py embedding function usage
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


@dataclass
class LLMResponse:
    """Standard LLM response structure."""
    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str


class LLMClient:
    """Thin wrapper around OpenAI SDK for LLM operations."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE")
        self.client = OpenAI(api_key=api_key, base_url=api_base)
        self.model = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Send chat completion request."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=response.choices[0].finish_reason,
        )

    def chat_with_history(
        self,
        system_prompt: str,
        conversation: list[dict[str, str]],
        user_message: str,
    ) -> LLMResponse:
        """Chat with conversation history context."""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation)
        messages.append({"role": "user", "content": user_message})
        return self.chat(messages)
```

### Pattern 2: Document Parser Protocol

**What:** Protocol-based parser architecture for different document types
**When to use:** ATTACH-AI-01, ATTACH-AI-02 for parsing attachments

```python
# Source: Project pattern from common/patterns.md Protocol pattern
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class DocumentParser(Protocol):
    """Protocol for document parsers."""

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file type."""
        ...

    def extract_text(self, file_path: Path) -> str:
        """Extract text content from document."""
        ...

    def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata (author, date, etc.)."""
        ...


class PDFParser:
    """PyMuPDF-based PDF parser."""

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    def extract_text(self, file_path: Path) -> str:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
```

### Pattern 3: Thread Timeline Enhancement

**What:** Extend existing `get_thread_timeline()` with sender/recipient matching
**When to use:** THREAD-01, THREAD-02, THREAD-03 for comprehensive thread view

```python
# Source: Existing db.py get_thread_timeline() method
def get_enhanced_thread_timeline(
    self,
    seed_message_id: str,
    include_sender_thread: bool = True,
    limit: int = 100,
) -> list[dict]:
    """Get thread with related sender/recipient correspondence."""
    # Start with existing thread timeline
    timeline = self.get_thread_timeline(seed_message_id, limit)

    if not include_sender_thread or not timeline:
        return timeline

    # Get all unique participants
    participants = set()
    for email in timeline:
        if email.get("sender"):
            participants.add(email["sender"])
        if email.get("recipient"):
            for r in email["recipient"].split(","):
                participants.add(r.strip())

    # Find related emails by participants
    # (exclude already included)
    existing_ids = {e["message_id"] for e in timeline}
    for participant in participants:
        related = self.search_emails(
            sender=participant,
            limit=20,
        )
        for email in related:
            if email["message_id"] not in existing_ids:
                timeline.append(email)
                existing_ids.add(email["message_id"])

    # Sort by date
    timeline.sort(key=lambda x: x.get("date") or "")
    return timeline
```

### Anti-Patterns to Avoid

- **Tight LLM coupling:** Don't call LLM synchronously in CLI command handlers; use async or timeout patterns
- **Large context windows:** Don't send entire email histories to LLM; summarize first
- **No fallback:** Don't fail silently if LLM is unavailable; degrade gracefully
- **Storing raw parsed text in SQLite:** Use ChromaDB for searchable content, store summaries in SQLite

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM API calls | Custom HTTP client | OpenAI SDK | Handles retries, streaming, errors |
| PDF text extraction | Regex on raw PDF | PyMuPDF | Encoding issues, layout complexity |
| Excel reading | CSV conversion | openpyxl | Formulas, formatting, multiple sheets |
| Token counting | Manual character count | tiktoken | Accurate token estimation |
| Image to text | OCR library | OpenAI Vision API | Already available, better results |
| Thread reconstruction | Custom threading logic | Existing `get_thread_timeline()` | Already implemented and tested |

**Key insight:** Most infrastructure is already in place (OpenAI SDK, document parsers, thread timeline). Focus on integration and prompt engineering rather than building new parsers.

## Common Pitfalls

### Pitfall 1: LLM Rate Limiting / Timeouts

**What goes wrong:** LLM API calls hang or fail, blocking CLI commands
**Why it happens:** Network issues, rate limits, large context windows
**How to avoid:**
- Set reasonable timeouts (30s default)
- Implement retry with exponential backoff
- Show progress indicator for long operations
- Cache LLM results for repeated queries
**Warning signs:** Commands taking >5 seconds, timeout errors in logs

### Pitfall 2: Attachment Path Issues

**What goes wrong:** Can't find attachment files to parse
**Why it happens:** `local_path` may be None, relative paths, missing files
**How to avoid:**
- Validate `local_path` exists before parsing
- Use absolute paths for attachments directory
- Handle missing files gracefully (skip, don't error)
**Warning signs:** FileNotFoundError, empty attachment content

### Pitfall 3: Context Window Overflow

**What goes wrong:** Thread summaries or replies truncated or rejected
**Why it happens:** Too much email history sent to LLM
**How to avoid:**
- Limit thread context to recent 10 emails
- Summarize older emails before including
- Use token counting (tiktoken) to check before sending
**Warning signs:** "context_length_exceeded" errors, truncated responses

### Pitfall 4: Incomplete Thread Reconstruction

**What goes wrong:** Missing emails in thread timeline
**Why it happens:** Some email clients don't set proper `In-Reply-To` or `References` headers
**How to avoid:**
- Fall back to subject matching for suspected threads
- Include sender/recipient correspondence (THREAD-03)
- Allow manual thread association
**Warning signs:** Thread jumps, missing replies

### Pitfall 5: PII Leakage to LLM

**What goes wrong:** Sensitive data sent to external LLM API
**Why it happens:** Email bodies contain credentials, personal info
**How to avoid:**
- Warn users about LLM usage in documentation
- Consider local LLM option (Ollama) for privacy
- Allow LLM features to be disabled via config
**Warning signs:** API keys, passwords in LLM prompts

## Code Examples

### Thread Summary Generation

```python
# Source: Project pattern for LLM integration
def generate_thread_summary(
    llm_client: LLMClient,
    timeline: list[dict],
    current_email: dict,
) -> str:
    """Generate summary of email thread for context."""
    if len(timeline) <= 1:
        return ""

    # Build thread context
    thread_text = []
    for email in timeline:
        if email["message_id"] == current_email["message_id"]:
            continue  # Skip current email
        thread_text.append(
            f"From: {email.get('sender', 'Unknown')}\n"
            f"Date: {email.get('date', 'Unknown')}\n"
            f"Subject: {email.get('subject', 'No Subject')}\n"
            f"Preview: {(email.get('body_text') or '')[:200]}...\n"
        )

    prompt = f"""Summarize this email thread in 2-3 sentences:

{'---'.join(thread_text)}

Summary:"""

    response = llm_client.chat(
        [{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
    )
    return response.content
```

### Attachment Content Extraction

```python
# Source: PyMuPDF documentation patterns
from pathlib import Path


def extract_attachment_content(file_path: Path) -> str:
    """Extract text content from various attachment types."""
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        import fitz
        doc = fitz.open(file_path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text

    elif suffix in (".xlsx", ".xls"):
        from openpyxl import load_workbook
        wb = load_workbook(file_path, read_only=True, data_only=True)
        text_parts = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                row_text = " | ".join(str(cell) if cell else "" for cell in row)
                if row_text.strip():
                    text_parts.append(row_text)
        wb.close()
        return "\n".join(text_parts)

    elif suffix == ".pptx":
        from pptx import Presentation
        prs = Presentation(file_path)
        text_parts = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text_parts.append(shape.text)
        return "\n".join(text_parts)

    elif suffix in (".txt", ".md"):
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            return f.read()

    return ""
```

### AI Reply Composition

```python
# Source: Project pattern for reply functionality
SYSTEM_PROMPT = """You are an email assistant helping compose professional replies.
Write concise, clear responses. Match the tone of the original email.
Always end with a professional closing."""

def compose_ai_reply(
    llm_client: LLMClient,
    original_email: dict,
    thread_context: list[dict] | None = None,
    user_intent: str | None = None,
) -> str:
    """Compose AI-suggested reply for an email."""
    # Build context
    context = f"""Original Email:
From: {original_email.get('sender', 'Unknown')}
Subject: {original_email.get('subject', 'No Subject')}
Date: {original_email.get('date', 'Unknown')}
Body:
{original_email.get('body_text', '')[:1000]}
"""
    if thread_context:
        thread_summary = generate_thread_summary(llm_client, thread_context, original_email)
        if thread_summary:
            context = f"Thread Context:\n{thread_summary}\n\n{context}"

    user_message = "Please compose a reply to this email."
    if user_intent:
        user_message = f"Please compose a reply with this intent: {user_intent}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context},
        {"role": "user", "content": user_message},
    ]

    response = llm_client.chat(messages, temperature=0.7, max_tokens=500)
    return response.content
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual reply composition | AI-assisted with context | 2024+ | Faster, more professional |
| Attachment as binary blobs | Parse and index content | 2023+ | Searchable attachments |
| Simple thread list | Timeline with summaries | 2024+ | Better context understanding |
| Single LLM provider | Multi-provider with fallback | 2025+ | Reliability, cost optimization |

**Deprecated/outdated:**
- Tesseract OCR for images: Use vision APIs (OpenAI GPT-4o Vision) for better accuracy
- Simple keyword-based threading: Use References/In-Reply-To headers + sender matching

## Open Questions

1. **Which LLM provider for image parsing (ATTACH-AI-02)?**
   - What we know: OpenAI SDK supports Vision API; already using OpenAI for embeddings
   - What's unclear: Cost implications, quality comparison with alternatives
   - Recommendation: Start with OpenAI GPT-4o-mini Vision; monitor costs; consider local models (LLaVA via Ollama) as fallback

2. **Feedback storage strategy for REPLY-AI-03?**
   - What we know: SQLite available, ChromaDB for vector search
   - What's unclear: How much feedback to store, retrieval strategy for few-shot
   - Recommendation: Store last 50 positive examples in SQLite; retrieve similar by sender/topic for few-shot prompts

3. **Rate limiting for LLM calls?**
   - What we know: OpenAI has rate limits; CLI is single-user
   - What's unclear: Should we implement queuing?
   - Recommendation: Simple timeout + error message for now; add queuing if needed

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest with pytest-mock |
| Config file | pyproject.toml (pytest.ini_options) |
| Quick run command | `pytest tests/test_{module}.py -v -x` |
| Full suite command | `pytest --cov=scripts --cov-report=term-missing` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| THREAD-01 | Auto-retrieve related correspondence | unit | `pytest tests/test_thread_manager.py::test_get_enhanced_timeline -x` | Wave 0 |
| THREAD-02 | Timeline view full/summary display | unit | `pytest tests/test_thread_manager.py::test_format_thread_view -x` | Wave 0 |
| THREAD-03 | Show sent/received in thread | integration | `pytest tests/test_thread_manager.py::test_sender_recipient_matching -x` | Wave 0 |
| ATTACH-AI-01 | Parse Excel/doc/PPT/PDF/txt/md | unit | `pytest tests/test_attachment_parser.py -x` | Wave 0 |
| ATTACH-AI-02 | Parse images with vision | unit | `pytest tests/test_attachment_parser.py::test_image_parser -x` | Wave 0 |
| REPLY-AI-01 | AI-polished reply composition | unit | `pytest tests/test_reply_assistant.py::test_compose_reply -x` | Wave 0 |
| REPLY-AI-02 | User confirmation before send | integration | `pytest tests/test_cli.py::test_reply_with_confirmation -x` | Wave 0 |
| REPLY-AI-03 | Learn from feedback history | unit | `pytest tests/test_reply_assistant.py::test_feedback_learning -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_{module}.py -v --cov=scripts/mail_manager/{module}`
- **Per wave merge:** `pytest --cov=scripts --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_thread_manager.py` - covers THREAD-01, THREAD-02, THREAD-03
- [ ] `tests/test_attachment_parser.py` - covers ATTACH-AI-01, ATTACH-AI-02
- [ ] `tests/test_reply_assistant.py` - covers REPLY-AI-01, REPLY-AI-03
- [ ] `tests/test_llm_client.py` - covers LLM integration mocking
- [ ] `conftest.py` extension - fixtures for mock LLM responses, sample attachments
- [ ] Framework install: `pip install pytest-mock` - for mock patching

### Mock Strategies

**LLM API Mocking:**
```python
# In conftest.py
@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing without real API calls."""
    with patch("openai.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock chat completion
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Mocked AI response"
        mock_response.model = "gpt-4o-mini"
        mock_response.usage = MagicMock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        mock_response.choices[0].finish_reason = "stop"
        mock_client.chat.completions.create.return_value = mock_response

        yield mock_client
```

**Document Parser Mocking:**
```python
# In conftest.py
@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a sample PDF file for testing."""
    # Use existing test files or create minimal ones
    pdf_path = tmp_path / "test.pdf"
    # Create minimal PDF (or use fixture from test resources)
    return pdf_path

@pytest.fixture
def mock_pymupdf():
    """Mock PyMuPDF for unit tests."""
    with patch("fitz.open") as mock_open:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Sample PDF content"
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.close = MagicMock()
        mock_open.return_value = mock_doc
        yield mock_open
```

## Sources

### Primary (HIGH confidence)

- Project codebase analysis: `scripts/mail_manager/db.py`, `scripts/mail_manager/detail.py`, `scripts/mail_manager/client.py`
- Installed packages verification: `pip show openai PyMuPDF openpyxl python-pptx`
- Existing test infrastructure: `tests/conftest.py`, `pyproject.toml`

### Secondary (MEDIUM confidence)

- OpenAI Python SDK documentation patterns (from training knowledge, verified via pip show)
- PyMuPDF API patterns (from training knowledge, verified via pip show)
- RFC 5256 email threading (standard, well-documented)

### Tertiary (LOW confidence)

- Vision API best practices - need to verify with actual API documentation
- Feedback learning optimal strategies - experimental, may need iteration

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All packages already installed, familiar patterns
- Architecture: HIGH - Building on existing patterns (db.py, detail.py, templates.py)
- Pitfalls: MEDIUM - LLM integration edge cases need real-world testing
- Test strategy: HIGH - Following existing pytest patterns from conftest.py

**Research date:** 2026-04-05
**Valid until:** 30 days (stable libraries, may need refresh for LLM API changes)
