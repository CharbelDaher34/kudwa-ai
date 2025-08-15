from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON,Column
# ==============================================================================
# UNIFIED FINANCIAL REPORTING SCHEMA
# ==============================================================================

# class UnifiedReport(SQLModel, table=True):
#     """
#     Stores metadata for a single financial report, combining fields from
#     both the original 'Report' and 'FinancialStatement' models.
#     """
#     id: Optional[int] = Field(default=None, primary_key=True)
    
#     # --- Fields from Schema 2 ('Report') ---
#     report_name: str = Field(index=True)
#     report_basis: str
#     start_period: datetime
#     end_period: datetime
#     currency: Optional[str]
#     generated_time: datetime

#     # --- Fields from Schema 1 ('FinancialStatement') ---
#     platform_id: str  # To identify the source system (e.g., 'rootfi', 'qbo')
#     platform_unique_id: Optional[str] = None # The original ID from the source system
#     rootfi_company_id: Optional[int] = None # Specific ID if the source is rootfi
    
#     # --- Calculated/Summary Fields from Schema 1 ---
#     # These are kept for quick access but could also be calculated on the fly
#     # from the associated accounts.
#     gross_profit: Optional[float] = None
#     operating_profit: Optional[float] = None
#     net_profit: Optional[float] = None
#     earnings_before_taxes: Optional[float] = None
#     taxes: Optional[float] = None
    
#     # --- Relationships ---
#     # A single relationship to a flexible chart of accounts.
#     accounts: List["Account"] = Relationship(back_populates="report")


# class Account(SQLModel, table=True):
#     """
#     Represents a single account in the report (e.g., "Revenue", "Software Fees").
#     This model replaces all the separate `...Item` tables from Schema 1.
#     The hierarchy is self-contained.
#     """
#     id: Optional[int] = Field(default=None, primary_key=True)
    
#     # --- Fields from Schema 2 ('Account') ---
#     name: str
#     # The 'group' field is the key to replacing Schema 1's separate tables.
#     group: str = Field(description="The financial group, e.g., 'Revenue', 'Cost of Goods Sold', 'Operating Expense'")
    
#     # Source-specific ID (e.g., from QBO or another system)
#     source_account_id: Optional[str] = Field(default=None, index=True) 

#     # --- Hierarchy Management (from both schemas) ---
#     parent_id: Optional[int] = Field(default=None, foreign_key="account.id")
#     parent: Optional["Account"] = Relationship(
#         back_populates="children",
#         sa_relationship_kwargs={"remote_side": "Account.id"}
#     )
#     children: List["Account"] = Relationship(back_populates="parent")

#     # --- Relationship to the main report ---
#     report_id: int = Field(foreign_key="unifiedreport.id")
#     report: "UnifiedReport" = Relationship(back_populates="accounts")
    
#     # --- Relationship to its financial values ---
#     financial_entries: List["FinancialEntry"] = Relationship(back_populates="account")


# class FinancialEntry(SQLModel, table=True):
#     """
#     Stores a single financial value for a specific account.
#     This model is more granular than Schema 1's simple 'value' field,
#     which is an advantage.
#     """
#     id: Optional[int] = Field(default=None, primary_key=True)
#     value: float
#     # We keep the 'date' field from Schema 2 for granularity. For Schema 1 data,
#     # this could simply be the 'end_period' of the report.
#     date: datetime

#     # --- Relationship to the account ---
#     account_id: int = Field(foreign_key="account.id")
#     account: "Account" = Relationship(back_populates="financial_entries")

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