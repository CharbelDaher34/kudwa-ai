from sqlmodel import SQLModel, Field, Relationship, Session, select, func
from typing import List, Optional
from datetime import datetime
from db import engine

## rootfi data

class FinancialStatement(SQLModel, table=True):
    rootfi_id: int = Field(primary_key=True)
    rootfi_created_at: str
    rootfi_updated_at: str
    rootfi_deleted_at: Optional[str] = None
    rootfi_company_id: int
    platform_id: str
    platform_unique_id: Optional[str] = None
    currency_id: Optional[str] = None
    period_end: str = Field(description="End date of the financial period", sa_column_kwargs={"comment": "End date of the financial period"})
    period_start: str = Field(description="Start date of the financial period", sa_column_kwargs={"comment": "Start date of the financial period"})
    gross_profit: float = Field(description="Calculated gross profit")
    operating_profit: float = Field(description="Calculated operating profit")
    earnings_before_taxes: Optional[float] = None
    taxes: Optional[float] = None
    net_profit: float
    custom_fields: Optional[str] = None
    updated_at: Optional[str] = None

    # Relationships
    revenue_items: List["RevenueItem"] = Relationship(back_populates="financial_statement")
    cost_of_goods_sold_items: List["CostOfGoodsSoldItem"] = Relationship(back_populates="financial_statement")
    operating_expense_items: List["OperatingExpenseItem"] = Relationship(back_populates="financial_statement")
    non_operating_revenue_items: List["NonOperatingRevenueItem"] = Relationship(back_populates="financial_statement")
    non_operating_expense_items: List["NonOperatingExpenseItem"] = Relationship(back_populates="financial_statement")

# Base item class for common fields
class BaseFinancialItem(SQLModel):
    name: str
    value: float
    account_id: Optional[str] = None

# Specific item classes for each section type
class RevenueItem(BaseFinancialItem, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    financial_statement_id: int = Field(foreign_key="financialstatement.rootfi_id")
    parent_id: Optional[int] = Field(default=None, foreign_key="revenueitem.id")
    
    financial_statement: FinancialStatement = Relationship(back_populates="revenue_items")
    children: List["RevenueItem"] = Relationship(back_populates="parent")
    parent: Optional["RevenueItem"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "RevenueItem.id"}
    )

class CostOfGoodsSoldItem(BaseFinancialItem, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    financial_statement_id: int = Field(foreign_key="financialstatement.rootfi_id")
    parent_id: Optional[int] = Field(default=None, foreign_key="costofgoodssolditem.id")
    
    financial_statement: FinancialStatement = Relationship(back_populates="cost_of_goods_sold_items")
    children: List["CostOfGoodsSoldItem"] = Relationship(back_populates="parent")
    parent: Optional["CostOfGoodsSoldItem"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "CostOfGoodsSoldItem.id"}
    )

class OperatingExpenseItem(BaseFinancialItem, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    financial_statement_id: int = Field(foreign_key="financialstatement.rootfi_id")
    parent_id: Optional[int] = Field(default=None, foreign_key="operatingexpenseitem.id")
    
    financial_statement: FinancialStatement = Relationship(back_populates="operating_expense_items")
    children: List["OperatingExpenseItem"] = Relationship(back_populates="parent")
    parent: Optional["OperatingExpenseItem"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "OperatingExpenseItem.id"}
    )

class NonOperatingRevenueItem(BaseFinancialItem, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    financial_statement_id: int = Field(foreign_key="financialstatement.rootfi_id")
    parent_id: Optional[int] = Field(default=None, foreign_key="nonoperatingrevenueitem.id")
    
    financial_statement: FinancialStatement = Relationship(back_populates="non_operating_revenue_items")
    children: List["NonOperatingRevenueItem"] = Relationship(back_populates="parent")
    parent: Optional["NonOperatingRevenueItem"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "NonOperatingRevenueItem.id"}
    )

class NonOperatingExpenseItem(BaseFinancialItem, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    financial_statement_id: int = Field(foreign_key="financialstatement.rootfi_id")
    parent_id: Optional[int] = Field(default=None, foreign_key="nonoperatingexpenseitem.id")
    
    financial_statement: FinancialStatement = Relationship(back_populates="non_operating_expense_items")
    children: List["NonOperatingExpenseItem"] = Relationship(back_populates="parent")
    parent: Optional["NonOperatingExpenseItem"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "NonOperatingExpenseItem.id"}
    )
    
    
### First json data    
 
    
# 1. DEFINE THE DATABASE MODELS
# ==============================================================================
# These classes define the structure of your database tables.

class Report(SQLModel, table=True):
    """
    Stores the metadata for a single Profit and Loss report.
    Each report can have many accounts and many financial entries.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    report_name: str = Field(index=True)
    report_basis: str
    start_period: datetime
    end_period: datetime
    currency: str
    generated_time: datetime

    # Relationships: A report is linked to multiple accounts and entries.
    accounts: List["Account"] = Relationship(back_populates="report")


class Account(SQLModel, table=True):
    """
    Represents a single account in the P&L report (e.g., "Revenue", "Software Fees").
    Accounts can be nested to create a hierarchy.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    qbo_id: int = Field(index=True, unique=True) # QBO ID from the JSON
    name: str
    type: str = Field(description="The type of account") # e.g., "Account"
    group: str = Field(description="The group this account belongs to") # e.g., "Income", "Cost of Goods Sold"

    # Self-referencing relationship for parent-child hierarchy
    parent_id: Optional[int] = Field(default=None, foreign_key="account.id")
    parent: Optional["Account"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Account.id"}
    )
    children: List["Account"] = Relationship(back_populates="parent")

    # Relationship to the report it belongs to
    report_id: int = Field(foreign_key="report.id")
    report: "Report" = Relationship(back_populates="accounts")

    # Relationship to its financial entries
    financial_entries: List["FinancialEntry"] = Relationship(back_populates="account")


class FinancialEntry(SQLModel, table=True):
    """
    Stores a single financial value for a specific account and date.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    value: float
    date: datetime

    # Relationship to the account it belongs to
    account_id: int = Field(foreign_key="account.id")
    account: "Account" = Relationship(back_populates="financial_entries")
