# Reflection — Lab 19

**Tên:** Hà Huy Nhất
**Cohort:** K4
**Path đã chạy:** _lite_

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Trên golden set, hybrid là lựa chọn ổn định nhất và thắng trung bình vì nó
kết hợp tín hiệu exact-match của BM25 với tín hiệu ngữ nghĩa của vector search.
Với `exact` queries, BM25 thường mạnh nhất hoặc ngang hybrid vì query chứa đúng
từ kỹ thuật trong corpus. Với `mixed` queries, hybrid thắng rõ nhất vì một phần
query khớp keyword còn phần còn lại cần semantic signal. Với `paraphrase`, path
lite dùng `BAAI/bge-small-en-v1.5` nên tiếng Việt paraphrase không thật mạnh;
đây là lý do production nên đo lại với model multilingual như `bge-m3`.

Em không dùng hybrid khi query rất exact và latency/cost cần tối thiểu, lúc đó
BM25 đủ tốt. Em cũng không dùng hybrid khi domain chủ yếu là paraphrase đa ngữ
và đã có embedding model tốt, vì pure vector đơn giản hơn và có thể đủ chính xác.

---

## Điều ngạc nhiên nhất khi làm lab này

Điều ngạc nhiên nhất là embedding model choice ảnh hưởng rất rõ: cùng một
pipeline hybrid nhưng semantic search trên tiếng Việt paraphrase có thể yếu nếu
model mặc định thiên về tiếng Anh.

---

## Bonus challenge

- [X] Đã làm bonus (xem `bonus/`)
- [ ] Pair work với: _<tên đồng đội nếu có>_
