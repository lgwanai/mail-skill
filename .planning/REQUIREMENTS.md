# Requirements: Mail Skill v2.0

**Defined:** 2026-04-04
**Core Value:** 让邮件管理从"手动操作"变为"意图驱动"

## v1 Requirements

### Code Quality (代码质量)

- [ ] **QUAL-01**: 项目测试覆盖率达到 80%+，关键路径（fetch, search, send, reply）有完整测试
- [ ] **QUAL-02**: 所有 Python 文件添加类型注解，通过 mypy 类型检查
- [x] **QUAL-03**: 统一错误处理格式，所有命令返回标准 JSON 结构 `{"status": "success|error", "code": "...", "message": "..."}`
- [x] **QUAL-04**: 使用 ruff 进行代码格式化和 lint，符合 PEP 8 规范

### Natural Language Search (智能搜索)

- [ ] **SRCH-01**: 支持自然语言日期解析，如"上周"、"昨天"、"最近3天"、"上个月"
- [x] **SRCH-02**: 支持发件人名称模糊匹配，如"王总"匹配"王某某 <wang@company.com>"
- [x] **SRCH-03**: 支持关键词自动提取，组合 FTS + 向量搜索
- [x] **SRCH-04**: 保持向后兼容，原 search 命令行为不变，新增 smart-search 命令
- [x] **SRCH-05**: 搜索响应时间 < 2秒

### Smart Classification (智能分类)

- [x] **CLAS-01**: 数据库新增 importance 字段（critical/high/normal/low）
- [x] **CLAS-02**: 数据库新增 category 字段（work/personal/notification/promo/uncategorized）
- [x] **CLAS-03**: 实现规则优先分类，基于发件人规则、关键词规则
- [ ] **CLAS-04**: 分类结果持久化存储，支持按分类筛选
- [ ] **CLAS-05**: 支持手动重新分类，分类置信度存储

### Attachment Preview Service (附件预览服务)

- [ ] **ATCH-01**: 启动本地 HTTP 服务器，自动寻找空闲端口（8080-8099）
- [ ] **ATCH-02**: 绑定 127.0.0.1，禁止外网访问
- [ ] **ATCH-03**: 生成附件下载链接，支持浏览器直接预览/下载
- [ ] **ATCH-04**: 路径穿越防护，只允许访问 mail_data/attachments 目录
- [ ] **ATCH-05**: 服务器状态持久化，跨命令共享端口信息
- [ ] **ATCH-06**: 新增 attachments 命令，列出附件并生成预览链接

### Reply Templates (回复模板)

- [ ] **TMPL-01**: 支持 YAML 格式定义回复模板，存储在账户目录下
- [ ] **TMPL-02**: 模板支持变量占位符，如 `{{sender_name}}`、`{{date}}`
- [ ] **TMPL-03**: 新增 templates list/show/create 命令
- [ ] **TMPL-04**: reply 命令支持 --template 参数
- [ ] **TMPL-05**: 发送前验证所有必填变量已填充

### Email Detail Enhancement (邮件详情优化)

- [x] **DET-01**: 邮件详情展示优化，支持 Markdown 格式输出
- [x] **DET-02**: 显示完整邮件头信息（发件人、收件人、抄送、时间、主题）
- [x] **DET-03**: 显示分类信息（重要性、类别）
- [x] **DET-04**: 附件列表带预览链接
- [x] **DET-05**: 显示邮件线程上下文（父邮件/回复邮件）

### Mark Enhancement (标记增强)

- [ ] **MARK-01**: 支持批量标记已读/未读（多个 message_id）
- [ ] **MARK-02**: 支持批量标记星标
- [ ] **MARK-03**: 支持按搜索结果批量操作（如"标记所有已读"）
- [ ] **MARK-04**: 新增标签功能，支持自定义标签

## v2 Requirements (Deferred)

### AI-Powered Features

- **AI-01**: LLM 驱动的回复建议
- **AI-02**: 智能跟进提醒（3天未回复提醒）
- **AI-03**: 邮件行动项提取

### Attachment AI Features

- [x] **ATTACH-AI-01**: LLM client infrastructure for AI-powered features
- [x] **ATTACH-AI-02**: Image parsing via vision API with content storage for search

### Analytics

- **ANLT-01**: 邮件统计仪表板（响应时间、邮件量趋势）
- **ANLT-02**: 联系人互动分析

## Out of Scope

| Feature | Reason |
|---------|--------|
| 腾讯 COS 附件存储 | v2.0 仅支持本地服务器模式 |
| 邮件自动化规则 | 复杂度高，易出错 |
| 多语言国际化 | 中文优先 |
| 移动端支持 | CLI/AI Agent 场景 |
| 云同步 | 本地优先，隐私保护 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| QUAL-01 | Phase 1 | Pending |
| QUAL-02 | Phase 1 | Pending |
| QUAL-03 | Phase 1 | Complete |
| QUAL-04 | Phase 1 | Complete |
| ATCH-01 | Phase 2 | Pending |
| ATCH-02 | Phase 2 | Pending |
| ATCH-03 | Phase 2 | Pending |
| ATCH-04 | Phase 2 | Pending |
| ATCH-05 | Phase 2 | Pending |
| ATCH-06 | Phase 2 | Pending |
| SRCH-01 | Phase 3 | Pending |
| SRCH-02 | Phase 3 | Complete |
| SRCH-03 | Phase 3 | Complete |
| SRCH-04 | Phase 3 | Complete |
| SRCH-05 | Phase 3 | Complete |
| CLAS-01 | Phase 4 | Complete |
| CLAS-02 | Phase 4 | Complete |
| CLAS-03 | Phase 4 | Complete |
| CLAS-04 | Phase 4 | Pending |
| CLAS-05 | Phase 4 | Pending |
| TMPL-01 | Phase 5 | Pending |
| TMPL-02 | Phase 5 | Pending |
| TMPL-03 | Phase 5 | Pending |
| TMPL-04 | Phase 5 | Pending |
| TMPL-05 | Phase 5 | Pending |
| DET-01 | Phase 5 | Complete |
| DET-02 | Phase 5 | Complete |
| DET-03 | Phase 5 | Complete |
| DET-04 | Phase 5 | Complete |
| DET-05 | Phase 5 | Complete |
| MARK-01 | Phase 5 | Pending |
| MARK-02 | Phase 5 | Pending |
| MARK-03 | Phase 5 | Pending |
| MARK-04 | Phase 5 | Pending |
| ATTACH-AI-01 | Phase 6 | Complete |
| ATTACH-AI-02 | Phase 6 | Complete |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 - CLAS-01, CLAS-02 complete*
