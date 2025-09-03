from typing import Optional
from pydantic import BaseModel
 
class GraphCursors(BaseModel):
	before: Optional[str]
	after: Optional[str]

class GraphPagination(BaseModel):
	cursor: GraphCursors