# Prototype — AI chatbot tư vấn xe VinFast

## Mô tả
Chatbot AI hỗ trợ tư vấn mua xe điện VinFast và trả lời các câu hỏi phổ biến về xe, showroom, bảo hành, bảo dưỡng, cũng như hỗ trợ đặt lịch hẹn đến showroom.

Prototype hiện tập trung vào 4 flow chính:
1. Tư vấn chọn xe theo nhu cầu và ngân sách.
2. Hỏi đáp thông tin về các dòng xe điện VinFast.
3. Tìm showroom và hỗ trợ tra cứu thông tin liên quan.
4. Thu thập thông tin đặt lịch hẹn xem xe / lái thử và lưu lại dưới dạng JSON.

## Level: Functional prototype
- Có bản CLI prototype để test nhanh luồng hỏi đáp.
- Có web demo local bằng FastAPI để trình bày trong hackathon.
- Có agent dùng LangGraph + tools để phân tách phần suy luận và phần truy xuất dữ liệu/hành động.
- Có lưu thông tin đặt lịch vào thư mục `thongtindatlich` để mô phỏng bước handoff sang backend / sales team.

## Links
- GitHub repo: https://github.com/bignohtinf/Nhom23-403-Day06
- Web demo local: chạy `uvicorn web_app:app --reload --port 8000`
- Agent code: xem `agent.py` và `agent_v2.py`
- Web app: xem `web_app.py`
- Data: xem thư mục `data/`
- Demo slides: xem file `demo-slides.pdf`
- Booking logs: xem thư mục `thongtindatlich/`

## Tools
- Backend / App: Python, FastAPI
- Agent framework: LangChain, LangGraph
- LLM: OpenAI Chat model (qua biến môi trường trong `.env`)
- Data nguồn nội bộ: JSON files trong `data/`
  - `cars.json`
  - `maintenance.json`
  - `reviews_processed.json`
- Web search / enrichment:
  - Tavily API (nếu có key)
  - SerpAPI (nếu có key)
  - DuckDuckGo fallback scraping
- Frontend demo: HTML template trong thư mục `templates/`

## Cách hoạt động của prototype
1. Người dùng nhập câu hỏi hoặc nhu cầu, ví dụ: ngân sách, số người trong gia đình, mục đích sử dụng, mong muốn xem xe.
2. Agent phân tích ý định của người dùng.
3. Nếu cần dữ liệu nội bộ, agent gọi tools để truy vấn thông tin xe, review, bảo dưỡng.
4. Nếu cần thông tin ngoài dữ liệu local như showroom hoặc chính sách cập nhật, agent có thể gọi web search.
5. Nếu người dùng muốn đặt lịch, chatbot sẽ hỏi đủ các trường cần thiết:
   - Họ tên
   - SĐT
   - Showroom
   - Ngày giờ
6. Sau khi thu đủ thông tin, hệ thống lưu JSON vào thư mục `thongtindatlich`.

## Giá trị của prototype
- Thay vì chỉ là FAQ bot, prototype hướng đến một sales assistant cho VinFast.
- Chatbot không chỉ trả lời thông tin xe mà còn hỗ trợ chuyển đổi hành động, ví dụ đặt lịch đi xem showroom.
- Kiến trúc agent + tools giúp dễ mở rộng thêm các tính năng như kiểm tra tồn xe, test drive, CRM handoff, hoặc dashboard quản lý lịch hẹn.

## Điểm mạnh hiện tại
- Có dữ liệu nội bộ để trả lời các câu hỏi cơ bản về xe.
- Có web demo local, dễ mang đi trình bày.
- Có flow đặt lịch, gần với use case thực tế trong bán xe.
- Có thể mở rộng theo hướng production tốt hơn chatbot chỉ prompt thuần.

## Hạn chế hiện tại
- Thông tin showroom / tồn xe chưa phải dữ liệu realtime chính thức end-to-end.
- Phần lưu lịch hiện mới dừng ở mức JSON file, chưa nối CRM hay database thật.

## Phân công
| Thành viên | Phần | Output |
|-----------|------|--------|
| Nguyễn Công Hùng & Bùi Đức Tiến | Thu thập dữ liệu xe điện VinFast; Xây dựng agent và tools | `agent.py`, `agent_v2.py`, `data/` |
| Phùng Hữu Phú | Thiết kế flow tư vấn / showroom / đặt lịch; Prototype research | logic hội thoại trong agent + demo flow |
| Chu Thành Thông | Web demo local, báo cáo, promt test | `web_app.py`, `templates/`, `demo-slides.pdf`, README |
