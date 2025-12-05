================================================================================
                    HƯỚNG DẪN THÊM HÌNH ẢNH CỜ TƯỚNG
================================================================================

=== 1. ẢNH BÀN CỜ (BOARD) ===

Đặt file: static/assets/board.png

Yêu cầu:
  - Tên file: board.png
  - Định dạng: PNG hoặc JPG
  - Kích thước: 540 x 600 pixels (khuyến nghị)
  - Nội dung: Bàn cờ tướng đầy đủ với sông và cung điện

Nơi tải:
  - https://commons.wikimedia.org/wiki/File:Xiangqi_board.svg
  - https://github.com/nicoschmitt/xiangqi-board/blob/master/src/assets/board.png


=== 2. ẢNH QUÂN CỜ (PIECES) ===

Đặt 14 file PNG vào folder: static/assets/pieces/

QUÂN ĐỎ (Red):
--------------
  red_king.png      - Tướng đỏ (帥)
  red_advisor.png   - Sĩ đỏ (仕)
  red_elephant.png  - Tượng đỏ (相)
  red_rook.png      - Xe đỏ (俥)
  red_knight.png    - Mã đỏ (傌)
  red_cannon.png    - Pháo đỏ (炮)
  red_pawn.png      - Tốt đỏ (兵)

QUÂN ĐEN (Black):
-----------------
  black_king.png    - Tướng đen (將)
  black_advisor.png - Sĩ đen (士)
  black_elephant.png- Tượng đen (象)
  black_rook.png    - Xe đen (車)
  black_knight.png  - Mã đen (馬)
  black_cannon.png  - Pháo đen (砲)
  black_pawn.png    - Tốt đen (卒)

Yêu cầu hình quân cờ:
  - Định dạng: PNG với nền trong suốt (transparent background)
  - Kích thước: 60x60 pixels hoặc 80x80 pixels
  - Hình vuông (width = height)


=== 3. NƠI TẢI HÌNH ẢNH MIỄN PHÍ ===

1. Wikimedia Commons:
   https://commons.wikimedia.org/wiki/Category:Xiangqi_pieces
   
2. GitHub - nicoschmitt/xiangqi-board (MIT License):
   https://github.com/nicoschmitt/xiangqi-board/tree/master/src/assets
   
3. CleanPNG (Free):
   https://www.cleanpng.com/free/chinese-chess.html

4. Flaticon (Free with attribution):
   https://www.flaticon.com/search?word=chinese%20chess


=== 4. CẤU TRÚC THƯ MỤC ===

static/
└── assets/
    ├── board.png          <-- Ảnh bàn cờ
    └── pieces/
        ├── red_king.png
        ├── red_advisor.png
        ├── red_elephant.png
        ├── red_rook.png
        ├── red_knight.png
        ├── red_cannon.png
        ├── red_pawn.png
        ├── black_king.png
        ├── black_advisor.png
        ├── black_elephant.png
        ├── black_rook.png
        ├── black_knight.png
        ├── black_cannon.png
        └── black_pawn.png


=== 5. LƯU Ý ===

- Nếu không có hình ảnh, game sẽ tự động vẽ bằng Canvas + chữ Hán
- Để tắt dùng hình ảnh, đổi trong main.js:
    USE_IMAGES = false       (tắt ảnh quân cờ)
    USE_BOARD_IMAGE = false  (tắt ảnh bàn cờ)

================================================================================
