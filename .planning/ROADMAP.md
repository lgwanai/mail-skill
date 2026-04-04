# Roadmap: Mail Skill v2.0

## Overview

Transform Mail Skill from a basic email tool into an intelligent assistant. The journey starts with code quality foundations, then delivers attachment preview service, natural language search, smart classification, and finally enhanced user experience features (templates, detail pages, and mark enhancements).

## Phases

- [x] **Phase 1: Code Quality Foundation** - Test coverage, type annotations, unified error handling, lint standards
- [ ] **Phase 2: Attachment Preview Service** - Local HTTP server for secure attachment preview and download
- [ ] **Phase 3: Natural Language Search** - Intent-driven search with date parsing and sender matching
- [ ] **Phase 4: Smart Classification** - Rule-based email importance and category classification
- [ ] **Phase 5: User Experience Enhancement** - Reply templates, detail page optimization, and mark enhancements

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
- [ ] 02-01-PLAN.md — Core server module with security (server.py, test_server.py)
- [ ] 02-02-PLAN.md — CLI integration for attachments command (mail_cli.py, test_cli.py)

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
**Plans**: TBD

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
**Plans**: TBD

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
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Code Quality Foundation | 6/6 | Complete | 01-PLAN, 02-PLAN, 03-PLAN, 04-PLAN, 05-PLAN, 06-PLAN |
| 2. Attachment Preview Service | 0/2 | Planning | - |
| 3. Natural Language Search | 0/TBD | Not started | - |
| 4. Smart Classification | 0/TBD | Not started | - |
| 5. User Experience Enhancement | 0/TBD | Not started | - |
| 6. Smart Enhancements | 0/TBD | Not started | - |

### Phase 6: Smart Enhancements (邮件关联、附件解读、大模型润色)

**Goal**: Enhance email thread visualization, attachment content understanding, and AI-powered reply composition
**Depends on**: Phase 5
**Requirements**: THREAD-01, THREAD-02, THREAD-03, ATTACH-AI-01, ATTACH-AI-02, REPLY-AI-01, REPLY-AI-02, REPLY-AI-03

Features:
1. **邮件关联显示增强**: Fetch one email and auto-retrieve all related correspondence (sent/received) with timeline view - full display for current email, summary for others
2. **附件智能解读**: Parse and summarize Excel, doc, PPT, PDF, txt, md, images for enhanced search indexing
3. **大模型润色回复**: AI-polished email replies with user confirmation, learning from feedback history

**Plans**: TBD

Plans:
- [ ] TBD (run /gsd:plan-phase 6 to break down)

---
*Roadmap created: 2026-04-04*
*Last updated: 2026-04-04 - Phase 2 plans created*
