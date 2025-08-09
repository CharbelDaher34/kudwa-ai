from typing import List, Optional, Union
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column
from pydantic import BaseModel, field_validator, field_serializer


# Reusable recursive line item
class LineItem(BaseModel):
    name: str
    value: Union[int, float]  # Allow both int and float explicitly
    account_id: Optional[str] = None
    line_items: List["LineItem"] = []

    @field_validator("line_items", mode="before")
    @classmethod
    def _coerce_children(cls, v):
        if not v:
            return []
        return [item if isinstance(item, LineItem) else LineItem(**item) for item in v]
    
    @field_validator("value", mode="before")
    @classmethod
    def _coerce_value(cls, v):
        """Ensure value is numeric"""
        if isinstance(v, (int, float)):
            return float(v)  # Convert to float for consistency
        try:
            return float(v)
        except (ValueError, TypeError):
            raise ValueError(f"Value must be numeric, got {type(v)}")

LineItem.model_rebuild()  # finalize recursion


class FinancialReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # flat fields
    rootfi_id: int
    rootfi_created_at: str
    rootfi_updated_at: str
    rootfi_deleted_at: Optional[str] = None
    rootfi_company_id: int
    platform_id: str
    platform_unique_id: Optional[str] = None
    currency_id: Optional[str] = None
    period_end: str
    period_start: str

    gross_profit: Optional[float] = None
    operating_profit: Optional[float] = None
    earnings_before_taxes: Optional[float] = None
    taxes: Optional[float] = None
    net_profit: Optional[float] = None
    custom_fields: Optional[str] = None
    updated_at: Optional[str] = None

    # All nested groups reuse the SAME schema (LineItem), stored as JSON
    revenue: Optional[List[LineItem]] = Field(default=None, sa_column=Column(JSON))
    cost_of_goods_sold: Optional[List[LineItem]] = Field(default=None, sa_column=Column(JSON))
    operating_expenses: Optional[List[LineItem]] = Field(default=None, sa_column=Column(JSON))
    non_operating_revenue: Optional[List[LineItem]] = Field(default=None, sa_column=Column(JSON))
    non_operating_expenses: Optional[List[LineItem]] = Field(default=None, sa_column=Column(JSON))

    # ---- Pydantic v2: parse lists of dicts into LineItem and serialize back to JSON ----
    @field_validator(
        "revenue", "cost_of_goods_sold", "operating_expenses",
        "non_operating_revenue", "non_operating_expenses", mode="before"
    )
    @classmethod
    def _coerce_groups(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            return v
        return [item if isinstance(item, LineItem) else LineItem(**item) for item in v]

    @field_serializer(
        "revenue", "cost_of_goods_sold", "operating_expenses",
        "non_operating_revenue", "non_operating_expenses",
        when_used="always"
    )
    def _dump_groups(self, v):
        if not v:
            return None
        return [item.model_dump() if isinstance(item, LineItem) else item for item in v]
    
    # Property getters that ensure LineItem conversion
    @property 
    def revenue_items(self) -> Optional[List[LineItem]]:
        """Get revenue as LineItem objects"""
        if not self.revenue:
            return None
        return [item if isinstance(item, LineItem) else LineItem(**item) for item in self.revenue]
    
    @property 
    def cost_of_goods_sold_items(self) -> Optional[List[LineItem]]:
        """Get cost_of_goods_sold as LineItem objects"""
        if not self.cost_of_goods_sold:
            return None
        return [item if isinstance(item, LineItem) else LineItem(**item) for item in self.cost_of_goods_sold]
    
    @property 
    def operating_expenses_items(self) -> Optional[List[LineItem]]:
        """Get operating_expenses as LineItem objects"""
        if not self.operating_expenses:
            return None
        return [item if isinstance(item, LineItem) else LineItem(**item) for item in self.operating_expenses]
    
    @property 
    def non_operating_revenue_items(self) -> Optional[List[LineItem]]:
        """Get non_operating_revenue as LineItem objects"""
        if not self.non_operating_revenue:
            return None
        return [item if isinstance(item, LineItem) else LineItem(**item) for item in self.non_operating_revenue]
    
    @property 
    def non_operating_expenses_items(self) -> Optional[List[LineItem]]:
        """Get non_operating_expenses as LineItem objects"""
        if not self.non_operating_expenses:
            return None
        return [item if isinstance(item, LineItem) else LineItem(**item) for item in self.non_operating_expenses]
