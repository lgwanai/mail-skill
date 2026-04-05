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
