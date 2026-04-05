# Roadmap: Mail Skill v2.0

## Overview

Transform Mail Skill from a basic email tool into an intelligent assistant. The journey starts with code quality foundations, then delivers attachment preview service, natural language search, smart classification, and finally enhanced user experience features (templates, detail pages, and mark enhancements).

## Phases

- [x] **Phase 1: Code Quality Foundation** - Test coverage, type annotations, unified error handling, lint standards
- [x] **Phase 2: Attachment Preview Service** - Local HTTP server for secure attachment preview and download
- [x] **Phase 3: Natural Language Search** - Intent-driven search with date parsing and sender matching
- [x] **Phase 4: Smart Classification** - Rule-based email importance and category classification
- [x] **Phase 5: User Experience Enhancement** - Reply templates, detail page optimization, and mark enhancements
- [ ] **Phase 6: Smart Enhancements** - Thread visualization, attachment AI, LLM-powered replies

## Phase Details

### Phase 1: Code Quality Foundation
**Goal**: Establish solid engineering practices that enable safe iteration
**Depends on**: Nothing (first phase)
**Requirements**: QUAL-01, QUAL-02, QUAL-03, QUAL-04
**Success Criteria** (what must be TRUE):
  1. User can run the full test suite and see 80%+ coverage report
  2. User can run mypy and see zero type errors
  3. User can run ruff and see all code passes lint checks
  4. All CLI commands return consistent JSON error structures when failing
**Plans**: 6 plans in 4 waves

Plans:
- [x] 01-PLAN.md — Create foundational config files (pyproject.toml, requirements-dev.txt, errors.py, models.py)
- [x] 02-PLAN.md — Create test infrastructure with shared fixtures (conftest.py)
- [x] 03-PLAN.md — Add type annotations and tests for MailClient (client.py, test_client.py)
- [x] 04-PLAN.md — Add type annotations and tests for MailDatabase (db.py, test_db.py)
- [x] 05-PLAN.md — Migrate CLI to unified error handling and add CLI tests (mail_cli.py, test_cli.py, test_errors.py)
- [x] 06-PLAN.md — Apply ruff formatting/linting and verify coverage baseline

### Phase 2: Attachment Preview Service
**Goal**: Users can preview and download email attachments via browser
**Depends on**: Phase 1
**Requirements**: ATCH-01, ATCH-02, ATCH-03, ATCH-04, ATCH-05, ATCH-06
**Success Criteria** (what must be TRUE):
  1. User can run `attachments` command and see list of attachments with preview links
  2. User can click a preview link and download the attachment in browser
  3. Attachment server only accepts localhost connections (security verified)
  4. User cannot access files outside the attachments directory (path traversal blocked)
  5. Server port persists across commands without conflicts
**Plans**: 2 plans in 2 waves

Plans:
- [x] 02-01-PLAN.md — Core server module with security (server.py, test_server.py)
- [x] 02-02-PLAN.md — CLI integration for attachments command (mail_cli.py, test_cli.py)

### Phase 3: Natural Language Search
**Goal**: Users can search emails using natural language queries instead of structured filters
**Depends on**: Phase 2
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05
**Success Criteria** (what must be TRUE):
  1. User can search "last week emails from Wang" and get correct results
  2. User can search "yesterday budget discussion" and get relevant matches
  3. Original `search` command behavior remains unchanged (backward compatibility)
  4. Natural language search completes within 2 seconds
  5. User can see which query components were extracted (date, sender, keywords)
**Plans**: 4 plans in 4 waves

Plans:
- [x] 03-00-PLAN.md — Test stubs and empty modules for TDD foundation (Wave 0)
- [x] 03-01-PLAN.md — Date parser module for Chinese date expressions (date_parser.py, test_date_parser.py)
- [ ] 03-02-PLAN.md — Query parser with sender matching and keyword extraction (query_parser.py, test_query_parser.py)
- [ ] 03-03-PLAN.md — CLI integration for smart-search command (mail_cli.py, test_cli.py)

### Phase 4: Smart Classification
**Goal**: Emails are automatically categorized by importance and type
**Depends on**: Phase 3
**Requirements**: CLAS-01, CLAS-02, CLAS-03, CLAS-04, CLAS-05
**Success Criteria** (what must be TRUE):
  1. User can see importance level (critical/high/normal/low) on each email
  2. User can see category (work/personal/notification/promo) on each email
  3. User can filter emails by importance or category
  4. User can manually reclassify an email and see the change persist
  5. User can see classification confidence score
**Plans**: 4 plans in 4 waves

Plans:
- [x] 04-00-PLAN.md — Test stubs and empty modules for TDD foundation (Wave 0)
- [x] 04-01-PLAN.md — Database schema extension with classification columns and rule loading (db.py, rules.py, classifier.py)
- [ ] 04-02-PLAN.md — EmailClassifier implementation with rule matching and confidence scoring (classifier.py, test_classifier.py)
- [ ] 04-03-PLAN.md — CLI integration for classification display, filtering, and reclassification (mail_cli.py, test_cli.py)

### Phase 5: User Experience Enhancement
**Goal**: Users have efficient tools for reply, viewing, and batch operations
**Depends on**: Phase 4
**Requirements**: TMPL-01, TMPL-02, TMPL-03, TMPL-04, TMPL-05, DET-01, DET-02, DET-03, DET-04, DET-05, MARK-01, MARK-02, MARK-03, MARK-04
**Success Criteria** (what must be TRUE):
  1. User can list available reply templates and apply one to a reply
  2. User can see beautifully formatted email details with full headers and thread context
  3. User can see attachments with preview links in email detail view
  4. User can batch mark multiple emails as read/unread or starred
  5. User can add custom tags to emails
**Plans**: 6 plans in 3 waves

Plans:
- [x] 05-00-PLAN.md — Test stubs for templates, detail, and batch mark modules (Wave 0)
- [x] 05-01-PLAN.md — YAML templates with variable placeholders and validation (TMPL-01, TMPL-02, TMPL-05)
- [x] 05-02-PLAN.md — Enhanced email detail formatting with Markdown, headers, classification, attachments (DET-01~05)
- [x] 05-03-PLAN.md — Batch operations and custom tags in database layer (MARK-01, MARK-02, MARK-04)
- [x] 05-04-PLAN.md — CLI integration for templates and enhanced detail view (TMPL-03, TMPL-04)
- [x] 05-05-PLAN.md — CLI integration for batch mark and tag commands (MARK-01, MARK-02, MARK-03)

### Phase 6: Smart Enhancements
**Goal**: Enhance email thread visualization, attachment content understanding, and AI-powered reply composition
**Depends on**: Phase 5
**Requirements**: THREAD-01, THREAD-02, THREAD-03, ATTACH-AI-01, ATTACH-AI-02, REPLY-AI-01, REPLY-AI-02, REPLY-AI-03

**Success Criteria** (what must be TRUE):
  1. User can fetch one email and see all related correspondence (sent/received) in timeline view
  2. User can see full detail for current email and summary for other emails in thread
  3. User can parse attachments (PDF, Excel, PowerPoint, images) and see extracted content
  4. User can request AI-generated reply suggestions with thread context
  5. User confirms or edits AI reply before sending
  6. AI learns from user feedback to improve future suggestions

**Plans**: 7 plans in 5 waves

Plans:
- [ ] 06-00-PLAN.md — Test stubs for LLM client, thread manager, attachment parser, reply assistant (Wave 0)
- [ ] 06-01-PLAN.md — LLM client abstraction with OpenAI SDK wrapper (THREAD-02, ATTACH-AI-02, REPLY-AI-01)
- [ ] 06-02-PLAN.md — Document parsers for PDF, Excel, PowerPoint, text (ATTACH-AI-01)
- [ ] 06-03-PLAN.md — Image parser with vision API and attachment content storage (ATTACH-AI-02)
- [ ] 06-04-PLAN.md — Enhanced thread management with sender matching and timeline view (THREAD-01, THREAD-02, THREAD-03)
- [ ] 06-05-PLAN.md — AI reply composition with feedback learning (REPLY-AI-01, REPLY-AI-03)
- [ ] 06-06-PLAN.md — CLI integration for parse-attachments, read --thread, ai-reply (ATTACH-AI-01, ATTACH-AI-02, REPLY-AI-02)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Code Quality Foundation | 6/6 | Complete | 01-PLAN, 02-PLAN, 03-PLAN, 04-PLAN, 05-PLAN, 06-PLAN |
| 2. Attachment Preview Service | 2/2 | Complete | 02-01-PLAN, 02-02-PLAN |
| 3. Natural Language Search | 3/4 | In Progress|  |
| 4. Smart Classification | 2/4 | In Progress | 04-00-PLAN, 04-01-PLAN |
| 5. User Experience Enhancement | 6/6 | Complete | 05-00-PLAN, 05-01-PLAN, 05-02-PLAN, 05-03-PLAN, 05-04-PLAN, 05-05-PLAN |
| 6. Smart Enhancements | 0/7 | Not started | - |

---
*Roadmap created: 2026-04-04*
*Last updated: 2026-04-05 - Phase 6 plans created*
