# Individual reflection — Chủ Thành Thông (2A202600014)

## 1. Role cụ thể trong nhóm
Mình là người phụ trách **Frontend Development, Spec Design, Metrics & Evaluation Framework, và Dataset Construction** cho VinFast AI Chatbot. Tập trung vào việc xây dựng giao diện người dùng, định nghĩa tiêu chí đánh giá chất lượng, và chuẩn bị bộ dữ liệu test toàn diện.

## 2. Phần phụ trách cụ thể (3 đóng góp có output rõ)

### 2.1 Xây dựng Frontend Web UI (Next.js + React + Tailwind CSS)
- **Output:** 
  - Hoàn thành giao diện chatbot đầy đủ với 4 trang chính: Home, Models, Warranty, Chatbot
  - Hỗ trợ 3 role (Customer, Dealer, Admin) với UI/UX khác nhau
  - Tích hợp appointment booking form với validation
  - Responsive design cho mobile/tablet/desktop
  - Real-time chat interface với auto-scroll
  - Quick replies context-aware theo role
  
- **Giá trị:** 
  - Cung cấp giao diện chuyên nghiệp để demo sản phẩm
  - Cho phép user tương tác trực tiếp với agent thay vì chỉ CLI
  - Hỗ trợ multi-role giúp kiểm thử các luồng khác nhau
  - Tăng trải nghiệm người dùng và khả năng chuyển đổi (conversion)

### 2.2 Thiết kế Spec & Requirements Document (EARS + INCOSE)
- **Output:**
  - Hoàn thành `01-spec-template.md` với 7 phần chi tiết:
    - AI Product Canvas (Value, Trust, Feasibility)
    - User Stories 4 paths (Happy, Low-confidence, Failure, Correction)
    - Eval metrics + threshold cụ thể
    - Top 3 failure modes + mitigation
    - ROI 3 kịch bản (Conservative, Realistic, Optimistic)
    - Mini AI spec (1 trang tóm tắt)
    - Implementation roadmap
  - Tuân thủ EARS patterns (Ubiquitous, Event-driven, State-driven, etc.)
  - Tuân thủ INCOSE quality rules (active voice, no vague terms, measurable criteria)
  
- **Giá trị:**
  - Cung cấp tài liệu spec chuyên nghiệp cho hackathon
  - Giúp nhóm hiểu rõ requirements và scope
  - Dễ dàng mở rộng hoặc điều chỉnh requirements sau này
  - Hỗ trợ stakeholder hiểu rõ giá trị và risk của sản phẩm

### 2.3 Xây dựng Metrics Framework & Evaluation Dataset
- **Output:**
  - Định nghĩa 6 metrics chính với threshold rõ ràng:
    - Tỉ lệ user hài lòng (≥80%)
    - Top-2 gợi ý trùng với tư vấn viên (≥70%)
    - Latency (< 2 phút)
    - Accuracy thông tin (≥95%)
    - Lỗi hệ thống (< 1%)
    - Tỉ lệ chuyển sang tư vấn viên (≤30%)
  
  - Chuẩn bị dataset đánh giá gồm:
    - 50+ test cases cho tư vấn mua xe (budget, seats, range, fuel type)
    - 30+ test cases cho bảo dưỡng/bảo hành (model-specific)
    - 40+ test cases cho phân tích review (pros/cons, sentiment)
    - 20+ test cases cho booking (validation, edge cases)
    - 15+ test cases cho failure modes (data missing, bias, hallucination)
    - 10+ test cases cho security (prompt injection, data leakage)
  
  - Tạo evaluation rubric với 4 cột: Input, Expected Output, Constraints, Pass/Fail
  
- **Giá trị:**
  - Cung cấp cách đo lường chất lượng hệ thống một cách khoa học
  - Giúp nhóm phát hiện bugs sớm thay vì chờ demo
  - Hỗ trợ continuous improvement sau hackathon
  - Dễ dàng so sánh hiệu suất giữa các phiên bản

## 3. SPEC phần mạnh nhất, yếu nhất? Vì sao?

### Mạnh nhất: AI Product Canvas + User Stories 4 paths
- **Vì sao:** 
  - Canvas rõ ràng phân biệt Value (khách hàng được gì), Trust (xử lý khi sai), Feasibility (chi phí, risk)
  - 4 paths cover toàn bộ scenario: happy path, low-confidence, failure, correction
  - Giúp team hiểu rõ không chỉ "cái gì" mà còn "tại sao" và "khi nào"
  - Dễ convert thành test cases và acceptance criteria

### Yếu nhất: Failure modes mitigation chưa đủ chi tiết
- **Vì sao:**
  - Mình nêu 3 failure modes chính nhưng mitigation còn mơ hồ
  - Ví dụ: "Cập nhật dữ liệu hàng tuần" nhưng chưa nêu cách kiểm tra dữ liệu cũ, cách alert khi dữ liệu lỗi thời
  - Chưa có SOP (Standard Operating Procedure) cụ thể cho từng failure mode
  - Nên thêm phần "Detection mechanism" và "Rollback plan"

## 4. Đóng góp cụ thể khác với mục 2

### 4.1 Thiết kế UI/UX cho multi-role
- Tạo 3 role selector buttons (Customer, Dealer, Admin) với visual feedback rõ ràng
- Thiết kế quick replies context-aware: Customer thấy "Mẫu xe, Giá, Bảo hành, Lái thử, Đặt lịch"; Dealer thấy "Xem lịch, Xác nhận, Doanh số, Quản lý khách, Support"
- Hỗ trợ appointment form modal chỉ hiển thị cho Customer role

### 4.2 Xây dựng evaluation rubric chi tiết
- Tạo bảng evaluation với 4 cột bắt buộc: Input, Expected Output, Constraints, Pass/Fail
- Mỗi test case có metadata: intent, priority (P0/P1/P2), category (happy/edge/failure)
- Tạo scoring system: P0 fail = -10 điểm, P1 fail = -5 điểm, P2 fail = -2 điểm

### 4.3 Chuẩn bị dataset test cases
- Phân loại test cases theo intent: recommendation, maintenance, review, booking, security
- Mỗi category có mix của happy path, edge cases, failure modes
- Tạo test data generator để dễ mở rộng dataset sau này

### 4.4 Hỗ trợ integration giữa frontend và backend
- Tạo API client (`lib/api.ts`) với các hàm: sendMessage, getHistory, createAppointment, getAppointments
- Hỗ trợ error handling và retry logic
- Tạo context provider (AuthContext) để quản lý user state

## 5. 1 điều học được trong hackathon mà trước đó chưa biết

**Mình học được rằng spec không phải chỉ là tài liệu, mà là công cụ để align team và giảm miscommunication.**

Trước hackathon, mình nghĩ spec chỉ là "viết ra yêu cầu rồi xong". Nhưng qua project này, mình thấy:
- Spec tốt giúp team hiểu rõ "tại sao" chứ không chỉ "cái gì"
- Metrics rõ ràng giúp team biết khi nào "xong" thay vì cứ sửa mãi
- Dataset test cases sớm giúp phát hiện bugs trước khi demo, thay vì chạy dồn ở cuối
- Multi-role design không chỉ tăng tính năng, mà còn giúp test nhiều scenario khác nhau

Ngoài ra, mình cũng học được rằng **frontend không phải chỉ "làm đẹp", mà là phần quan trọng để user hiểu được sản phẩm**. Ví dụ:
- Hiển thị "Cập nhật lần cuối: [ngày]" giúp user biết dữ liệu có mới không
- Tách rõ "Thông tin hãng" vs "Ý kiến AI" giúp user tin tưởng hơn
- Quick replies context-aware giúp user biết có thể hỏi gì tiếp theo

## 6. Nếu làm lại, mình sẽ đổi gì?

### 6.1 Tạo evaluation rubric sớm hơn
Mình sẽ tạo bảng evaluation rubric ngay từ tuần 1, thay vì tuần 2. Làm vậy thì:
- Team biết rõ "pass" là gì từ đầu
- Có thể test incremental thay vì dồn ở cuối
- Dễ phát hiện bugs sớm

### 6.2 Thiết kế spec với input từ backend team
Mình sẽ hỏi backend team sớm hơn về:
- API response format
- Error handling strategy
- Rate limiting
- Authentication flow

Làm vậy thì frontend và backend có thể develop song song mà không bị conflict.

### 6.3 Tạo design system từ đầu
Mình sẽ tạo Figma design system với:
- Color palette
- Typography scale
- Component library (Button, Input, Modal, etc.)
- Responsive breakpoints

Làm vậy thì:
- Tất cả component consistent
- Dễ maintain và mở rộng
- Dễ handoff cho designer khác

### 6.4 Chuẩn bị dataset test cases sớm hơn
Mình sẽ chuẩn bị dataset test cases ngay từ tuần 1, thay vì tuần 2. Làm vậy thì:
- Agent team có thể test ngay khi xây dựng tools
- Dễ phát hiện bugs sớm
- Có thể iterate nhanh hơn

## 7. AI giúp gì? AI sai/mislead ở đâu?

### AI giúp:
- **Brainstorming spec:** AI giúp mình nhanh chóng brainstorm các use cases, failure modes, metrics. Ví dụ, mình hỏi "Failure modes nào có thể xảy ra với chatbot tư vấn xe?" → AI liệt kê 10+ modes, mình chọn 3 cái quan trọng nhất.

- **Viết spec document:** AI giúp mình viết nhanh các phần như Canvas, User Stories, Metrics. Mình chỉ cần review và tinh chỉnh, thay vì viết từ đầu.

- **Thiết kế UI/UX:** AI gợi ý layout, color scheme, responsive design. Ví dụ, mình hỏi "Làm sao để hiển thị 3 role buttons đẹp?" → AI gợi ý button group, active state, hover effect.

- **Tạo test cases:** AI giúp mình sinh nhanh test cases cho từng intent. Ví dụ, mình hỏi "Tạo 10 test cases cho tư vấn mua xe" → AI sinh 10 cases với input, expected output, constraints.

- **Code generation:** AI giúp mình viết nhanh React components, API client, validation logic. Mình chỉ cần review logic và integrate vào project.

### AI sai/mislead:
- **Overscope:** AI đôi khi gợi ý features quá phức tạp, ví dụ "Thêm real-time inventory tracking", "Tích hợp payment gateway", "Xây dựng recommendation engine". Những cái này nghe hay nhưng vượt scope hackathon. Mình phải kiểm soát scope bằng cách luôn hỏi "Có demo được trong thời gian còn lại không?"

- **Overengineer:** AI đôi khi gợi ý architecture quá phức tạp, ví dụ "Dùng Redux + Redux Saga", "Tạo GraphQL API", "Dùng Kubernetes". Những cái này tốt cho production nhưng overkill cho hackathon. Mình phải chọn simple solution thay vì perfect solution.

- **Misleading metrics:** AI đôi khi gợi ý metrics không thực tế, ví dụ "Accuracy 99%", "Latency < 100ms". Mình phải điều chỉnh thành realistic metrics dựa trên constraint thực tế.

- **Incomplete test cases:** AI sinh test cases nhanh nhưng đôi khi thiếu edge cases hoặc security cases. Mình phải review kỹ và thêm các cases mà AI bỏ sót.

### Bài học:
- **AI là tool, không phải decision maker:** AI rất tốt để tăng tốc brainstorming, code generation, test case creation. Nhưng mình vẫn cần quyết định scope, priority, feasibility.

- **Luôn hỏi "Có demo được không?":** Trước khi nhận đề xuất từ AI, mình luôn hỏi "Có demo được trong thời gian còn lại không?" Nếu không, mình bỏ qua.

- **Review kỹ output của AI:** AI sinh nhanh nhưng không phải lúc nào cũng đúng. Mình phải review kỹ logic, edge cases, security trước khi dùng.

- **Combine AI + human judgment:** AI tốt ở brainstorming, code generation, test case creation. Nhưng human judgment tốt ở scope control, priority setting, feasibility assessment. Combine cả hai là tối ưu.

## 8. Kết luận

Qua hackathon này, mình đã học được rằng **xây dựng sản phẩm AI không chỉ là code, mà là sự kết hợp của spec tốt, UI/UX tốt, metrics rõ ràng, và test cases toàn diện.**

Mình cũng học được rằng **frontend không phải chỉ "làm đẹp", mà là phần quan trọng để user hiểu được sản phẩm và tin tưởng vào nó.**

Nếu có cơ hội làm lại, mình sẽ:
1. Tạo evaluation rubric sớm hơn
2. Thiết kế spec với input từ backend team
3. Tạo design system từ đầu
4. Chuẩn bị dataset test cases sớm hơn

Và mình sẽ luôn nhớ: **AI là tool để tăng tốc, nhưng human judgment vẫn là chìa khóa để thành công.**
