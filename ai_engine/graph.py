"""
LangGraph pipeline that triages a support ticket in four steps:

    classify_ticket -> analyze_sentiment -> summarize_ticket -> draft_response

Each node calls the OpenAI API (via langchain-openai) with structured output
so the graph state is populated with typed, predictable fields. The graph is
compiled once at import time and reused across requests.
"""
from __future__ import annotations

from typing import List, Optional, TypedDict

from django.conf import settings
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------
class TicketState(TypedDict, total=False):
    title: str
    description: str
    available_categories: List[str]

    category: Optional[str]
    priority: Optional[str]
    classification_confidence: Optional[float]

    sentiment: Optional[str]

    summary: Optional[str]

    suggested_response: Optional[str]


# ---------------------------------------------------------------------------
# Structured output schemas for each node
# ---------------------------------------------------------------------------
class ClassificationResult(BaseModel):
    category: str = Field(description="Best-fit category for this ticket")
    priority: str = Field(description="One of: low, medium, high, urgent")
    confidence: float = Field(description="Confidence score between 0 and 1", ge=0, le=1)


class SentimentResult(BaseModel):
    sentiment: str = Field(description="One of: positive, neutral, negative")


class SummaryResult(BaseModel):
    summary: str = Field(description="A 1-2 sentence summary of the customer's issue")


class ResponseResult(BaseModel):
    suggested_response: str = Field(
        description="A short, empathetic, professional first-response draft for a support agent to send"
    )


def _llm(temperature: float = 0.0) -> ChatOpenAI:
    kwargs = {
        "model": settings.OPENAI_MODEL,
        "api_key": settings.OPENAI_API_KEY,
        "temperature": temperature,
    }
    # Allows pointing at any OpenAI-compatible endpoint (Groq, OpenRouter, etc.)
    # instead of OpenAI's own servers, e.g. for free-tier testing.
    if getattr(settings, "OPENAI_BASE_URL", None):
        kwargs["base_url"] = settings.OPENAI_BASE_URL
    return ChatOpenAI(**kwargs)


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
def classify_ticket(state: TicketState) -> TicketState:
    categories = state.get("available_categories") or []
    categories_hint = (
        f"Choose the category from this existing list when a good match exists: {categories}. "
        "If none fit well, propose a new short category name."
        if categories
        else "Propose a short, sensible category name."
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a support ticket triage assistant. Classify the ticket's category "
                "and urgency priority (low, medium, high, urgent). " + categories_hint,
            ),
            ("human", "Title: {title}\n\nDescription: {description}"),
        ]
    )
    structured_llm = _llm().with_structured_output(ClassificationResult)
    chain = prompt | structured_llm
    result: ClassificationResult = chain.invoke(
        {"title": state["title"], "description": state["description"]}
    )
    return {
        "category": result.category,
        "priority": result.priority.lower(),
        "classification_confidence": result.confidence,
    }


def analyze_sentiment(state: TicketState) -> TicketState:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You analyze the emotional tone of a customer support ticket. "
                "Respond with sentiment as one of: positive, neutral, negative.",
            ),
            ("human", "Title: {title}\n\nDescription: {description}"),
        ]
    )
    structured_llm = _llm().with_structured_output(SentimentResult)
    chain = prompt | structured_llm
    result: SentimentResult = chain.invoke(
        {"title": state["title"], "description": state["description"]}
    )
    return {"sentiment": result.sentiment.lower()}


def summarize_ticket(state: TicketState) -> TicketState:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Summarize the customer's issue in 1-2 concise sentences for an agent."),
            ("human", "Title: {title}\n\nDescription: {description}"),
        ]
    )
    structured_llm = _llm().with_structured_output(SummaryResult)
    chain = prompt | structured_llm
    result: SummaryResult = chain.invoke(
        {"title": state["title"], "description": state["description"]}
    )
    return {"summary": result.summary}


def draft_response(state: TicketState) -> TicketState:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful, empathetic customer support agent. Draft a short first-response "
                "(3-5 sentences) acknowledging the issue described below and outlining next steps. "
                "Take into account the detected sentiment: {sentiment}. Do not invent specific "
                "resolution details you cannot know.",
            ),
            ("human", "Title: {title}\n\nDescription: {description}\n\nSummary: {summary}"),
        ]
    )
    structured_llm = _llm(temperature=0.4).with_structured_output(ResponseResult)
    chain = prompt | structured_llm
    result: ResponseResult = chain.invoke(
        {
            "title": state["title"],
            "description": state["description"],
            "summary": state.get("summary", ""),
            "sentiment": state.get("sentiment", "neutral"),
        }
    )
    return {"suggested_response": result.suggested_response}


# ---------------------------------------------------------------------------
# Build & compile the graph
# ---------------------------------------------------------------------------
def build_graph():
    graph = StateGraph(TicketState)

    graph.add_node("classify_ticket", classify_ticket)
    graph.add_node("analyze_sentiment", analyze_sentiment)
    graph.add_node("summarize_ticket", summarize_ticket)
    graph.add_node("draft_response", draft_response)

    graph.set_entry_point("classify_ticket")
    graph.add_edge("classify_ticket", "analyze_sentiment")
    graph.add_edge("analyze_sentiment", "summarize_ticket")
    graph.add_edge("summarize_ticket", "draft_response")
    graph.add_edge("draft_response", END)

    return graph.compile()


_compiled_graph = None


def get_compiled_graph():
    """Lazily compile & cache the graph so importing this module doesn't require an API key."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
