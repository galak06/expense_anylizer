from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class Transaction(BaseModel):
    date: datetime
    description: str
    amount: float
    category: Optional[str] = None
    month: Optional[str] = None

    @field_validator('month', mode='before')
    @classmethod
    def set_month_from_date(cls, value, info):
        if value is None and 'date' in info.data:
            return info.data['date'].strftime('%Y-%m')
        return value


class MappingRow(BaseModel):
    keyword: str
    category: str


class MatchResult(BaseModel):
    category: Optional[str]
    strategy: Literal['keyword', 'fuzzy', 'llm']
    confidence: float = Field(ge=0.0, le=1.0)
    keyword_used: Optional[str] = None
    note: Optional[str] = None
