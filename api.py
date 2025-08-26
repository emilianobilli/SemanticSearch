from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from contextlib import asynccontextmanager
import uvicorn
import logging

from victordb import VictorTableClient, VictorIndexClient, VictorSession
from search import SemanticSearch
from schema import (
    DocumentCreateRequest,
    SearchRequest,
    ErrorDetail
)
from settings import get_settings
from victor_server import ServerConfig, VictorServerManager

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

# Global variable
semantic_search: Optional[SemanticSearch] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global semantic_search
    
    # Obtener configuración
    config = get_settings()
    
    # Startup
    server_manager = None
    try:
        # Crear configuración del servidor VictorDB personalizada
        server_config = ServerConfig(
            name=config.victor_name,
            index_dims=config.victor_index_dims,
            index_type=config.victor_index_type,
            index_method=config.victor_index_method
        )
        logger.info(f"VictorDB Configuration: {server_config}")
        # Iniciar servidor VictorDB
        server_manager = VictorServerManager(server_config)
        logger.info("Starting VictorDB server...")
        if not server_manager.start_all():
            raise Exception("Failed to start VictorDB server")
        
        logger.info("VictorDB server started successfully")
        
        # Esperar un poco para que el servidor se inicialice
        import time
        time.sleep(2)
        
        # Initialize database connections
        table = VictorTableClient()
        table.connect(unix_path=server_config.table_socket)
        
        index = VictorIndexClient()
        index.connect(unix_path=server_config.index_socket)
        
        session = VictorSession(table)
        semantic_search = SemanticSearch(session, index)
        
        logger.info("Semantic Search API initialized successfully")
        logger.info(f"Database name: {server_config.name}")
        logger.info(f"Index dimensions: {server_config.index_dims}")
        logger.info(f"Index type: {server_config.index_type}")
        logger.info(f"Index method: {server_config.index_method}")
        logger.info(f"Table socket: {server_config.table_socket}")
        logger.info(f"Index socket: {server_config.index_socket}")
        
    except Exception as e:
        logger.error(f"Failed to initialize API: {e}")
        if server_manager:
            server_manager.stop_all()
        raise
    
    yield  # La aplicación se ejecuta aquí
    
    # Shutdown
    logger.info("Shutting down Semantic Search API...")
    if server_manager:
        logger.info("Stopping VictorDB server...")
        server_manager.stop_all()
        logger.info("VictorDB server stopped")

# Initialize FastAPI app
app = FastAPI(
    title="Semantic Search API",
    description="API para búsqueda semántica de documentos",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS with settings
config = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Semantic Search API is running"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    if semantic_search is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {"status": "healthy", "message": "All services are operational"}

@app.post("/document")
async def create_document(document_data: DocumentCreateRequest):
    """Ingest a single document into the search index"""
    if semantic_search is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = semantic_search.embed_document(document=document_data)
    
    if isinstance(result, ErrorDetail):
        raise HTTPException(status_code=400, detail=result.message)
    
    return result

@app.get("/search")
async def search_documents(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return")
):
    """Search for documents using semantic similarity"""
    if semantic_search is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    request = SearchRequest(query=q, limit=limit)
    result = semantic_search.search(request=request)
    
    if isinstance(result, ErrorDetail):
        raise HTTPException(status_code=500, detail=result.message)
    
    return result

@app.get("/documents/{document_id}")
async def get_document(document_id: int):
    """Get a specific document by ID"""
    if semantic_search is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = semantic_search.retrieve(document_id=document_id)
    
    if isinstance(result, ErrorDetail):
        if result.code == "DOCUMENT_NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.message)
        else:
            raise HTTPException(status_code=500, detail=result.message)
    
    return result

@app.delete("/documents/{document_id}")
async def delete_document(document_id: int):
    """Delete a document and its associated chunks by ID"""
    if semantic_search is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = semantic_search.delete(document_id=document_id)
    
    if isinstance(result, ErrorDetail):
        if result.code == "DOCUMENT_NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.message)
        else:
            raise HTTPException(status_code=500, detail=result.message)
    
    return result

if __name__ == "__main__":
    config = get_settings()
    logger.info("Starting Semantic Search API...")
    logger.info(f"Host: {config.api_host}:{config.api_port}")
    logger.info(f"Reload: {config.api_reload}")
    uvicorn.run(
        "api:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.api_reload,
        log_level=config.api_log_level
    )
