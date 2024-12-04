from pydantic import BaseModel, Field
from typing import List, Optional


class ColumnData(BaseModel):
    name: str = Field(description="Column name")
    type: str = Field(description="Column data type, like 'string', 'number', 'date'")
    description: Optional[str] = Field(default='N/A', description="Column short description")

class TableData(BaseModel):
    name: str = Field(description="Table name")
    columns: List[ColumnData] = Field(description="List of columns")
    description: Optional[str] = Field(default='N/A', description="Table short description")

class DBData(BaseModel):
    name: str = Field(description="Database name")
    tables: List[TableData] = Field(description="List of tables")
    description: Optional[str] = Field(default='N/A', description="Database short description")
