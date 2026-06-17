import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import google.generativeai as genai
from openai import OpenAI
from typing import List, Dict, Any
from backend.app.config import settings

class VectorDBService:
    _qdrant_client = None

    def __init__(self):
        # Initialize Qdrant Client as a singleton to share the in-memory state across the process
        if VectorDBService._qdrant_client is None:
            if settings.QDRANT_URL:
                VectorDBService._qdrant_client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY
                )
            else:
                # local in-memory Qdrant client
                VectorDBService._qdrant_client = QdrantClient(path=":memory:")
                
        self.qdrant_client = VectorDBService._qdrant_client
            
        self.collection_name = "documents"
        self.use_gemini = bool(
            settings.GEMINI_API_KEY 
            and settings.GEMINI_API_KEY.strip() != "" 
            and "placeholder" not in settings.GEMINI_API_KEY.lower() 
            and "your_gemini" not in settings.GEMINI_API_KEY.lower()
        )
        
        if self.use_gemini:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.vector_size = 768
        else:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.vector_size = 1536
            
    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for a text chunk using Gemini or OpenAI.
        """
        if self.use_gemini:
            try:
                response = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_document"
                )
                return response["embedding"]
            except Exception as e:
                # Fallback to a zero vector or dummy if it fails
                print(f"Gemini embedding failed: {e}")
                return [0.0] * self.vector_size
        else:
            try:
                response = self.openai_client.embeddings.create(
                    input=[text],
                    model="text-embedding-3-small"
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"OpenAI embedding failed: {e}")
                return [0.0] * self.vector_size

    def create_collection(self):
        """
        Ensures the collection exists with the appropriate vector parameters.
        """
        # Recreate collection to ensure it is clean for new uploads in our local/memory flow
        # In a real environment, we'd do self.qdrant_client.get_collection, but recreated is fine for MVP/testing.
        self.qdrant_client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
        )

    def index_chunks(self, document_id: int, chunks: List[str]):
        """
        Embeds and indexes document chunks in Qdrant.
        """
        self.create_collection()
        points = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            embedding = self._get_embedding(chunk)
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "document_id": document_id,
                        "chunk_index": i,
                        "text": chunk
                    }
                )
            )
        if points:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )

    def search_similar_chunks(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Searches Qdrant for chunks similar to the query.
        """
        query_vector = self._get_embedding(query)
        try:
            if hasattr(self.qdrant_client, "query_points"):
                response = self.qdrant_client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit
                )
                search_result = response.points
            else:
                search_result = self.qdrant_client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit
                )
            return [
                {
                    "text": hit.payload["text"],
                    "score": hit.score,
                    "document_id": hit.payload["document_id"]
                } for hit in search_result
            ]
        except Exception as e:
            print(f"Qdrant search failed: {e}")
            return []

    def delete_document_vectors(self, document_id: int):
        """
        Deletes all vector points associated with a specific document ID.
        """
        try:
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
        except Exception as e:
            print(f"Failed to delete Qdrant vectors for doc {document_id}: {e}")
