# SPEC draft — Nhom23-403


## Track: VinFast — AI chatbot hỗ trợ mua xe/bảo dưỡng, phân tích review


## Problem statement
Người dùng quan tâm xe VinFast (mua mới hoặc đang sở hữu) phải tự tra rất nhiều
nguồn thông tin rời rạc: website hãng, group Facebook, review YouTube, hotline
dịch vụ. Họ mất thời gian so sánh phiên bản/giá/ưu đãi, không rõ lịch bảo dưỡng
phù hợp, và khó đọc hết review để rút ra kết luận công bằng. AI chatbot có thể
thu thập câu hỏi tự nhiên của khách, gợi ý cấu hình xe phù hợp, nhắc/bóc tách
thông tin bảo dưỡng, và tóm tắt review theo tiêu chí user quan tâm.


## Canvas draft


| | Value | Trust | Feasibility |
|---|-------|-------|-------------|
| Trả lời | Người dùng muốn mua/đang dùng xe VinFast. Pain: loạn thông tin (marketing vs review), khó chọn phiên bản, không nhớ lịch bảo dưỡng. AI: gợi ý 2–3 mẫu/cấu hình phù hợp nhu cầu + ước tính chi phí sở hữu, kèm checklist bảo dưỡng và tóm tắt review theo pros/cons. | Nếu AI tư vấn sai (chọn mẫu/phiên bản không hợp nhu cầu, hiểu lệch review) → user thất vọng, mất niềm tin vào thương hiệu. Cần luôn show nguồn (link spec/khuyến nghị chính thức), tách rõ “thông tin hãng” vs “ý kiến cộng đồng”, và cho phép chuyển nhanh sang tư vấn viên thật. | Có thể dùng RAG trên: spec chính thức của VinFast, bảng giá, tài liệu bảo dưỡng, FAQ; cộng thêm tập review đã được làm sạch. API call ~$0.01/lượt, latency mục tiêu <4s. Risk: dữ liệu review bias, thông tin giá/khuyến mãi lỗi thời. |


**Auto hay aug?** Augmentation — AI là trợ lý tuyến đầu gợi ý mẫu xe/bảo dưỡng,
nhưng quyết định cuối cùng (chốt cấu hình, giá, lịch dịch vụ) vẫn do tư vấn viên
và tài liệu chính thức xác nhận.


**Learning signal:** xem user có bấm “Nói chuyện với tư vấn viên” sau khi được
gợi ý hay không; mẫu xe/bảo dưỡng nào được chốt trong CRM so với gợi ý ban đầu
của AI; đánh giá hài lòng sau tư vấn (thumbs up/down + lý do).


## Hướng đi chính
- Prototype: chatbot hỏi 3–5 câu về nhu cầu (ngân sách, quãng đường, số chỗ,
ưu tiên điện/xăng, nhu cầu bảo dưỡng) → gợi ý 2–3 mẫu/cấu hình + tóm tắt pros/cons
- Thử thêm luồng: user dán 1–2 review dài (hoặc link) → AI tóm tắt thành bullet
theo tiêu chí “hiệu năng”, “tiện nghi”, “chi phí sử dụng”
- Eval: tỉ lệ user “hài lòng với gợi ý” ≥ 80%; top-2 gợi ý trùng với tư vấn viên
ở mức ≥ 70%; thời gian từ câu hỏi đầu đến gợi ý < 2 phút
- Main failure modes: dữ liệu giá/ưu đãi lỗi thời; AI bias theo review cực đoan;
không phân biệt được câu hỏi thông tin hãng vs câu hỏi ý kiến cá nhân


## Phân công
- Tiến: Canvas + failure modes
- Dũng: User stories 4 paths (đúng/không chắc/sai/mất tin)
- Hùng: Eval metrics + ROI (so với quy trình tư vấn hiện tại)
- Phú + Thông: Prototype research + prompt test, chuẩn bị demo flow chat