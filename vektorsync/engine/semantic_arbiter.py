from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class LatentSemanticConvergenceArbiter:
    CONVERGENCE_SIMILARITY_THRESHOLD = 0.80

    @classmethod
    def evaluate_semantic_alignment(cls, text_server: str, text_client: str) -> dict:
        if text_server.strip() == text_client.strip():
            return {
                "aligned": True,
                "similarity_score": 1.0,
                "resolved_text": text_client,
                "diagnostic": "Deterministic text equivalence"
            }

        if not text_server.strip() or not text_client.strip():
            return {
                "aligned": False,
                "similarity_score": 0.0,
                "resolved_text": None,
                "diagnostic": "Unilateral content deletion detected"
            }

        vectorizer = TfidfVectorizer(ngram_range=(1, 3), analyzer="char_wb")
        tfidf_vectors = vectorizer.fit_transform([text_server, text_client])
        score = float(cosine_similarity(tfidf_vectors[0:1], tfidf_vectors[1:2])[0][0])

        if score >= cls.CONVERGENCE_SIMILARITY_THRESHOLD:
            optimal_text = text_client if len(text_client) >= len(text_server) else text_server
            return {
                "aligned": True,
                "similarity_score": round(score, 4),
                "resolved_text": optimal_text,
                "diagnostic": f"Semantic alignment confirmed (Cosine: {round(score, 2)} >= {cls.CONVERGENCE_SIMILARITY_THRESHOLD})"
            }
        else:
            return {
                "aligned": False,
                "similarity_score": round(score, 4),
                "resolved_text": None,
                "diagnostic": f"Semantic divergence confirmed (Cosine: {round(score, 2)} < {cls.CONVERGENCE_SIMILARITY_THRESHOLD})"
            }