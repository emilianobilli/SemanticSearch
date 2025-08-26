from pydantic import BaseModel, Field
from typing import List, Optional

# Document schemas (based on model.Document)
class DocumentCreateRequest(BaseModel):
    """Request to create a new document"""
    title: str = Field(..., description="Document title")
    author: str = Field("", description="Document author")
    source: str = Field("", description="Document source")
    raw_text: str = Field(..., description="Complete document content")
    metadata: List[str] = Field(default=[], description="Additional tags or metadata")

class DocumentDetail(BaseModel):
    """Complete document details"""
    id: Optional[str] = None
    title: str
    author: str
    source: str
    raw_text: str
    metadata: List[str]

# Chunk schemas (based on model.DocumentChunk)
class ChunkDetail(BaseModel):
    """Text chunk details"""
    id: Optional[str] = None
    document_id: str
    content: str
    position: int

class ChunkWithScore(BaseModel):
    """Chunk with similarity score"""
    chunk: ChunkDetail
    distance: float = Field(..., ge=0.0, description="Vector distance")

# Search schemas
class SearchRequest(BaseModel):
    """Semantic search request"""
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")

class SearchResult(BaseModel):
    """Semantic search result"""
    query: str
    total_found: int
    results: List[ChunkWithScore]

# Standard response schemas
class SuccessResponse(BaseModel):
    """Standard response for successful operations"""
    success: bool = True
    message: str
    data: Optional[dict] = None

class ErrorDetail(BaseModel):
    """Error details"""
    code: str
    message: str
    field: Optional[str] = None
