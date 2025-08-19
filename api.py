from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import uvicorn

from victordb import VictorTableClient, VictorIndexClient, VictorSession
from search import SemanticSearch
from model import Document
from settings import get_settings

# Pydantic models for API
class DocumentCreate(BaseModel):
    title: str
    author: str = ""
    source: str = ""
    published_at: str = ""
    raw_text: str
    metadata: List[str] = []

class DocumentResponse(BaseModel):
    id: Optional[str]  # Cambiar a string para evitar truncado de JavaScript
    title: str
    author: str
    source: str
    published_at: str
    raw_text: str
    metadata: List[str]

class SearchResponse(BaseModel):
    query: str
    total_results: int
    documents: List[DocumentResponse]

class HealthResponse(BaseModel):
    status: str
    message: str

class DocumentIngestResult(BaseModel):
    success: bool
    message: str
    document_id: Optional[str]
    index: int

class BulkIngestResponse(BaseModel):
    results: List[DocumentIngestResult]
    total_processed: int
    successful: int
    failed: int

# Global variables for database connections
semantic_search: Optional[SemanticSearch] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global semantic_search
    
    # Obtener configuración
    config = get_settings()
    
    # Startup
    try:
        # Initialize database connections
        table = VictorTableClient()
        table.connect(unix_path=config.victor_table_socket)
        
        index = VictorIndexClient()
        index.connect(unix_path=config.victor_index_socket)
        
        session = VictorSession(table)
        semantic_search = SemanticSearch(session, index)
        
        print("Semantic Search API initialized successfully")
        print(f"Table socket: {config.victor_table_socket}")
        print(f"Index socket: {config.victor_index_socket}")
    except Exception as e:
        print(f"Failed to initialize API: {e}")
        raise
    
    yield  # La aplicación se ejecuta aquí
    
    # Shutdown (opcional - puedes agregar lógica de limpieza aquí)
    print("Shutting down Semantic Search API...")

# Initialize FastAPI app
app = FastAPI(
    title="Semantic Search API",
    description="API para búsqueda semántica de documentos",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS with settings
config = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,  # Usar configuración
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="Semantic Search API is running"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    if semantic_search is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return HealthResponse(
        status="healthy",
        message="All services are operational"
    )


@app.post("/documents", response_model=BulkIngestResponse)
async def create_documents(documents_data: List[DocumentCreate]):
    """Ingest multiple documents into the search index"""
    if semantic_search is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        results = []
        successful = 0
        failed = 0
        
        for i, document_data in enumerate(documents_data):
            try:
                # Create Document object
                document = Document(
                    title=document_data.title,
                    author=document_data.author,
                    source=document_data.source,
                    published_at=document_data.published_at,
                    raw_text=document_data.raw_text,
                    metadata=document_data.metadata
                )
                
                # Ingest the document
                success = semantic_search.ingest(document=document)
                
                if success:
                    successful += 1
                    results.append(DocumentIngestResult(
                        success=True,
                        message=f"Document '{document.title}' ingested successfully",
                        document_id=str(document.id) if document.id else None,
                        index=i
                    ))
                else:
                    failed += 1
                    results.append(DocumentIngestResult(
                        success=False,
                        message=f"Failed to ingest document '{document.title}'",
                        document_id=None,
                        index=i
                    ))
                    
            except Exception as e:
                failed += 1
                error_msg = f"Error processing document '{document_data.title}': {str(e)}"
                results.append(DocumentIngestResult(
                    success=False,
                    message=error_msg,
                    document_id=None,
                    index=i
                ))
        
        return BulkIngestResponse(
            results=results,
            total_processed=len(documents_data),
            successful=successful,
            failed=failed
        )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing documents: {str(e)}"
        )

@app.post("/document", response_model=DocumentIngestResult)
async def create_single_document(document_data: DocumentCreate):
    """Ingest a single document into the search index"""
    if semantic_search is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Create Document object
        document = Document(
            title=document_data.title,
            author=document_data.author,
            source=document_data.source,
            published_at=document_data.published_at,
            raw_text=document_data.raw_text,
            metadata=document_data.metadata
        )
        
        # Ingest the document
        success = semantic_search.ingest(document=document)
        
        if success:
            return DocumentIngestResult(
                success=True,
                message=f"Document '{document.title}' ingested successfully",
                document_id=str(document.id) if document.id else None,
                index=0
            )
        else:
            return DocumentIngestResult(
                success=False,
                message=f"Failed to ingest document '{document.title}'",
                document_id=None,
                index=0
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting document: {str(e)}"
        )

@app.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., description="Search query"),
    top: int = Query(None, description="Number of results to return")
):
    """Search for documents using semantic similarity"""
    if semantic_search is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    # Usar configuración para límites de búsqueda
    config = get_settings()
    if top is None:
        top = config.default_search_results
    elif top > config.max_search_results:
        top = config.max_search_results
    elif top < 1:
        top = 1
    
    try:
        # Perform semantic search
        documents = semantic_search.search(query=q, top=top)
        
        # Convert to response format
        document_responses = []
        for doc in documents:
            document_responses.append(DocumentResponse(
                id=str(doc.id) if doc.id else None,  # Convertir a string
                title=doc.title,
                author=doc.author,
                source=doc.source,
                published_at=doc.published_at,
                raw_text=doc.raw_text,
                metadata=doc.metadata
            ))
        
        return SearchResponse(
            query=q,
            total_results=len(document_responses),
            documents=document_responses
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error performing search: {str(e)}"
        )

@app.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """Get a specific document by ID"""
    if semantic_search is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        doc_id = int(document_id)
        document = semantic_search.retrieve(document_id=doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return DocumentResponse(
            id=str(document.id) if document.id else None,
            title=document.title,
            author=document.author,
            source=document.source,
            published_at=document.published_at,
            raw_text=document.raw_text,
            metadata=document.metadata
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving document: {str(e)}"
        )

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its associated chunks by ID"""
    if semantic_search is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    try:
        doc_id = int(document_id)
        success = semantic_search.delete(document_id=doc_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found or could not be deleted")
        return {"success": True, "message": f"Document {document_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document: {str(e)}"
        )

if __name__ == "__main__":
    config = get_settings()
    print("Starting Semantic Search API...")
    print(f"Host: {config.api_host}:{config.api_port}")
    print(f"Reload: {config.api_reload}")
    uvicorn.run(
        "api:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.api_reload,
        log_level=config.api_log_level
    )
