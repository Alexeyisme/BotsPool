"""
Chat-related models for BotsPool

This module contains all models related to chat functionality,
including requests, responses, sessions, and messages.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .base import BaseEntity, TimestampMixin
from .enums import GraphType, FrontendType, ChatStatus, MessageType


class ChatContext(BaseModel):
    """
    Chat context information.

    Stores contextual information for chat sessions.
    """

    current_bot: Optional[str] = Field(None, description="Currently active bot/graph")
    user_preferences: Dict[str, Any] = Field(
        default_factory=dict, description="User preferences"
    )
    session_data: Dict[str, Any] = Field(
        default_factory=dict, description="Session-specific data"
    )
    conversation_history: List[str] = Field(
        default_factory=list, description="Recent conversation context"
    )

    @validator("conversation_history")
    def limit_conversation_history(cls, v):
        """Limit conversation history to prevent memory issues."""
        return v[-10:] if len(v) > 10 else v


class ChatMessage(BaseModel):
    """
    Individual chat message.

    Represents a single message in a chat conversation.
    """

    id: UUID = Field(..., description="Message ID")
    message_type: MessageType = Field(..., description="Type of message")
    content: str = Field(
        ..., min_length=1, max_length=4000, description="Message content"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message timestamp"
    )
    user_id: Optional[UUID] = Field(None, description="User ID (for user messages)")
    graph_type: Optional[str] = Field(
        None, description="Graph type (for assistant messages)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Message metadata"
    )

    @validator("content")
    def validate_content(cls, v):
        """Validate message content."""
        if not v.strip():
            raise ValueError("Message content cannot be empty")
        return v.strip()


class ChatSession(BaseEntity):
    """
    Chat session model.

    Represents a conversation session between a user and AI graphs.
    """

    user_id: UUID = Field(..., description="User ID")
    session_id: str = Field(..., description="Unique session identifier")
    frontend_type: FrontendType = Field(..., description="Frontend type")
    status: ChatStatus = Field(ChatStatus.ACTIVE, description="Session status")

    # Session metadata
    title: Optional[str] = Field(None, max_length=200, description="Session title")
    description: Optional[str] = Field(
        None, max_length=500, description="Session description"
    )

    # Context and state
    context: ChatContext = Field(
        default_factory=ChatContext, description="Session context"
    )
    current_graph: Optional[GraphType] = Field(
        None, description="Currently active graph"
    )

    # Statistics
    message_count: int = Field(0, ge=0, description="Total message count")
    last_message_at: Optional[datetime] = Field(
        None, description="Last message timestamp"
    )

    # Frontend-specific data
    frontend_data: Dict[str, Any] = Field(
        default_factory=dict, description="Frontend-specific data"
    )

    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the session."""
        self.message_count += 1
        self.last_message_at = message.timestamp
        self.updated_at = datetime.utcnow()

        # Update conversation history
        if message.message_type == MessageType.USER:
            self.context.conversation_history.append(f"User: {message.content}")
        elif message.message_type == MessageType.ASSISTANT:
            self.context.conversation_history.append(f"Assistant: {message.content}")

    def end_session(self) -> None:
        """End the chat session."""
        self.status = ChatStatus.ENDED
        self.updated_at = datetime.utcnow()

    def pause_session(self) -> None:
        """Pause the chat session."""
        self.status = ChatStatus.PAUSED
        self.updated_at = datetime.utcnow()

    def resume_session(self) -> None:
        """Resume the chat session."""
        self.status = ChatStatus.ACTIVE
        self.updated_at = datetime.utcnow()


class ChatRequest(BaseModel):
    """
    Chat request model.

    Used for incoming chat requests from frontends.
    """

    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    user_id: UUID = Field(..., description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")

    # Context information
    context: Optional[ChatContext] = Field(None, description="Chat context")

    # Frontend metadata
    frontend_type: FrontendType = Field(..., description="Frontend type")
    frontend_data: Dict[str, Any] = Field(
        default_factory=dict, description="Frontend-specific data"
    )

    # Request metadata
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Request timestamp"
    )

    @validator("message")
    def validate_message(cls, v):
        """Validate message content."""
        if not v.strip():
            raise ValueError("Message cannot be empty")

        # Check for potentially malicious content
        import re

        if re.search(r"<script|javascript:|data:", v, re.IGNORECASE):
            raise ValueError("Message contains potentially malicious content")

        return v.strip()

    @validator("frontend_data")
    def validate_frontend_data(cls, v):
        """Validate frontend data size."""
        if len(str(v)) > 10000:
            raise ValueError("Frontend data too large")
        return v


class ChatResponse(BaseModel):
    """
    Chat response model.

    Used for responses from AI graphs to frontends.
    """

    response: str = Field(..., description="AI response message")
    graph_type: GraphType = Field(
        ..., description="Graph type that generated the response"
    )
    user_id: UUID = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")

    # Response metadata
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    processing_time: Optional[float] = Field(
        None, ge=0, description="Processing time in seconds"
    )
    tokens_used: Optional[int] = Field(
        None, ge=0, description="Tokens used for generation"
    )

    # Graph instance information
    instance_id: Optional[str] = Field(None, description="Graph instance ID")

    # Response metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Response metadata"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="Suggested follow-up actions"
    )

    # API versioning
    api_version: str = Field("v1", description="API version")


class ChatStreamChunk(BaseModel):
    """
    Chat stream chunk model.

    Used for streaming responses from AI graphs.
    """

    type: str = Field(..., description="Chunk type (start, chunk, end, error)")
    content: Optional[str] = Field(None, description="Chunk content")
    conversation_id: str = Field(..., description="Conversation ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Chunk timestamp"
    )


class ChatHistory(BaseModel):
    """
    Chat history model.

    Used for retrieving chat history.
    """

    session_id: str = Field(..., description="Session ID")
    messages: List[ChatMessage] = Field(..., description="Chat messages")
    total_count: int = Field(..., ge=0, description="Total message count")
    has_more: bool = Field(False, description="Whether there are more messages")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")


class ChatAnalytics(BaseModel):
    """
    Chat analytics model.

    Used for chat usage analytics and insights.
    """

    session_id: str = Field(..., description="Session ID")
    user_id: UUID = Field(..., description="User ID")
    graph_type: GraphType = Field(..., description="Graph type")

    # Session statistics
    message_count: int = Field(..., ge=0, description="Total message count")
    user_message_count: int = Field(..., ge=0, description="User message count")
    assistant_message_count: int = Field(
        ..., ge=0, description="Assistant message count"
    )

    # Timing statistics
    session_duration: float = Field(
        ..., ge=0, description="Session duration in seconds"
    )
    average_response_time: float = Field(..., ge=0, description="Average response time")
    total_processing_time: float = Field(..., ge=0, description="Total processing time")

    # Token usage
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    input_tokens: int = Field(..., ge=0, description="Input tokens")
    output_tokens: int = Field(..., ge=0, description="Output tokens")

    # Quality metrics
    user_satisfaction: Optional[float] = Field(
        None, ge=0, le=5, description="User satisfaction rating"
    )
    error_count: int = Field(0, ge=0, description="Number of errors")

    # Timestamps
    started_at: datetime = Field(..., description="Session start time")
    ended_at: Optional[datetime] = Field(None, description="Session end time")


class ChatSearchRequest(BaseModel):
    """
    Chat search request model.

    Used for searching through chat history.
    """

    user_id: UUID = Field(..., description="User ID")
    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    graph_type: Optional[GraphType] = Field(None, description="Filter by graph type")
    date_from: Optional[datetime] = Field(None, description="Search from date")
    date_to: Optional[datetime] = Field(None, description="Search to date")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Result offset")


class ChatSearchResult(BaseModel):
    """
    Chat search result model.

    Used for chat search results.
    """

    session_id: str = Field(..., description="Session ID")
    message_id: UUID = Field(..., description="Message ID")
    content: str = Field(..., description="Message content")
    graph_type: GraphType = Field(..., description="Graph type")
    timestamp: datetime = Field(..., description="Message timestamp")
    relevance_score: float = Field(
        ..., ge=0, le=1, description="Search relevance score"
    )
