# 🏯 Cờ Tướng Online - Chinese Chess Web Application

## 📋 Giới thiệu

Ứng dụng web chơi cờ tướng trực tuyến với AI thông minh, được phát triển bằng Python Flask và Socket.IO.

### ✨ Tính năng chính:
- ✅ Đăng ký, đăng nhập, quản lý tài khoản
- ✅ Chơi với AI (3 cấp độ: Dễ, Trung Bình, Khó)
- ✅ Chơi PvP (Player vs Player) qua mã phòng
- ✅ AI sử dụng thuật toán Minimax + Alpha-Beta Pruning
- ✅ Hệ thống xếp hạng điểm (Rating)
- ✅ Lịch sử trận đấu
- ✅ Giao diện responsive, hỗ trợ mobile

---

## 🛠️ Công nghệ sử dụng

| Thành phần | Công nghệ |
|------------|-----------|
| **Backend** | Python Flask + Flask-SocketIO |
| **Database** | SQL Server (ODBC Driver 17) |
| **AI Engine** | Minimax + Alpha-Beta + Iterative Deepening |
| **Frontend** | HTML5 Canvas + JavaScript + Socket.IO |
| **Bảo mật** | bcrypt password hashing |

---

## 📦 Hướng dẫn Cài đặt

### Bước 1: Clone dự án

```bash
git clone <repository-url>
cd CoTuongWeb
```

### Bước 2: Cài đặt Python packages

```bash
pip install -r requirements.txt
```

### Bước 3: Cài đặt SQL Server

1. **Cài SQL Server Express** (miễn phí):  
   https://www.microsoft.com/en-us/sql-server/sql-server-downloads

2. **Cài ODBC Driver 17**:  
   https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

3. **Tạo Database** - Mở SQL Server Management Studio (SSMS):
   ```sql
   -- Chạy file: database/create_database.sql
   ```

### Bước 4: Cấu hình Database

Mở file `config.py` và cập nhật thông tin kết nối:

```python
class Config:
    SQL_SERVER = 'localhost'        # Tên server SQL
    SQL_DATABASE = 'CoTuongDB'      # Tên database
    SQL_USERNAME = 'sa'             # Username
    SQL_PASSWORD = 'your_password'  # Password
```

**Nếu dùng Windows Authentication**, sửa trong `server/db.py`:
```python
connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={self.server};"
    f"DATABASE={self.database};"
    f"Trusted_Connection=yes;"
)
```

### Bước 5: Chạy ứng dụng

```bash
python app.py
```

Mở trình duyệt: **http://localhost:5000**

---

## 🎮 Hướng dẫn sử dụng

### Chơi với AI:
1. Đăng nhập → Chọn **"Chơi với AI"**
2. Chọn độ khó (Dễ / Trung bình / Khó)
3. Click **"Bắt đầu chơi"**

### Chơi PvP:
1. **Tạo phòng**: Click "Tạo phòng" → Gửi mã phòng cho bạn bè
2. **Tham gia**: Nhập mã phòng → Click "Tham gia"

---

# 🧠 THUẬT TOÁN AI - MINIMAX VÀ ALPHA-BETA PRUNING

## 1. TỔNG QUAN THUẬT TOÁN

### 1.1. Minimax là gì?

**Minimax** là thuật toán tìm kiếm trong game đối kháng, dựa trên giả định:
- **Cả hai người chơi đều chơi tối ưu**
- **MAX (AI)**: Cố gắng **tối đa hóa** điểm số
- **MIN (Đối thủ)**: Cố gắng **tối thiểu hóa** điểm số

### 1.2. Cách hoạt động

```
Depth 0 (MAX):     [MAX chọn nước có điểm cao nhất]
                          MAX
                        /  |  \
Depth 1 (MIN):      MIN   MIN   MIN  [Đối thủ chọn nước có điểm thấp nhất]
                   /|\    |    /|\
Depth 2 (MAX):   ...    ...    ...   [AI lại chọn nước cao nhất]
                   |      |      |
Depth 3:        [Đánh giá bàn cờ]
```

**Nguyên lý**: AI giả sử đối thủ sẽ chọn nước **tệ nhất cho AI**, nên AI phải chọn nước **tốt nhất trong trường hợp xấu nhất**.

---

## 2. ALPHA-BETA PRUNING (CẮT TỈA ALPHA-BETA)

### 2.1. Vấn đề của Minimax thuần túy

- Minimax phải duyệt **TẤT CẢ** các nhánh
- Độ phức tạp: **O(b^d)** với b = số nước đi, d = độ sâu
- Cờ tướng có ~30-50 nước đi mỗi lượt → **Rất chậm!**

### 2.2. Giải pháp: Alpha-Beta Pruning

**Ý tưởng**: Cắt bỏ các nhánh **chắc chắn không ảnh hưởng** đến kết quả cuối cùng.

**Hai tham số quan trọng**:
- **Alpha (α)**: Giá trị **TỐT NHẤT** mà MAX đã tìm thấy
- **Beta (β)**: Giá trị **TỐT NHẤT** mà MIN đã tìm thấy

**Quy tắc cắt tỉa**:
- Nếu **α ≥ β** → **DỪNG** duyệt nhánh này (Pruning)

### 2.3. Ví dụ minh họa

```
         MAX (chọn lớn nhất)
        /          \
    MIN(A)        MIN(B)
    /    \           |
  [3]   [5]        [2] ← DỪNG! Không cần xét tiếp
                    
Giải thích:
- MAX đã biết nhánh A cho điểm ít nhất = 3 (vì MIN sẽ chọn min(3,5) = 3)
- Nhánh B cho ra [2], nhỏ hơn 3
- MIN ở B sẽ chọn ≤ 2 → MAX không bao giờ chọn B
- → CẮT BỎ các nhánh con còn lại của B
```

### 2.4. Hiệu quả

| Thuật toán | Độ phức tạp | Ví dụ (b=30, d=4) |
|------------|-------------|-------------------|
| Minimax | O(b^d) | 810,000 nút |
| Alpha-Beta (tốt nhất) | O(b^(d/2)) | 900 nút |
| Alpha-Beta (trung bình) | O(b^(3d/4)) | ~27,000 nút |

**Kết luận**: Alpha-Beta có thể **nhanh hơn 30-900 lần** so với Minimax thuần!

---

## 3. CÁC CẢI TIẾN BỔ SUNG

### 3.1. Iterative Deepening (Tăng dần độ sâu)

**Vấn đề**: Không biết nên tìm sâu bao nhiêu?

**Giải pháp**: Tìm kiếm từ depth 1, 2, 3... cho đến khi hết thời gian.

```
Iteration 1: depth=1 → Best move = A (0.01s)
Iteration 2: depth=2 → Best move = B (0.05s)
Iteration 3: depth=3 → Best move = B (0.3s)
Iteration 4: depth=4 → Best move = C (2.0s)
... HẾT GIỜ → Trả về C
```

**Ưu điểm**:
- Luôn có **kết quả dự phòng** nếu hết thời gian
- Cải thiện thứ tự xét nước đi (Move Ordering)

### 3.2. Transposition Table (Bảng băm)

**Vấn đề**: Nhiều chuỗi nước đi dẫn đến **cùng một thế cờ**.

**Giải pháp**: Lưu các thế cờ đã đánh giá vào **bảng băm (Hash Table)**.

```python
# Ví dụ:
transposition_table = {
    hash("thế cờ A"): {"score": 150, "depth": 4, "best_move": "E2-E4"},
    hash("thế cờ B"): {"score": -80, "depth": 3, "best_move": "C7-C6"},
}
```

**Hiệu quả**: Tránh tính toán lặp lại → **Nhanh hơn 2-3 lần**.

### 3.3. Killer Move Heuristic

**Ý tưởng**: Nước đi gây cắt tỉa ở vị trí này có thể cũng tốt ở vị trí tương tự.

**Cách hoạt động**:
1. Khi nước đi X gây cắt tỉa, lưu X vào "Killer Moves"
2. Ở các nhánh sau, **ưu tiên xét X trước**
3. Nếu X vẫn tốt → Cắt tỉa nhanh hơn

### 3.4. Move Ordering (Sắp xếp nước đi)

**Nguyên lý**: Alpha-Beta hiệu quả nhất khi **xét nước tốt trước**.

**Thứ tự ưu tiên**:
1. **Nước từ Transposition Table** (đã biết tốt)
2. **Killer Moves** (đã gây cắt tỉa)
3. **Nước ăn quân** (capture moves)
4. **Nước thường** (quiet moves)

---

## 4. HÀM ĐÁNH GIÁ THẾ CỜ (EVALUATION FUNCTION)

### 4.1. Giá trị quân cờ (Material Value)

| Quân cờ | Ký hiệu | Điểm | Giải thích |
|---------|---------|------|------------|
| **Tướng (King)** | K | 10,000 | Mất = Thua |
| **Xe (Rook)** | R | 900 | Mạnh nhất, đi thẳng không giới hạn |
| **Pháo (Cannon)** | C | 450 | Cần "bắc cầu" để ăn quân |
| **Mã (Knight)** | N | 400 | Đi hình chữ L, bị cản chân |
| **Tượng (Elephant)** | E | 200 | Chỉ đi trong nửa sân |
| **Sĩ (Advisor)** | A | 200 | Bảo vệ Tướng trong cung |
| **Tốt (Pawn)** | P | 100 | Qua sông tăng sức mạnh |

**Công thức cơ bản**:
```
Điểm = Σ(Quân ta × Giá trị) - Σ(Quân địch × Giá trị)
```

### 4.2. Điểm vị trí (Position Score Table)

Mỗi quân cờ có **bảng điểm vị trí** riêng.

**Ví dụ - Mã (Knight)**:
```
        Cột: 0   1   2   3   4   5   6   7   8
Hàng 0:    [0,  0,  0,  0,  0,  0,  0,  0,  0]
Hàng 1:    [0,  0,  0,  0,  0,  0,  0,  0,  0]
Hàng 2:    [0,  0,  0,  0,  0,  0,  0,  0,  0]
Hàng 3:    [0,  0,  0,  0,  0,  0,  0,  0,  0]
Hàng 4:    [0,  0,  0,  0,  0,  0,  0,  0,  0]
Hàng 5:    [0,  0, 10, 20, 30, 20, 10,  0,  0]  ← Qua sông mạnh hơn
Hàng 6:    [0,  0, 20, 30, 40, 30, 20,  0,  0]
Hàng 7:    [0,  0, 20, 30, 40, 30, 20,  0,  0]  ← Giữa bàn cờ tốt nhất
Hàng 8:    [0,  0, 10, 20, 30, 20, 10,  0,  0]
Hàng 9:    [0,  0,  0,  0,  0,  0,  0,  0,  0]
```

**Ý nghĩa**: Mã ở **giữa bàn cờ, qua sông** được cộng thêm điểm.

### 4.3. Đánh giá thế cờ (Pattern Recognition)

AI nhận biết và đánh giá các **thế cờ chiến thuật**:

#### a) An toàn Tướng (King Safety)
```python
# Có Sĩ bảo vệ: +20 điểm/Sĩ
# Có Tượng bảo vệ: +10 điểm/Tượng
# Tướng ra khỏi vị trí an toàn: -10 điểm
```

#### b) Kiểm soát cột mở (Open File Control)
```python
# Xe trên cột không có Tốt: +30 điểm
# Xe trên cột giữa (cột 4): +20 điểm
# Pháo có quân bắc cầu: +10 điểm
```

#### c) Ghìm quân (Pin Detection)
```python
# Ghìm quân địch vào Tướng: +80 điểm
# Quân bị ghìm không thể di chuyển tự do
```

#### d) Xe liên hoàn (Connected Rooks)
```python
# Hai Xe cùng hàng/cột: +50 điểm
# Xe liên hoàn bảo vệ lẫn nhau, rất mạnh
```

#### e) Khả năng di động (Mobility)
```python
# Mỗi nước đi hợp lệ: +5 điểm
# Quân nhiều nước đi = linh hoạt = mạnh hơn
```

---

## 5. CÁCH AI ĂN QUÂN

### 5.1. Quy trình ra quyết định

```
1. Sinh tất cả nước đi hợp lệ
   ↓
2. Với mỗi nước đi:
   - Thực hiện nước đi (tạm thời)
   - Đánh giá thế cờ mới
   - Hoàn tác nước đi
   ↓
3. Chọn nước đi có điểm cao nhất
```

### 5.2. Ví dụ cụ thể

**Tình huống**: Xe đỏ có thể ăn Mã đen

```
Trước khi ăn:
- Điểm quân ta: Xe(900) + Tốt(100) = 1000
- Điểm quân địch: Mã(400) + Tốt(100) = 500
- Điểm chênh lệch: 1000 - 500 = +500

Sau khi Xe ăn Mã:
- Điểm quân ta: Xe(900) + Tốt(100) = 1000
- Điểm quân địch: Tốt(100) = 100
- Điểm chênh lệch: 1000 - 100 = +900

→ Lợi thế tăng từ +500 → +900 (+400 điểm)
→ AI sẽ chọn nước ăn Mã!
```

### 5.3. Ăn quân có "đánh đổi"

```
Tình huống: Xe có thể ăn Mã, nhưng sau đó Xe bị ăn lại

Trước:     Xe(900) vs Mã(400)
Sau ăn:    Mất Xe(900), được Mã(400)
Kết quả:   -500 điểm

→ AI sẽ KHÔNG ăn vì bị lỗ 500 điểm!
```

**Trừ khi**: Ăn quân giúp chiếu hết hoặc có lợi thế chiến thuật khác.

---

## 6. ĐỘ KHÓ CỦA AI

| Độ khó | Depth | Thời gian | Max Moves | Đặc điểm |
|--------|-------|-----------|-----------|----------|
| **Dễ** | 2 | 1s | 50 | Nhìn trước 2 nước, dễ sai lầm |
| **Trung bình** | 3 | 3s | 40 | Nhìn trước 3 nước, khá mạnh |
| **Khó** | 4 | 10s | 30 | Nhìn trước 4 nước, rất mạnh |

**Depth 4 nghĩa là**:
- AI đi nước 1 → Đối thủ đáp → AI đi nước 2 → Đối thủ đáp
- AI "nhìn thấy" trước **4 nước đi**

---

## 7. TÓM TẮT THUẬT TOÁN

### Sơ đồ hoạt động:

```
┌─────────────────────────────────────────────────────────┐
│                    AI CỜ TƯỚNG                          │
├─────────────────────────────────────────────────────────┤
│  1. Nhận thế cờ hiện tại                               │
│                    ↓                                    │
│  2. Sinh tất cả nước đi hợp lệ                         │
│                    ↓                                    │
│  3. Iterative Deepening (Depth 1 → Max Depth)          │
│     ┌──────────────────────────────────────┐           │
│     │  MINIMAX + ALPHA-BETA PRUNING        │           │
│     │  - MAX: Chọn nước tốt nhất           │           │
│     │  - MIN: Đối thủ chọn nước xấu nhất   │           │
│     │  - Cắt tỉa khi α ≥ β                 │           │
│     └──────────────────────────────────────┘           │
│                    ↓                                    │
│  4. Đánh giá thế cờ:                                   │
│     - Giá trị quân cờ (Material)                       │
│     - Điểm vị trí (Position)                           │
│     - An toàn Tướng (King Safety)                      │
│     - Thế cờ (Patterns)                                │
│                    ↓                                    │
│  5. Chọn nước đi có điểm cao nhất                      │
│                    ↓                                    │
│  6. Thực hiện nước đi                                  │
└─────────────────────────────────────────────────────────┘
```

### Công thức đánh giá tổng hợp:

```
Score = Material + Position + KingSafety + Tactics + Mobility

Trong đó:
- Material: Σ(Giá trị quân ta) - Σ(Giá trị quân địch)
- Position: Σ(Điểm vị trí quân ta) - Σ(Điểm vị trí quân địch)
- KingSafety: Độ an toàn Tướng ta - Độ an toàn Tướng địch
- Tactics: Điểm ghìm quân, cột mở, xe liên hoàn...
- Mobility: (Số nước đi ta - Số nước đi địch) × 5
```

---

## 📁 Cấu trúc Project

```
CoTuongWeb/
├── app.py                 # Flask application chính
├── config.py              # Cấu hình (DB, Secret Key)
├── requirements.txt       # Python dependencies
├── README.md              # File hướng dẫn này
│
├── database/
│   └── create_database.sql # Script tạo database
│
├── server/
│   ├── ai.py              # 🧠 AI Engine (Minimax + Alpha-Beta)
│   ├── auth.py            # Xác thực người dùng
│   ├── board.py           # Logic bàn cờ + Hàm đánh giá
│   ├── db.py              # Kết nối Database
│   └── models.py          # Data models
│
├── static/
│   ├── assets/            # Hình ảnh (tùy chọn)
│   ├── css/style.css      # Stylesheet
│   └── js/main.js         # Client-side logic
│
└── templates/
    ├── index.html         # Trang đăng nhập
    ├── lobby.html         # Chọn chế độ chơi
    ├── game.html          # Trang chơi game
    ├── profile.html       # Trang cá nhân
    └── leaderboard.html   # Bảng xếp hạng
```

---

## ⚠️ Xử lý lỗi thường gặp

### Lỗi kết nối Database
```
Kiểm tra: SQL Server đang chạy (services.msc)
Kiểm tra: Thông tin config.py đúng chưa
Kiểm tra: ODBC Driver 17 đã cài chưa
```

### Lỗi Socket.IO
```
Kiểm tra: Firewall không chặn port 5000
Kiểm tra: Browser console để xem lỗi chi tiết
```

### Lỗi import modules
```bash
pip install -r requirements.txt
```

---

## 📝 License

Project được phát triển cho mục đích học tập. Tự do sử dụng và chỉnh sửa.

---

## 🙏 Credits

- Luật cờ tướng truyền thống Việt Nam
- Thuật toán AI: Minimax + Alpha-Beta Pruning
- UI: Pure CSS + HTML5 Canvas

**Chúc bạn chơi vui! 🎮**
