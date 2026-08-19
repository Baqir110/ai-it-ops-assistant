import os
from pathlib import Path
from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.models.schemas import RunbookSource

RUNBOOKS_DIR = os.path.join("data", "runbooks")
PERSIST_DIR = os.path.join("data", "chroma_db")
COLLECTION_NAME = "it_ops_runbooks"


class RunbookSearchEngine:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = None
        self.initialize_vector_store()

    def initialize_vector_store(self):
        os.makedirs(RUNBOOKS_DIR, exist_ok=True)
        os.makedirs(PERSIST_DIR, exist_ok=True)

        documents = []

        for file_path in Path(RUNBOOKS_DIR).glob("*.md"):
            with open(file_path, "r", encoding="utf-8") as file:
                documents.append(
                    Document(
                        page_content=file.read(),
                        metadata={"source": str(file_path)},
                    )
                )

        self.vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=self.embeddings,
            persist_directory=PERSIST_DIR,
        )

        if documents:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
            )

            chunks = text_splitter.split_documents(documents)

            existing = self.vector_store.get()

            if not existing["ids"]:
                self.vector_store.add_documents(chunks)

    def _search_distinct_runbooks(
        self,
        query: str,
        top_k: int,
    ):
        if self.vector_store is None:
            return []

        total_chunks = self.vector_store._collection.count()

        if total_chunks == 0:
            return []

        fetch_k = min(
            max(top_k * 4, top_k),
            total_chunks,
        )

        results = self.vector_store.similarity_search_with_score(
            query,
            k=fetch_k,
        )

        best_matches = {}

        for doc, distance in results:
            source_path = doc.metadata.get(
                "source",
                "Unknown Runbook",
            )

            # Chroma returns distance: lower is better.
            # Convert it to a score where higher is better.
            relevance_score = 1 / (1 + float(distance))

            if (
                source_path not in best_matches
                or relevance_score > best_matches[source_path][1]
            ):
                best_matches[source_path] = (
                    doc,
                    relevance_score,
                )

        distinct_matches = sorted(
            best_matches.values(),
            key=lambda item: item[1],
            reverse=True,
        )

        return distinct_matches[:top_k]

    def search(
        self,
        query: str,
        top_k: int = 2,
    ) -> List[RunbookSource]:

        results = self._search_distinct_runbooks(
            query,
            top_k,
        )

        return [
            RunbookSource(
                title=os.path.basename(
                    doc.metadata.get(
                        "source",
                        "Unknown Runbook",
                    )
                ),
                file_path=doc.metadata.get(
                    "source",
                    "Unknown Runbook",
                ),
                relevance_score=round(
                    float(score),
                    2,
                ),
            )
            for doc, score in results
        ]

    def search_with_content(
        self,
        query: str,
        top_k: int = 2,
    ):
        results = self._search_distinct_runbooks(
            query,
            top_k,
        )

        matches = []

        for doc, score in results:
            source_path = doc.metadata.get(
                "source",
                "Unknown Runbook",
            )

            matches.append(
                {
                    "title": os.path.basename(source_path),
                    "file_path": source_path,
                    "content": doc.page_content,
                    "relevance_score": round(
                        float(score),
                        2,
                    ),
                }
            )

        return matches
