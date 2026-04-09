# Individual reflection — Bùi Đức Tiến

---

## 1. Role

**Agent developer · Data contributor · System prompt designer**

- **Data contributor:** Thu thập và chuẩn hóa dữ liệu chính sách bảo trì bảo dưỡng vào `maintenance.json` — bao gồm lịch bảo dưỡng định kỳ theo mốc km/tháng, danh sách hạng mục kiểm tra, và chi phí tham khảo cho từng model VinFast.
- **Agent developer:** Design workflow 3 luồng requests (dữ liệu hệ thống → LLM làm giàu → LLM fallback) và trực tiếp build 3 tool:
  - `calculate_ownership_cost` — tính chi phí phát sinh khi sở hữu xe (giá lăn bánh, góp hàng tháng, phân tích thu nhập)
  - `query_maintenance` — truy xuất lịch bảo dưỡng theo model và mốc km
  - `query_reviews` — phân tích review cộng đồng theo pros/cons
- **System prompt designer:** Đóng góp vào thiết kế system prompt, đặc biệt phần phân biệt nguồn thông tin chính hãng vs cộng đồng.

---

## 2. Đóng góp cụ thể

### 3-tier data workflow
Thiết kế kiến trúc xử lý dữ liệu 3 tầng — đây là quyết định kiến trúc quan trọng nhất mình đóng góp vào dự án:

| Tầng | Hành động | Nhãn hiển thị |
|------|-----------|---------------|
| 1 | Truy xuất file JSON trong `data/` | `[Dữ liệu hệ thống]` |
| 2 | JSON có nhưng thiếu → LLM làm giàu thêm | `[Bổ sung từ AI]` |
| 3 | Không tìm thấy → LLM trả lời từ kiến thức | `[Thông tin tham khảo từ AI]` |

Thiết kế này giải quyết bài toán trust — user biết thông tin đến từ đâu thay vì nhận một câu trả lời không rõ nguồn gốc.

### Tool `calculate_ownership_cost`
Tool phức tạp nhất trong dự án, bao gồm:
- Tính thuế trước bạ theo tỉnh/thành (Hà Nội 12%, các tỉnh khác 10%)
- Áp dụng **công thức annuity** để tính góp hàng tháng:

```
M = P × [r(1+r)^n] / [(1+r)^n - 1]
```

Trong đó `P` = số tiền vay, `r` = lãi suất tháng, `n` = số kỳ. Phần khó nhất là xử lý đúng quy đổi lãi suất năm → tháng và các edge case khi user nhập thiếu thông tin (không có thu nhập, không có số kỳ vay...).

- Phân tích % thu nhập hàng tháng cần dùng để trả góp — giúp user tự đánh giá khả năng mua.

### Tool `query_maintenance`
Truy xuất đúng chunk từ `maintenance.json` theo `model` + `km_milestone`, trả về checklist hạng mục bảo dưỡng và chi phí tham khảo.

### Tool `query_reviews`
Phân tích review cộng đồng, cân bằng pros/cons, gắn nhãn nguồn để chatbot không bị bias theo review cực đoan.

---

## 3. Điểm mạnh / điểm yếu của spec

### Điểm mạnh
- **3-tier workflow rõ ràng** — tách biệt data chính hãng vs AI inference, tăng độ tin cậy của câu trả lời.
- **Booking validation chặt chẽ** — 7 điều kiện kiểm tra giúp tránh đặt lịch sai thực tế (Chủ Nhật, ngoài giờ làm việc, ngày quá khứ...).
- **Web search fallback 3 tầng** (Tavily → SerpAPI → DuckDuckGo) — hệ thống vẫn hoạt động khi không có API key thương mại.
- **Gắn nhãn nguồn** trên mọi câu trả lời — giải quyết trực tiếp failure mode "AI nói sai mà user không biết".

### Điểm yếu
- **Dữ liệu JSON tĩnh** — giá xe, khuyến mãi, chính sách bảo hành thay đổi liên tục nhưng hệ thống không tự cập nhật. User có thể nhận thông tin lỗi thời.
- **Không có TTL (time-to-live)** cho các chunk nhạy cảm về giá — thiếu cơ chế invalidation.
- **Coverage model xe còn hạn chế** — `maintenance.json` chỉ có dữ liệu cho một số model phổ biến, chưa đủ để tư vấn toàn bộ lineup VinFast.
- **Chưa có test tự động** — việc kiểm tra tool `calculate_ownership_cost` chủ yếu bằng tay, dễ bỏ sót edge case.

---

## 4. Đóng góp khác

- Tham gia thiết kế metadata schema cho 2 parts dữ liệu ( electric / service), đặc biệt phần fields `km_milestone`, , và `expires_at`.
- Góp ý về luồng tư vấn mua xe: cấu trúc 3–5 câu hỏi tuần tự thay vì hỏi tất cả cùng lúc — giúp trải nghiệm tự nhiên hơn.
- Viết phần system prompt về quy tắc phân biệt nguồn và cách prefix câu trả lời theo `source_type`.

---

## 5. Điều học được

Trước hackathon, mình nghĩ chatbot chủ yếu là viết prompt tốt. Sau khi làm project này, mình hiểu rõ hơn rằng một chatbot thực tế cần nhiều thành phần hơn:

**Về kiến trúc:**
Prompt chỉ là một lớp. Phần quyết định chất lượng thực sự là kiến trúc dữ liệu và cách retrieve — garbage in, garbage out dù prompt có hay đến đâu. 3-tier workflow mình design là minh chứng: cùng một câu hỏi, nếu không phân tầng rõ ràng thì LLM sẽ hallucinate thông tin giá xe thay vì thú nhận không có dữ liệu.

**Về tool design:**
Mỗi tool cần có contract rõ ràng — input schema, output schema, và đặc biệt là failure modes. Tool `calculate_ownership_cost` dạy mình bài học này: công thức annuity trông đơn giản trên giấy nhưng khi implement cần xử lý hàng chục edge case (lãi suất = 0, kỳ hạn = 0, thu nhập không nhập...) trước khi thực sự dùng được trong production.

**Về LangGraph:**
Graph-based agent orchestration khác hoàn toàn với chain truyền thống — việc debug vòng lặp `agent ↔ tools` phức tạp hơn nhiều so với pipeline tuyến tính. State management giữa các node cần được thiết kế cẩn thận ngay từ đầu.

**Về trust trong AI:**
Gắn nhãn nguồn không phải là tính năng "nice to have" — đó là yêu cầu bắt buộc với bất kỳ AI nào tư vấn về tài chính hay quyết định lớn. User cần biết khi nào AI đang trích dẫn dữ liệu thực tế và khi nào đang suy luận.

---

## 6. Nếu làm lại

**Ưu tiên số 1: Thay JSON tĩnh bằng RAG thực sự.**
Kiến trúc hiện tại dùng JSON file tĩnh là điểm yếu lớn nhất. Nếu làm lại, mình sẽ build RAG pipeline đúng nghĩa từ đầu:
- Vector store (pgvector hoặc Chroma) thay cho flat JSON lookup
- Chunking theo semantic boundary, không theo file
- Metadata filtering theo `model`, `km_milestone`, `expires_at` như đã thiết kế trong schema
- TTL tự động cho chunk chứa giá/khuyến mãi — crawl lại mỗi 7 ngày

Điều này giúp hệ thống scale được khi thêm model mới hay cập nhật chính sách, thay vì phải edit JSON thủ công.

**Ưu tiên số 2: Test coverage cho financial tools.**
`calculate_ownership_cost` là tool ảnh hưởng trực tiếp đến quyết định tài chính của user — sai ở đây có hậu quả thực tế. Mình sẽ viết unit test với ít nhất 20 case bao gồm: vay 0%, vay 100%, thu nhập không đủ, kỳ hạn tối đa, các tỉnh khác nhau.

---

## 7. AI giúp gì / AI sai gì

### AI giúp được
- **Viết boilerplate nhanh:** Scaffold ban đầu cho tool structure, FastAPI endpoint, LangGraph node — tiết kiệm khoảng 2–3 giờ setup.
- **Debug công thức annuity:** Khi implement sai thứ tự tính lãi tháng, AI giải thích đúng ngay lần đầu và chỉ ra edge case mình bỏ sót (khi `r = 0` thì công thức chia cho 0).
- **Gợi ý validation logic:** 7 điều kiện booking phần lớn được AI gợi ý — mình chỉ nghĩ ra 4, AI bổ sung thêm các case như Chủ Nhật và giới hạn 60 ngày.
- **Cấu trúc `maintenance.json`:** AI gợi ý schema phù hợp với cả truy xuất theo km lẫn theo tháng, tiết kiệm thời gian thiết kế.

### AI sai / cần kiểm tra lại
- **Giá xe và chính sách:** AI nhiều lần đưa ra số liệu giá VinFast không chính xác (đặc biệt giá sau ưu đãi). Phải crawl thủ công và không tin số liệu AI generate mà không verify.
- **Tên model và phiên bản:** AI hay nhầm lẫn giữa VF8 Eco/Plus và các phiên bản cũ/mới — cần hardcode danh sách model chính xác thay vì để AI tự điền.
- **Lịch bảo dưỡng:** AI suy luận lịch bảo dưỡng từ pattern chung của ngành ô tô, không phải từ owner manual thực tế của VinFast. Đây là lý do mình phải thu thập `maintenance.json` từ tài liệu chính hãng thay vì dùng AI generate.
- **LangGraph syntax:** Một số snippet AI đề xuất dùng API cũ của LangGraph (trước v0.2), phải đọc doc trực tiếp để sửa lại.
