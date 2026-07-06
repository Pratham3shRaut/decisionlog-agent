"""
Provider-agnostic pieces shared by every LLM backend:
  - the DecisionAnalysis schema
  - the detection prompt builder
  - the Q&A prompt builder
  - cosine similarity

Each provider (gemini.py, openai_provider.py) implements only the raw model calls
and reuses these so prompts/schema stay identical across providers.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class DecisionAnalysis(BaseModel):
    is_decision: bool = Field(
        description="True if the message represents a clear decision, agreement, resolution, or plan of action. False if it is just a question, normal conversation, brainstorming, or proposal without agreement."
    )
    summary: Optional[str] = Field(
        default=None,
        description="A concise summary of what was decided (e.g., 'We will deploy the feature on Friday'). If the message uses first-person pronouns like 'I' or 'my', resolve them to the Message Sender's name if provided. If the message refers to relative dates like 'tomorrow', 'today', or days of the week, resolve them to absolute dates (e.g. 'July 2, 2026') using the Current Date. Leave empty if is_decision is False."
    )
    rationale: Optional[str] = Field(
        default=None,
        description="The reason, explanation, or context for why this decision was made. If the message uses first-person pronouns like 'I' or 'my' in the explanation, resolve them to the Message Sender's name. Resolve any relative dates to absolute dates using the Current Date. Leave empty if is_decision is False or no explanation is provided."
    )
    decision_maker: Optional[str] = Field(
        default=None,
        description="The name or user ID of the person who made the decision, or 'Team' if it was a group agreement. Prefer using the Message Sender's name if the decision is individual. Leave empty if is_decision is False."
    )


_DETECTION_RULES = """
    Rules:
    - Only mark is_decision=True if the team has actually settled on a course of action.
    - Questions, requests for opinions, and status checks ("should we...?", "what do you think?", "has anyone looked at...?") are NOT decisions.
    - Brainstorming and proposals without agreement ("maybe we could try...", "just an idea") are NOT decisions.
    - Sarcastic or joking messages are NOT decisions, even if phrased like one.
    - Noncommittal or hedging responses ("yeah maybe", "leaning towards", "not sure yet") are NOT decisions.
    - A short agreement like "agreed", "+1", "sounds good", or "let's do that" IS a decision, but only if the
      Recent Conversation Context makes clear what specific proposal is being agreed to. If there is no context
      and the message alone is ambiguous, mark is_decision=False.
    - Generic acknowledgements with no decision content ("lgtm", "ok", "thanks") are NOT decisions.
"""


def build_detection_prompt(text, context=None, sender_name=None, current_date=None) -> str:
    sender_info = f"Message Sender: {sender_name}\n" if sender_name else ""
    date_info = f"Current Date: {current_date}\n" if current_date else ""
    if context:
        return f"""
        Recent Conversation Context:
        {context}
        {_DETECTION_RULES}
        {sender_info}{date_info}Current Message:
        "{text}"
        """
    return f"""
    Analyze the following Slack message to determine if a team decision, resolution, or finalized plan of action has occurred.
    {_DETECTION_RULES}
    {sender_info}{date_info}Current Message:
    "{text}"
    """


def build_qa_prompt(query: str, logs: List[dict], current_date: Optional[str] = None) -> str:
    formatted_logs = ""
    for idx, log in enumerate(logs, 1):
        formatted_logs += f"{idx}. Decision: {log.get('summary')}\n"
        if log.get('rationale'):
            formatted_logs += f"   Why: {log.get('rationale')}\n"
        if log.get('decision_maker'):
            formatted_logs += f"   Who: {log.get('decision_maker')}\n"
        formatted_logs += f"   Date: {log.get('created_at')}\n\n"

    date_info = f"Current Date of Question: {current_date}\n" if current_date else ""
    return f"""
    You are the DecisionLog Assistant. A user is asking a question about past team decisions.
    Use the following logged decisions as context to answer their question accurately.

    {date_info}If the context does not contain the answer, say that you couldn't find any relevant decisions logged for that query.
    Keep the tone professional, helpful, and concise.

    Logged Decisions Context:
    {formatted_logs if formatted_logs else "No matching decisions found."}

    User Question:
    "{query}"
    """


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two equal-length vectors. Returns 0.0 if empty/mismatched."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
