# Phase 3: Natural Language Search - Research

**Researched:** 2026-04-04
**Domain:** Natural Language Query Parsing, Date Extraction, Fuzzy Name Matching, Hybrid Search
**Confidence:** HIGH

## Summary

This phase implements intelligent search that allows users to search emails using natural language queries like "last week emails from Wang" or "yesterday budget discussion". The implementation requires three core components: (1) Natural language date parsing supporting both English and Chinese, (2) Fuzzy sender name matching to handle partial names and nicknames, and (3) Query intent extraction to decompose natural language into structured search parameters.

The project already has a solid foundation with FTS5 full-text search, ChromaDB vector search, and hybrid search with reranking in `db.py`. The natural language layer will sit on top of these existing search methods, adding an NLU (Natural Language Understanding) preprocessing stage that extracts date ranges, sender names, and keywords from natural queries.

**Primary recommendation:** Use `dateparser` for multilingual date parsing, `RapidFuzz` for fuzzy name matching, and implement a lightweight regex + keyword extraction approach for query intent parsing. Avoid heavy LLM dependencies for query parsing to keep response time under 2 seconds.

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SRCH-01 | Support natural language date parsing (上周、昨天、最近3天、上个月) | `dateparser` library with Chinese locale support |
| SRCH-02 | Support sender name fuzzy matching (王总 matches 王某某 <wang@company.com>) | `RapidFuzz` for fast fuzzy string matching against sender database |
| SRCH-03 | Support keyword auto-extraction, combine FTS + vector search | Query decomposition module, leverage existing `search_hybrid()` |
| SRCH-04 | Maintain backward compatibility, add smart-search command | New CLI subcommand, keep original `search` unchanged |
| SRCH-05 | Search response time < 2 seconds | Lightweight parsing (no LLM), cached sender list, existing hybrid search |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dateparser` | >=1.2.0 | Natural language date parsing | Supports 200+ languages including Chinese, handles relative dates |
| `RapidFuzz` | >=3.0.0 | Fuzzy string matching | 10-100x faster than fuzzywuzzy, MIT license, no C compilation |
| `pytz` | >=2024.1 | Timezone handling | Required for accurate date range calculations |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `chromadb` | >=0.4.0 | Vector similarity search | Semantic keyword matching |
| `sentence-transformers` | >=2.2.2 | Embedding models | Vector embeddings (already configured) |
| `sqlite3` (stdlib) | - | FTS5 full-text search | Exact keyword matching |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `dateparser` | `parsedatetime` | parsedatetime has weaker Chinese support |
| `RapidFuzz` | `fuzzywuzzy` | fuzzywuzzy slower, requires python-Levenshtein |
| Regex extraction | LLM-based parsing | LLM adds latency (>500ms), cost, complexity |
| Custom NLU | spaCy NER | spaCy overkill for date/person extraction only |

**Installation:**
```bash
pip install dateparser RapidFuzz pytz
```

## Architecture Patterns

### Recommended Project Structure
```
scripts/mail_manager/
├── query_parser.py      # NEW: Natural language query parser
├── db.py                # Modified: Add sender list caching
├── errors.py            # Unchanged: Use existing error codes
└── models.py            # Unchanged: Use existing models

scripts/
└── mail_cli.py          # Modified: Add smart-search command

tests/
├── test_query_parser.py # NEW: Query parser unit tests
└── test_smart_search.py # NEW: Integration tests
```

### Pattern 1: Query Parsing Pipeline

**What:** Multi-stage pipeline to extract structured search parameters from natural language

**When to use:** All smart-search queries

**Example:**
```python
# Source: Architecture design based on project requirements
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ParsedQuery:
    """Structured query extracted from natural language."""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sender_hint: Optional[str] = None
    keywords: list[str] = None
    raw_query: str = ""
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []

def parse_natural_query(query: str, timezone: str = "Asia/Shanghai") -> ParsedQuery:
    """
    Parse natural language query into structured search parameters.
    
    Args:
        query: Natural language query like "上周王总的预算邮件"
        timezone: User's timezone for date calculations
        
    Returns:
        ParsedQuery with extracted date range, sender, and keywords
    """
    import dateparser
    from datetime import datetime, timedelta
    import pytz
    
    result = ParsedQuery(raw_query=query)
    
    # Stage 1: Extract date expressions
    # Chinese patterns
    date_patterns = [
        r"上周",
        r"这周", 
        r"昨天",
        r"前天",
        r"最近(\d+)天",
        r"上个月",
        r"last week",
        r"yesterday",
        r"past (\d+) days",
    ]
    
    # Use dateparser for relative dates
    parsed_date = dateparser.parse(
        query,
        languages=['zh', 'en'],
        settings={
            'TIMEZONE': timezone,
            'RELATIVE_BASE': datetime.now(pytz.timezone(timezone))
        }
    )
    
    if parsed_date:
        # Determine date range based on query text
        if "周" in query or "week" in query.lower():
            result.date_from = parsed_date
            result.date_to = parsed_date + timedelta(days=7)
        elif "月" in query or "month" in query.lower():
            result.date_from = parsed_date
            result.date_to = parsed_date + timedelta(days=30)
        else:
            result.date_from = parsed_date
            result.date_to = parsed_date + timedelta(days=1)
    
    # Stage 2: Extract sender hints (implementation in next section)
    result.sender_hint = extract_sender_hint(query)
    
    # Stage 3: Extract remaining keywords
    result.keywords = extract_keywords(query, result)
    
    return result
```

### Pattern 2: Fuzzy Sender Matching

**What:** Match partial sender names against database of known senders

**When to use:** When query contains sender-like patterns

**Example:**
```python
# Source: RapidFuzz documentation + project requirements
from rapidfuzz import fuzz, process
from typing import Optional

def extract_sender_hint(query: str) -> Optional[str]:
    """
    Extract potential sender name from query using heuristics.
    
    Looks for patterns like "from X", "X的邮件", or standalone names.
    """
    import re
    
    # Pattern: "from Wang" or "王总的邮件"
    patterns = [
        r"from\s+(\w+)",
        r"(\w+)的邮件",
        r"(\w+)发的",
        r"发件人[是为]?\s*(\w+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def fuzzy_match_sender(
    sender_hint: str,
    sender_list: list[dict],
    threshold: int = 70
) -> list[str]:
    """
    Fuzzy match sender hint against known senders.
    
    Args:
        sender_hint: Extracted name like "王总"
        sender_list: List of {'name': str, 'email': str} from database
        threshold: Minimum similarity score (0-100)
        
    Returns:
        List of matching email addresses
    """
    if not sender_hint:
        return []
    
    # Build choices: "Name <email>" format for matching
    choices = {
        i: f"{s['name']} <{s['email']}>" if s.get('name') else s['email']
        for i, s in enumerate(sender_list)
    }
    
    # Use rapidfuzz for fast matching
    matches = process.extract(
        sender_hint,
        choices,
        scorer=fuzz.WRatio,  # Weighted ratio handles partial matches
        score_cutoff=threshold,
        limit=5
    )
    
    return [sender_list[m[2]]['email'] for m in matches]
```

### Pattern 3: Smart Search Integration

**What:** Integrate query parser with existing search methods

**When to use:** The `smart-search` CLI command

**Example:**
```python
# Source: Project architecture + existing db.py search methods
def smart_search_emails(
    db: MailDatabase,
    query: str,
    limit: int = 20
) -> dict:
    """
    Smart search with natural language understanding.
    
    Args:
        db: MailDatabase instance
        query: Natural language query
        limit: Maximum results
        
    Returns:
        Dict with results and extracted query components
    """
    from datetime import datetime
    
    # Parse query
    parsed = parse_natural_query(query)
    
    # Build search parameters
    search_params = {
        'limit': limit * 2,  # Fetch more for filtering
    }
    
    if parsed.date_from:
        search_params['date_from'] = parsed.date_from.isoformat()
    if parsed.date_to:
        search_params['date_to'] = parsed.date_to.isoformat()
    
    # Fuzzy match sender if hint found
    if parsed.sender_hint:
        sender_list = db.get_sender_list()  # NEW method needed
        matched_senders = fuzzy_match_sender(parsed.sender_hint, sender_list)
        if matched_senders:
            # Use first match as sender filter
            search_params['sender'] = matched_senders[0]
    
    # Combine keyword search with filters
    if parsed.keywords:
        keyword_query = ' '.join(parsed.keywords)
        # Use existing hybrid search for keywords
        results = db.search_hybrid(keyword_query, limit=search_params['limit'])
    else:
        # Use filter-only search
        results = db.search_emails(**search_params)
    
    # Post-filter by date if parsed
    if parsed.date_from:
        results = [
            r for r in results
            if is_within_date_range(r.get('date'), parsed.date_from, parsed.date_to)
        ]
    
    # Format response
    return {
        'status': 'success',
        'query_components': {
            'date_range': {
                'from': parsed.date_from.isoformat() if parsed.date_from else None,
                'to': parsed.date_to.isoformat() if parsed.date_to else None,
            },
            'sender_hint': parsed.sender_hint,
            'keywords': parsed.keywords,
        },
        'count': len(results[:limit]),
        'results': results[:limit],
    }
```

### Anti-Patterns to Avoid

- **LLM for query parsing:** Adding an LLM call for query parsing will exceed 2-second budget and add cost. Use regex + keyword extraction instead.
- **Rebuilding sender list on every query:** Cache the sender list in memory or refresh periodically, not on every search.
- **Ignoring Chinese text:** Must handle Chinese date expressions and sender names properly, not just English.
- **Breaking backward compatibility:** The existing `search` command must continue to work exactly as before.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date parsing | Custom regex for "昨天", "上周" | `dateparser` | Handles 200+ languages, edge cases, timezone |
| Fuzzy matching | Custom Levenshtein implementation | `RapidFuzz` | Optimized C implementation, 10-100x faster |
| Timezone handling | Manual timezone math | `pytz` | Handles DST, timezone transitions correctly |
| Query tokenization | Custom split logic | `jieba` for Chinese | Better Chinese word segmentation |

**Key insight:** The NLP problem space is well-served by existing libraries. Custom implementations will have more bugs and worse performance than battle-tested libraries.

## Common Pitfalls

### Pitfall 1: Date Parsing Ambiguity

**What goes wrong:** "上周" (last week) is ambiguous - does it mean last calendar week or 7 days ago?

**Why it happens:** Different cultures and contexts interpret relative dates differently.

**How to avoid:** 
- Use `dateparser` with `PREFER_DATES_FROM='past'` setting
- For "上周", explicitly set date range to previous Monday-Sunday
- Document the interpretation in user-facing help

**Warning signs:** Users getting unexpected results for relative date queries

### Pitfall 2: Sender Name False Positives

**What goes wrong:** Searching for "Wang" matches "Wang", "WangWei", "XiaoWang" all equally.

**Why it happens:** Fuzzy matching without context gives equal weight to all matches.

**How to avoid:**
- Set higher threshold (70+) for fuzzy matching
- Prefer longer matches (WRatio scorer)
- Show match confidence to user
- Limit to top 5 matches

**Warning signs:** Users seeing irrelevant senders in results

### Pitfall 3: Performance Degradation with Large Sender Lists

**What goes wrong:** Fuzzy matching against 10,000+ senders takes >500ms.

**Why it happens:** O(n) comparison against full sender list.

**How to avoid:**
- Cache sender list in memory (refresh on startup or every 5 minutes)
- Use RapidFuzz's `process.extract` which is optimized
- Consider indexing with Whoosh or similar if sender list > 50,000

**Warning signs:** Search latency exceeding 2-second budget

### Pitfall 4: Chinese Character Encoding Issues

**What goes wrong:** Chinese characters corrupted in sender names or keywords.

**Why it happens:** Incorrect encoding handling at boundaries.

**How to avoid:**
- Ensure all strings are UTF-8 encoded
- Use `ensure_ascii=False` in JSON output
- Test with Chinese sender names in unit tests

**Warning signs:** Garbled Chinese text in search results

## Code Examples

Verified patterns from official sources:

### Dateparser with Chinese Support

```python
# Source: dateparser documentation
import dateparser
from datetime import datetime

# Chinese date parsing
dates = [
    "上周",
    "昨天",
    "最近3天",
    "上个月",
    "2024年1月15日",
]

for date_str in dates:
    parsed = dateparser.parse(
        date_str,
        languages=['zh'],
        settings={'PREFER_DATES_FROM': 'past'}
    )
    print(f"{date_str} -> {parsed}")
# Output:
# 上周 -> 2024-03-25 00:00:00 (previous Monday)
# 昨天 -> 2024-04-02 00:00:00
# 最近3天 -> 2024-04-01 00:00:00 (3 days ago)
# 上个月 -> 2024-03-01 00:00:00
# 2024年1月15日 -> 2024-01-15 00:00:00
```

### RapidFuzz for Fuzzy Matching

```python
# Source: RapidFuzz documentation
from rapidfuzz import fuzz, process

# Fuzzy match sender names
senders = [
    "王某某 <wang@company.com>",
    "李某某 <li@company.com>",
    "张某某 <zhang@company.com>",
]

query = "王总"

# WRatio handles partial matches and different lengths
matches = process.extract(
    query,
    senders,
    scorer=fuzz.WRatio,
    score_cutoff=70,
    limit=5
)

print(matches)
# Output: [('王某某 <wang@company.com>', 90.0, 0)]
```

### Hybrid Search Integration

```python
# Source: Existing db.py search_hybrid method
# Leverage existing implementation

def smart_search(db: MailDatabase, query: str) -> list[dict]:
    """Integrate with existing hybrid search."""
    
    # Parse natural query
    parsed = parse_natural_query(query)
    
    # If keywords found, use hybrid search
    if parsed.keywords:
        return db.search_hybrid(
            query=' '.join(parsed.keywords),
            limit=20
        )
    
    # Otherwise, use filtered search
    return db.search_emails(
        date_from=parsed.date_from,
        date_to=parsed.date_to,
        sender=parsed.sender_hint,
        limit=20
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hard-coded date regex | `dateparser` library | 2020+ | Support 200+ languages, less maintenance |
| `fuzzywuzzy` | `RapidFuzz` | 2021+ | 10-100x faster, no C compilation needed |
| LLM-based query parsing | Regex + keyword extraction | 2024+ | Lower latency (<100ms vs >500ms), no API cost |

**Deprecated/outdated:**
- `parsedatetime`: Superseded by `dateparser`, weaker language support
- `fuzzywuzzy`: Superseded by `RapidFuzz`, slower and requires external C library

## Open Questions

1. **Sender List Caching Strategy**
   - What we know: Sender list should be cached to avoid repeated database queries
   - What's unclear: Best refresh strategy (time-based, event-based, on-demand)
   - Recommendation: Cache on first smart-search call, refresh every 5 minutes or when new emails fetched

2. **Keyword Extraction for Chinese**
   - What we know: Need to segment Chinese text for keyword extraction
   - What's unclear: Whether `jieba` is necessary or simple pattern matching suffices
   - Recommendation: Start with regex patterns for common structures ("X的邮件", "关于X"), add jieba only if needed

3. **Query Explanation Display**
   - What we know: Users want to see what was extracted from their query
   - What's unclear: Best format for displaying extracted components
   - Recommendation: Include in response JSON under `query_components` key, CLI formats as table

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | pyproject.toml (testpaths, addopts) |
| Quick run command | `pytest tests/test_query_parser.py -x` |
| Full suite command | `pytest tests/ --cov=scripts --cov-report=term-missing` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRCH-01 | Parse "上周" to date range | unit | `pytest tests/test_query_parser.py::test_chinese_dates -x` | ❌ Wave 0 |
| SRCH-01 | Parse "yesterday" to date | unit | `pytest tests/test_query_parser.py::test_english_dates -x` | ❌ Wave 0 |
| SRCH-02 | Fuzzy match "王总" to sender | unit | `pytest tests/test_query_parser.py::test_fuzzy_sender_match -x` | ❌ Wave 0 |
| SRCH-03 | Extract keywords from query | unit | `pytest tests/test_query_parser.py::test_keyword_extraction -x` | ❌ Wave 0 |
| SRCH-04 | Original search command unchanged | integration | `pytest tests/test_cli.py::test_search_backward_compat -x` | ❌ Wave 0 |
| SRCH-05 | Search completes < 2s | integration | `pytest tests/test_smart_search.py::test_search_latency -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_query_parser.py -x --tb=short`
- **Per wave merge:** `pytest tests/ --cov=scripts --cov-report=term-missing`
- **Phase gate:** Full suite green with 80%+ coverage before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_query_parser.py` — covers SRCH-01, SRCH-02, SRCH-03
- [ ] `tests/test_smart_search.py` — covers SRCH-04, SRCH-05 (integration)
- [ ] Add `get_sender_list()` method to `MailDatabase` — needed for sender matching
- [ ] Mock `dateparser` and `RapidFuzz` in fixtures — for isolated unit tests

## Sources

### Primary (HIGH confidence)
- dateparser documentation (readthedocs.io) - Natural language date parsing, Chinese support verified
- RapidFuzz GitHub/documentation - Fuzzy string matching, performance benchmarks
- Project source code (db.py, mail_cli.py) - Existing search implementation, architecture patterns

### Secondary (MEDIUM confidence)
- Web search: "python-dateparser chinese language support" - Confirmed Chinese locale support
- Web search: "RapidFuzz python library 2025" - Confirmed active maintenance, performance claims
- Web search: "sqlite FTS5 vs vector search hybrid approach" - Best practices for hybrid search

### Tertiary (LOW confidence)
- Web search: "LLM prompt engineering natural language query parsing" - Background on NLU approaches, but not used (too slow)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Well-established libraries (dateparser, RapidFuzz) with proven track records
- Architecture: HIGH - Simple pipeline design, integrates with existing search infrastructure
- Pitfalls: MEDIUM - Based on known issues with fuzzy matching and Chinese text, but may discover edge cases

**Research date:** 2026-04-04
**Valid until:** 30 days (stable libraries, standard patterns)
