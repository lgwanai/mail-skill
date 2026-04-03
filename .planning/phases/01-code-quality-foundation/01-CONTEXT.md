# Phase 1: Code Quality Foundation - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

建立代码质量基础设施：测试覆盖、类型注解、统一错误处理、代码规范。这是后续功能迭代的保障层，不涉及用户可见功能。

**Scope:**
- QUAL-01: 测试覆盖率 80%+
- QUAL-02: 类型注解 + mypy
- QUAL-03: 统一错误处理格式
- QUAL-04: ruff 格式化和 lint

</domain>

<decisions>
## Implementation Decisions

### 测试策略

- **覆盖顺序**: 关键路径优先 → fetch, search, send, reply 先覆盖
- **测试类型**: 单元测试为主，集成测试后续补充
- **Mock 策略**: Mock 外部依赖（IMAP/SMTP/数据库），保证测试速度
- **覆盖率目标**: 核心模块 80%+，其他模块 60%+

### 类型注解策略

- **添加顺序**: 核心模块优先 → client.py, db.py 先加，再 CLI
- **数据结构**: 使用 `dataclass + typing`，Python 原生方案，无额外依赖
- **mypy 严格度**: 宽松模式，允许部分 `Any` 和 `# type: ignore`，渐进式改进

### 错误码设计

- **格式**: 大写下划线 → `EMAIL_NOT_FOUND`, `IMAP_CONNECTION_FAILED`
- **分类**: 按来源分类
  - `USER_xxx` - 客户端错误（参数错误、资源不存在）
  - `SERVER_xxx` - 服务端错误（IMAP/SMTP 连接失败）
  - `BIZ_xxx` - 业务错误（权限不足、状态冲突）
- **响应结构**: 简洁统一
  ```json
  {
    "status": "error",
    "code": "EMAIL_NOT_FOUND",
    "message": "Email with message_id 'xxx' not found"
  }
  ```
- **迁移策略**: 全量迁移，一次性修改所有命令

### Linter 配置

- **规则集**: PEP 8 标准，不引入争议性规则
- **触发时机**: 保存时自动格式化
- **配置位置**: `pyproject.toml`

### Claude's Discretion

- 具体测试用例设计
- 类型注解的具体写法（可选类型 vs Union）
- 错误码的具体命名（在分类框架内自由发挥）

</decisions>

<specifics>
## Specific Ideas

- "先加固代码质量再添加新功能" — 项目级决策，测试覆盖是功能迭代的保障
- 用户倾向于务实的目标（核心 80%，其他 60%），而非理想化的全量 80%

</specifics>

<code_context>
## Existing Code Insights

### 当前代码结构
- `scripts/mail_cli.py` - CLI 入口，约 1000 行，包含所有命令处理
- `scripts/mail_manager/client.py` - MailClient 类，IMAP/SMTP 操作
- `scripts/mail_manager/db.py` - MailDatabase 类，SQLite + ChromaDB 操作

### 现有错误处理模式
- 混用 JSON 错误 `{"status": "error", "message": "..."}` 和异常抛出
- 需要统一为标准 JSON 结构

### 测试现状
- 当前无任何测试文件
- 需要新建 `tests/` 目录结构

### 类型注解现状
- 当前无类型注解
- 需要从零开始添加

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-code-quality-foundation*
*Context gathered: 2026-04-04*
