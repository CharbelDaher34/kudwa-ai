from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON,Column
# ==============================================================================
# GENERIC FINANCIAL REPORTING SCHEMA
# ==============================================================================

class UnifiedReport(SQLModel, table=True):
    """
    Stores metadata for a single financial report.
    Generic schema that can handle any financial data source.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # --- Core Report Fields ---
    report_name: str = Field(index=True)
    report_basis: str
    start_period: datetime
    end_period: datetime
    currency: Optional[str]
    generated_time: datetime

    # --- Source System Fields ---
    platform_id: str = Field(description="Source system identifier (e.g., 'quickbooks', 'rootfi', 'sage')")
    platform_unique_id: Optional[str] = None  # The original ID from the source system
    company_id: Optional[str] = None  # Generic company identifier from source system
    
    # --- Calculated/Summary Fields ---
    # These are kept for quick access but could also be calculated on the fly
    # from the associated accounts.
    gross_profit: Optional[float] = None
    operating_profit: Optional[float] = None
    net_profit: Optional[float] = None
    earnings_before_taxes: Optional[float] = None
    taxes: Optional[float] = None
    
    # --- Additional Metadata ---
    extra_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional platform-specific metadata",
        sa_column=Column(JSON)
    )
    
    # --- Relationships ---
    # A single relationship to a flexible chart of accounts.
    accounts: List["Account"] = Relationship(back_populates="report")


class Account(SQLModel, table=True):
    """
    Represents a single account in the report (e.g., "Revenue", "Software Fees").
    Generic model that can handle accounts from any financial system.
    The hierarchy is self-contained.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # --- Core Account Fields ---
    name: str
    # The 'group' field is the key to categorizing financial data generically
    group: str = Field(description="The financial group, e.g., 'Revenue', 'Cost of Goods Sold', 'Operating Expense'")
    
    # Source-specific ID (e.g., from QBO, RootFi, or another system)
    source_account_id: Optional[str] = Field(default=None, index=True) 

    # --- Hierarchy Management ---
    parent_id: Optional[int] = Field(default=None, foreign_key="account.id")
    parent: Optional["Account"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Account.id"}
    )
    children: List["Account"] = Relationship(back_populates="parent")

    # --- Additional Metadata ---
    extra_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional account-specific metadata from source system",
        sa_column=Column(JSON)
    )

    # --- Relationship to the main report ---
    report_id: int = Field(foreign_key="unifiedreport.id")
    report: "UnifiedReport" = Relationship(back_populates="accounts")
    
    # --- Relationship to its financial values ---
    financial_entries: List["FinancialEntry"] = Relationship(back_populates="account")


class FinancialEntry(SQLModel, table=True):
    """
    Stores a single financial value for a specific account.
    Generic model that can handle financial data from any source system.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    value: float
    # Date field provides flexibility for different reporting periods
    date: datetime
    
    # Optional period classification for different data types
    period_type: Optional[str] = Field(default="monthly", description="Type of period: 'monthly', 'quarterly', 'yearly', 'total'")

    # --- Additional Metadata ---
    extra_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional entry-specific metadata from source system",
        sa_column=Column(JSON)
    )

    # --- Relationship to the account ---
    account_id: int = Field(foreign_key="account.id")
    account: "Account" = Relationship(back_populates="financial_entries")

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