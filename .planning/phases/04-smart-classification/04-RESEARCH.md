# Phase 4: Smart Classification - Research

**Researched:** 2026-04-04
**Domain:** Email classification system with importance and category labeling
**Confidence:** HIGH

## Summary

This phase implements automatic email classification with importance levels (critical/high/normal/low) and categories (work/personal/notification/promo). The research shows that a **rule-based approach** is optimal for this phase - it's deterministic, fast, requires no training data, and integrates cleanly with the existing architecture. The existing `cmd_summarize()` function already demonstrates keyword-based categorization patterns that can be extended into a persistent classification system.

**Primary recommendation:** Build a rule-based classifier using YAML configuration for sender rules and keyword rules, with confidence scores derived from rule match counts and specificity. Store classifications in new SQLite columns with indexes for filtering.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| YAML (stdlib via PyYAML) | >=6.0 | Classification rules configuration | Human-readable, editable by users |
| dataclasses (stdlib) | Python 3.8+ | Classification result structure | Type-safe, no dependencies |
| re (stdlib) | Python 3.8+ | Pattern matching for keywords | Already used throughout codebase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite3 (stdlib) | Python 3.8+ | Persistent classification storage | All classification operations |
| CrossEncoder (existing) | bge-reranker-base | Semantic importance scoring | Optional: when keyword rules insufficient |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Rule-based classifier | ML classifier (sklearn/transformers) | ML requires training data, adds latency, overkill for 4 categories |
| SQLite storage | ChromaDB metadata | SQLite already stores email data; simpler querying |
| Fixed taxonomy | User-defined labels | Fixed taxonomy prevents label drift; user feedback via reclassification |

**Installation:**
```bash
# No new dependencies required - all stdlib or existing
# PyYAML already used for configuration in other projects
pip install pyyaml>=6.0  # If not already installed
```

## Architecture Patterns

### Recommended Project Structure
```
scripts/mail_manager/
├── classifier.py        # NEW: EmailClassifier class
├── rules.py            # NEW: Rule definitions and loader
├── db.py               # EXTENDED: Add classification columns
├── models.py           # EXTENDED: Add Classification dataclass
└── mail_cli.py         # EXTENDED: Add classify commands

config/
└── classification_rules.yaml  # NEW: User-editable rules

mail_data/{account}/
└── classification_rules.yaml  # OPTIONAL: Account-specific rules override
```

### Pattern 1: Rule-Based Classification with Confidence

**What:** Multi-stage rule matching with confidence aggregation
**When to use:** All email classification
**Example:**
```python
# Source: Based on existing cmd_summarize() keyword pattern
@dataclass
class Classification:
    importance: str      # "critical", "high", "normal", "low"
    category: str        # "work", "personal", "notification", "promo"
    confidence: float    # 0.0 to 1.0
    matched_rules: list[str]  # Which rules matched

@dataclass
class Rule:
    name: str
    rule_type: str       # "sender", "keyword", "pattern"
    patterns: list[str]
    importance: str | None
    category: str | None
    weight: float = 1.0  # Rule weight for confidence

class EmailClassifier:
    def __init__(self, rules_path: str | None = None):
        self.rules = self._load_rules(rules_path)

    def classify(self, email: dict) -> Classification:
        matches = []
        for rule in self.rules:
            if self._match_rule(rule, email):
                matches.append(rule)

        if not matches:
            return Classification("normal", "uncategorized", 0.5, [])

        # Aggregate by weighted voting
        importance_scores = defaultdict(float)
        category_scores = defaultdict(float)

        for rule in matches:
            if rule.importance:
                importance_scores[rule.importance] += rule.weight
            if rule.category:
                category_scores[rule.category] += rule.weight

        importance = max(importance_scores, key=importance_scores.get)
        category = max(category_scores, key=category_scores.get)
        confidence = min(1.0, sum(r.weight for r in matches) / len(self.rules))

        return Classification(importance, category, confidence, [r.name for r in matches])
```

### Pattern 2: Classification Rules Configuration

**What:** YAML-based rule configuration for user customization
**When to use:** All classification rule storage
**Example:**
```yaml
# config/classification_rules.yaml
rules:
  # Critical importance senders
  - name: "Critical Senders - Management"
    type: sender
    patterns:
      - "boss@company.com"
      - "ceo@company.com"
      - "hr@company.com"
    importance: critical
    weight: 2.0

  # High importance keywords
  - name: "Urgent Keywords"
    type: keyword
    patterns:
      - "紧急"
      - "urgent"
      - "重要"
      - "important"
      - "asap"
    importance: high
    weight: 1.5

  # Verification codes category
  - name: "Verification Codes"
    type: keyword
    patterns:
      - "验证码"
      - "verification code"
      - "安全码"
      - "activation code"
    category: notification
    importance: high
    weight: 2.0

  # Promotional emails
  - name: "Promotional Keywords"
    type: keyword
    patterns:
      - "促销"
      - "优惠"
      - "unsubscribe"
      - "退订"
      - "newsletter"
    category: promo
    importance: low
    weight: 1.0

  # Work domain senders
  - name: "Work Domain"
    type: sender_pattern
    patterns:
      - "@company.com$"
      - "@internal.company.com$"
    category: work
    weight: 1.0
```

### Pattern 3: Database Schema Extension

**What:** Add classification columns with indexes
**When to use:** Persistent classification storage
**Example:**
```sql
-- Add to _init_db() in db.py
ALTER TABLE emails ADD COLUMN importance TEXT DEFAULT 'normal';
ALTER TABLE emails ADD COLUMN category TEXT DEFAULT 'uncategorized';
ALTER TABLE emails ADD COLUMN classification_confidence REAL DEFAULT 0.0;
ALTER TABLE emails ADD COLUMN manual_override BOOLEAN DEFAULT 0;

-- Indexes for filtering
CREATE INDEX IF NOT EXISTS idx_importance ON emails(importance);
CREATE INDEX IF NOT EXISTS idx_category ON emails(category);
CREATE INDEX IF NOT EXISTS idx_classification_confidence ON emails(classification_confidence);
```

### Anti-Patterns to Avoid
- **LLM-first classification:** Requiring LLM for every classification adds latency and cost. Use rule-based first, LLM only for uncertain cases.
- **No confidence tracking:** Users need to know when classification is uncertain. Always store and display confidence.
- **Immutable classifications:** Users must be able to correct mistakes. Store manual overrides separately.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rule matching | Custom regex engine | Python re module + YAML config | Standard, well-tested, user-editable |
| Confidence scoring | Complex ML scoring | Weighted vote from matched rules | Simple, explainable, sufficient |
| Category taxonomy | Dynamic label system | Fixed 4-category enum | Prevents label drift, simpler UX |
| Rule storage | Database tables | YAML file in config/ | User-editable, version-controllable |

**Key insight:** The existing `cmd_summarize()` demonstrates keyword-based categorization works well. Extending this pattern with persistence and confidence scoring provides value without ML complexity.

## Common Pitfalls

### Pitfall 1: Classification Label Drift
**What goes wrong:** Auto-classification labels become inconsistent, duplicated, or abandoned over time.
**Why it happens:** No canonical label taxonomy defined, confidence thresholds too low, no human feedback loop.
**How to avoid:** Fixed 4-category taxonomy (work/personal/notification/promo), confidence thresholds with "uncertain" bucket (confidence < 0.5), manual reclassification updates classifier rules.
**Warning signs:** Users manually reclassifying many emails, labels with very few emails, labels with most emails.

### Pitfall 2: Classification Not Persisted
**What goes wrong:** Computing classification on-the-fly without storing, causing slow repeated queries.
**Why it happens:** Implementing classification as display-only feature without database integration.
**How to avoid:** Store in SQLite with indexes, classify on fetch, reclassify on demand.
**Warning signs:** Search by category is slow, classification changes between views.

### Pitfall 3: No Manual Override Mechanism
**What goes wrong:** Users cannot correct wrong classifications, losing trust in the feature.
**Why it happens:** Classification implemented as write-only, no update path.
**How to avoid:** Add `manual_override` boolean column, add `reclassify` command, store override history.
**Warning signs:** Users complaining about wrong classifications, feature ignored entirely.

### Pitfall 4: Over-classification
**What goes wrong:** Every email forced into a category, even when inappropriate.
**Why it happens:** No "uncategorized" default, confidence threshold too low.
**How to avoid:** Default category "uncategorized", require minimum confidence (e.g., 0.3) for category assignment.
**Warning signs:** Many emails in wrong categories, users ignoring category filters.

## Code Examples

Verified patterns from existing codebase:

### Existing Keyword Pattern (cmd_summarize)
```python
# Source: scripts/mail_cli.py lines 1143-1147
important_keywords = [
    "重要", "紧急", "urgent", "important", "通知", "账单", "合同", "面试", "offer"
]
verification_keywords = ["验证码", "activation code", "verify", "code", "安全码"]
action_keywords = ["回复", "确认", "请查收", "跟进", "action required", "please reply"]

for email in emails:
    subject = email.get("subject", "").lower()
    body = email.get("body_text", "").lower()
    if any(kw in subject or kw in body[:500] for kw in verification_keywords):
        # Classify as verification
```

### Database Update Pattern
```python
# Source: scripts/mail_manager/db.py lines 637-682
def update_flags(
    self,
    message_id: str,
    is_read: bool | None = None,
    is_starred: bool | None = None,
    labels: list | None = None,
    folder: str | None = None,
) -> None:
    updates: list[str] = []
    params: list[Any] = []

    if is_read is not None:
        updates.append("is_read = ?")
        params.append(is_read)
    # ... similar for other fields

    sql = f"UPDATE emails SET {', '.join(updates)} WHERE message_id = ?"
    params.append(message_id)

    with self._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
```

### Dataclass Pattern for Results
```python
# Source: scripts/mail_manager/models.py lines 14-23
@dataclass
class Attachment:
    filename: str
    content_type: str
    size: int
    local_path: str | None = None

@dataclass
class EmailData:
    message_id: str
    subject: str
    # ... other fields
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ML-only classification | Rule-based with optional ML | Pragmatic: no training data needed | Faster, more predictable, user-configurable |
| Dynamic labels | Fixed taxonomy | Research finding: prevents drift | Simpler UX, better filter reliability |
| One-time classification | Persistent with manual override | User feedback requirement | Trust through correction capability |

**Deprecated/outdated:**
- spam/ham binary classification: Not relevant for importance/category split
- Training-based classifiers: Overkill for 4 categories with clear rules

## Open Questions

1. **Should classification happen on fetch or on-demand?**
   - What we know: Classifying on fetch is faster for filtering later
   - What's unclear: Performance impact during batch fetch
   - Recommendation: Classify on fetch with async option for large batches

2. **Should confidence scores be normalized across rule counts?**
   - What we know: More matched rules should increase confidence
   - What's unclear: Optimal normalization formula
   - Recommendation: Use weighted sum normalized by total rule weights (0-1 scale)

3. **Should user corrections update global or account-specific rules?**
   - What we know: Account-specific rules already supported in architecture
   - What's unclear: User preference for scope
   - Recommendation: Start with account-specific, add global option in Phase 5

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml |
| Quick run command | `pytest tests/test_classifier.py -x -v` |
| Full suite command | `pytest --cov=scripts --cov-report=term-missing` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLAS-01 | Database has importance field with 4 levels | unit | `pytest tests/test_db.py::test_classification_columns -x` | No - Wave 0 |
| CLAS-02 | Database has category field with 5 values | unit | `pytest tests/test_db.py::test_category_columns -x` | No - Wave 0 |
| CLAS-03 | Rule-based classification matches sender/keyword | unit | `pytest tests/test_classifier.py::test_keyword_rule_match -x` | No - Wave 0 |
| CLAS-04 | Classification persists and filters work | integration | `pytest tests/test_db.py::test_search_by_classification -x` | No - Wave 0 |
| CLAS-05 | Manual reclassification persists with confidence | unit | `pytest tests/test_classifier.py::test_manual_reclassify -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_classifier.py -x`
- **Per wave merge:** `pytest --cov=scripts --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_classifier.py` - unit tests for EmailClassifier class
- [ ] `tests/test_db.py` extended - classification column tests
- [ ] `scripts/mail_manager/classifier.py` - empty module for TDD
- [ ] `scripts/mail_manager/rules.py` - empty module for TDD
- [ ] `config/classification_rules.yaml` - default rules file

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis (db.py, mail_cli.py, query_parser.py)
- Project architecture research (ARCHITECTURE.md, STACK.md)
- Pitfall analysis (PITFALLS.md)

### Secondary (MEDIUM confidence)
- Training knowledge of rule-based classification patterns
- Python dataclass and YAML best practices

### Tertiary (LOW confidence)
- None - all recommendations based on codebase analysis

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib or existing dependencies
- Architecture: HIGH - Extends proven patterns from existing code
- Pitfalls: HIGH - Documented in existing PITFALLS.md

**Research date:** 2026-04-04
**Valid until:** 30 days (stable domain)
