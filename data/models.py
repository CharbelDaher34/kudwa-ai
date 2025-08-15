from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON,Column
## new schmea
# Define our simplified database model
class FinancialStatement(SQLModel, table=True):
    """Simplified model for financial statement data that works for both file formats"""
    id: Optional[int] = Field(default=None, primary_key=True)
    period: date  # First day of the reporting period
    account_id: str = Field(index=True)
    account_name: str = Field(index=True, description="Name of the financial transaction")
    amount: float
    parent_account_id: Optional[str] = None

# ==============================================================================
# CONVERSATION & MESSAGE MODELS (EDITED)
# ==============================================================================

class Conversation(SQLModel, table=True):
    """
    Represents a chat conversation, grouping multiple messages.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    topic: Optional[str] = Field(default=None, description="Optional topic of the conversation")
    created_time: datetime = Field(default_factory=datetime.utcnow, description="When the conversation was created")

    # Relationship to messages
    messages: List["Message"] = Relationship(back_populates="conversation")


class Message(SQLModel, table=True):
    """
    Stores an individual message within a conversation.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id", description="The conversation this message belongs to")
    conversation: Conversation = Relationship(back_populates="messages")

    sender_type: str = Field(index=True, description="Who sent the message: 'user' or 'system'")
    sender: Optional[str] = Field(default=None, description="Identifier of sender (username or system name)")
    content: str = Field(description="Message text content")
    sent_time: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the message was sent")

    usage: Dict[str, Any] = Field(
        default_factory=dict,  # ensures it defaults to {}
        description="Usage stats (e.g., LLM token counts)",
        sa_column=Column(JSON)  # use SQLAlchemy Column for JSON storage
    )