# Individual reflection — Phùng Hữu Phú (2A202600283)

## 1) Role cụ thể trong nhóm
Mình là người phụ trách **prototype research + prompt test + thiết kế flow chart agent** , tập trung vào việc chuyển ý tưởng trong `spec_draft.md` thành luồng chạy được để demo.

## 2) Phần phụ trách cụ thể (2-3 đóng góp có output rõ)
1. **Xây dựng prototype định hướng agent + tools**
   - Output: prototype vận hành theo luồng hỏi nhu cầu -> truy vấn data local -> bổ sung bằng LLM khi thiếu thông tin -> trả lời có nguồn.
   - Giá trị: giúp nhóm có khung làm việc thống nhất cho cả bản CLI và web demo.

2. **Xây bộ prompt test theo intent**
   - Output: bộ câu test cho các nhóm tác vụ chính: tư vấn mua xe, bảo dưỡng/bảo hành, review, showroom/booking, và case thiếu dữ kiện, các câu hỏi prompt injection.
   - Giá trị: dùng để kiểm tra agent có hỏi ngược đúng, gọi tool đúng, và giữ được cấu trúc trả lời ổn định.

3. **Chuẩn bị flow chart cho agent**
   - Output: 2 sơ đồ chính:
     - sơ đồ 3 tầng xử lý dữ liệu (JSON local -> LLM enrich -> AI fallback),
     - sơ đồ điều phối ToolNode và fallback stack của web search.
   - Giá trị: hỗ trợ demo mạch lạc, đồng thời giúp team debug luồng tool-call nhanh hơn.

## 3) SPEC phần mạnh nhất, yếu nhất? Vì sao?
- **Mạnh nhất:** phần xác định use case và hướng augmentation trong `spec_draft.md` (AI hỗ trợ tư vấn, không thay thế quyết định cuối cùng).  
  **Vì:** bám đúng bối cảnh thực tế của bài toán bán xe, có nhấn mạnh tách nguồn "thông tin hãng" và "ý kiến cộng đồng" nên dễ triển khai thành flow kỹ thuật.

- **Yếu nhất:** phần eval chưa đủ cụ thể về cách đo ở mức từng intent.  
  **Vì:** có nêu metric tổng quan, nhưng thiếu bộ test tiêu chuẩn và quy trình chấm định lượng cho từng tác vụ (ví dụ: đủ trường booking, độ đúng của khuyến nghị, độ nhất quán nhãn nguồn).

## 4) Đóng góp cụ thể khác với mục 2
- Hỗ trợ rà và tinh chỉnh system prompt để giảm trả lời mơ hồ, tăng yêu cầu ghi nhãn nguồn rõ ràng.
- Hỗ trợ debug các case agent dễ đi lệch luồng (hỏi thiếu dữ kiện nhưng trả lời ngay, hoặc trả lời quá tự tin khi chưa đủ thông tin).
- Hỗ trợ nhóm chuẩn bị nội dung thuyết trình demo theo logic "data first, tool second, AI enrich last" để giải thích kiến trúc nhất quán.
-Xây dựng Slide thuyết trình Demo và báo cáo Demo trước các nhóm khác.

## 5) 1 điều học được trong hackathon mà trước đó chưa biết
-Mình học được rằng với bài toán chatbot thực tế, **chất lượng không nằm ở prompt hay**, mà nằm ở **thiết kế orchestration giữa dữ liệu, tools và flow hội thoại**; nếu không có flow rõ, model sẽ dễ trả lời đúng câu chữ nhưng sai quy trình nghiệp vụ.
-Việc test agent sau khi xây dựng là rất quan trọng, mình đã tìm ra được khá nhiều lỗi ngớ ngẩn của agent và đã fix được trước khi demo sản phẩm.

## 6) Nếu làm lại, mình sẽ đổi gì?
Mình sẽ tạo ngay từ đầu một file test chuẩn (dạng bảng) cho từng intent, mỗi test có 4 cột bắt buộc: `input`, `tool expected`, `output constraints`, `pass/fail`.  
Làm vậy thì từ giữa sprint đã đo được chất lượng và biết chính xác đang hỏng ở prompt, ở tool hay ở dữ liệu, thay vì chờ gần demo mới sửa dồn.

## 7) AI giúp gì? AI sai/mislead ở đâu?
- **AI giúp:** tăng tốc brainstorming flow, gợi ý cấu trúc prompt theo intent, và sinh nhanh nhiều biến thể câu test để phủ case.
- **AI sai/mislead:** có lúc đề xuất giải pháp vượt phạm vi hackathon (đòi realtime inventory, tích hợp quá nhiều nguồn web, xây dựng backend phức tạp), dễ làm team lệch scope nếu không kiểm soát.
- **Cách mình rút kinh nghiệm:** luôn chốt lại với tiêu chí "có demo được trong thời gian còn lại không" trước khi nhận đề xuất từ AI.
