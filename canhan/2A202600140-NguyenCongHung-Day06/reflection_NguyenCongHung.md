# Individual reflection — Nguyễn Công Hùng (2A202600140)

## 1. Role
Agent developer + data contributor + conversation flow designer.  
Phụ trách thu thập dữ liệu xe điện VinFast, xây dựng agent chatbot bằng LangChain/LangGraph, phát triển các tools cho agent, và tham gia thiết kế luồng hội thoại cho các tình huống như tư vấn mua xe, hỏi thông tin xe, tìm showroom, và đặt lịch hẹn xem xe.

## 2. Đóng góp cụ thể
- Thu thập và chuẩn hóa dữ liệu về các dòng xe điện VinFast để chatbot có thể trả lời các câu hỏi cơ bản như giá, phân khúc, số chỗ, tầm hoạt động, và đối tượng sử dụng phù hợp.
- Xây dựng agent chatbot có khả năng xử lý nhiều ý định khác nhau thay vì chỉ trả lời theo kịch bản cố định, bao gồm:
  - tư vấn mua xe theo nhu cầu và ngân sách,
  - hỏi đáp thông tin về xe điện VinFast,
  - hỗ trợ tìm showroom,
  - hỗ trợ đặt lịch hẹn xem xe.
- Xây dựng các tools cho agent, ví dụ:
  - tool tra cứu thông tin xe từ dữ liệu nội bộ,
  - tool so sánh các mẫu xe,
  - tool hỗ trợ tư vấn chọn xe theo nhu cầu,
  - tool lưu thông tin đặt lịch hẹn của khách hàng dưới dạng JSON,
  - tool hỗ trợ tra cứu thông tin bảo hành / showroom từ web khi cần.
- Tham gia thiết kế conversation flow để chatbot biết khi nào nên hỏi thêm thông tin, khi nào nên gọi tool, và khi nào nên đưa ra gợi ý cụ thể cho người dùng.
- Hỗ trợ test nhiều câu hỏi thực tế để kiểm tra agent có trả lời đúng luồng và dùng đúng tool hay không.

## 3. SPEC mạnh/yếu
- **Mạnh nhất:** nhóm xác định khá rõ các use case thực tế của chatbot VinFast, không chỉ dừng ở hỏi đáp thông tin xe mà còn mở rộng sang tư vấn mua xe và đặt lịch hẹn showroom. Phần flow hội thoại vì vậy có tính ứng dụng cao hơn một chatbot FAQ thông thường.
- **Mạnh nhất tiếp theo:** nhóm bắt đầu nghĩ theo hướng agent + tools thay vì chỉ prompt trực tiếp cho model. Điều này giúp hệ thống rõ vai trò hơn: model dùng để suy luận, còn dữ liệu và hành động nằm ở tools.
- **Yếu nhất:** phần đánh giá chất lượng hệ thống chưa thật sự sâu. Nhóm mới test theo case thủ công là chính, chưa có bộ tiêu chí rõ ràng cho từng chức năng, ví dụ:
  - tư vấn mua xe đúng nhu cầu đến mức nào,
  - agent có hỏi đủ thông tin trước khi đặt lịch hay chưa,
  - câu trả lời về showroom/bảo hành có đáng tin cậy và nhất quán không.
- **Yếu tiếp theo:** phần assumption về dữ liệu showroom và tồn xe còn hạn chế vì chưa có nguồn realtime. Agent có thể hỗ trợ tìm showroom và hướng dẫn đặt lịch, nhưng câu hỏi “showroom nào còn xe” vẫn cần ghi rõ mức độ chắc chắn và xác nhận lại với showroom thực tế.

## 4. Đóng góp khác
- Tham gia thiết kế luồng hội thoại cho các tình huống quan trọng như:
  - khách hỏi chung chung “nên mua xe nào”,
  - khách muốn tìm showroom gần mình,
  - khách muốn đặt lịch xem xe nhưng chưa cung cấp đủ thông tin,
  - khách hỏi về chính sách bảo hành.
- Đề xuất chatbot cần thu đủ 4 trường khi đặt lịch hẹn gồm: họ tên, số điện thoại, showroom, ngày giờ; sau đó lưu thành JSON để có thể xử lý tiếp ở backend.
- Hỗ trợ kiểm thử các tình huống bảo mật cơ bản như prompt injection, yêu cầu lộ system prompt, lộ API key, hoặc truy cập dữ liệu nội bộ ngoài phạm vi chatbot.
- Hỗ trợ tinh chỉnh system prompt để agent tập trung đúng vai trò: tư vấn xe, hỏi lại khi thiếu dữ kiện, không bịa thông tin, và ưu tiên gọi tool khi cần dữ liệu.

## 5. Điều học được
Trước hackathon, mình nghĩ chatbot chủ yếu là viết prompt tốt. Sau khi làm project này, mình hiểu rõ hơn rằng một chatbot thực tế cần nhiều thành phần hơn:
- dữ liệu phải được chuẩn hóa thì câu trả lời mới ổn định,
- agent phải biết lúc nào cần suy luận và lúc nào cần dùng tool,
- conversation flow rất quan trọng vì người dùng thường hỏi thiếu thông tin hoặc đổi ý giữa chừng,
- với bài toán tư vấn sản phẩm, chất lượng không chỉ nằm ở “trả lời đúng”, mà còn ở việc hỏi đúng câu bổ sung và dẫn người dùng đến hành động tiếp theo như đặt lịch xem xe.

Mình cũng học được rằng việc xây chatbot cho sản phẩm thực tế giống làm product hơn là chỉ làm mô hình. Ví dụ, câu trả lời tốt không phải lúc nào cũng là câu dài nhất, mà là câu giúp người dùng ra quyết định nhanh hơn: nên chọn mẫu nào, nên đến showroom nào, cần cung cấp gì để đặt lịch.

## 6. Nếu làm lại
Nếu làm lại, mình sẽ làm 3 việc sớm hơn:
- Chuẩn hóa schema dữ liệu xe ngay từ đầu để tránh phải sửa nhiều chỗ khi thêm tool mới.
- Thiết kế test cases cho từng chức năng từ sớm, thay vì xây agent trước rồi mới test dồn ở cuối.
- Tách rõ hơn giữa phần “trả lời từ dữ liệu nội bộ” và phần “tra cứu web” để dễ kiểm soát độ tin cậy của câu trả lời.

Ngoài ra, mình cũng sẽ ưu tiên làm demo end-to-end sớm hơn, đặc biệt là flow đặt lịch hẹn, vì đây là chức năng dễ nhìn thấy giá trị nhất trong bối cảnh tư vấn bán xe.

## 7. AI giúp gì / AI sai gì
- **Giúp:** AI hỗ trợ mình khá tốt trong việc brainstorm kiến trúc agent, viết nhanh khung code cho LangChain/LangGraph, gợi ý cách tổ chức tools, và đề xuất các câu test cho chatbot. AI cũng giúp tăng tốc việc viết prompt và sửa logic flow.
- **Sai/mislead:** AI đôi khi gợi ý các chức năng nghe rất hay nhưng vượt quá scope hackathon, ví dụ cố gắng làm quá nhiều thứ như tồn kho realtime, booking đầy đủ backend, hay tích hợp nhiều nguồn dữ liệu ngoài khả năng của nhóm trong thời gian ngắn. Nếu không kiểm soát scope, rất dễ bị lan man.
- **Bài học:** AI rất tốt để tăng tốc triển khai và brainstorming, nhưng vẫn cần người quyết định phạm vi, độ ưu tiên, và mức độ thực tế của tính năng trong thời gian hackathon.