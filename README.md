# Mail Skill 📧

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Test Coverage](https://img.shields.io/badge/coverage-75%25-green.svg)]()

**Mail Skill** 是一个专门为 AI 智能体（如 Claude Code、Trae 等）设计的强大邮件管理技能。它让 AI 能够像专业秘书一样帮你处理邮件——收发、搜索、分类、总结、回复，样样精通。

---

## ✨ 核心功能

### 📬 邮件收发
- **多账户支持**：同时管理多个邮箱账户，数据隔离存储
- **异步收取**：后台批量拉取邮件，支持指定文件夹、时间范围、已读状态过滤
- **专业发信**：Markdown 自动转精美 HTML，支持附件、抄送、密送
- **智能回复**：自动带上原始邮件历史，支持回复全部

### 🔍 智能搜索
- **全文搜索**：基于 SQLite FTS5 的快速关键词搜索
- **语义搜索**：基于 OpenAI Embeddings + ChromaDB 的向量相似度搜索
- **混合搜索**：FTS + 向量 + Cross-Encoder 重排序，搜索更精准
- **自然语言搜索**：支持中文日期表达式，如"上周老板发的关于预算的邮件"

### 🤖 AI 增强功能
- **邮件分类**：自动识别重要程度（critical/high/normal/low）和类别（work/personal/notification/promo）
- **AI 回复**：基于原始邮件和上下文线程生成专业回复，支持用户意图指导
- **邮件总结**：按发件人分组生成摘要报告，快速掌握邮件概况
- **附件解析**：支持 PDF、Excel、PPT、图片（OCR）等内容提取

### 🏷️ 邮件管理
- **标签系统**：添加/删除标签，支持批量操作
- **批量标记**：批量设置已读/星标状态
- **邮件移动**：在文件夹间移动邮件
- **邮件删除**：本地和服务器同步删除

### 🎨 用户体验
- **Web 配置界面**：通过浏览器轻松配置账户和设置
- **精美输出**：邮件详情以 Markdown 格式呈现，阅读体验极佳
- **附件预览**：本地 HTTP 服务器提供附件在线预览
- **签名档**：每个账户可配置独立签名

---

## 📦 安装

### 环境要求
- Python 3.8 或以上
- 支持 IMAP/SMTP 的邮箱账户
- OpenAI API Key（用于 AI 功能，可选）

### 快速安装

```bash
# 1. 克隆或下载项目
git clone <repository-url>
cd mail-skill

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动配置服务
python scripts/mail_cli.py config
```

打开浏览器访问显示的 URL（如 `http://127.0.0.1:8100`），完成以下配置：

1. **AI 设置**：填写 OpenAI API Key（用于语义搜索、AI 回复等功能）
2. **邮箱账户**：添加你的邮箱账户信息

> **提示**：大多数邮箱（QQ、Gmail、网易等）需要使用**应用专用密码**而非登录密码。请在邮箱设置中开启 IMAP/SMTP 服务并生成授权码。

---

## 🚀 使用指南

### 基础命令

```bash
# 收取邮件（默认最近 7 天）
python scripts/mail_cli.py fetch

# 搜索邮件
python scripts/mail_cli.py search --query "项目报告"

# 语义搜索（理解含义，不只是关键词）
python scripts/mail_cli.py search --query "下周会议安排" --vector

# 自然语言搜索
python scripts/mail_cli.py smart-search "上周老板发的关于预算的邮件"

# 阅读邮件
python scripts/mail_cli.py read <message_id>

# 发送邮件
python scripts/mail_cli.py send --to recipient@example.com --subject "主题" --body "正文"

# 回复邮件
python scripts/mail_cli.py reply <message_id> --body "回复内容"
```

### AI 功能

```bash
# 邮件分类
python scripts/mail_cli.py classify <message_id>

# AI 生成回复（预览模式）
python scripts/mail_cli.py ai-reply <message_id> --dry-run

# 生成邮件摘要报告
python scripts/mail_cli.py summary-report --days 7

# 解析附件内容
python scripts/mail_cli.py parse-attachments --message-id <message_id>
```

### 管理命令

```bash
# 标签管理
python scripts/mail_cli.py tag add <message_id> "重要"
python scripts/mail_cli.py tag batch-add "待处理" --from-search "from:boss"

# 批量标记
python scripts/mail_cli.py batch-mark --from-search "newsletter" --read 1

# 查看邮件线程
python scripts/mail_cli.py thread <message_id>

# 重建搜索索引
python scripts/mail_cli.py rebuild-index
```

---

## 📁 项目结构

```
mail-skill/
├── scripts/
│   ├── mail_cli.py              # 主 CLI 入口
│   └── mail_manager/
│       ├── client.py            # IMAP/SMTP 客户端
│       ├── db.py                # 数据库操作（SQLite + ChromaDB）
│       ├── config_server.py     # Web 配置服务
│       ├── config_manager.py    # 配置管理
│       ├── config_db.py         # 配置数据库
│       ├── classifier.py        # 邮件分类器
│       ├── query_parser.py      # 自然语言查询解析
│       ├── date_parser.py       # 中文日期解析
│       ├── detail.py            # 邮件详情格式化
│       ├── templates.py         # 邮件模板
│       ├── thread_manager.py    # 邮件线程管理
│       ├── summary_report.py    # 邮件摘要报告
│       ├── reply_assistant.py   # AI 回复助手
│       ├── server.py            # 附件预览服务器
│       ├── errors.py            # 错误码定义
│       ├── llm/                 # LLM 客户端
│       │   ├── client.py
│       │   └── prompts.py
│       └── attachment_parser/   # 附件解析器
│           ├── pdf_parser.py
│           ├── excel_parser.py
│           ├── pptx_parser.py
│           ├── image_parser.py
│           └── text_parser.py
├── tests/                       # 测试文件
├── mail_data/                   # 数据目录（运行时生成）
│   ├── config.db                # 配置数据库
│   └── <account>/               # 按账户隔离存储
│       ├── mail_index.db        # 邮件索引
│       ├── eml/                 # 原始邮件
│       ├── attachments/         # 附件
│       └── signature.md         # 签名档
├── SKILL.md                     # Agent 技能说明
├── README.md                    # 本文件
└── requirements.txt             # 依赖列表
```

---

## 🗓️ 更新日志

### v2.0.0 (2024-04)

#### 新功能

**Web 配置界面**
- 新增 `config` 命令，通过浏览器进行可视化配置
- 支持 AI 设置、存储设置、邮箱账户的 Web 管理界面
- 配置数据存储在 SQLite 数据库中，更安全可靠

**自然语言搜索**
- 支持"上周"、"本月"、"昨天"等中文日期表达式
- 自动提取搜索意图中的发件人、时间范围、关键词
- 与发件人列表进行模糊匹配，提高搜索准确度

**邮件分类系统**
- 自动识别邮件重要程度：critical / high / normal / low
- 自动识别邮件类别：work / personal / notification / promo
- 支持基于规则引擎的分类（可配置 YAML 规则）
- 支持手动重新分类

**AI 回复助手**
- 基于原始邮件内容生成专业回复
- 支持包含邮件线程上下文
- 支持"用户意图"指导（如"礼貌拒绝"、"确认参加"）
- 回复反馈学习机制，越用越准

**邮件摘要报告**
- 按发件人分组生成 Markdown 格式摘要报告
- 支持自定义日期范围
- LLM 生成每组的简要总结
- 支持输出到文件

**附件内容解析**
- 支持 PDF 文档文本提取
- 支持 Excel 表格内容读取
- 支持 PPT 演示文稿内容提取
- 支持图片 OCR（通过视觉模型）
- 解析内容存入数据库，支持搜索

**邮件线程管理**
- 增强的线程时间线显示
- 基于发件人/收件人匹配的线程关联
- 支持生成线程摘要

**批量操作**
- 批量标记已读/星标
- 批量添加标签
- 支持从搜索结果批量操作

**其他改进**
- 邮件详情 Markdown 格式化，阅读体验更好
- 邮件模板系统，支持自定义模板
- 统一的错误码和响应格式
- 完整的类型注解

#### 技术改进

- 测试覆盖率达到 75%
- 模块化架构，易于扩展
- 完善的错误处理机制

---

## 🔧 配置参考

### 邮箱账户配置

| 字段 | 说明 | 示例 |
|------|------|------|
| EMAIL | 邮箱地址 | user@qq.com |
| PASSWORD | 应用授权码 | xxxxxxxx |
| IMAP_SERVER | IMAP 服务器 | imap.qq.com |
| IMAP_PORT | IMAP 端口 | 993 |
| SMTP_SERVER | SMTP 服务器 | smtp.qq.com |
| SMTP_PORT | SMTP 端口 | 465 |
| USE_SSL | 是否使用 SSL | true |

### AI 配置

| 字段 | 说明 | 默认值 |
|------|------|--------|
| OPENAI_API_KEY | OpenAI API 密钥 | - |
| OPENAI_API_BASE | API 基础 URL | https://api.openai.com/v1 |
| LLM_MODEL_NAME | 语言模型 | gpt-4o-mini |
| EMBEDDING_MODEL_NAME | 向量模型 | text-embedding-3-small |
| RERANKER_MODEL_NAME | 重排序模型 | BAAI/bge-reranker-base |

### 常见邮箱服务器配置

| 邮箱 | IMAP 服务器 | SMTP 服务器 |
|------|-------------|-------------|
| QQ 邮箱 | imap.qq.com:993 | smtp.qq.com:465 |
| Gmail | imap.gmail.com:993 | smtp.gmail.com:465 |
| 网易 163 | imap.163.com:993 | smtp.163.com:465 |
| Outlook | outlook.office365.com:993 | smtp.office365.com:587 |

---

## ❓ 常见问题

**Q: 连接邮箱失败怎么办？**
> 检查以下几点：
> 1. 确认 IMAP/SMTP 服务已开启
> 2. 使用**应用专用密码**而非登录密码
> 3. 检查服务器地址和端口是否正确
> 4. 检查网络是否需要代理

**Q: 搜索结果为空？**
> 运行 `python scripts/mail_cli.py rebuild-index` 重建搜索索引。

**Q: AI 功能报错？**
> 确认已配置有效的 OpenAI API Key。可以通过 `config` 命令检查配置。

**Q: 附件预览打不开？**
> 附件预览服务会在首次访问时自动启动。检查 `./mail_data/<account>/` 目录下是否有附件文件。

**Q: 数据存储在哪里？**
> 所有数据存储在 `./mail_data/` 目录下，按账户隔离。删除此目录不影响邮箱服务器上的原始数据。

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
