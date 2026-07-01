import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini Client
# It will automatically pick up GEMINI_API_KEY from environment
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Pydantic schema for structured decision detection
class DecisionAnalysis(BaseModel):
    is_decision: bool = Field(
        description="True if the message represents a clear decision, agreement, resolution, or plan of action. False if it is just a question, normal conversation, brainstorming, or proposal without agreement."
    )
    summary: Optional[str] = Field(
        default=None,
        description="A concise summary of what was decided (e.g., 'We will deploy the feature on Friday'). Leave empty if is_decision is False."
    )
    rationale: Optional[str] = Field(
        default=None,
        description="The reason, explanation, or context for why this decision was made. Leave empty if is_decision is False or no explanation is provided."
    )
    decision_maker: Optional[str] = Field(
        default=None,
        description="The name or user ID of the person who made the decision, or 'Team' if it was a group agreement. Leave empty if is_decision is False."
    )

def detect_decision(text: str, context: Optional[str] = None) -> DecisionAnalysis:
    """
    Analyzes a message text (with optional preceding context) to determine if a decision was made.
    """
    prompt = f"""
    Analyze the following Slack message to determine if a team decision, resolution, or finalized plan of action has occurred.
    
    Current Message:
    "{text}"
    """
    if context:
        prompt = f"""
        Recent Conversation Context:
        {context}
        
        Current Message:
        "{text}"
        """ + prompt

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DecisionAnalysis,
                temperature=0.1,  # Low temperature for deterministic analysis
            ),
        )
        
        # The response text will be a JSON string conforming to DecisionAnalysis
        data = json.loads(response.text)
        return DecisionAnalysis(**data)
    except Exception as e:
        print(f"Error calling Gemini for decision detection: {e}")
        # Return a fallback non-decision
        return DecisionAnalysis(is_decision=False)

def answer_query(query: str, logs: List[dict]) -> str:
    """
    Generates an answer to a user's question about past decisions, using the logged decisions as context.
    """
    # Format logs as a readable context
    formatted_logs = ""
    for idx, log in enumerate(logs, 1):
        formatted_logs += f"{idx}. Decision: {log.get('summary')}\n"
        if log.get('rationale'):
            formatted_logs += f"   Why: {log.get('rationale')}\n"
        if log.get('decision_maker'):
            formatted_logs += f"   Who: {log.get('decision_maker')}\n"
        formatted_logs += f"   Date: {log.get('created_at')}\n\n"

    prompt = f"""
    You are the DecisionLog Assistant. A user is asking a question about past team decisions.
    Use the following logged decisions as context to answer their question accurately.
    
    If the context does not contain the answer, say that you couldn't find any relevant decisions logged for that query.
    Keep the tone professional, helpful, and concise.

    Logged Decisions Context:
    {formatted_logs if formatted_logs else "No matching decisions found."}

    User Question:
    "{query}"
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
            ),
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error calling Gemini for Q&A: {e}")
        return "Sorry, I encountered an error while searching for the answer."
