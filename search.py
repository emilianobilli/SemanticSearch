from embed import TextEmbedding
from model import Document, DocumentChunk
from victordb import VictorSession, VictorIndexClient

class SemanticSearch(object):
    def __init__(self, session: VictorSession, index: VictorIndexClient):
        self.text_embedding = TextEmbedding()
        self.session = session
        self.index = index

    def ingest(self, *, document: Document) -> bool:
        try:
            
            # Save document to database
            if not document.save(self.session):
                print(f"Failed to save document: {document.title}")
                return False
            
            # Generate embeddings for the content chunks
            chunks_data = self.text_embedding.embed_passage(document.raw_text)
            
            if not chunks_data:
                print(f"No chunks generated for document: {document.title}")
                return False
            
            # Create and save chunks
            chunks_saved = 0
            for vector, text in chunks_data:
                chunk = DocumentChunk(
                    content=text,
                    document_id=document.id #type: ignore
                )
                
                # Save chunk to database
                if chunk.save(self.session):
                    # Insert vector into index
                    try:
                        self.index.insert(chunk.id, vector) #type: ignore
                        chunks_saved += 1
                    except Exception as e:
                        print(f"Failed to insert chunk into index: {e}")
                        chunks_saved += 1
                else:
                    print(f"Failed to save chunk for document: {document.title}")
            
            print(f"Document '{document.title}' ingested successfully with {chunks_saved} chunks")
            return chunks_saved > 0
            
        except Exception as e:
            print(f"Error ingesting document '{document.title}': {e}")
            return False

    def search(self, *, query: str, top: int = 10) -> list[Document]:
        vector = self.text_embedding.embed_query(query)
        try:
            results = self.index.search(vector, top)
        except Exception as e:
            print(str(e))
            return []
        
        documents_prefilter = []
        for chunk_id, distance in results:
            chunk = DocumentChunk.get(self.session, chunk_id)
            if chunk:
                if chunk.document_id not in documents_prefilter:
                    documents_prefilter.append(chunk.document_id)
                print(chunk_id, distance, chunk.document_id)


        documents = []
        for document_id in documents_prefilter:
            doc = Document.get(self.session, document_id)
            if doc:
                documents.append(doc)
        return documents
                

    def retrieve(self, *, document_id:int) -> Document | None:
        return Document.get(self.session, document_id)

    
    def delete(self, *, document_id:int) -> bool:
        try:
            # Get the document
            doc = Document.get(self.session, document_id)
            if not doc:
                print(f"Document with id {document_id} not found.")
                return False

            # Get and delete associated chunks
            chunks = DocumentChunk.query_eq(self.session, "document_id", document_id)
            for chunk in chunks:
                # Delete from index
                try:
                    if chunk.id:
                        self.index.delete(chunk.id)
                except Exception as e:
                    print(f"Error deleting chunk from index: {e}")
                # Delete from database
                chunk.delete(self.session)

            # Delete the document
            doc.delete(self.session)
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False