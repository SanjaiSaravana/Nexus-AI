import io
import pytest
from app.evaluation.dataset import EVAL_DOCUMENTS, EVAL_BENCHMARK_CASES
from app.evaluation.evaluate import RAGEvaluator
from app.services.rag_service import rag_service, ANTI_HALLUCINATION_RESPONSE

@pytest.mark.asyncio
async def test_rag_evaluation_benchmark(client, user_a_headers):
    # 1. Ingest evaluation documents for User A
    doc_map = {}
    for doc_info in EVAL_DOCUMENTS:
        files = {
            "file": (doc_info["filename"], io.BytesIO(doc_info["content"].encode("utf-8")), "text/plain")
        }
        resp = await client.post("/documents/upload", files=files, headers=user_a_headers)
        assert resp.status_code == 201
        doc_map[doc_info["filename"]] = resp.json()["document"]["id"]

    results = []

    # 2. Run benchmark cases
    for case in EVAL_BENCHMARK_CASES:
        query = case["query"]
        expected_doc = case["expected_doc"]
        expected_keywords = case["expected_keywords"]
        is_answerable = case["is_answerable"]

        chat_resp = await client.post(
            "/chat/query",
            json={"message": query},
            headers=user_a_headers
        )
        assert chat_resp.status_code == 200
        data = chat_resp.json()

        answer = data["answer"]
        citations = data["citations"]

        ans_rel = RAGEvaluator.evaluate_answer_relevance(answer, expected_keywords, is_answerable)
        cited_doc_content = " ".join(d["content"] for d in EVAL_DOCUMENTS if any(c["document_name"] == d["filename"] for c in citations))
        faith = RAGEvaluator.evaluate_faithfulness(answer, cited_doc_content, is_answerable)
        cit_corr = 1.0 if not is_answerable and len(citations) == 0 else (
            1.0 if any(c["document_name"] == expected_doc for c in citations) else 0.0
        )

        results.append({
            "id": case["id"],
            "answer_relevance": ans_rel,
            "faithfulness": faith,
            "citation_correctness": cit_corr,
            "answer": answer[:80]
        })

    # Summary checks
    avg_relevance = sum(r["answer_relevance"] for r in results) / len(results)
    avg_faithfulness = sum(r["faithfulness"] for r in results) / len(results)
    avg_citation = sum(r["citation_correctness"] for r in results) / len(results)

    print(f"\n--- RAG EVALUATION BENCHMARK METRICS ---")
    print(f"Answer Relevance: {avg_relevance:.2%}")
    print(f"Faithfulness: {avg_faithfulness:.2%}")
    print(f"Citation Correctness: {avg_citation:.2%}")

    assert avg_relevance >= 0.75, f"Answer relevance too low: {avg_relevance}"
    assert avg_faithfulness >= 0.85, f"Faithfulness too low: {avg_faithfulness}"
    assert avg_citation >= 0.80, f"Citation correctness too low: {avg_citation}"
