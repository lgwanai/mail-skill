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
