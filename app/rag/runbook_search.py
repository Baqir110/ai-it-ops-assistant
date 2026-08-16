import os
from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from app.models.schemas import RunbookSource

RUNBOOKS_DIR = os.path.join("data", "runbooks")
PERSIST_DIR = os.path.join("data", "chroma_db")

class RunbookSearchEngine:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = None
        self.initialize_vector_store()

    def initialize_vector_store(self):
        if not os.path.exists(RUNBOOKS_DIR):
            os.makedirs(RUNBOOKS_DIR, exist_ok=True)

        # Standard Python file loading removes the deprecated community loader
        documents = []
        for file_path in Path(RUNBOOKS_DIR).glob("*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                documents.append(Document(page_content=f.read(), metadata={"source": str(file_path)}))

        if documents:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            chunks = text_splitter.split_documents(documents)
            self.vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=PERSIST_DIR
            )
        else:
            self.vector_store = Chroma(
                embedding_function=self.embeddings,
                persist_directory=PERSIST_DIR
            )

    def search(self, query: str, top_k: int = 2) -> List[RunbookSource]:
        if not self.vector_store:
            return []

        results = self.vector_store.similarity_search_with_relevance_scores(query, k=top_k)
        sources = []
        for doc, score in results:
            title = doc.metadata.get("source", "Unknown Runbook")
            filename = os.path.basename(title)
            sources.append(
                RunbookSource(
                    title=filename,
                    file_path=title,
                    relevance_score=round(float(score), 2)
                )
            )
        return sources