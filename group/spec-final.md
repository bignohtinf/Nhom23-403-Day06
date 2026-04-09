# SPEC — VinFast AI Chatbot

**Nhóm:** Nhom23-403
**Track:** ☑ VinFast · ☐ Vinmec · ☐ VinUni-VinSchool · ☐ XanhSM · ☐ Open
**Problem statement (1 câu):** Khách hàng quan tâm xe VinFast phải tự tra cứu nhiều nguồn thông tin rời rạc (website, Facebook, YouTube, hotline) → mất thời gian so sánh giá/phiên bản, không rõ lịch bảo dưỡng, khó đọc review. AI chatbot giúp gợi ý xe phù hợp, tóm tắt bảo dưỡng, và phân tích review theo tiêu chí.

---

## 1. AI Product Canvas

|   | Value | Trust | Feasibility |
|---|-------|-------|-------------|
| **Câu hỏi** | User nào? Pain gì? AI giải gì? | Khi AI sai thì sao? User sửa bằng cách nào? | Cost/latency bao nhiêu? Risk chính? |
| **Trả lời** | Khách hàng mua/sở hữu xe VinFast. Pain: loạn thông tin (marketing vs review thực), khó chọn phiên bản, quên lịch bảo dưỡng. AI: gợi ý 2–3 mẫu/cấu hình phù hợp nhu cầu + ước tính chi phí sở hữu, kèm checklist bảo dưỡng và tóm tắt review theo pros/cons. | Nếu AI tư vấn sai (chọn mẫu không hợp, hiểu lệch review) → user thất vọng, mất niềm tin. Cần luôn show nguồn (link chính hãng), tách rõ "thông tin hãng" vs "ý kiến cộng đồng", cho phép chuyển sang tư vấn viên thật. | Dùng RAG trên: spec chính thức VinFast, bảng giá, tài liệu bảo dưỡng, FAQ, review đã làm sạch. API call ~$0.01/lượt, latency <4s. Risk: dữ liệu giá lỗi thời, review bias, hallucination. |

**Automation hay augmentation?** ☐ Automation · ☑ Augmentation
Justify: *Augmentation — AI là trợ lý tuyến đầu gợi ý mẫu xe/bảo dưỡng, nhưng quyết định cuối cùng (chốt cấu hình, giá, lịch dịch vụ) vẫn do tư vấn viên và tài liệu chính thức xác nhận. User thấy gợi ý, chấp nhận/từ chối, cost of reject = 0.*

**Learning signal:**

1. User correction đi vào đâu? → Chat history + feedback form (thumbs up/down + lý do)
2. Product thu signal gì để biết tốt lên hay tệ đi? → Tỉ lệ user "hài lòng với gợi ý" ≥ 80%; top-2 gợi ý trùng với tư vấn viên ≥ 70%; thời gian từ câu hỏi đầu đến gợi ý < 2 phút
3. Data thuộc loại nào? ☑ User-specific · ☑ Domain-specific · ☑ Real-time · ☑ Human-judgment · ☐ Khác
   Có marginal value không? (Model đã biết cái này chưa?) → Có. Dữ liệu VinFast cụ thể (giá, bảo hành, review) không có trong training data của LLM. RAG + web search cung cấp thông tin real-time.

---

## 2. User Stories — 4 paths

### Feature 1: Tư vấn mẫu xe phù hợp nhu cầu

**Trigger:** User nhập câu hỏi về nhu cầu mua xe (ngân sách, quãng đường, số chỗ, ưu tiên điện/xăng, bảo hành, đánh giá người dùng)

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy — AI đúng, tự tin** | User thấy gì? Flow kết thúc ra sao? | User hỏi "Tôi có 800 triệu, gia đình 4 người, di nội thành, chưa có chỗ sạc" → AI gợi ý VF 3, VF 5 với pros/cons → User bấm "Đặt lịch lái thử" hoặc "Nói chuyện với tư vấn viên" |
| **Low-confidence — AI không chắc** | System báo "không chắc" bằng cách nào? User quyết thế nào? | User hỏi câu mơ hồ "Xe nào tốt nhất?" → AI hiển thị 3 mẫu + confidence % + "Bạn có thể cung cấp thêm thông tin về ngân sách/nhu cầu không?" |
| **Failure — AI sai** | User biết AI sai bằng cách nào? Recover ra sao? | AI gợi ý VF 9 (1.2 tỷ) cho user có ngân sách 500 triệu → User thấy giá quá cao → Bấm "Không phù hợp" → AI hỏi lại tiêu chí |
| **Correction — user sửa** | User sửa bằng cách nào? Data đó đi vào đâu? | User bấm "Không phù hợp" + chọn lý do "Giá quá cao" → Feedback lưu vào Firestore → Cải thiện prompt/scoring |

### Feature 2: Tóm tắt bảo dưỡng & bảo hành

**Trigger:** User hỏi "Bảo hành bao lâu?", "Bảo dưỡng bao giờ?", "Chi phí bảo dưỡng bao nhiêu?"

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy — Dữ liệu đầy đủ** | User thấy gì? | User hỏi "VF 5 bảo hành bao lâu?" → AI trả: "Pin 8 năm, khung gầm 5 năm, bộ phận khác 3 năm" + link chính hãng |
| **Low-confidence — Dữ liệu thiếu** | System báo thiếu thông tin? | User hỏi "Chi phí bảo dưỡng VF 7 bao nhiêu?" → Dữ liệu JSON thiếu → AI: "[Thông tin tham khảo từ AI] Bảo dưỡng định kỳ ~2-3 triệu/lần. Liên hệ hotline 1900 23 23 89 để xác nhận chính xác" |
| **Failure — Thông tin sai** | User biết sai bằng cách nào? | AI nói "VF 3 bảo hành 10 năm" (sai, chỉ 8 năm) → User liên hệ hotline → Phát hiện sai → Feedback |
| **Correction — User báo sai** | User báo sai bằng cách nào? | Bấm "Thông tin này không chính xác" → Ghi chú → Lưu vào log → Team review + update data |

### Feature 3: Phân tích review theo tiêu chí

**Trigger:** User hỏi "Mọi người nói gì về VF 6?", "VF 8 có tốt không?", hoặc dán link review

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy — Review đầy đủ** | User thấy gì? | User hỏi "VF 5 có những ưu/nhược điểm gì?" → AI tóm tắt: "✓ Hiệu năng: tăng tốc nhanh, êm ái. ✗ Chi phí: sạc chậm, pin yếu trong mùa đông" |
| **Low-confidence — Review ít** | System báo thiếu review? | User hỏi "VF 9 mọi người nói gì?" → Dữ liệu review ít → AI: "Dữ liệu review hạn chế. Dựa trên [X] review, VF 9 được đánh giá cao về [...]" |
| **Failure — Review bias** | User biết review bias? | Review chỉ từ những người giàu → Gợi ý VF 9 cho user ngân sách 500 triệu → User thất vọng |
| **Correction — User báo bias** | User báo bằng cách nào? | Bấm "Gợi ý này không phù hợp với tôi" + lý do → Feedback lưu vào log |

### Feature 4: Đặt lịch lái thử / tư vấn

**Trigger:** User bấm "Đặt lịch lái thử" hoặc "Nói chuyện với tư vấn viên"

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy — Đặt lịch thành công** | User thấy gì? | User điền form (tên, SĐT, mẫu xe, ngày/giờ) → Validate thành công → Hiển thị "Lịch hẹn đã được tạo. Tư vấn viên sẽ gọi xác nhận trong 30 phút" |
| **Low-confidence — Ngày không hợp lệ** | System báo lỗi? | User chọn Chủ Nhật → AI: "Showroom không hoạt động Chủ Nhật. Vui lòng chọn Thứ Hai-Thứ Bảy" |
| **Failure — Lỗi hệ thống** | User biết lỗi? | Form submit nhưng không lưu được → Hiển thị "Lỗi kết nối. Vui lòng thử lại hoặc gọi 1900 23 23 89" |
| **Correction — User sửa thông tin** | User sửa bằng cách nào? | Bấm "Sửa lịch" → Mở form lại → Thay đổi ngày/giờ → Submit lại |

---

## 3. Eval metrics + threshold

**Optimize precision hay recall?** ☑ Precision · ☐ Recall
Tại sao? *Precision cao hơn recall. Nếu AI gợi ý sai mẫu xe → user thất vọng, mất niềm tin vào thương hiệu. Tốt hơn là gợi ý ít nhưng chính xác, hoặc hỏi lại user để làm rõ nhu cầu.*

Nếu sai ngược lại (recall cao, precision thấp) thì chuyện gì xảy ra? *Nếu recall cao nhưng precision thấp → AI gợi ý quá nhiều mẫu không phù hợp → user bỏ dùng vì không tin tưởng.*

| Metric | Threshold | Red flag (dừng khi) |
|--------|-----------|---------------------|
| Tỉ lệ user "hài lòng với gợi ý" (thumbs up) | ≥ 80% | < 70% trong 1 tuần |
| Top-2 gợi ý trùng với tư vấn viên | ≥ 70% | < 60% trong 1 tuần |
| Thời gian từ câu hỏi đầu đến gợi ý | < 2 phút | > 3 phút (latency quá cao) |
| Tỉ lệ user chuyển sang tư vấn viên sau gợi ý | ≤ 30% | > 50% (gợi ý không đủ tự tin) |
| Accuracy thông tin bảo hành/bảo dưỡng | ≥ 95% | < 90% (dữ liệu sai) |
| Tỉ lệ lỗi hệ thống (500 error, timeout) | < 1% | > 2% |

---

## 4. Top 3 failure modes

*Liệt kê cách product có thể fail — không phải list features.*
*"Failure mode nào user KHÔNG BIẾT bị sai? Đó là cái nguy hiểm nhất."*

| # | Trigger | Hậu quả | Mitigation |
|---|---------|---------|------------|
| 1 | **Dữ liệu giá/ưu đãi lỗi thời** (cập nhật chậm hoặc sai) | AI gợi ý giá cũ → User đến showroom thấy giá khác → Thất vọng, mất niềm tin | Cập nhật dữ liệu giá hàng tuần; Luôn show "Cập nhật lần cuối: [ngày]"; Hỏi user xác nhận giá trước khi đặt lịch |
| 2 | **AI bias theo review cực đoan** (review quá tích cực hoặc quá tiêu cực) | Review chỉ từ những người giàu/khó tính → Gợi ý không phù hợp với đa số user | Phân tích sentiment; Lọc review spam/fake; Hiển thị "Dựa trên [X] review"; Cho user filter theo tiêu chí |
| 3 | **Không phân biệt câu hỏi thông tin hãng vs ý kiến cá nhân** (AI trả lời chung chung) | User hỏi "VF 5 có tốt không?" → AI trả lời mơ hồ → User không biết nên chọn hay không | Phân loại intent rõ ràng; Nếu ý kiến cá nhân → hỏi lại "Bạn quan tâm tiêu chí nào? (Giá, Hiệu năng, Tiện nghi, Chi phí)"; Nếu thông tin hãng → trả lời cụ thể từ dữ liệu |

---

## 5. ROI 3 kịch bản

|   | Conservative | Realistic | Optimistic |
|---|-------------|-----------|------------|
| **Assumption** | 100 user/ngày, 60% hài lòng, 20% đặt lịch | 500 user/ngày, 80% hài lòng, 35% đặt lịch | 2000 user/ngày, 90% hài lòng, 50% đặt lịch |
| **Cost** | $50/ngày inference (OpenAI API) | $200/ngày | $500/ngày |
| **Benefit** | Giảm 2h support/ngày (tư vấn viên) | Giảm 8h/ngày, tăng conversion 15% | Giảm 20h/ngày, tăng retention 5%, tăng conversion 25% |
| **Net** | 2h × $50/h = $100/ngày benefit vs $50 cost = +$50/ngày | 8h × $50/h = $400/ngày benefit vs $200 cost = +$200/ngày | 20h × $50/h = $1000/ngày benefit vs $500 cost = +$500/ngày |

**Kill criteria:** *Khi nào nên dừng?*
- Tỉ lệ hài lòng < 70% trong 2 tuần liên tục
- Cost > benefit trong 2 tháng liên tục
- Accuracy thông tin < 90% (dữ liệu sai quá nhiều)
- Latency > 5 giây (user chờ lâu, bỏ dùng)

---

## 6. Mini AI spec (1 trang)

### Tóm tắt sản phẩm

**VinFast AI Chatbot** là một trợ lý tư vấn xe điện thông minh, giúp khách hàng:
1. **Tư vấn mẫu xe phù hợp** dựa trên nhu cầu (ngân sách, quãng đường, số chỗ, ưu tiên điện/xăng)
2. **Tóm tắt bảo dưỡng & bảo hành** từ tài liệu chính hãng
3. **Phân tích review** theo tiêu chí (Hiệu năng, Tiện nghi, Chi phí)
4. **Đặt lịch lái thử / tư vấn** trực tiếp

**Cho ai?** Khách hàng quan tâm xe VinFast (mua mới hoặc đang sở hữu), muốn tìm hiểu nhanh mà không phải tra cứu nhiều nguồn.

**AI làm gì?** 
- **Augmentation** (không phải Automation): AI gợi ý, user quyết định. Tư vấn viên xác nhận cuối cùng.
- **Retrieval-Augmented Generation (RAG)**: Truy xuất dữ liệu từ JSON (cars.json, maintenance.json, reviews_processed.json) + web search (DuckDuckGo, SerpAPI, Tavily) + LLM (OpenAI GPT-4o-mini) để trả lời.
- **Multi-role support**: Customer (khách hàng), Dealer (cửa hàng), Admin (quản lý hệ thống).

**Quality thế nào?**
- **Precision**: ≥ 80% (gợi ý chính xác)
- **Latency**: < 2 phút (từ câu hỏi đến gợi ý)
- **Accuracy thông tin**: ≥ 95% (bảo hành, bảo dưỡng)

**Risk chính:**
1. Dữ liệu giá/ưu đãi lỗi thời → Cập nhật hàng tuần + show "Cập nhật lần cuối"
2. Review bias → Phân tích sentiment + lọc spam + cho user filter
3. Hallucination → Luôn show nguồn (link chính hãng) + tách "thông tin hãng" vs "ý kiến AI"

**Data flywheel:**
- User hỏi → AI trả lời + lưu chat history
- User feedback (thumbs up/down + lý do) → Cải thiện prompt/scoring
- Tư vấn viên xác nhận gợi ý → Cập nhật training data
- Dữ liệu giá/review mới → Cập nhật JSON + web search

**Tech stack:**
- **Frontend**: Next.js 16 + React 19 + Tailwind CSS (web UI)
- **Backend**: FastAPI (Python) + Firebase (auth, Firestore)
- **AI**: LangGraph (agent loop) + LangChain (RAG) + OpenAI GPT-4o-mini
- **Data**: JSON (cars.json, maintenance.json, reviews_processed.json) + Web search (DuckDuckGo, SerpAPI, Tavily)
- **Deployment**: Docker + Vercel (frontend) + Heroku/Railway (backend)

---


