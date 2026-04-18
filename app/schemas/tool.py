from pydantic import BaseModel
from typing import Optional

class ToolInfo(BaseModel):
    id: str
    name: str
    description: str
    category: str
    icon: str
    max_files: int = 1
