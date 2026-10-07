import time
import httpx
from typing import List, Dict, Optional, Tuple
from app.models.document import Citation, SearchResult
from app.models.schemas import QueryResponse
from app.services.vector_store import vector_store
from app.config import settings

class RAGEngine:
    FALLBACK_MESSAGE = (
        "The provided internal documents do not contain sufficient information "
        "to answer this question reliably."
    )

    @classmethod
    def format_citations(cls, results: List[SearchResult]) -> List[Citation]:
        citations = []
        for r in results:
            c = r.chunk
            citations.append(Citation(
                doc_id=c.doc_id,
                filename=c.filename,
                page_number=c.page_number or 1,
                chunk_index=c.chunk_index,
                score=r.similarity_score,
                excerpt=c.text[:220] + ("..." if len(c.text) > 220 else "")
            ))
        return citations

    @classmethod
    def assemble_context(cls, results: List[SearchResult]) -> str:
        context_blocks = []
        for idx, r in enumerate(results, start=1):
            c = r.chunk
            header = f"[Source {idx} | File: {c.filename} | Page: {c.page_number or 1} | Match: {int(r.similarity_score * 100)}%]"
            context_blocks.append(f"{header}\n{c.text}\n")
        return "\n---\n".join(context_blocks)

    @classmethod
    async def generate_llm_answer(
        cls,
        query: str,
        context: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, bool]:
        """
        Synthesizes grounded answer using OpenAI if API key available,
        or high-precision extractive summarizer when running locally in offline mode.
        """
        if not context.strip():
            return cls.FALLBACK_MESSAGE, False

        system_prompt = (
            "You are an enterprise technical knowledge assistant.\n"
            "Answer the user's question strictly and ONLY using the provided source excerpts below.\n"
            "Rules:\n"
            "1. Ground every statement in the source text.\n"
            "2. If the source excerpts do not contain the answer, reply EXACTLY with:\n"
            f"   '{cls.FALLBACK_MESSAGE}'\n"
            "3. Cite your sources using [File: <name>, Page: <page>] notation.\n"
            "4. Do not invent facts, speculate, or reference outside information.\n\n"
            f"SOURCE EXCERPTS:\n{context}"
        )

        if settings.OPENAI_API_KEY:
            try:
                messages = [{"role": "system", "content": system_prompt}]
                if history:
                    messages.extend(history[-4:])
                messages.append({"role": "user", "content": query})

                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                        json={
                            "model": "gpt-4o-mini",
                            "messages": messages,
                            "temperature": 0.1,
                            "max_tokens": 600
                        }
                    )
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"].strip()
                        grounded = cls.FALLBACK_MESSAGE.lower() not in content.lower()
                        return content, grounded
            except Exception as e:
                print(f"[RAGEngine] External LLM error: {e}")

        # High-Precision Built-in Grounded Extractive Mode (Zero external dependencies)
        return cls._extractive_grounded_answer(query, context)

    @classmethod
    def _extractive_grounded_answer(cls, query: str, context: str) -> Tuple[str, bool]:
        """
        Extracts the most relevant sentences directly from retrieved sources
        and verifies token overlap to eliminate hallucination.
        """
        query_terms = set(query.lower().replace("?", "").replace(".", "").split())
        stop_words = {"what", "is", "the", "are", "how", "to", "for", "in", "of", "and", "a", "an", "do", "does", "can"}
        important_terms = query_terms - stop_words

        sentences = []
        for line in context.split("\n"):
            if line.startswith("[Source") or line.startswith("---") or not line.strip():
                continue
            for s in line.split(". "):
                s_clean = s.strip()
                if len(s_clean) > 20:
                    sentences.append(s_clean)

        ranked_sentences = []
        for s in sentences:
            s_lower = s.lower()
            overlap = sum(1 for term in important_terms if term in s_lower)
            if overlap > 0:
                ranked_sentences.append((overlap, s))

        if not ranked_sentences:
            return cls.FALLBACK_MESSAGE, False

        ranked_sentences.sort(key=lambda x: x[0], reverse=True)
        top_sentences = [s for _, s in ranked_sentences[:3]]
        
        answer = " ".join(top_sentences)
        if not answer.endswith("."):
            answer += "."

        return f"Based on the internal documentation:\n\n{answer}", True

    @classmethod
    async def query(
        cls,
        query: str,
        top_k: int = 4,
        filter_doc_ids: Optional[List[str]] = None
    ) -> QueryResponse:
        start_time = time.perf_counter()
        
        # 1. Vector Search with threshold gating
        search_results = await vector_store.search(
            query=query,
            top_k=top_k,
            min_similarity=settings.SIMILARITY_THRESHOLD,
            filter_doc_ids=filter_doc_ids
        )

        citations = cls.format_citations(search_results)
        context = cls.assemble_context(search_results)

        # 2. Grounded Synthesis
        answer, is_grounded = await cls.generate_llm_answer(query, context)
        if not is_grounded:
            citations = []
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return QueryResponse(
            query=query,
            answer=answer,
            grounded=is_grounded,
            citations=citations,
            retrieved_chunks_count=len(search_results),
            processing_time_ms=round(elapsed_ms, 2)
        )
