import uuid
import re
import math
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk
from app.schemas.chat import Citation
from app.services.embedding import embedding_service
from app.core.config import settings
from app.core.prompt_guard import prompt_guard

ANTI_HALLUCINATION_RESPONSE = "I couldn't find sufficient information in your connected knowledge."

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
    "which", "this", "that", "these", "those", "then", "just", "so", "than",
    "such", "both", "through", "about", "for", "is", "of", "while", "during",
    "to", "from", "in", "out", "on", "off", "over", "under", "again", "further",
    "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "few", "more", "most", "other", "some", "no", "nor", "not", "only", "own",
    "same", "too", "very", "can", "will", "should", "now", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "would", "could", "my", "your", "his", "her", "its", "our", "their", "me",
    "him", "them", "i", "we", "you", "he", "she", "it", "they"
}

GENERIC_WORDS = {
    "year", "years", "time", "date", "day", "days", "make", "work", "worked",
    "working", "good", "strong", "strongest", "best", "new", "use", "used", "tell"
}

class RAGService:
    def rewrite_query(self, query: str) -> str:
        """Query understanding and rewriting to focus key information retrieval terms."""
        cleaned = query.strip()
        pattern = r'^(?:please|could you please|can you please|tell me|what is|what are|who is|explain|i want to know about|do you know)\s+'
        rewritten = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        rewritten = re.sub(r'[^\w\s]', ' ', rewritten).strip()
        return rewritten if len(rewritten) > 3 else cleaned

    def compute_sparse_score(self, query_terms: List[str], text: str) -> float:
        """Compute BM25-inspired term frequency score for meaningful keyword matching."""
        if not text or not query_terms:
            return 0.0

        meaningful_terms = [t.lower() for t in query_terms if t.lower() not in STOP_WORDS]
        if not meaningful_terms:
            return 0.0

        lower_text = text.lower()
        words = lower_text.split()
        doc_len = len(words)
        if doc_len == 0:
            return 0.0

        score = 0.0
        for term in meaningful_terms:
            tf = words.count(term)
            if tf > 0:
                score += (tf * 2.5) / (tf + 1.2 * (0.25 + 0.75 * (doc_len / 150)))
            elif term in lower_text:
                score += 0.75

        return score

    async def retrieve_chunks(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
        document_ids: Optional[List[uuid.UUID]] = None,
        top_k: int = 5
    ) -> List[Tuple[DocumentChunk, float]]:
        """Hybrid vector + sparse retrieval strictly scoped to user_id."""
        rewritten = self.rewrite_query(query)
        raw_words = re.findall(r'\b\w+\b', rewritten)
        query_terms = [w for w in raw_words if w.lower() not in STOP_WORDS and len(w) > 2]
        query_vector = await embedding_service.get_embedding(rewritten)

        # 1. Fetch user chunks with parent document (User Isolation)
        stmt = (
            select(DocumentChunk)
            .options(selectinload(DocumentChunk.document))
            .where(DocumentChunk.user_id == user_id)
        )
        if document_ids:
            stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))

        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return []

        # 2. Score chunks (Dense + Sparse)
        dense_scores = []
        sparse_scores = []

        for chunk in chunks:
            # Dense cosine similarity
            if chunk.embedding:
                dense_sim = embedding_service.cosine_similarity(query_vector, chunk.embedding)
            else:
                dense_sim = 0.0
            dense_scores.append((chunk, dense_sim))

            # Sparse score
            sp_score = self.compute_sparse_score(query_terms, chunk.content)
            sparse_scores.append((chunk, sp_score))

        # Rank lists
        dense_ranked = sorted(dense_scores, key=lambda x: x[1], reverse=True)
        sparse_ranked = sorted(sparse_scores, key=lambda x: x[1], reverse=True)

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_k = 60
        fused_scores: Dict[uuid.UUID, float] = {}
        chunk_map: Dict[uuid.UUID, DocumentChunk] = {}
        dense_sim_map: Dict[uuid.UUID, float] = {}
        sparse_score_map: Dict[uuid.UUID, float] = {}

        for rank, (chunk, d_sim) in enumerate(dense_ranked):
            chunk_map[chunk.id] = chunk
            dense_sim_map[chunk.id] = d_sim
            fused_scores[chunk.id] = fused_scores.get(chunk.id, 0.0) + (1.0 / (rrf_k + rank + 1))

        for rank, (chunk, sp_sim) in enumerate(sparse_ranked):
            chunk_map[chunk.id] = chunk
            sparse_score_map[chunk.id] = sp_sim
            if sp_sim > 0:
                fused_scores[chunk.id] = fused_scores.get(chunk.id, 0.0) + (1.0 / (rrf_k + rank + 1))

        # Sort by fused score
        sorted_chunks = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        top_candidates = sorted_chunks[:top_k]

        results = []
        for c_id, f_score in top_candidates:
            c = chunk_map[c_id]
            d_sim = dense_sim_map.get(c_id, 0.0)
            sp_score = sparse_score_map.get(c_id, 0.0)
            # True match score: considers both semantic similarity and term match
            rel_score = round(max(d_sim, min(1.0, sp_score / 3.0)), 3)
            results.append((c, rel_score))

        return results

    def build_context_and_citations(
        self,
        chunks_with_scores: List[Tuple[DocumentChunk, float]],
        graph_context: Optional[str] = None
    ) -> Tuple[str, List[Citation]]:
        """Construct prompt context block and structured citation models."""
        context_parts = []
        citations: List[Citation] = []

        if graph_context and graph_context.strip():
            context_parts.append(f"[Knowledge Graph Context]\n{graph_context.strip()}\n")

        for idx, (chunk, score) in enumerate(chunks_with_scores, start=1):
            doc_name = chunk.document.filename if chunk.document else "Document"
            header = f"[Source {idx}: {doc_name} | Page {chunk.page_number or 1} | Section: {chunk.section_heading or 'General'}]"
            safe_content = prompt_guard.sanitize_untrusted_text(chunk.content)
            context_parts.append(f"{header}\n{safe_content}\n")

            excerpt = safe_content[:200].replace("\n", " ").strip()
            if len(safe_content) > 200:
                excerpt += "..."

            citations.append(Citation(
                citation_id=f"c{idx}",
                document_id=str(chunk.document_id),
                document_name=doc_name,
                chunk_id=str(chunk.id),
                page_number=chunk.page_number,
                section=chunk.section_heading,
                excerpt=excerpt,
                relevance_score=score
            ))

        full_context = "\n---\n".join(context_parts)
        return full_context, citations

    async def generate_response(
        self,
        query: str,
        context: str,
        citations: List[Citation],
        memories: Optional[List[Any]] = None,
        graph_context: Optional[str] = None
    ) -> Tuple[str, List[Citation]]:
        """Generate grounded answer using LLM or local grounded synthesizer with memory & graph integration and anti-hallucination."""
        # Check substantive query terms
        raw_words = set(re.findall(r'\b\w+\b', query.lower())) - STOP_WORDS
        substantive_terms = [w for w in raw_words if w not in GENERIC_WORDS]

        # Case 1: No document context, but Knowledge Graph or User Memories may answer
        if not citations:
            if graph_context and graph_context.strip():
                ans = f"Based on your knowledge graph:\n\n{graph_context.strip()}"
                return ans, []
            if memories:
                matching_mems = []
                for m in memories:
                    m_lower = m.content.lower()
                    if any(w in m_lower for w in (substantive_terms or raw_words)):
                        matching_mems.append(m.content)
                if matching_mems:
                    ans = "Based on your remembered profile:\n\n" + "\n\n".join(f"• {m}" for m in matching_mems)
                    return ans, []
            return ANTI_HALLUCINATION_RESPONSE, []

        context_lower = context.lower()
        if substantive_terms:
            substantive_hits = [w for w in substantive_terms if w in context_lower]
            if not substantive_hits:
                if graph_context and graph_context.strip():
                    return f"Based on your knowledge graph:\n\n{graph_context.strip()}", []
                # Check if memories answer what documents do not
                if memories:
                    matching_mems = [m.content for m in memories if any(w in m.content.lower() for w in substantive_terms)]
                    if matching_mems:
                        return "Based on your remembered profile:\n\n" + "\n\n".join(f"• {m}" for m in matching_mems), []
                return ANTI_HALLUCINATION_RESPONSE, []
        else:
            # If all query words were generic, at least one raw word must exist
            if not any(w in context_lower for w in raw_words):
                if graph_context and graph_context.strip():
                    return f"Based on your knowledge graph:\n\n{graph_context.strip()}", []
                return ANTI_HALLUCINATION_RESPONSE, []

        # Remote OpenAI LLM if configured
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
            try:
                import httpx
                mem_directive = ""
                if memories:
                    mem_facts = "\n".join(f"- {m.content}" for m in memories)
                    mem_directive = f"\n\nUser Background & Preferences:\n{mem_facts}"

                sys_instruction = (
                    "You are NEXUS AI, an accurate personal intelligence assistant. "
                    "Answer the user's question using ONLY the provided Source context and Knowledge Graph facts. "
                    "Attribute facts with inline citation brackets like [1], [2] matching the Source numbers when applicable. "
                    f"CRITICAL: If the question cannot be answered from the provided context, reply exactly with: '{ANTI_HALLUCINATION_RESPONSE}'. "
                    "Do not make up facts or extrapolate beyond the provided text."
                )
                safe_prompts = prompt_guard.format_safe_rag_prompt(
                    system_instruction=sys_instruction,
                    user_query=query,
                    retrieved_documents=[{"filename": f"Source {i+1}", "content": c.excerpt} for i, c in enumerate(citations)] if citations else [{"filename": "Sources", "content": context}],
                    user_memories=[m.content for m in memories] if memories else None
                )

                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(
                        f"{settings.OPENAI_BASE_URL}/chat/completions",
                        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                        json={
                            "model": "gpt-4o-mini",
                            "messages": [
                                {"role": "system", "content": safe_prompts["system_prompt"]},
                                {"role": "user", "content": safe_prompts["user_prompt"]}
                            ],
                            "temperature": 0.1
                        }
                    )
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"].strip()
                        if ANTI_HALLUCINATION_RESPONSE in content:
                            return ANTI_HALLUCINATION_RESPONSE, []
                        return content, citations
            except Exception:
                pass

        # Built-in High-Precision Grounded Extractor & Synthesizer
        answer = self._synthesize_local_grounded_answer(
            query=query,
            context=context,
            citations=citations,
            target_terms=substantive_terms or list(raw_words),
            graph_context=graph_context
        )
        if answer == ANTI_HALLUCINATION_RESPONSE:
            if graph_context and graph_context.strip():
                return f"Based on your knowledge graph:\n\n{graph_context.strip()}", []
            if memories:
                matching_mems = [m.content for m in memories if any(w in m.content.lower() for w in (substantive_terms or raw_words))]
                if matching_mems:
                    return "Based on your remembered profile:\n\n" + "\n\n".join(f"• {m}" for m in matching_mems), []
            return ANTI_HALLUCINATION_RESPONSE, []

        return answer, citations

    def _synthesize_local_grounded_answer(
        self,
        query: str,
        context: str,
        citations: List[Citation],
        target_terms: List[str],
        graph_context: Optional[str] = None
    ) -> str:
        """Local fact extraction and synthesis ensuring answer strictly adheres to context."""
        matched_items = []
        source_blocks = context.split("---")

        for b_idx, block in enumerate(source_blocks, start=1):
            if "[Source" not in block and citations:
                continue
            content_only = re.sub(r'\[Source \d+:[^\]]+\]', '', block).strip()
            content_only = re.sub(r'\[Knowledge Graph Context\]', '', content_only).strip()
            if not content_only:
                continue

            lines = [l.strip() for l in content_only.split("\n") if l.strip()]
            for i, line in enumerate(lines):
                line_lower = line.lower()
                matches = sum(1 for w in target_terms if w in line_lower)
                if matches > 0:
                    matched_items.append((matches, i, f"{line} [{b_idx}]" if "[Source" in block else line))
                    # If line is a header or category, include following subordinate bullet points
                    for j in range(i + 1, min(i + 5, len(lines))):
                        sub_l = lines[j]
                        if sub_l.startswith(("-", "*", "•")) or (not sub_l.endswith(":") and len(sub_l) < 120):
                            matched_items.append((matches - 0.05, j, f"{sub_l} [{b_idx}]" if "[Source" in block else sub_l))

        if not matched_items and graph_context:
            for line in graph_context.split("\n"):
                if any(w in line.lower() for w in target_terms):
                    matched_items.append((1.0, 0, line))

        if not matched_items:
            return ANTI_HALLUCINATION_RESPONSE

        # Deduplicate while preserving order of highest matched content
        matched_items.sort(key=lambda x: (x[0], -x[1]), reverse=True)
        seen = set()
        output_lines = []
        for _, _, text in matched_items:
            base_text = re.sub(r'\s*\[\d+\]$', '', text)
            if base_text not in seen:
                seen.add(base_text)
                output_lines.append(text)
            if len(output_lines) >= 7:
                break

        if not citations and graph_context:
            return "Based on your knowledge graph:\n\n" + "\n\n".join(output_lines)
        return "Based on your connected documents:\n\n" + "\n\n".join(output_lines)

    async def stream_rag_response(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
        document_ids: Optional[List[uuid.UUID]] = None,
        top_k: int = 5,
        memories: Optional[List[Any]] = None,
        graph_context: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream RAG response tokens and final citations as an asynchronous generator."""
        if graph_context is None:
            try:
                from app.services.graph.graph_service import graph_service
                graph_context = await graph_service.get_rag_context(user_id=user_id, query=query)
            except Exception:
                graph_context = ""

        chunks_with_scores = await self.retrieve_chunks(
            db=db,
            user_id=user_id,
            query=query,
            document_ids=document_ids,
            top_k=top_k
        )

        context, citations = self.build_context_and_citations(chunks_with_scores, graph_context=graph_context)
        answer, final_citations = await self.generate_response(
            query=query,
            context=context,
            citations=citations,
            memories=memories,
            graph_context=graph_context
        )

        tokens = re.findall(r'\S+|\s+', answer)
        for token in tokens:
            yield {"type": "token", "content": token}

        yield {
            "type": "citations",
            "citations": [c.model_dump() for c in final_citations]
        }
        yield {"type": "done"}

rag_service = RAGService()
