"""Prompt templates for LLM-powered features.

Contains prompt templates for thread summary, reply composition, and attachment parsing.
"""

THREAD_SUMMARY_PROMPT = """Summarize this email thread in 2-3 sentences. Focus on the main topic, key decisions, and any action items.

Thread:
{thread_content}

Summary:"""

REPLY_SYSTEM_PROMPT = """You are an email assistant helping compose professional replies.
Write concise, clear responses. Match the tone of the original email.
Always end with a professional closing.

Guidelines:
- Be helpful and professional
- Keep responses brief unless detail is needed
- Match the sender's formality level
- Include relevant context when responding to questions"""

ATTACHMENT_SUMMARY_PROMPT = """Summarize the content of this document in 2-3 sentences. Focus on the main topic and key points.

Document content:
{content}

Summary:"""

# Image description prompt for vision API
IMAGE_DESCRIPTION_PROMPT = """Describe the content of this image in detail. Include:
1. Main subject or objects
2. Any text visible in the image
3. Overall context or purpose

If this is a screenshot, diagram, or chart, explain what information it conveys."""

# Email summary prompt for individual email summarization
EMAIL_SUMMARY_PROMPT = """Analyze this email and extract a structured summary. Return ONLY valid JSON with these keys:

{{
    "key_points": ["list of main points from the email"],
    "action_items": ["list of actions requested or implied"],
    "deadline": "YYYY-MM-DD format if mentioned, or null",
    "priority": "high/medium/low based on urgency",
    "one_liner": "single sentence summary of the email"
}}

Email details:
- From: {sender}
- Subject: {subject}
- Date: {date}

Body:
{body}

Return only the JSON object, no additional text."""

# Overall summary prompt for aggregating individual email summaries
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

Return only the JSON object, no additional text."""

EMAIL_CLASSIFICATION_PROMPT = """分析以下邮件，判断其重要性和类别。

发件人: {sender}
主题: {subject}
内容摘要: {body}

请按以下 JSON 格式返回分类结果：
{"importance": "critical/high/normal/low", "category": "work/personal/notification/promo", "reason": "简短说明分类理由"}

重要性说明：
- critical: 紧急重要，需要立即处理（如老板/客户要求、截止日期临近）
- high: 重要但不紧急，需要优先处理（如工作安排、项目相关）
- normal: 普通邮件，按正常流程处理
- low: 低优先级，可稍后处理（如通知、订阅）

类别说明：
- work: 工作相关（项目、会议、任务安排等）
- personal: 个人相关（私人事务、朋友往来）
- notification: 系统通知（账单、提醒、自动邮件）
- promo: 营销推广（广告、促销、订阅内容）

只返回 JSON，不要其他内容。"""
