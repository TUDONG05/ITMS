# Shared

Thư mục này chứa artefact dùng chung, không chứa mã runtime dùng đồng thời bởi Angular và Python.

- `contracts/`: tài liệu hợp đồng và artefact API. S0-04 sẽ đưa OpenAPI/DTO chính thức vào đây.
- `fixtures/`: dữ liệu mẫu có cấu trúc, không chứa dữ liệu thật hoặc secret.

Khi đổi contract, cập nhật version, consumer chịu ảnh hưởng và kiểm tra tương thích trước khi tích hợp.
