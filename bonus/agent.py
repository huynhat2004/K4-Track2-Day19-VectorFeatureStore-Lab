from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qdrant_client import QdrantClient, models
from rank_bm25 import BM25Okapi
from app.embeddings import Embedder

ROOT = Path(__file__).resolve().parent.parent
FEAST_DIR = ROOT / "app" / "feast_repo"
COLLECTION = "bonus_hybrid_memory"


@dataclass
class Memory:
    memory_id: str
    user_id: str
    text: str


class HybridMemoryAgent:
    def __init__(self) -> None:
        self.embedder = Embedder()
        self.client = QdrantClient(":memory:")
        self.client.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(size=self.embedder.dim, distance=models.Distance.COSINE),
        )
        self.memories: list[Memory] = []
        self._bm25 = BM25Okapi([["empty"]])

    def remember(self, text: str, user_id: str = "u_001") -> None:
        """Thêm một episodic memory mới cho người dùng."""
        chunks = self._chunk(text)
        start = len(self.memories)
        vectors = list(self.embedder.embed(chunks))
        points = []
        for offset, (chunk, vector) in enumerate(zip(chunks, vectors)):
            memory_id = f"m_{start + offset:04d}"
            self.memories.append(Memory(memory_id, user_id, chunk))
            points.append(models.PointStruct(
                id=start + offset,
                vector=vector.tolist(),
                payload={"memory_id": memory_id, "user_id": user_id, "text": chunk},
            ))
        self.client.upsert(collection_name=COLLECTION, points=points)
        self._rebuild_bm25()

    def recall(self, query: str, user_id: str = "u_001") -> str:
        """Truy xuất top-K memories, ghép với profile features và trả về context."""
        profile = self._get_profile(user_id)
        hits = self._hybrid_search(query, user_id=user_id, top_k=3)
        lines = [
            f"Hồ sơ người dùng {user_id}:",
            f"- preferred_language: {profile['preferred_language']}",
            f"- reading_speed_wpm: {profile['reading_speed_wpm']}",
            f"- topic_affinity: {profile['topic_affinity']}",
            f"- queries_last_hour: {profile['queries_last_hour']}",
            "",
            f"Câu hỏi: {query}",
            "Top memories liên quan:",
        ]
        for i, hit in enumerate(hits, 1):
            lines.append(f"{i}. {hit['text']} (score={hit['score']:.4f})")
        lines.extend([
            "",
            "Chỉ dẫn context cho LLM:",
            "Trả lời bằng tiếng Việt trừ khi user yêu cầu khác; bám vào top memories và điều chỉnh độ sâu theo profile/reading speed.",
        ])
        return "\n".join(lines)

    def _chunk(self, text: str) -> list[str]:
        parts = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
        return parts or [text.strip()]

    def _rebuild_bm25(self) -> None:
        rows = [self._tokens(m.text) for m in self.memories] or [["empty"]]
        self._bm25 = BM25Okapi(rows)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return text.lower().split()

    def _hybrid_search(self, query: str, user_id: str, top_k: int = 3) -> list[dict[str, object]]:
        if not self.memories:
            return []
        sparse = self._keyword_search(query, user_id, depth=max(10, top_k * 4))
        dense = self._vector_search(query, user_id, depth=max(10, top_k * 4))
        scores: dict[str, float] = {}
        meta: dict[str, dict[str, object]] = {}
        for hits in (sparse, dense):
            for rank, hit in enumerate(hits, start=1):
                scores[hit["memory_id"]] = scores.get(hit["memory_id"], 0.0) + 1.0 / (60 + rank)
                meta.setdefault(hit["memory_id"], hit)
        ordered = sorted(scores.items(), key=lambda kv: -kv[1])[:top_k]
        return [{**meta[mid], "score": score} for mid, score in ordered]

    def _keyword_search(self, query: str, user_id: str, depth: int) -> list[dict[str, object]]:
        scores = self._bm25.get_scores(self._tokens(query))
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])
        hits = []
        for idx in ranked:
            m = self.memories[idx]
            if m.user_id == user_id:
                hits.append({"memory_id": m.memory_id, "text": m.text, "score": float(scores[idx])})
            if len(hits) >= depth:
                break
        return hits

    def _vector_search(self, query: str, user_id: str, depth: int) -> list[dict[str, object]]:
        q_vec = next(self.embedder.embed([query])).tolist()
        flt = models.Filter(must=[
            models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))
        ])
        pts = self.client.query_points(collection_name=COLLECTION, query=q_vec, query_filter=flt, limit=depth).points
        return [
            {"memory_id": p.payload["memory_id"], "text": p.payload["text"], "score": float(p.score)}
            for p in pts
        ]

    def _get_profile(self, user_id: str) -> dict[str, object]:
        fallback = {
            "preferred_language": "vi",
            "reading_speed_wpm": 220,
            "topic_affinity": "cloud",
            "queries_last_hour": 8,
        }
        try:
            from feast import FeatureStore
            fs = FeatureStore(repo_path=str(FEAST_DIR))
            data = fs.get_online_features(
                features=[
                    "user_profile_features:reading_speed_wpm",
                    "user_profile_features:preferred_language",
                    "user_profile_features:topic_affinity",
                    "query_velocity_features:queries_last_hour",
                ],
                entity_rows=[{"user_id": user_id}],
            ).to_dict()
            return {
                "reading_speed_wpm": data["reading_speed_wpm"][0] or fallback["reading_speed_wpm"],
                "preferred_language": data["preferred_language"][0] or fallback["preferred_language"],
                "topic_affinity": data["topic_affinity"][0] or fallback["topic_affinity"],
                "queries_last_hour": data["queries_last_hour"][0] or fallback["queries_last_hour"],
            }
        except Exception:
            return fallback
