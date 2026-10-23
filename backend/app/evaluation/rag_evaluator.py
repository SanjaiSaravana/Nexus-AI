"""
RAG Evaluator implementing standardized evaluation metrics:
- Context Precision: Proportion of retrieved chunks that contain target facts.
- Context Recall: Proportion of ground truth facts/documents found in the retrieved context.
- Answer Relevance: Alignment of the answer with the query intent and target answer.
- Faithfulness: Verification that claims in the answer are grounded in context without hallucination.
- Citation Accuracy: Verification that citations reference existing documents with accurate excerpts.
"""

import re
from typing import Dict, Any, List, Optional
from app.services.rag_service import ANTI_HALLUCINATION_RESPONSE

class RAGEvaluator:
    """Evaluates RAG pipeline components against golden benchmark datasets."""

    @staticmethod
    def evaluate_context_precision(
        retrieved_chunks_with_scores: list,
        expected_keywords: List[str],
        expected_docs: List[str]
    ) -> float:
        """
        Context Precision = (relevant retrieved chunks) / (total retrieved chunks).
        A chunk is considered relevant if it belongs to an expected document or contains target keywords.
        """
        if not retrieved_chunks_with_scores:
            # If nothing was retrieved and none expected, precision is 1.0; else 0.0
            return 1.0 if not expected_docs else 0.0

        if not expected_docs and not expected_keywords:
            # Unanswerable query: retrieving nothing is ideal (1.0), retrieving chunks is 0.0
            return 0.0 if retrieved_chunks_with_scores else 1.0

        relevant_count = 0
        for chunk, _ in retrieved_chunks_with_scores:
            c_doc = getattr(getattr(chunk, "document", None), "filename", "") or ""
            c_text = (getattr(chunk, "content", "") or "").lower()

            doc_match = any(doc.lower() in c_doc.lower() for doc in expected_docs) if expected_docs else False
            keyword_match = any(k.lower() in c_text for k in expected_keywords) if expected_keywords else False

            if doc_match or keyword_match:
                relevant_count += 1

        return round(relevant_count / len(retrieved_chunks_with_scores), 3)

    @staticmethod
    def evaluate_context_recall(
        retrieved_chunks_with_scores: list,
        expected_snippets: List[str],
        expected_docs: List[str]
    ) -> float:
        """
        Context Recall = (ground truth items retrieved) / (total ground truth items).
        Measures whether the retrieval pipeline captured all key context pieces.
        """
        if not expected_docs and not expected_snippets:
            # Negative/unanswerable queries have no ground truth context
            return 1.0

        retrieved_text = " ".join([
            (getattr(chunk, "content", "") or "").lower()
            for chunk, _ in retrieved_chunks_with_scores
        ])
        retrieved_docs = {
            (getattr(getattr(chunk, "document", None), "filename", "") or "").lower()
            for chunk, _ in retrieved_chunks_with_scores
        }

        # Check document coverage
        doc_matches = sum(1 for d in expected_docs if any(d.lower() in rd for rd in retrieved_docs)) if expected_docs else 0
        total_docs = len(expected_docs)

        # Check snippet/fact coverage
        snippet_matches = 0
        for s in expected_snippets:
            # Look for overlapping words (excluding stop words)
            words = [w.lower() for w in re.split(r'\W+', s) if len(w) > 3]
            if words and any(w in retrieved_text for w in words):
                snippet_matches += 1
        total_snippets = len(expected_snippets)

        total_expected = total_docs + total_snippets
        if total_expected == 0:
            return 1.0

        total_matched = doc_matches + snippet_matches
        return round(total_matched / total_expected, 3)

    @staticmethod
    def evaluate_answer_relevance(
        answer: str,
        expected_keywords: List[str],
        expected_answer: str,
        is_answerable: bool
    ) -> float:
        """
        Answer Relevance: Evaluates whether the generated response directly answers the user's
        question without extraneous evasion, or properly triggers anti-hallucination.
        """
        ans_clean = (answer or "").strip()

        if not is_answerable:
            # For unanswerable queries, system MUST trigger the anti-hallucination guard
            if ans_clean == ANTI_HALLUCINATION_RESPONSE or "couldn't find sufficient information" in ans_clean.lower():
                return 1.0
            return 0.0

        if ans_clean == ANTI_HALLUCINATION_RESPONSE:
            # Hallucination guard triggered incorrectly on an answerable query
            return 0.0

        ans_lower = ans_clean.lower()
        if not expected_keywords:
            return 1.0 if len(ans_clean) > 20 else 0.5

        # Measure keyword recall in the answer
        keyword_hits = sum(1 for k in expected_keywords if k.lower() in ans_lower)
        relevance_score = keyword_hits / len(expected_keywords)

        return round(min(1.0, relevance_score), 3)

    @staticmethod
    def evaluate_faithfulness(
        answer: str,
        context: str,
        is_answerable: bool
    ) -> float:
        """
        Faithfulness: Verifies that factual statements made in the answer are strictly supported
        by the retrieved context and not fabricated (hallucinated).
        """
        if not is_answerable:
            # If question was unanswerable and handled cleanly, faithfulness is perfect
            return 1.0

        if not answer or answer == ANTI_HALLUCINATION_RESPONSE:
            return 1.0

        # Extract meaningful claim words (length > 3, excluding common syntax and stop words)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', answer.lower())
        stop_words = {
            "based", "your", "connected", "documents", "that", "this", "from",
            "with", "have", "been", "here", "also", "into", "their", "will",
            "more", "some", "which", "about", "could", "would", "these"
        }
        claim_words = [w for w in words if w not in stop_words]
        if not claim_words:
            return 1.0

        ctx_lower = (context or "").lower()
        grounded_claims = sum(1 for w in claim_words if w in ctx_lower)

        return round(grounded_claims / len(claim_words), 3)

    @staticmethod
    def evaluate_citation_accuracy(
        citations: list,
        expected_docs: List[str],
        retrieved_context: str,
        is_answerable: bool
    ) -> float:
        """
        Citation Accuracy: Checks that citations point to valid source documents
        and that the citation excerpt actually exists in the retrieved context.
        """
        if not is_answerable:
            # No citations expected for unanswerable queries
            return 1.0 if not citations else 0.0

        if not citations:
            # Answerable query should cite sources if documents were expected
            return 0.0 if expected_docs else 1.0

        valid_citations = 0
        ctx_lower = (retrieved_context or "").lower()

        for c in citations:
            doc_name = getattr(c, "document_name", None) or (c.get("document_name") if isinstance(c, dict) else "")
            excerpt = getattr(c, "excerpt", None) or (c.get("excerpt") if isinstance(c, dict) else "")

            doc_valid = any(exp.lower() in (doc_name or "").lower() for exp in expected_docs) if expected_docs else True
            excerpt_valid = (len(excerpt or "") >= 10) and ((excerpt or "").lower() in ctx_lower if ctx_lower else True)

            if doc_valid and excerpt_valid:
                valid_citations += 1

        return round(valid_citations / max(1, len(citations)), 3)

rag_evaluator = RAGEvaluator()
