# Stack: Mail Skill

## Language & Runtime

- **Python 3.8+** - Primary language
- No web framework (CLI tool)

## Core Dependencies

### Email Handling
| Package | Version | Purpose |
|---------|---------|---------|
| `imap-tools` | >=1.5.0 | IMAP email fetching and manipulation |
| `smtplib` | stdlib | SMTP email sending |

### Data Storage
| Package | Version | Purpose |
|---------|---------|---------|
| `sqlite3` | stdlib | Primary database with FTS5 |
| `chromadb` | >=0.4.0 | Vector embeddings storage |

### AI & Search
| Package | Version | Purpose |
|---------|---------|---------|
| `sentence-transformers` | >=2.2.2 | Local embeddings & reranking |
| `OpenAI API` | optional | Cloud embeddings |

### Text Processing
| Package | Version | Purpose |
|---------|---------|---------|
| `beautifulsoup4` | >=4.12.0 | HTML parsing |
| `markdown` | >=3.4.0 | Markdown to HTML conversion |
| `jinja2` | >=3.1.0 | Template rendering |

### Utilities
| Package | Version | Purpose |
|---------|---------|---------|
| `python-dotenv` | >=1.0.0 | Configuration loading |

## Build & Package

- No build system (direct Python execution)
- Entry point: `scripts/mail_cli.py`

## Testing

- No test framework currently configured
- Testing infrastructure needed

## External Services

### Email Servers
- IMAP servers (Gmail, Outlook, Feishu, Netease, etc.)
- SMTP servers for sending

### Optional APIs
- OpenAI API (or compatible) for cloud embeddings
- SiliconFlow API support

## Development Tools

- No linting/formatting tools configured
- No type checking configured

## Deployment

- Designed for local execution
- No containerization
- Data stored locally in `./mail_data/`
