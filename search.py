from embed import TextEmbedding
from victordb import VictorSession, VictorIndexClient
from typing import Union

from model import (
    Document,
    DocumentChunk
)

from schema import (
    DocumentCreateRequest,
    DocumentDetail,
    ChunkWithScore,
    ChunkDetail,
    SuccessResponse,
    SearchRequest,
    SearchResult,
    ErrorDetail
)

class SemanticSearch(object):
    def __init__(self, session: VictorSession, index: VictorIndexClient):
        self.text_embedding = TextEmbedding()
        self.session = session
        self.index = index

    def embed_document(
        self, 
        *, 
        document: DocumentCreateRequest
    ) -> Union[SuccessResponse, ErrorDetail]:
    
        doc = Document(
            title=document.title,
            author=document.author,
            source=document.source,
            raw_text=document.raw_text,
            metadata=document.metadata
        )
    
        if not doc.save(self.session):
            return ErrorDetail(
                code="DOCUMENT_SAVE_FAILED",
                message=f"Failed to save document: {document.title}"
            )
    

        raw_chunks = self.text_embedding.embed_passage(document.raw_text)
        if not raw_chunks:
            return ErrorDetail(
                code="NO_CHUNKS_GENERATED",
                message="No chunks could be generated from the document content"
            )
        
        total_chunks = 0
        for vector, raw_text in raw_chunks:
            chunk = DocumentChunk(
                content= raw_text,
                document_id = doc.id, #type: ignore
                position = total_chunks + 1
            )

            if chunk.save(self.session):
                try:
                    self.index.insert(chunk.id, vector) #type: ignore
                    total_chunks += 1
                except Exception as e:
                    chunk.delete(self.session)
                    print(f"Failed to insert chunk into index: {e}")
                    # Consider rollback strategy here
        
        return SuccessResponse(
            success = True,
            message = "Document ingested successfully"
        )


    def search(self, *, request: SearchRequest) -> Union[SearchResult, ErrorDetail]:
        vector = self.text_embedding.embed_query(request.query)
        try:
            results = self.index.search(vector, request.limit)
        except Exception as e:
            return ErrorDetail(
                code="SEARCH_FAILED",
                message=str(e)
            )

        elements = []
        for chunk_id, distance in results:
            chunk = DocumentChunk.get(self.session, chunk_id)
            if chunk:
                elements.append(
                    ChunkWithScore(
                        chunk = ChunkDetail(
                            id=str(chunk.id),
                            document_id=str(chunk.document_id),
                            content=chunk.content,
                            position= chunk.position,
                        ),
                        distance=distance
                    )
                )
        return SearchResult(
            query = request.query,
            total_found = len(elements),
            results = elements
        )

    def retrieve(self, *, document_id: int) -> Union[DocumentDetail, ErrorDetail]:
        """Retrieve a document by its ID"""
        try:
            doc = Document.get(self.session, document_id)
            if not doc:
                return ErrorDetail(
                    code="DOCUMENT_NOT_FOUND",
                    message=f"Document with id {document_id} not found"
                )
            
            return DocumentDetail(
                id=str(doc.id) if doc.id else None,
                title=doc.title,
                author=doc.author,
                source=doc.source,
                raw_text=doc.raw_text,
                metadata=doc.metadata
            )
        except Exception as e:
            return ErrorDetail(
                code="RETRIEVE_FAILED",
                message=f"Error retrieving document: {str(e)}"
            )

    def delete(self, *, document_id: int) -> Union[SuccessResponse, ErrorDetail]:
        """Delete a document and all its associated chunks"""
        try:
            # Get the document first
            doc = Document.get(self.session, document_id)
            if not doc:
                return ErrorDetail(
                    code="DOCUMENT_NOT_FOUND",
                    message=f"Document with id {document_id} not found"
                )

            # Get and delete associated chunks
            chunks = DocumentChunk.query_eq(self.session, "document_id", document_id)
            deleted_chunks = 0
            
            for chunk in chunks:
                # Delete from vector index first
                try:
                    if chunk.id:
                        self.index.delete(chunk.id)
                except Exception as e:
                    print(f"Warning: Failed to delete chunk from index: {e}")
                
                # Delete chunk from database
                if chunk.delete(self.session):
                    deleted_chunks += 1

            # Delete the document itself
            if doc.delete(self.session):
                return SuccessResponse(
                    success=True,
                    message=f"Document '{doc.title}' and {deleted_chunks} chunks deleted successfully"
                )
            else:
                return ErrorDetail(
                    code="DELETE_FAILED",
                    message="Failed to delete document from database"
                )
                
        except Exception as e:
            return ErrorDetail(
                code="DELETE_FAILED",
                message=f"Error deleting document: {str(e)}"
            )

