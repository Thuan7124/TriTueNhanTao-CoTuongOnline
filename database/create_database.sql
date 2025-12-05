-- ============================================
-- CỜ TƯỚNG WEB - SQL SERVER DATABASE SCRIPT
-- ============================================
-- Chạy script này trong SQL Server Management Studio (SSMS)
-- hoặc Azure Data Studio để tạo database

-- Bước 1: Tạo Database
--USE master;
--GO

-- Xóa database cũ nếu tồn tại (cẩn thận khi chạy trên production)
--IF EXISTS (SELECT name FROM sys.databases WHERE name = N'CoTuongDB')
--BEGIN
--    ALTER DATABASE CoTuongDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
--    DROP DATABASE CoTuongDB;
--END
--GO

-- Tạo database mới
--CREATE DATABASE CoTuongDB;
--GO

--USE CoTuongDB;
GO

-- ============================================
-- Bước 2: Tạo bảng Users (Người dùng)
-- ============================================
CREATE TABLE Users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(50) NOT NULL UNIQUE,
    email NVARCHAR(100) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    last_login DATETIME NULL,
    is_active BIT DEFAULT 1,
    -- Thống kê
    games_played INT DEFAULT 0,
    games_won INT DEFAULT 0,
    games_lost INT DEFAULT 0,
    games_drawn INT DEFAULT 0,
    elo_rating INT DEFAULT 1000,  -- Rating mặc định 1000
    -- Chuỗi thắng
    win_streak INT DEFAULT 0,      -- Chuỗi thắng hiện tại
    max_win_streak INT DEFAULT 0,  -- Chuỗi thắng cao nhất
    -- Chỉ tính PvP games để xếp hạng
    pvp_games_played INT DEFAULT 0,
    -- Thông tin cá nhân
    avatar_url NVARCHAR(255) NULL,       -- Đường dẫn ảnh avatar
    bio NVARCHAR(500) NULL,              -- Tiểu sử ngắn
    display_name NVARCHAR(50) NULL,      -- Tên hiển thị
    birthday DATE NULL,                   -- Ngày sinh
    gender NVARCHAR(10) NULL,            -- Giới tính: male, female, other
    phone NVARCHAR(15) NULL,             -- Số điện thoại
    location NVARCHAR(100) NULL          -- Địa chỉ/Thành phố
);
GO

-- Index cho tìm kiếm nhanh
CREATE INDEX IX_Users_Username ON Users(username);
CREATE INDEX IX_Users_Email ON Users(email);
CREATE INDEX IX_Users_ELO ON Users(elo_rating DESC);
GO

-- ============================================
-- Bước 3: Tạo bảng Games (Các ván đấu)
-- ============================================
CREATE TABLE Games (
    game_id INT IDENTITY(1,1) PRIMARY KEY,
    room_code NVARCHAR(20) NOT NULL UNIQUE,  -- Mã phòng để 2 người chơi cùng
    
    -- Người chơi (ID liên kết với bảng Users, NULL nếu là Guest hoặc AI)
    red_player_id INT NULL,          -- ID người chơi quân Đỏ
    black_player_id INT NULL,        -- ID người chơi quân Đen
    
    -- Tên người chơi (lưu trực tiếp để hiển thị, kể cả Guest/AI)
    red_player_name NVARCHAR(100) NULL,    -- Tên: username, 'Guest', hoặc 'AI (easy/medium/hard)'
    black_player_name NVARCHAR(100) NULL,  -- Tên: username, 'Guest', hoặc 'AI (easy/medium/hard)'
    
    -- Loại game
    game_type NVARCHAR(20) NOT NULL, -- 'pvp' (người vs người), 'pve' (người vs máy)
    ai_difficulty NVARCHAR(20) NULL, -- 'easy', 'medium', 'hard' (chỉ dùng cho pve)
    
    -- Trạng thái game
    status NVARCHAR(20) DEFAULT 'waiting', -- 'waiting', 'playing', 'finished', 'abandoned'
    current_turn NVARCHAR(10) DEFAULT 'red', -- 'red' hoặc 'black'
    
    -- Trạng thái bàn cờ (JSON string)
    board_state NVARCHAR(MAX) NULL,
    
    -- Kết quả
    winner NVARCHAR(20) NULL,        -- 'red', 'black', 'draw', NULL (chưa kết thúc)
    end_reason NVARCHAR(50) NULL,    -- 'checkmate', 'resign', 'timeout', 'draw_agreement'
    
    -- Thời gian
    created_at DATETIME DEFAULT GETDATE(),
    started_at DATETIME NULL,
    ended_at DATETIME NULL,
    
    -- Foreign Keys (có thể NULL cho Guest)
    CONSTRAINT FK_Games_RedPlayer FOREIGN KEY (red_player_id) REFERENCES Users(user_id),
    CONSTRAINT FK_Games_BlackPlayer FOREIGN KEY (black_player_id) REFERENCES Users(user_id)
);
GO

-- Index cho tìm kiếm
CREATE INDEX IX_Games_RoomCode ON Games(room_code);
CREATE INDEX IX_Games_Status ON Games(status);
CREATE INDEX IX_Games_RedPlayer ON Games(red_player_id);
CREATE INDEX IX_Games_BlackPlayer ON Games(black_player_id);
GO

-- ============================================
-- Bước 4: Tạo bảng Moves (Các nước đi)
-- ============================================
CREATE TABLE Moves (
    move_id INT IDENTITY(1,1) PRIMARY KEY,
    game_id INT NOT NULL,
    move_number INT NOT NULL,        -- Số thứ tự nước đi
    player NVARCHAR(10) NOT NULL,    -- 'red' hoặc 'black'
    
    -- Vị trí
    from_row INT NOT NULL,
    from_col INT NOT NULL,
    to_row INT NOT NULL,
    to_col INT NOT NULL,
    
    -- Thông tin thêm
    piece_type NVARCHAR(20) NOT NULL,     -- Loại quân cờ di chuyển
    captured_piece NVARCHAR(20) NULL,     -- Quân bị ăn (nếu có)
    is_check BIT DEFAULT 0,               -- Có chiếu tướng không
    
    -- Notation (ký hiệu nước đi theo chuẩn)
    notation NVARCHAR(20) NULL,
    
    created_at DATETIME DEFAULT GETDATE(),
    
    CONSTRAINT FK_Moves_Game FOREIGN KEY (game_id) REFERENCES Games(game_id) ON DELETE CASCADE
);
GO

CREATE INDEX IX_Moves_GameId ON Moves(game_id);
GO

-- ============================================
-- Bước 5: Tạo bảng Sessions (Phiên đăng nhập)
-- ============================================
CREATE TABLE Sessions (
    session_id NVARCHAR(100) PRIMARY KEY,
    user_id INT NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    expires_at DATETIME NOT NULL,
    ip_address NVARCHAR(50) NULL,
    user_agent NVARCHAR(255) NULL,
    
    CONSTRAINT FK_Sessions_User FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);
GO

CREATE INDEX IX_Sessions_UserId ON Sessions(user_id);
CREATE INDEX IX_Sessions_ExpiresAt ON Sessions(expires_at);
GO

-- ============================================
-- Bước 6: Stored Procedures
-- ============================================

-- SP: Tạo user mới
CREATE PROCEDURE sp_CreateUser
    @username NVARCHAR(50),
    @email NVARCHAR(100),
    @password_hash NVARCHAR(255)
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Kiểm tra username đã tồn tại
    IF EXISTS (SELECT 1 FROM Users WHERE username = @username)
    BEGIN
        RAISERROR('Username đã tồn tại', 16, 1);
        RETURN;
    END
    
    -- Kiểm tra email đã tồn tại
    IF EXISTS (SELECT 1 FROM Users WHERE email = @email)
    BEGIN
        RAISERROR('Email đã được sử dụng', 16, 1);
        RETURN;
    END
    
    INSERT INTO Users (username, email, password_hash)
    VALUES (@username, @email, @password_hash);
    
    SELECT SCOPE_IDENTITY() AS user_id;
END
GO

-- SP: Lấy thông tin user theo username
CREATE PROCEDURE sp_GetUserByUsername
    @username NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT user_id, username, email, password_hash, created_at, last_login,
           games_played, games_won, games_lost, games_drawn, elo_rating
    FROM Users
    WHERE username = @username AND is_active = 1;
END
GO

-- SP: Cập nhật lần đăng nhập cuối
CREATE PROCEDURE sp_UpdateLastLogin
    @user_id INT
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE Users SET last_login = GETDATE() WHERE user_id = @user_id;
END
GO

-- SP: Tạo game mới
CREATE PROCEDURE sp_CreateGame
    @room_code NVARCHAR(20),
    @game_type NVARCHAR(20),
    @ai_difficulty NVARCHAR(20) = NULL,
    @red_player_id INT = NULL,
    @black_player_id INT = NULL,
    @red_player_name NVARCHAR(100) = NULL,
    @black_player_name NVARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Nếu là PvE, tự động set started_at
    IF @game_type = 'pve'
    BEGIN
        INSERT INTO Games (room_code, game_type, ai_difficulty, red_player_id, black_player_id, 
                          red_player_name, black_player_name, status, started_at)
        VALUES (@room_code, @game_type, @ai_difficulty, @red_player_id, @black_player_id,
                @red_player_name, @black_player_name, 'playing', GETDATE());
    END
    ELSE
    BEGIN
        INSERT INTO Games (room_code, game_type, ai_difficulty, red_player_id, black_player_id,
                          red_player_name, black_player_name, status)
        VALUES (@room_code, @game_type, @ai_difficulty, @red_player_id, @black_player_id,
                @red_player_name, @black_player_name, 'waiting');
    END
    
    SELECT SCOPE_IDENTITY() AS game_id;
END
GO

-- SP: Cập nhật kết quả game (bao gồm ELO và streak)
CREATE PROCEDURE sp_EndGame
    @game_id INT,
    @winner NVARCHAR(20),
    @end_reason NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Cập nhật game
    UPDATE Games 
    SET status = 'finished',
        winner = @winner,
        end_reason = @end_reason,
        ended_at = GETDATE()
    WHERE game_id = @game_id;
    
    -- Lấy thông tin game
    DECLARE @red_player INT, @black_player INT, @game_type NVARCHAR(20);
    SELECT @red_player = red_player_id, 
           @black_player = black_player_id,
           @game_type = game_type
    FROM Games WHERE game_id = @game_id;
    
    -- Chỉ cập nhật ELO và streak cho PvP
    IF @game_type = 'pvp'
    BEGIN
        -- Cập nhật người chơi đỏ
        IF @red_player IS NOT NULL
        BEGIN
            UPDATE Users SET 
                games_played = games_played + 1,
                pvp_games_played = pvp_games_played + 1,
                games_won = games_won + CASE WHEN @winner = 'red' THEN 1 ELSE 0 END,
                games_lost = games_lost + CASE WHEN @winner = 'black' THEN 1 ELSE 0 END,
                games_drawn = games_drawn + CASE WHEN @winner = 'draw' OR @winner IS NULL THEN 1 ELSE 0 END,
                -- ELO: +25 thắng, -20 thua, +5 hòa
                elo_rating = elo_rating + CASE 
                    WHEN @winner = 'red' THEN 25
                    WHEN @winner = 'black' THEN -20
                    ELSE 5 END,
                -- Win streak
                win_streak = CASE 
                    WHEN @winner = 'red' THEN win_streak + 1
                    ELSE 0 END,
                max_win_streak = CASE 
                    WHEN @winner = 'red' AND win_streak + 1 > max_win_streak THEN win_streak + 1
                    ELSE max_win_streak END
            WHERE user_id = @red_player;
        END
        
        -- Cập nhật người chơi đen
        IF @black_player IS NOT NULL
        BEGIN
            UPDATE Users SET 
                games_played = games_played + 1,
                pvp_games_played = pvp_games_played + 1,
                games_won = games_won + CASE WHEN @winner = 'black' THEN 1 ELSE 0 END,
                games_lost = games_lost + CASE WHEN @winner = 'red' THEN 1 ELSE 0 END,
                games_drawn = games_drawn + CASE WHEN @winner = 'draw' OR @winner IS NULL THEN 1 ELSE 0 END,
                -- ELO: +25 thắng, -20 thua, +5 hòa
                elo_rating = elo_rating + CASE 
                    WHEN @winner = 'black' THEN 25
                    WHEN @winner = 'red' THEN -20
                    ELSE 5 END,
                -- Win streak
                win_streak = CASE 
                    WHEN @winner = 'black' THEN win_streak + 1
                    ELSE 0 END,
                max_win_streak = CASE 
                    WHEN @winner = 'black' AND win_streak + 1 > max_win_streak THEN win_streak + 1
                    ELSE max_win_streak END
            WHERE user_id = @black_player;
        END
    END
    ELSE
    BEGIN
        -- PvE: chỉ cập nhật số trận, không ảnh hưởng ELO
        IF @red_player IS NOT NULL
        BEGIN
            UPDATE Users SET games_played = games_played + 1
            WHERE user_id = @red_player;
        END
        IF @black_player IS NOT NULL
        BEGIN
            UPDATE Users SET games_played = games_played + 1
            WHERE user_id = @black_player;
        END
    END
END
GO

-- SP: Lưu nước đi
CREATE PROCEDURE sp_SaveMove
    @game_id INT,
    @move_number INT,
    @player NVARCHAR(10),
    @from_row INT,
    @from_col INT,
    @to_row INT,
    @to_col INT,
    @piece_type NVARCHAR(20),
    @captured_piece NVARCHAR(20) = NULL,
    @is_check BIT = 0,
    @notation NVARCHAR(20) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    INSERT INTO Moves (game_id, move_number, player, from_row, from_col, to_row, to_col,
                       piece_type, captured_piece, is_check, notation)
    VALUES (@game_id, @move_number, @player, @from_row, @from_col, @to_row, @to_col,
            @piece_type, @captured_piece, @is_check, @notation);
    
    SELECT SCOPE_IDENTITY() AS move_id;
END
GO

-- SP: Lấy lịch sử nước đi của game
CREATE PROCEDURE sp_GetGameMoves
    @game_id INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT move_id, move_number, player, from_row, from_col, to_row, to_col,
           piece_type, captured_piece, is_check, notation, created_at
    FROM Moves
    WHERE game_id = @game_id
    ORDER BY move_number;
END
GO

-- ============================================
-- Bước 7: Tạo bảng PveHighscores (Điểm cao PvE)
-- ============================================
CREATE TABLE PveHighscores (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    difficulty NVARCHAR(10) NOT NULL,  -- 'easy', 'medium', 'hard'
    game_score FLOAT NOT NULL DEFAULT 0,
    moves_count INT NOT NULL DEFAULT 0,
    elapsed_time INT NOT NULL DEFAULT 0,  -- Thời gian (giây)
    pieces_captured INT NOT NULL DEFAULT 0,  -- Số quân ăn được
    pieces_lost INT NOT NULL DEFAULT 0,  -- Số quân bị mất
    won BIT NOT NULL DEFAULT 1,  -- Chỉ lưu khi thắng
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_PveHighscores_Users FOREIGN KEY (user_id) REFERENCES Users(user_id)
);
GO

-- Index cho query leaderboard
CREATE INDEX IX_PveHighscores_Difficulty_Score ON PveHighscores (difficulty, game_score DESC, moves_count ASC);
CREATE INDEX IX_PveHighscores_UserId ON PveHighscores (user_id);
GO

-- SP: Lưu điểm cao PvE
CREATE PROCEDURE sp_SavePveHighscore
    @user_id INT,
    @difficulty NVARCHAR(10),
    @game_score FLOAT,
    @moves_count INT,
    @elapsed_time INT,
    @pieces_captured INT,
    @pieces_lost INT
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Lấy điểm cao nhất hiện tại của user
    DECLARE @existing_score FLOAT = 0;
    DECLARE @existing_moves INT = 9999;
    
    -- Lấy điểm cao nhất
    SELECT @existing_score = ISNULL(MAX(game_score), 0)
    FROM PveHighscores 
    WHERE user_id = @user_id AND difficulty = @difficulty;
    
    -- Lấy số nước ít nhất với điểm cao nhất đó
    SELECT @existing_moves = ISNULL(MIN(moves_count), 9999)
    FROM PveHighscores 
    WHERE user_id = @user_id AND difficulty = @difficulty AND game_score = @existing_score;
    
    -- Chỉ insert nếu điểm mới cao hơn hoặc (bằng điểm nhưng ít nước hơn)
    IF @game_score > @existing_score OR (@game_score = @existing_score AND @moves_count < @existing_moves)
    BEGIN
        INSERT INTO PveHighscores (user_id, difficulty, game_score, moves_count, elapsed_time, pieces_captured, pieces_lost)
        VALUES (@user_id, @difficulty, @game_score, @moves_count, @elapsed_time, @pieces_captured, @pieces_lost);
        
        SELECT 'new_highscore' AS result, SCOPE_IDENTITY() AS id;
    END
    ELSE
    BEGIN
        SELECT 'not_highscore' AS result, NULL AS id;
    END
END
GO

-- SP: Lấy bảng xếp hạng PvE theo độ khó
CREATE PROCEDURE sp_GetPveLeaderboard
    @difficulty NVARCHAR(10),
    @limit INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Lấy điểm cao nhất của mỗi user cho độ khó này
    -- Xếp hạng theo: game_score DESC, moves_count ASC (điểm cao, ít nước đi hơn thắng)
    WITH RankedScores AS (
        SELECT 
            p.user_id,
            u.username,
            p.game_score,
            p.moves_count,
            p.elapsed_time,
            p.pieces_captured,
            p.pieces_lost,
            p.created_at,
            ROW_NUMBER() OVER (PARTITION BY p.user_id ORDER BY p.game_score DESC, p.moves_count ASC) as rn
        FROM PveHighscores p
        INNER JOIN Users u ON p.user_id = u.user_id
        WHERE p.difficulty = @difficulty
    )
    SELECT TOP (@limit)
        ROW_NUMBER() OVER (ORDER BY game_score DESC, moves_count ASC) as rank,
        user_id,
        username,
        game_score,
        moves_count,
        elapsed_time,
        pieces_captured,
        pieces_lost,
        created_at
    FROM RankedScores
    WHERE rn = 1
    ORDER BY game_score DESC, moves_count ASC;
END
GO

-- ============================================
-- Bước 8: Tạo user admin mẫu (password: admin123)
-- ============================================
-- Password hash được tạo bằng bcrypt
-- Bạn cần thay đổi password hash này khi triển khai thực tế
INSERT INTO Users (username, email, password_hash, elo_rating)
VALUES ('admin', 'admin@cotuwong.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4/VOwNJO0HhMhV4.', 1500);
GO

PRINT N'============================================';
PRINT N'Database CoTuongDB đã được tạo thành công!';
PRINT N'============================================';
GO
