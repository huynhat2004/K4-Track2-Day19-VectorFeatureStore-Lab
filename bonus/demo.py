from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bonus.agent import HybridMemoryAgent


def seed(agent: HybridMemoryAgent) -> None:
    memories = [
        "Tôi đã đọc ghi chú Kubernetes về Horizontal Pod Autoscaler, readiness probe và cách scale deployment khi CPU tăng.",
        "Bài cloud security nhấn mạnh IAM least privilege, network policy, secret rotation và audit log cho workload trên Kubernetes.",
        "Tài liệu autoscaling giải thích queue depth, target tracking và tự động mở rộng hạ tầng theo lưu lượng người dùng.",
        "Ghi chú về vector database: hybrid search kết hợp BM25 với embedding để xử lý query tiếng Việt lẫn thuật ngữ tiếng Anh.",
        "Người dùng thích bản tóm tắt ngắn bằng tiếng Việt, ưu tiên chủ đề cloud, security và AI ứng dụng trong hệ thống production.",
    ]
    for text in memories:
        agent.remember(text, user_id="u_001")


def main() -> None:
    agent = HybridMemoryAgent()
    seed(agent)
    queries = [
        "Tôi đã đọc gì về Kubernetes?",
        "Gợi ý tôi nên đọc gì tiếp",
        "Tôi đang quan tâm gì gần đây?",
        "Tài liệu về tự động mở rộng hạ tầng?",
        "Cho tôi summary cloud security",
    ]
    for i, query in enumerate(queries, 1):
        print(f"\n=== Câu hỏi {i}: {query} ===")
        print(agent.recall(query, user_id="u_001"))


if __name__ == "__main__":
    main()
