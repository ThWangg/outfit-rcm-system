# Hướng Dẫn Chạy Dự Án (OutfitRS)

## 📌 Giới Thiệu Dự Án
OutfitRS là một hệ thống gợi ý phối đồ thông minh cá nhân hóa theo ngữ cảnh. Hệ thống tự động phân tích chỉ số cơ thể (BMI), điều kiện thời tiết thực tế (nhiệt độ, độ ẩm, sức gió) và các dịp sự kiện (đi chơi, đi làm, thể thao) để đề xuất bộ trang phục tối ưu nhất bằng cách kết hợp bộ lọc luật cứng sinh học với mô hình Machine Learning và thuật toán Cosine Similarity.

---

## 🛠️ Công Nghệ Sử Dụng
* **Backend**: Python, Flask (Web Server)
* **Machine Learning**: Scikit-Learn (mô hình RandomForestClassifier dùng để chấm điểm độ tương thích phong cách và hành vi người dùng)
* **Cơ sở dữ liệu**: SQLite (mặc định) hoặc MySQL
* **Frontend**: HTML5, Vanilla JavaScript, CSS (thiết kế trực quan, hỗ trợ lấy thời tiết trực tuyến qua Open-Meteo API)

---

## 🚀 Cách Chạy Dự Án

### Bước 1: Cài đặt thư viện cần thiết
Mở Terminal/PowerShell tại thư mục dự án và chạy lệnh sau để cài đặt các thư viện:
```bash
pip install flask requests scikit-learn mysql-connector-python
```

### Bước 2: Khởi tạo cơ sở dữ liệu mẫu
Nạp danh mục 350+ quần áo và tạo 600+ tương tác mẫu phục vụ cho việc huấn luyện mô hình ML:
```bash
python init_db.py
```

### Bước 3: Chạy server
Khởi chạy server Flask:
```bash
python app.py
```

Sau khi chạy thành công, truy cập trình duyệt Web theo địa chỉ: [http://127.0.0.1:5000](http://127.0.0.1:5000)
