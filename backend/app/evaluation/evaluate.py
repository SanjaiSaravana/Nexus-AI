from typing import Dict, Any, List
from app.services.rag_service import rag_service, ANTI_HALLUCINATION_RESPONSE

class RAGEvaluator:
    @staticmethod
    def evaluate_retrieval(
        retrieved_chunks_with_scores: list,
        expected_doc: str
    ) -> float:
        """Retrieval Relevance: returns 1.0 if the expected document is in top results, else 0.0."""
        if not expected_doc:
            return 1.0 if not retrieved_chunks_with_scores else 0.5
        for chunk, _ in retrieved_chunks_with_scores:
            if chunk.document and chunk.document.filename == expected_doc:
                return 1.0
        return 0.0

    @staticmethod
    def evaluate_context_precision(
        retrieved_chunks_with_scores: list,
        expected_keywords: List[str]
    ) -> float:
        """Context Precision: proportion of retrieved chunks containing expected key terms."""
        if not retrieved_chunks_with_scores or not expected_keywords:
            return 1.0
        relevant_count = 0
        for chunk, _ in retrieved_chunks_with_scores:
            c_lower = chunk.content.lower()
            if any(k.lower() in c_lower for k in expected_keywords):
                relevant_count += 1
        return round(relevant_count / len(retrieved_chunks_with_scores), 2)

    @staticmethod
    def evaluate_answer_relevance(
        answer: str,
        expected_keywords: List[str],
        is_answerable: bool
    ) -> float:
        """Answer Relevance: does the answer contain target facts or correctly trigger anti-hallucination."""
        if not is_answerable:
            return 1.0 if answer == ANTI_HALLUCINATION_RESPONSE else 0.0

        if answer == ANTI_HALLUCINATION_RESPONSE:
            return 0.0

        ans_lower = answer.lower()
        matches = sum(1 for k in expected_keywords if k.lower() in ans_lower)
        return round(matches / max(1, len(expected_keywords)), 2)

    @staticmethod
    def evaluate_faithfulness(
        answer: str,
        context: str,
        is_answerable: bool
    ) -> float:
        """Faithfulness: verifies facts stated in the answer are grounded in context."""
        if not is_answerable:
            return 1.0 if answer == ANTI_HALLUCINATION_RESPONSE else 0.0

        if answer == ANTI_HALLUCINATION_RESPONSE:
            return 1.0

        # Check if words from answer (excluding stop words) exist in context
        import re
        words = re.findall(r'\b[a-zA-Z]{4,}\b', answer.lower())
        stop_words = {"based", "your", "connected", "documents", "that", "this", "from", "with", "have", "been"}
        fact_words = [w for w in words if w not in stop_words]
        if not fact_words:
            return 1.0

        ctx_lower = context.lower()
        grounded = sum(1 for w in fact_words if w in ctx_lower)
        return round(grounded / len(fact_words), 2)

    @staticmethod
    def evaluate_citation_correctness(
        citations: list,
        expected_doc: str,
        is_answerable: bool
    ) -> float:
        """Citation Correctness: verifies citations point to expected documents with non-empty excerpts."""
        if not is_answerable:
            return 1.0 if len(citations) == 0 else 0.0

        if not citations:
            return 0.0

        valid_citations = 0
        for c in citations:
            if c.document_name == expected_doc and len(c.excerpt) > 10:
                valid_citations += 1

        return round(valid_citations / len(citations), 2)
