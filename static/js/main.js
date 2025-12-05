/**
 * CỜ TƯỚNG ONLINE - Main JavaScript
 * Logic game phía client với Canvas rendering và Socket.IO
 */

// ============================================
// GLOBAL VARIABLES
// ============================================
let socket = null;
let canvas = null;
let ctx = null;

// Game state
let gameState = {
    board: null,           // Trạng thái bàn cờ 10x9
    turn: 'red',           // Lượt hiện tại
    selectedPiece: null,   // Quân đang chọn {row, col}
    validMoves: [],        // Các nước đi hợp lệ của quân đang chọn
    playerColor: 'red',    // Màu của người chơi
    isMyTurn: true,        // Có phải lượt của mình không
    gameOver: false,       // Game đã kết thúc chưa
    lastMove: null,        // Nước đi cuối cùng
    moveHistory: [],       // Lịch sử nước đi
    capturedByPlayer: [],  // Quân đối phương bị ta ăn
    capturedByOpponent: [], // Quân ta bị đối phương ăn
    playerScore: 0,        // Điểm của người chơi
    opponentScore: 0,      // Điểm của đối thủ
    aiThinking: false      // AI đang suy nghĩ (không đếm timer)
};

// Timer state
let timerState = {
    playerTime: 0,         // Thời gian còn lại của player (giây)
    opponentTime: 0,       // Thời gian còn lại của đối thủ (giây)
    turnTime: 30,          // Thời gian mỗi lượt (giây)
    timerInterval: null,   // Interval ID cho turn timer
    isRunning: false,
    turnStartTime: null,   // Thời điểm bắt đầu lượt
    gameStartTime: null,   // Thời điểm bắt đầu game
    elapsedInterval: null  // Interval ID cho elapsed time
};

// Điểm số cho từng loại quân cờ (điểm khi ăn quân)
const PIECE_POINTS = {
    'K': 0,    // Tướng - không tính điểm (ăn = thắng)
    'A': 2,    // Sĩ
    'E': 2,    // Tượng
    'R': 9,    // Xe
    'N': 4,    // Mã
    'C': 4.5,  // Pháo
    'P': 1     // Tốt/Chốt
};

// Điểm thưởng bonus (x10 để có giá trị cao hơn)
const BONUS_POINTS = {
    CHECKMATE: 100,        // Chiếu bí đối phương
    FAST_WIN: 150,         // Thắng nhanh (< 30 nước)
    MEDIUM_WIN: 100,       // Thắng vừa (< 50 nước)
    TIME_BONUS_PER_MIN: 20,// Điểm mỗi phút còn lại
    DEFENSE_BONUS: 50,     // Không mất Sĩ Tượng
    PERFECT_DEFENSE: 80    // Không mất quân nào
};

// Tên quân cờ tiếng Việt
const PIECE_NAMES = {
    'K': { red: 'Tướng', black: 'Tướng', symbol: { red: '帥', black: '將' } },
    'A': { red: 'Sĩ', black: 'Sĩ', symbol: { red: '仕', black: '士' } },
    'E': { red: 'Tượng', black: 'Tượng', symbol: { red: '相', black: '象' } },
    'R': { red: 'Xe', black: 'Xe', symbol: { red: '俥', black: '車' } },
    'N': { red: 'Mã', black: 'Mã', symbol: { red: '傌', black: '馬' } },
    'C': { red: 'Pháo', black: 'Pháo', symbol: { red: '炮', black: '砲' } },
    'P': { red: 'Tốt', black: 'Chốt', symbol: { red: '兵', black: '卒' } }
};

// Tên cột theo ký hiệu cờ tướng (1-9 từ phải sang trái cho đỏ)
const COL_NAMES_RED = ['9', '8', '7', '6', '5', '4', '3', '2', '1'];
const COL_NAMES_BLACK = ['1', '2', '3', '4', '5', '6', '7', '8', '9'];

// Board dimensions - ĐO CHÍNH XÁC TỪ ẢNH board.png
// Tọa độ 4 góc (đo bằng Paint):
//   Trên-trái (0,0): 42, 55
//   Trên-phải (0,8): 497, 55
//   Dưới-trái (9,0): 42, 560
//   Dưới-phải (9,8): 497, 560
//
// Tính toán:
//   cellWidth = (497 - 42) / 8 = 56.875
//   cellHeight = (560 - 55) / 9 = 56.11
const BOARD = {
    rows: 10,
    cols: 9,
    // Kích thước ô cờ - CHÍNH XÁC
    cellWidth: 56.875,
    cellHeight: 56.11,
    // Padding từ mép ảnh đến giao điểm đầu tiên
    paddingLeft: 42,
    paddingTop: 55,
    // Kích thước quân cờ
    pieceSize: 48
};

// ============================================
// IMAGE CONFIGURATION - Cấu hình dùng hình ảnh
// ============================================
// Đặt USE_IMAGES = true để dùng hình ảnh, false để dùng chữ Hán
const USE_IMAGES = true;
const USE_BOARD_IMAGE = true;  // Dùng ảnh bàn cờ

// Lưu cache hình ảnh
const pieceImages = {};
let boardImage = null;
let imagesLoaded = false;
let boardImageLoaded = false;

// Tên file hình ảnh trong folder static/assets/pieces/
// Format: {color}_{type}.png với background trong suốt (transparent PNG)
// Kích thước khuyến nghị: 60x60 pixels
const PIECE_IMAGE_NAMES = {
    'K': { red: 'red_king.png', black: 'black_king.png' },
    'A': { red: 'red_advisor.png', black: 'black_advisor.png' },
    'E': { red: 'red_elephant.png', black: 'black_elephant.png' },
    'R': { red: 'red_rook.png', black: 'black_rook.png' },
    'N': { red: 'red_knight.png', black: 'black_knight.png' },
    'C': { red: 'red_cannon.png', black: 'black_cannon.png' },
    'P': { red: 'red_pawn.png', black: 'black_pawn.png' }
};

// Tên file ảnh bàn cờ: static/assets/board.png
const BOARD_IMAGE_PATH = '/static/assets/board.png';

// Piece symbols (Unicode Chinese characters) - Fallback khi không có ảnh
const PIECE_SYMBOLS = {
    'K': { red: '帥', black: '將' },
    'A': { red: '仕', black: '士' },
    'E': { red: '相', black: '象' },
    'R': { red: '俥', black: '車' },
    'N': { red: '傌', black: '馬' },
    'C': { red: '炮', black: '砲' },
    'P': { red: '兵', black: '卒' }
};

// Colors
const COLORS = {
    board: '#F5DEB3',       // Wheat - màu bàn cờ
    boardDark: '#DEB887',   // BurlyWood - màu đậm hơn
    line: '#8B4513',        // SaddleBrown - màu đường kẻ
    redPiece: '#C0392B',    // Màu quân đỏ
    blackPiece: '#1A1A1A',  // Màu quân đen
    selected: '#FFD700',    // Gold - quân được chọn
    validMove: '#32CD32',   // LimeGreen - nước đi hợp lệ
    lastMove: '#87CEEB',    // SkyBlue - nước đi cuối
    check: '#FF4500'        // OrangeRed - chiếu tướng
};

// ============================================
// IMAGE LOADING
// ============================================
function loadBoardImage() {
    return new Promise((resolve) => {
        if (!USE_BOARD_IMAGE) {
            resolve();
            return;
        }
        
        boardImage = new Image();
        boardImage.onload = () => {
            boardImageLoaded = true;
            console.log('Board image loaded successfully');
            resolve();
        };
        boardImage.onerror = () => {
            console.warn('Failed to load board image, using canvas drawing');
            boardImageLoaded = false;
            resolve();
        };
        boardImage.src = BOARD_IMAGE_PATH;
        
        // Timeout
        setTimeout(() => {
            if (!boardImageLoaded) {
                console.warn('Board image loading timeout');
                resolve();
            }
        }, 3000);
    });
}

function loadPieceImages() {
    return new Promise((resolve) => {
        if (!USE_IMAGES) {
            resolve();
            return;
        }
        
        let loadedCount = 0;
        const totalImages = 14; // 7 loại x 2 màu
        
        for (const [type, colors] of Object.entries(PIECE_IMAGE_NAMES)) {
            for (const [color, filename] of Object.entries(colors)) {
                const img = new Image();
                img.onload = () => {
                    loadedCount++;
                    console.log(`Loaded: ${filename} (${loadedCount}/${totalImages})`);
                    if (loadedCount >= totalImages) {
                        imagesLoaded = true;
                        resolve();
                    }
                };
                img.onerror = () => {
                    loadedCount++;
                    console.warn(`Failed to load: ${filename}`);
                    if (loadedCount >= totalImages) {
                        resolve();
                    }
                };
                img.src = `/static/assets/pieces/${filename}`;
                pieceImages[`${color}_${type}`] = img;
            }
        }
        
        // Timeout sau 3 giây nếu không load được
        setTimeout(() => {
            if (!imagesLoaded) {
                console.warn('Image loading timeout, using text fallback');
                resolve();
            }
        }, 3000);
    });
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Chỉ init game nếu đang ở trang game
    if (typeof GAME_DATA !== 'undefined') {
        initGame();
    }
});

async function initGame() {
    canvas = document.getElementById('boardCanvas');
    if (!canvas) return;
    
    ctx = canvas.getContext('2d');
    
    // Lưu game type và AI difficulty vào gameState
    gameState.gameType = GAME_DATA.gameType || 'pvp';
    gameState.aiDifficulty = GAME_DATA.aiDifficulty || 'medium';
    
    // Load images first để lấy kích thước thực của board
    await Promise.all([loadBoardImage(), loadPieceImages()]);
    
    // Set canvas size theo kích thước ảnh board thực tế
    if (boardImageLoaded && boardImage) {
        canvas.width = boardImage.naturalWidth;
        canvas.height = boardImage.naturalHeight;
        console.log(`Board image size: ${canvas.width}x${canvas.height}`);
        console.log(`Using fixed cell size: ${BOARD.cellWidth}x${BOARD.cellHeight}`);
        console.log(`Padding: left=${BOARD.paddingLeft}, top=${BOARD.paddingTop}`);
    } else {
        // Fallback nếu không có ảnh board
        canvas.width = 540;
        canvas.height = 600;
    }
    
    // Init Socket.IO
    initSocket();
    
    // Add event listeners
    canvas.addEventListener('click', handleCanvasClick);
    
    // Determine player color
    determinePlayerColor();
    
    // Init timer
    initTimer();
    
    // Draw initial board
    drawBoard();
    
    // Hide overlay once connected
    setTimeout(() => {
        const overlay = document.getElementById('boardOverlay');
        if (overlay) overlay.classList.add('hidden');
    }, 1000);
}

function initSocket() {
    socket = io();
    
    socket.on('connect', () => {
        console.log('Connected to server, socket id:', socket.id);
        // Join game room
        console.log('Joining game room:', GAME_DATA.roomCode);
        socket.emit('join_game', {
            room_code: GAME_DATA.roomCode,
            user_id: GAME_DATA.currentUser?.id,
            username: GAME_DATA.currentUser?.username || 'Guest'
        });
    });
    
    socket.on('game_state', (data) => {
        console.log('Received game state:', data);
        if (data.board) {
            gameState.board = data.board.grid;
            gameState.turn = data.board.turn;
            updateTurnStatus();
            drawBoard();
        }
        
        // Cập nhật thông tin người chơi
        if (data.players) {
            const myColor = gameState.playerColor || 'red';
            const opponentColor = myColor === 'red' ? 'black' : 'red';
            
            // Cập nhật tên người chơi
            const playerNameEl = document.getElementById('playerName');
            const opponentNameEl = document.getElementById('opponentName');
            
            if (playerNameEl && data.players[myColor]) {
                playerNameEl.textContent = data.players[myColor].name || 'Bạn';
            }
            if (opponentNameEl && data.players[opponentColor]) {
                opponentNameEl.textContent = data.players[opponentColor].name || 'Đối thủ';
            }
            
            console.log('Updated player names:', {
                player: data.players[myColor]?.name,
                opponent: data.players[opponentColor]?.name
            });
        }
    });
    
    socket.on('move_made', (data) => {
        console.log('Move made event received:', data);
        handleOpponentMove(data);
    });
    
    socket.on('move_error', (data) => {
        console.log('Move error:', data);
        alert('Lỗi: ' + data.message);
        // Deselect piece
        gameState.selectedPiece = null;
        gameState.validMoves = [];
        drawBoard();
    });
    
    socket.on('game_over', (data) => {
        console.log('Game over:', data);
        handleGameOver(data);
    });
    
    socket.on('player_joined', (data) => {
        console.log('Player joined:', data);
        addSystemMessage(`${data.username} đã tham gia phòng`);
        updateOpponentInfo(data.username);
    });
    
    socket.on('player_left', (data) => {
        console.log('Player left:', data);
        addSystemMessage('Đối thủ đã rời phòng');
    });
    
    socket.on('draw_offered', () => {
        document.getElementById('drawOfferModal').style.display = 'flex';
    });
    
    socket.on('chat_message', (data) => {
        addChatMessage(data.username, data.message);
    });
    
    // Nhận sync time từ server để đồng bộ timer
    socket.on('time_sync', (data) => {
        if (data.red_time !== undefined) {
            if (gameState.playerColor === 'red') {
                timerState.playerTime = data.red_time;
            } else {
                timerState.opponentTime = data.red_time;
            }
        }
        if (data.black_time !== undefined) {
            if (gameState.playerColor === 'black') {
                timerState.playerTime = data.black_time;
            } else {
                timerState.opponentTime = data.black_time;
            }
        }
        updateTimerDisplay();
    });
    
    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        addSystemMessage('Mất kết nối với server');
    });
}

function determinePlayerColor() {
    // Với PvP, cần xác định màu dựa trên ID
    if (GAME_DATA.gameType === 'pvp') {
        if (GAME_DATA.currentUser) {
            // User đã đăng nhập
            if (GAME_DATA.redPlayerId === GAME_DATA.currentUser.id) {
                gameState.playerColor = 'red';
            } else if (GAME_DATA.blackPlayerId === GAME_DATA.currentUser.id) {
                gameState.playerColor = 'black';
            } else {
                // User không match - có thể là bug hoặc user khác
                console.warn('User ID không match với bất kỳ player nào');
                gameState.playerColor = 'red'; // Fallback
            }
        } else {
            // Guest trong PvP - cần xác định dựa vào vị trí trống
            // Nếu red_player_id là null thì guest là red
            // Nếu black_player_id là null thì guest là black
            if (GAME_DATA.redPlayerId === null) {
                gameState.playerColor = 'red';
            } else if (GAME_DATA.blackPlayerId === null) {
                gameState.playerColor = 'black';
            } else {
                // Cả 2 đều có người - guest không thể vào
                console.warn('Phòng đã đủ người');
                gameState.playerColor = 'red'; // Fallback
            }
        }
    } else {
        // PvE - dựa vào ai_difficulty
        if (GAME_DATA.currentUser) {
            if (GAME_DATA.redPlayerId === GAME_DATA.currentUser.id) {
                gameState.playerColor = 'red';
            } else if (GAME_DATA.blackPlayerId === GAME_DATA.currentUser.id) {
                gameState.playerColor = 'black';
            } else {
                gameState.playerColor = 'red';
            }
        } else {
            gameState.playerColor = 'red';
        }
    }
    
    console.log('Player color determined:', gameState.playerColor);
    console.log('GAME_DATA:', GAME_DATA);
    
    // Update UI
    updatePlayerSideDisplay();
    gameState.isMyTurn = (gameState.turn === gameState.playerColor);
}

// ============================================
// DRAWING FUNCTIONS
// ============================================

function drawBoard() {
    if (!ctx) return;
    
    // Clear canvas
    ctx.fillStyle = COLORS.board;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Vẽ bàn cờ bằng ảnh hoặc canvas
    if (USE_BOARD_IMAGE && boardImageLoaded && boardImage) {
        // Vẽ ảnh bàn cờ
        ctx.drawImage(boardImage, 0, 0, canvas.width, canvas.height);
    } else {
        // Vẽ bằng canvas (fallback)
        drawGridLines();
        drawRiver();
        drawPalace();
    }
    
    // Draw last move highlight
    if (gameState.lastMove) {
        highlightLastMove();
    }
    
    // Draw valid moves
    if (gameState.validMoves.length > 0) {
        drawValidMoves();
    }
    
    // Draw pieces
    drawPieces();
    
    // Draw selected piece highlight
    if (gameState.selectedPiece) {
        drawSelectedHighlight();
    }
}

function drawGridLines() {
    ctx.strokeStyle = COLORS.line;
    ctx.lineWidth = 2;
    
    const startX = BOARD.paddingLeft;
    const startY = BOARD.paddingTop;
    const endX = BOARD.paddingLeft + (BOARD.cols - 1) * BOARD.cellWidth;
    const endY = BOARD.paddingTop + (BOARD.rows - 1) * BOARD.cellHeight;
    
    // Vertical lines
    for (let col = 0; col < BOARD.cols; col++) {
        const x = startX + col * BOARD.cellWidth;
        
        // Top half
        ctx.beginPath();
        ctx.moveTo(x, startY);
        ctx.lineTo(x, startY + 4 * BOARD.cellHeight);
        ctx.stroke();
        
        // Bottom half
        ctx.beginPath();
        ctx.moveTo(x, startY + 5 * BOARD.cellHeight);
        ctx.lineTo(x, endY);
        ctx.stroke();
    }
    
    // Horizontal lines
    for (let row = 0; row < BOARD.rows; row++) {
        const y = startY + row * BOARD.cellHeight;
        ctx.beginPath();
        ctx.moveTo(startX, y);
        ctx.lineTo(endX, y);
        ctx.stroke();
    }
    
    // Border
    ctx.lineWidth = 3;
    ctx.strokeRect(startX, startY, (BOARD.cols - 1) * BOARD.cellWidth, (BOARD.rows - 1) * BOARD.cellHeight);
}

function drawRiver() {
    const x = BOARD.paddingLeft;
    const y = BOARD.paddingTop + 4 * BOARD.cellHeight;
    const width = (BOARD.cols - 1) * BOARD.cellWidth;
    const height = BOARD.cellHeight;
    
    // River background
    ctx.fillStyle = 'rgba(30, 144, 255, 0.1)';
    ctx.fillRect(x, y, width, height);
    
    // River text
    ctx.font = 'bold 24px serif';
    ctx.fillStyle = COLORS.line;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    ctx.fillText('楚', x + width * 0.25, y + height / 2);
    ctx.fillText('河', x + width * 0.35, y + height / 2);
    ctx.fillText('漢', x + width * 0.65, y + height / 2);
    ctx.fillText('界', x + width * 0.75, y + height / 2);
}

function drawPalace() {
    ctx.strokeStyle = COLORS.line;
    ctx.lineWidth = 2;
    
    // Top palace (black)
    const topPalaceX = BOARD.paddingLeft + 3 * BOARD.cellWidth;
    const topPalaceY = BOARD.paddingTop;
    
    ctx.beginPath();
    ctx.moveTo(topPalaceX, topPalaceY);
    ctx.lineTo(topPalaceX + 2 * BOARD.cellWidth, topPalaceY + 2 * BOARD.cellHeight);
    ctx.stroke();
    
    ctx.beginPath();
    ctx.moveTo(topPalaceX + 2 * BOARD.cellWidth, topPalaceY);
    ctx.lineTo(topPalaceX, topPalaceY + 2 * BOARD.cellHeight);
    ctx.stroke();
    
    // Bottom palace (red)
    const bottomPalaceX = BOARD.paddingLeft + 3 * BOARD.cellWidth;
    const bottomPalaceY = BOARD.paddingTop + 7 * BOARD.cellHeight;
    
    ctx.beginPath();
    ctx.moveTo(bottomPalaceX, bottomPalaceY);
    ctx.lineTo(bottomPalaceX + 2 * BOARD.cellWidth, bottomPalaceY + 2 * BOARD.cellHeight);
    ctx.stroke();
    
    ctx.beginPath();
    ctx.moveTo(bottomPalaceX + 2 * BOARD.cellWidth, bottomPalaceY);
    ctx.lineTo(bottomPalaceX, bottomPalaceY + 2 * BOARD.cellHeight);
    ctx.stroke();
}

function drawPieces() {
    if (!gameState.board) return;
    
    for (let row = 0; row < BOARD.rows; row++) {
        for (let col = 0; col < BOARD.cols; col++) {
            const piece = gameState.board[row][col];
            if (piece) {
                drawPiece(row, col, piece);
            }
        }
    }
}

function drawPiece(row, col, piece) {
    // Tính vị trí trung tâm của giao điểm
    const x = BOARD.paddingLeft + col * BOARD.cellWidth;
    const y = BOARD.paddingTop + row * BOARD.cellHeight;
    
    // Kích thước quân cờ cố định
    const size = BOARD.pieceSize;
    
    // Thử vẽ bằng hình ảnh trước
    if (USE_IMAGES && imagesLoaded) {
        const imgKey = `${piece.color}_${piece.type}`;
        const img = pieceImages[imgKey];
        
        if (img && img.complete && img.naturalWidth > 0) {
            // Vẽ hình ảnh quân cờ - căn giữa tại giao điểm
            ctx.drawImage(img, x - size/2, y - size/2, size, size);
            return;
        }
    }
    
    // Fallback: Vẽ bằng chữ Hán
    drawPieceWithText(x, y, piece, size);
}

function drawPieceWithText(x, y, piece, size) {
    const radius = (size || BOARD.pieceSize) / 2;
    
    // Draw piece circle
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    
    // Fill with gradient
    const gradient = ctx.createRadialGradient(x - 5, y - 5, 0, x, y, radius);
    gradient.addColorStop(0, '#FFF8DC');
    gradient.addColorStop(1, '#D2B48C');
    ctx.fillStyle = gradient;
    ctx.fill();
    
    // Border
    ctx.strokeStyle = piece.color === 'red' ? COLORS.redPiece : COLORS.blackPiece;
    ctx.lineWidth = 3;
    ctx.stroke();
    
    // Draw character
    const symbol = PIECE_SYMBOLS[piece.type]?.[piece.color] || piece.type;
    ctx.font = 'bold 28px serif';
    ctx.fillStyle = piece.color === 'red' ? COLORS.redPiece : COLORS.blackPiece;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(symbol, x, y + 2);
}

function drawSelectedHighlight() {
    if (!gameState.selectedPiece) return;
    
    const x = BOARD.paddingLeft + gameState.selectedPiece.col * BOARD.cellWidth;
    const y = BOARD.paddingTop + gameState.selectedPiece.row * BOARD.cellHeight;
    const radius = BOARD.pieceSize / 2 + 4;
    
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.strokeStyle = COLORS.selected;
    ctx.lineWidth = 4;
    ctx.stroke();
}

function drawValidMoves() {
    const radius = BOARD.pieceSize / 2;
    
    for (const move of gameState.validMoves) {
        const x = BOARD.paddingLeft + move.col * BOARD.cellWidth;
        const y = BOARD.paddingTop + move.row * BOARD.cellHeight;
        
        const targetPiece = gameState.board[move.row][move.col];
        
        if (targetPiece) {
            // Capture move - draw red circle
            ctx.beginPath();
            ctx.arc(x, y, radius + 4, 0, Math.PI * 2);
            ctx.strokeStyle = COLORS.check;
            ctx.lineWidth = 3;
            ctx.stroke();
        } else {
            // Normal move - draw green dot
            ctx.beginPath();
            ctx.arc(x, y, 12, 0, Math.PI * 2);
            ctx.fillStyle = COLORS.validMove;
            ctx.globalAlpha = 0.7;
            ctx.fill();
            ctx.globalAlpha = 1.0;
        }
    }
}

function highlightLastMove() {
    if (!gameState.lastMove) return;
    
    const { fromRow, fromCol, toRow, toCol } = gameState.lastMove;
    
    // Highlight from square
    ctx.fillStyle = 'rgba(52, 152, 219, 0.3)';
    ctx.fillRect(
        BOARD.paddingLeft + fromCol * BOARD.cellWidth - BOARD.cellWidth / 2,
        BOARD.paddingTop + fromRow * BOARD.cellHeight - BOARD.cellHeight / 2,
        BOARD.cellWidth,
        BOARD.cellHeight
    );
    
    // Highlight to square
    ctx.fillRect(
        BOARD.paddingLeft + toCol * BOARD.cellWidth - BOARD.cellWidth / 2,
        BOARD.paddingTop + toRow * BOARD.cellHeight - BOARD.cellHeight / 2,
        BOARD.cellWidth,
        BOARD.cellHeight
    );
}

// ============================================
// GAME LOGIC
// ============================================

function handleCanvasClick(event) {
    if (!gameState.board || gameState.gameOver) return;
    
    const rect = canvas.getBoundingClientRect();
    // Tính tỉ lệ scale nếu canvas bị resize bởi CSS
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    
    const clickX = (event.clientX - rect.left) * scaleX;
    const clickY = (event.clientY - rect.top) * scaleY;
    
    // Convert to board coordinates
    const col = Math.round((clickX - BOARD.paddingLeft) / BOARD.cellWidth);
    const row = Math.round((clickY - BOARD.paddingTop) / BOARD.cellHeight);
    
    console.log(`Click at (${clickX.toFixed(0)}, ${clickY.toFixed(0)}) -> row=${row}, col=${col}`);
    
    // Check bounds
    if (row < 0 || row >= BOARD.rows || col < 0 || col >= BOARD.cols) {
        return;
    }
    
    const clickedPiece = gameState.board[row][col];
    
    // If already selected a piece
    if (gameState.selectedPiece) {
        // Check if clicking on valid move
        const validMove = gameState.validMoves.find(m => m.row === row && m.col === col);
        
        if (validMove) {
            // Make the move
            makeMove(gameState.selectedPiece.row, gameState.selectedPiece.col, row, col);
        } else if (clickedPiece && clickedPiece.color === gameState.playerColor) {
            // Select different piece of same color
            selectPiece(row, col);
        } else {
            // Deselect
            gameState.selectedPiece = null;
            gameState.validMoves = [];
            drawBoard();
        }
    } else {
        // Select a piece if it's player's piece and player's turn
        if (clickedPiece) {
            console.log(`Clicked piece: ${clickedPiece.type} (${clickedPiece.color}), playerColor: ${gameState.playerColor}, turn: ${gameState.turn}`);
        }
        if (clickedPiece && clickedPiece.color === gameState.playerColor) {
            if (gameState.turn !== gameState.playerColor) {
                updateStatus('Chưa đến lượt của bạn!', 'opponent-turn');
                return;
            }
            selectPiece(row, col);
        }
    }
}

function selectPiece(row, col) {
    gameState.selectedPiece = { row, col };
    gameState.validMoves = calculateValidMoves(row, col);
    drawBoard();
}

function calculateValidMoves(row, col) {
    // Client-side move calculation (simplified)
    // The server will validate the actual move
    const piece = gameState.board[row][col];
    if (!piece) return [];
    
    const moves = [];
    
    switch (piece.type) {
        case 'K': // King/General
            moves.push(...getKingMoves(row, col, piece.color));
            break;
        case 'A': // Advisor
            moves.push(...getAdvisorMoves(row, col, piece.color));
            break;
        case 'E': // Elephant
            moves.push(...getElephantMoves(row, col, piece.color));
            break;
        case 'R': // Rook/Chariot
            moves.push(...getRookMoves(row, col, piece.color));
            break;
        case 'N': // Knight/Horse
            moves.push(...getKnightMoves(row, col, piece.color));
            break;
        case 'C': // Cannon
            moves.push(...getCannonMoves(row, col, piece.color));
            break;
        case 'P': // Pawn/Soldier
            moves.push(...getPawnMoves(row, col, piece.color));
            break;
    }
    
    return moves;
}

function getKingMoves(row, col, color) {
    const moves = [];
    const directions = [[0, 1], [0, -1], [1, 0], [-1, 0]];
    
    for (const [dr, dc] of directions) {
        const nr = row + dr;
        const nc = col + dc;
        
        if (isInPalace(nr, nc, color)) {
            if (canMoveTo(nr, nc, color)) {
                moves.push({ row: nr, col: nc });
            }
        }
    }
    
    return moves;
}

function getAdvisorMoves(row, col, color) {
    const moves = [];
    const directions = [[1, 1], [1, -1], [-1, 1], [-1, -1]];
    
    for (const [dr, dc] of directions) {
        const nr = row + dr;
        const nc = col + dc;
        
        if (isInPalace(nr, nc, color)) {
            if (canMoveTo(nr, nc, color)) {
                moves.push({ row: nr, col: nc });
            }
        }
    }
    
    return moves;
}

function getElephantMoves(row, col, color) {
    const moves = [];
    const elephantMoves = [
        { dr: 2, dc: 2, br: 1, bc: 1 },
        { dr: 2, dc: -2, br: 1, bc: -1 },
        { dr: -2, dc: 2, br: -1, bc: 1 },
        { dr: -2, dc: -2, br: -1, bc: -1 }
    ];
    
    for (const move of elephantMoves) {
        const nr = row + move.dr;
        const nc = col + move.dc;
        const br = row + move.br;
        const bc = col + move.bc;
        
        if (isValidPos(nr, nc) && isInOwnHalf(nr, color) && !gameState.board[br][bc]) {
            if (canMoveTo(nr, nc, color)) {
                moves.push({ row: nr, col: nc });
            }
        }
    }
    
    return moves;
}

function getRookMoves(row, col, color) {
    const moves = [];
    const directions = [[0, 1], [0, -1], [1, 0], [-1, 0]];
    
    for (const [dr, dc] of directions) {
        let nr = row + dr;
        let nc = col + dc;
        
        while (isValidPos(nr, nc)) {
            if (!gameState.board[nr][nc]) {
                moves.push({ row: nr, col: nc });
            } else {
                if (gameState.board[nr][nc].color !== color) {
                    moves.push({ row: nr, col: nc });
                }
                break;
            }
            nr += dr;
            nc += dc;
        }
    }
    
    return moves;
}

function getKnightMoves(row, col, color) {
    const moves = [];
    const knightMoves = [
        { dr: -2, dc: 1, br: -1, bc: 0 },
        { dr: -2, dc: -1, br: -1, bc: 0 },
        { dr: 2, dc: 1, br: 1, bc: 0 },
        { dr: 2, dc: -1, br: 1, bc: 0 },
        { dr: 1, dc: 2, br: 0, bc: 1 },
        { dr: 1, dc: -2, br: 0, bc: -1 },
        { dr: -1, dc: 2, br: 0, bc: 1 },
        { dr: -1, dc: -2, br: 0, bc: -1 }
    ];
    
    for (const move of knightMoves) {
        const nr = row + move.dr;
        const nc = col + move.dc;
        const br = row + move.br;
        const bc = col + move.bc;
        
        if (isValidPos(nr, nc) && !gameState.board[br][bc]) {
            if (canMoveTo(nr, nc, color)) {
                moves.push({ row: nr, col: nc });
            }
        }
    }
    
    return moves;
}

function getCannonMoves(row, col, color) {
    const moves = [];
    const directions = [[0, 1], [0, -1], [1, 0], [-1, 0]];
    
    for (const [dr, dc] of directions) {
        let nr = row + dr;
        let nc = col + dc;
        let jumped = false;
        
        while (isValidPos(nr, nc)) {
            if (!jumped) {
                if (!gameState.board[nr][nc]) {
                    moves.push({ row: nr, col: nc });
                } else {
                    jumped = true;
                }
            } else {
                if (gameState.board[nr][nc]) {
                    if (gameState.board[nr][nc].color !== color) {
                        moves.push({ row: nr, col: nc });
                    }
                    break;
                }
            }
            nr += dr;
            nc += dc;
        }
    }
    
    return moves;
}

function getPawnMoves(row, col, color) {
    const moves = [];
    
    // Forward direction
    const forward = color === 'red' ? -1 : 1;
    const crossedRiver = color === 'red' ? row <= 4 : row >= 5;
    
    // Forward move
    const nr = row + forward;
    if (isValidPos(nr, col) && canMoveTo(nr, col, color)) {
        moves.push({ row: nr, col: col });
    }
    
    // Sideways after crossing river
    if (crossedRiver) {
        if (isValidPos(row, col - 1) && canMoveTo(row, col - 1, color)) {
            moves.push({ row: row, col: col - 1 });
        }
        if (isValidPos(row, col + 1) && canMoveTo(row, col + 1, color)) {
            moves.push({ row: row, col: col + 1 });
        }
    }
    
    return moves;
}

// Helper functions
function isValidPos(row, col) {
    return row >= 0 && row < BOARD.rows && col >= 0 && col < BOARD.cols;
}

function isInPalace(row, col, color) {
    if (col < 3 || col > 5) return false;
    if (color === 'red') {
        return row >= 7 && row <= 9;
    } else {
        return row >= 0 && row <= 2;
    }
}

function isInOwnHalf(row, color) {
    if (color === 'red') {
        return row >= 5;
    } else {
        return row <= 4;
    }
}

function canMoveTo(row, col, color) {
    const piece = gameState.board[row][col];
    return !piece || piece.color !== color;
}

function makeMove(fromRow, fromCol, toRow, toCol) {
    console.log(`Making move: (${fromRow},${fromCol}) -> (${toRow},${toCol})`);
    
    // Nếu là PvE, set AI đang suy nghĩ sau khi player đi
    if (GAME_DATA.gameType === 'pve') {
        gameState.aiThinking = true;
    }
    
    // Send move to server
    socket.emit('make_move', {
        room_code: GAME_DATA.roomCode,
        from_row: fromRow,
        from_col: fromCol,
        to_row: toRow,
        to_col: toCol,
        player_color: gameState.playerColor
    });
    
    // Deselect
    gameState.selectedPiece = null;
    gameState.validMoves = [];
}

function handleOpponentMove(data) {
    console.log('handleOpponentMove called:', data);
    console.log('Current turn before:', gameState.turn);
    console.log('My color:', gameState.playerColor);
    
    // AI đã đi xong, tắt flag aiThinking
    if (GAME_DATA.gameType === 'pve' && data.is_ai) {
        gameState.aiThinking = false;
    }
    
    // Lưu lại quân bị ăn (nếu có) trước khi update board
    const capturedPiece = data.captured || null;
    const movedPiece = data.piece || null;
    
    // Update board
    if (data.board) {
        gameState.board = data.board.grid;
        gameState.turn = data.board.turn;
        console.log('Current turn after update:', gameState.turn);
    }
    
    // Sync timer nếu server gửi remaining_time
    if (data.remaining_time !== undefined) {
        // remaining_time là thời gian còn lại của người vừa đi
        if (data.player === gameState.playerColor) {
            timerState.playerTime = data.remaining_time;
        } else {
            timerState.opponentTime = data.remaining_time;
        }
    }
    
    // Record last move
    gameState.lastMove = {
        fromRow: data.from_row,
        fromCol: data.from_col,
        toRow: data.to_row,
        toCol: data.to_col
    };
    
    // Add captured piece to list
    if (capturedPiece) {
        addCapturedPiece(capturedPiece, data.player);
    }
    
    // Add to move history với thông tin quân cờ
    addMoveToHistory(data.player, data.from_row, data.from_col, data.to_row, data.to_col, movedPiece, capturedPiece);
    
    // Update turn status - QUAN TRỌNG: cập nhật isMyTurn
    updateTurnStatus();
    console.log('isMyTurn after update:', gameState.isMyTurn);
    
    // Reset timer cho lượt mới
    resetTurnTimer();
    
    // Redraw board
    drawBoard();
    
    // Play sound (if available)
    // playMoveSound();
}

function handleGameOver(data) {
    gameState.gameOver = true;
    stopTimer(); // Dừng timer khi game kết thúc
    
    // Tính điểm tổng kết
    const scoreBreakdown = calculateFinalScore(data);
    
    // Lưu điểm PvE nếu thắng và đã đăng nhập
    const isWinner = data.winner === gameState.playerColor;
    if (gameState.gameType === 'pve' && isWinner && window.currentUser) {
        savePveHighscore(scoreBreakdown);
    }
    
    const modal = document.getElementById('gameOverModal');
    const title = document.getElementById('gameOverTitle');
    const message = document.getElementById('gameOverMessage');
    const icon = document.getElementById('gameOverIcon');
    
    let reasonText = '';
    if (data.reason === 'timeout') {
        reasonText = ' (hết giờ)';
    } else if (data.reason === 'checkmate') {
        reasonText = ' (chiếu bí)';
    } else if (data.reason === 'resign') {
        reasonText = ' (đầu hàng)';
    }
    
    // Tạo HTML chi tiết điểm
    const scoreHtml = createScoreSummaryHtml(scoreBreakdown, data.winner === gameState.playerColor);
    
    if (data.winner === gameState.playerColor) {
        title.textContent = '🎉 Chúc mừng!';
        message.innerHTML = 'Bạn đã chiến thắng!' + reasonText + scoreHtml;
        icon.classList.remove('lose', 'draw');
    } else if (data.winner === null || data.reason === 'draw') {
        title.textContent = '🤝 Hòa!';
        message.innerHTML = 'Ván đấu kết thúc hòa.' + scoreHtml;
        icon.classList.remove('lose');
        icon.classList.add('draw');
    } else {
        title.textContent = '😔 Thua cuộc';
        message.innerHTML = 'Đối thủ đã chiến thắng!' + reasonText + scoreHtml;
        icon.classList.remove('draw');
        icon.classList.add('lose');
    }
    
    modal.style.display = 'flex';
}

// Lưu điểm cao PvE lên server
async function savePveHighscore(breakdown) {
    try {
        // Tính thời gian chơi (giây)
        const elapsedTime = timerState.gameStartTime 
            ? Math.floor((Date.now() - timerState.gameStartTime) / 1000)
            : 0;
        const piecesCaptured = gameState.capturedByPlayer.length;
        const piecesLost = gameState.capturedByOpponent.length;
        
        const response = await fetch('/api/pve-highscore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                difficulty: gameState.aiDifficulty,
                game_score: breakdown.total,
                moves_count: breakdown.totalMoves,
                elapsed_time: elapsedTime,
                pieces_captured: piecesCaptured,
                pieces_lost: piecesLost
            })
        });
        
        const data = await response.json();
        if (data.success && data.result === 'new_highscore') {
            console.log('🏆 Điểm cao mới đã được lưu!');
            // Có thể thêm notification cho user ở đây
            showNotification('🏆 Kỷ lục mới!', 'Bạn đã đạt điểm cao mới cho chế độ ' + getDifficultyName(gameState.aiDifficulty));
        }
    } catch (error) {
        console.error('Lỗi lưu điểm cao:', error);
    }
}

// Hiển thị thông báo
function showNotification(title, message) {
    // Kiểm tra xem có element notification không
    let notification = document.getElementById('highscoreNotification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'highscoreNotification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #ffd700, #ff8c00);
            color: #000;
            padding: 15px 25px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(255, 215, 0, 0.4);
            z-index: 10000;
            animation: slideIn 0.5s ease;
            font-weight: bold;
        `;
        document.body.appendChild(notification);
        
        // Thêm CSS animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    notification.innerHTML = `<div>${title}</div><small>${message}</small>`;
    notification.style.display = 'block';
    
    // Tự động ẩn sau 5 giây
    setTimeout(() => {
        notification.style.display = 'none';
    }, 5000);
}

// Lấy tên độ khó tiếng Việt
function getDifficultyName(difficulty) {
    const names = {
        'easy': 'Dễ',
        'medium': 'Trung bình',
        'hard': 'Khó'
    };
    return names[difficulty] || difficulty;
}

// Tính điểm tổng kết ván đấu
function calculateFinalScore(data) {
    const isWinner = data.winner === gameState.playerColor;
    const isDraw = data.winner === null || data.reason === 'draw';
    
    let breakdown = {
        capturePoints: gameState.playerScore,   // Điểm ăn quân
        checkmateBonus: 0,     // Bonus chiếu bí
        speedBonus: 0,         // Bonus thắng nhanh
        defenseBonus: 0,       // Bonus phòng thủ
        totalMoves: gameState.moveHistory.length,
        total: 0
    };
    
    // Điểm ăn quân đã tính sẵn
    breakdown.total = breakdown.capturePoints;
    
    if (isWinner) {
        // Bonus chiếu bí
        if (data.reason === 'checkmate') {
            breakdown.checkmateBonus = BONUS_POINTS.CHECKMATE;
            breakdown.total += breakdown.checkmateBonus;
        }
        
        // Bonus thắng nhanh
        const playerMoves = Math.ceil(breakdown.totalMoves / 2);
        if (playerMoves < 30) {
            breakdown.speedBonus = BONUS_POINTS.FAST_WIN;
        } else if (playerMoves < 50) {
            breakdown.speedBonus = BONUS_POINTS.MEDIUM_WIN;
        }
        breakdown.total += breakdown.speedBonus;
        
        // Bonus phòng thủ (không mất quân)
        if (gameState.capturedByOpponent.length === 0) {
            breakdown.defenseBonus = BONUS_POINTS.PERFECT_DEFENSE;
        } else {
            // Kiểm tra không mất Sĩ Tượng
            const lostDefenders = gameState.capturedByOpponent.filter(p => 
                p.type === 'A' || p.type === 'E'
            );
            if (lostDefenders.length === 0) {
                breakdown.defenseBonus = BONUS_POINTS.DEFENSE_BONUS;
            }
        }
        breakdown.total += breakdown.defenseBonus;
    }
    
    return breakdown;
}

// Tạo HTML hiển thị chi tiết điểm
function createScoreSummaryHtml(breakdown, isWinner) {
    let html = `
        <div class="score-summary">
            <h4><i class="fas fa-chart-bar"></i> Chi tiết điểm ván đấu</h4>
            <div class="score-row">
                <span>Điểm ăn quân:</span>
                <span class="score-value">${breakdown.capturePoints.toFixed(1)}</span>
            </div>`;
    
    if (isWinner) {
        if (breakdown.checkmateBonus > 0) {
            html += `
            <div class="score-row bonus">
                <span>🏆 Bonus chiếu bí:</span>
                <span class="score-value">+${breakdown.checkmateBonus}</span>
            </div>`;
        }
        if (breakdown.speedBonus > 0) {
            html += `
            <div class="score-row bonus">
                <span>⚡ Bonus thắng nhanh:</span>
                <span class="score-value">+${breakdown.speedBonus}</span>
            </div>`;
        }
        if (breakdown.defenseBonus > 0) {
            html += `
            <div class="score-row bonus">
                <span>🛡️ Bonus phòng thủ:</span>
                <span class="score-value">+${breakdown.defenseBonus}</span>
            </div>`;
        }
    }
    
    html += `
            <div class="score-row total">
                <span><strong>Tổng điểm:</strong></span>
                <span class="score-value total-value">${breakdown.total.toFixed(1)}</span>
            </div>
            <div class="score-info">
                <small>📊 Tổng số nước đi: ${breakdown.totalMoves}</small>
            </div>
        </div>`;
    
    return html;
}

// ============================================
// UI FUNCTIONS
// ============================================

function updateTurnStatus() {
    gameState.isMyTurn = (gameState.turn === gameState.playerColor);
    
    const statusDiv = document.getElementById('gameStatus');
    if (!statusDiv) return;
    
    const statusText = statusDiv.querySelector('.status-text');
    
    if (gameState.isMyTurn) {
        statusText.textContent = 'Lượt của bạn';
        statusDiv.className = 'game-status your-turn';
    } else {
        statusText.textContent = 'Lượt đối thủ';
        statusDiv.className = 'game-status opponent-turn';
    }
    
    // Reset timer cho lượt mới
    if (!gameState.gameOver) {
        resetTurnTimer();
    }
}

// ============================================
// TIMER FUNCTIONS
// ============================================

function initTimer() {
    const gameType = GAME_DATA.gameType;
    const aiDifficulty = GAME_DATA.aiDifficulty || 'medium';
    
    // Thời gian mỗi nước đi (giây)
    if (gameType === 'pve') {
        // PvE: thời gian mỗi nước dựa vào độ khó
        switch (aiDifficulty) {
            case 'easy':
                timerState.turnTime = 60;      // 60 giây mỗi nước
                break;
            case 'medium':
                timerState.turnTime = 45;      // 45 giây mỗi nước
                break;
            case 'hard':
                timerState.turnTime = 30;      // 30 giây mỗi nước (khó - AI cần thời gian)
                break;
            default:
                timerState.turnTime = 30;
        }
    } else {
        // PvP: 30 giây mỗi nước
        timerState.turnTime = 30;
    }
    
    timerState.playerTime = timerState.turnTime;
    timerState.opponentTime = timerState.turnTime;
    
    // Bắt đầu đếm thời gian trôi qua
    timerState.gameStartTime = Date.now();
    startElapsedTimer();
    
    // Reset điểm
    gameState.playerScore = 0;
    gameState.opponentScore = 0;
    updateScoreDisplay();
    
    updateTimerDisplay();
    startTimer();
}

function startElapsedTimer() {
    if (timerState.elapsedInterval) {
        clearInterval(timerState.elapsedInterval);
    }
    
    timerState.elapsedInterval = setInterval(() => {
        if (gameState.gameOver) {
            clearInterval(timerState.elapsedInterval);
            return;
        }
        updateElapsedDisplay();
    }, 1000);
    
    updateElapsedDisplay();
}

function updateElapsedDisplay() {
    const elapsedElement = document.getElementById('elapsedTime');
    if (elapsedElement && timerState.gameStartTime) {
        const elapsed = Math.floor((Date.now() - timerState.gameStartTime) / 1000);
        elapsedElement.textContent = formatTime(elapsed);
    }
}

function startTimer() {
    if (timerState.timerInterval) {
        clearInterval(timerState.timerInterval);
    }
    
    timerState.isRunning = true;
    timerState.turnStartTime = Date.now();
    
    timerState.timerInterval = setInterval(() => {
        if (gameState.gameOver) {
            stopTimer();
            return;
        }
        
        // Không đếm timer khi AI đang suy nghĩ (PvE)
        if (gameState.aiThinking) {
            return;
        }
        
        // Giảm thời gian của người đang đi
        if (gameState.isMyTurn) {
            timerState.playerTime--;
            if (timerState.playerTime <= 0) {
                timerState.playerTime = 0;
                handleTimeOut('player');
            }
        } else {
            // Chỉ đếm thời gian đối thủ nếu là PvP (không phải AI)
            if (GAME_DATA.gameType !== 'pve') {
                timerState.opponentTime--;
                if (timerState.opponentTime <= 0) {
                    timerState.opponentTime = 0;
                    handleTimeOut('opponent');
                }
            }
        }
        
        updateTimerDisplay();
    }, 1000);
}

function stopTimer() {
    if (timerState.timerInterval) {
        clearInterval(timerState.timerInterval);
        timerState.timerInterval = null;
    }
    timerState.isRunning = false;
}

function resetTurnTimer() {
    // Reset thời gian cho lượt mới
    if (gameState.isMyTurn) {
        timerState.playerTime = timerState.turnTime;
    } else {
        timerState.opponentTime = timerState.turnTime;
    }
    timerState.turnStartTime = Date.now();
    updateTimerDisplay();
}

function handleTimeOut(who) {
    if (gameState.gameOver) return;
    
    const gameType = GAME_DATA.gameType;
    
    if (who === 'player') {
        // Hết giờ của player
        if (gameType === 'pve') {
            // PvE: mất lượt, chuyển sang AI đi
            addSystemMessage('⏰ Hết thời gian! Mất lượt.');
            gameState.turn = gameState.playerColor === 'red' ? 'black' : 'red';
            gameState.isMyTurn = false;
            updateTurnStatus();
            
            // Gọi AI đi
            socket.emit('skip_turn', {
                room_code: GAME_DATA.roomCode
            });
        } else {
            // PvP: thua luôn - gửi màu của người thua
            socket.emit('timeout', {
                room_code: GAME_DATA.roomCode,
                loser: gameState.playerColor  // Gửi màu thay vì username
            });
            // Không gọi handleGameOver ở đây - để server emit game_over cho cả 2
        }
    } else {
        // Hết giờ của đối thủ
        if (gameType === 'pve') {
            // AI không bị timeout trong PvE - AI sẽ tự động đi khi xong
            // Không làm gì cả, chờ AI xử lý xong
            return;
        } else {
            // PvP: đối thủ thua - gửi thông báo nếu mình là người thấy
            const opponentColor = gameState.playerColor === 'red' ? 'black' : 'red';
            socket.emit('timeout', {
                room_code: GAME_DATA.roomCode,
                loser: opponentColor  // Gửi màu đối thủ
            });
            // Không gọi handleGameOver ở đây - để server emit game_over cho cả 2
        }
    }
}

function updateTimerDisplay() {
    const playerTimer = document.getElementById('playerTimer');
    const opponentTimer = document.getElementById('opponentTimer');
    
    if (playerTimer) {
        playerTimer.textContent = formatTime(timerState.playerTime);
        playerTimer.classList.toggle('low-time', timerState.playerTime <= 5);
        playerTimer.classList.toggle('active', gameState.isMyTurn);
    }
    
    if (opponentTimer) {
        opponentTimer.textContent = formatTime(timerState.opponentTime);
        opponentTimer.classList.toggle('low-time', timerState.opponentTime <= 5);
        opponentTimer.classList.toggle('active', !gameState.isMyTurn);
    }
}

function formatTime(seconds) {
    if (seconds < 0) seconds = 0;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function updateStatus(message, className) {
    const statusDiv = document.getElementById('gameStatus');
    if (statusDiv) {
        const statusText = statusDiv.querySelector('.status-text');
        statusText.textContent = message;
        statusDiv.className = 'game-status ' + (className || '');
    }
}

function updatePlayerSideDisplay() {
    const playerSide = document.getElementById('playerSide');
    const opponentSide = document.getElementById('opponentSide');
    
    if (playerSide) {
        playerSide.textContent = gameState.playerColor === 'red' ? 'Quân Đỏ' : 'Quân Đen';
        playerSide.style.color = gameState.playerColor === 'red' ? COLORS.redPiece : COLORS.blackPiece;
    }
    
    if (opponentSide) {
        const oppColor = gameState.playerColor === 'red' ? 'black' : 'red';
        opponentSide.textContent = oppColor === 'red' ? 'Quân Đỏ' : 'Quân Đen';
        opponentSide.style.color = oppColor === 'red' ? COLORS.redPiece : COLORS.blackPiece;
    }
}

function updateOpponentInfo(username) {
    const opponentName = document.getElementById('opponentName');
    if (opponentName) {
        opponentName.textContent = username;
    }
}

function addMoveToHistory(player, fromRow, fromCol, toRow, toCol, piece, captured) {
    const movesList = document.getElementById('movesList');
    if (!movesList) return;
    
    const moveNumber = gameState.moveHistory.length + 1;
    gameState.moveHistory.push({ player, fromRow, fromCol, toRow, toCol, piece, captured });
    
    // Tạo ký hiệu nước đi đẹp hơn
    const pieceName = PIECE_NAMES[piece?.type]?.symbol?.[player] || piece?.type || '?';
    const pieceNameVN = PIECE_NAMES[piece?.type]?.[player] || piece?.type || '?';
    
    // Tính hướng di chuyển
    let direction = '';
    if (toRow < fromRow) {
        direction = player === 'red' ? 'tiến' : 'thoái';
    } else if (toRow > fromRow) {
        direction = player === 'red' ? 'thoái' : 'tiến';
    } else {
        direction = 'bình';
    }
    
    // Cột (từ phải sang trái cho đỏ, trái sang phải cho đen)
    const colNames = player === 'red' ? COL_NAMES_RED : COL_NAMES_BLACK;
    const fromColName = colNames[fromCol];
    const toColName = colNames[toCol];
    
    // Format: Pháo 2 bình 5 hoặc Mã 8 tiến 7
    let moveText = '';
    if (direction === 'bình') {
        moveText = `${pieceName}${fromColName} ${direction} ${toColName}`;
    } else {
        const steps = Math.abs(toRow - fromRow);
        // Với Mã, Tượng, Sĩ thì hiện cột đích
        if (['N', 'E', 'A'].includes(piece?.type)) {
            moveText = `${pieceName}${fromColName} ${direction} ${toColName}`;
        } else {
            moveText = `${pieceName}${fromColName} ${direction} ${steps}`;
        }
    }
    
    // Thêm ký hiệu ăn quân
    if (captured) {
        const capturedSymbol = PIECE_NAMES[captured.type]?.symbol?.[captured.color] || captured.type;
        moveText += ` ✕${capturedSymbol}`;
    }
    
    const moveDiv = document.createElement('div');
    moveDiv.className = `move-item move-${player}`;
    
    // Hiển thị số thứ tự theo cặp (1 nước đỏ + 1 nước đen = 1 lượt)
    const displayNumber = Math.ceil(moveNumber / 2);
    const isRedMove = player === 'red';
    
    moveDiv.innerHTML = `
        <span class="move-number">${isRedMove ? displayNumber + '.' : ''}</span>
        <span class="move-text ${player}">${moveText}</span>
    `;
    
    // Kiểm tra xem người dùng có đang ở gần cuối danh sách không
    // Nếu đang scroll xem lịch sử cũ thì không auto scroll
    const isNearBottom = movesList.scrollHeight - movesList.scrollTop - movesList.clientHeight < 50;
    
    movesList.appendChild(moveDiv);
    
    // Chỉ auto scroll nếu đang ở gần cuối
    if (isNearBottom) {
        movesList.scrollTop = movesList.scrollHeight;
    }
}

// Thêm quân bị ăn vào danh sách và cập nhật điểm
function addCapturedPiece(capturedPiece, capturedBy) {
    if (!capturedPiece) return;
    
    // Tính điểm cho quân bị ăn
    const points = PIECE_POINTS[capturedPiece.type] || 0;
    
    // capturedBy là màu của người ăn
    if (capturedBy === gameState.playerColor) {
        // Ta ăn quân đối phương
        gameState.capturedByPlayer.push(capturedPiece);
        gameState.playerScore += points;
        updateCapturedDisplay('player');
    } else {
        // Đối phương ăn quân ta
        gameState.capturedByOpponent.push(capturedPiece);
        gameState.opponentScore += points;
        updateCapturedDisplay('opponent');
    }
    
    // Cập nhật hiển thị điểm
    updateScoreDisplay();
}

// Cập nhật hiển thị điểm số
function updateScoreDisplay() {
    const playerScoreEl = document.getElementById('playerScore');
    const opponentScoreEl = document.getElementById('opponentScore');
    
    if (playerScoreEl) {
        playerScoreEl.textContent = gameState.playerScore.toFixed(1);
    }
    if (opponentScoreEl) {
        opponentScoreEl.textContent = gameState.opponentScore.toFixed(1);
    }
}

function updateCapturedDisplay(who) {
    let container, pieces;
    
    if (who === 'player') {
        // Quân ta đã ăn được (của đối phương)
        container = document.getElementById('playerCaptured');
        pieces = gameState.capturedByPlayer;
    } else {
        // Quân đối phương đã ăn (của ta)
        container = document.getElementById('opponentCaptured');
        pieces = gameState.capturedByOpponent;
    }
    
    if (!container) {
        console.log('Container not found for', who);
        return;
    }
    
    // Clear và rebuild
    container.innerHTML = '';
    
    // Nhóm quân theo loại
    const grouped = {};
    pieces.forEach(p => {
        const key = `${p.color}_${p.type}`;
        if (!grouped[key]) {
            grouped[key] = { piece: p, count: 0 };
        }
        grouped[key].count++;
    });
    
    // Hiển thị
    Object.values(grouped).forEach(({ piece, count }) => {
        const symbol = PIECE_NAMES[piece.type]?.symbol?.[piece.color] || piece.type;
        const span = document.createElement('span');
        span.className = `captured-piece ${piece.color}`;
        span.innerHTML = count > 1 ? `${symbol}<sub>${count}</sub>` : symbol;
        span.title = PIECE_NAMES[piece.type]?.[piece.color] || piece.type;
        container.appendChild(span);
    });
}

// ============================================
// CHAT FUNCTIONS
// ============================================

function sendChat() {
    const input = document.getElementById('chatInput');
    if (!input) return;
    
    const message = input.value.trim();
    if (!message) return;
    
    socket.emit('chat_message', {
        room_code: GAME_DATA.roomCode,
        message: message,
        username: GAME_DATA.currentUser?.username || 'Guest'
    });
    
    input.value = '';
}

function addChatMessage(username, message) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message';
    
    // Sử dụng textContent để tránh XSS
    const authorSpan = document.createElement('span');
    authorSpan.className = 'author';
    authorSpan.textContent = username;
    
    const textSpan = document.createElement('span');
    textSpan.className = 'text';
    textSpan.textContent = message;
    
    msgDiv.appendChild(authorSpan);
    msgDiv.appendChild(textSpan);
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addSystemMessage(message) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message system';
    msgDiv.innerHTML = `<span class="text" style="color: #888; font-style: italic;">${message}</span>`;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// GAME ACTIONS
// ============================================

function requestUndo() {
    // TODO: Implement undo request
    alert('Chức năng đi lại chưa được hỗ trợ');
}

function offerDraw() {
    if (GAME_DATA.gameType === 'pve') {
        alert('Không thể cầu hòa khi chơi với AI');
        return;
    }
    socket.emit('offer_draw', { room_code: GAME_DATA.roomCode });
    addSystemMessage('Bạn đã đề nghị hòa');
}

function acceptDraw() {
    socket.emit('accept_draw', { room_code: GAME_DATA.roomCode });
    closeModal('drawOfferModal');
}

function declineDraw() {
    closeModal('drawOfferModal');
    addSystemMessage('Bạn đã từ chối hòa');
}

function confirmResign() {
    document.getElementById('resignModal').style.display = 'flex';
}

function resign() {
    socket.emit('resign', {
        room_code: GAME_DATA.roomCode,
        player_color: gameState.playerColor
    });
    closeModal('resignModal');
}

function leaveGame() {
    if (confirm('Bạn có chắc muốn rời phòng?')) {
        socket.emit('leave_game', { room_code: GAME_DATA.roomCode });
        window.location.href = '/lobby';
    }
}

function playAgain() {
    window.location.href = '/lobby';
}

function backToLobby() {
    window.location.href = '/lobby';
}

function copyRoomCode() {
    const roomCode = document.getElementById('roomCodeDisplay')?.textContent || GAME_DATA?.roomCode;
    if (roomCode) {
        navigator.clipboard.writeText(roomCode);
        alert('Đã copy mã phòng: ' + roomCode);
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

// Chat input enter key
document.addEventListener('DOMContentLoaded', function() {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendChat();
            }
        });
    }
});

// ============================================
// DEBUG TOOLS - Dùng trong Console (F12) để điều chỉnh
// ============================================
// Gọi: adjustBoard(paddingLeft, paddingTop, pieceSize)
// Ví dụ: adjustBoard(5, 5, 55)
window.adjustBoard = function(pl, pt, ps) {
    if (pl !== undefined) BOARD.paddingLeft = pl;
    if (pt !== undefined) BOARD.paddingTop = pt;
    if (ps !== undefined) BOARD.pieceSize = ps;
    
    // Tính lại cell size
    const innerWidth = canvas.width - BOARD.paddingLeft * 2;
    const innerHeight = canvas.height - BOARD.paddingTop * 2;
    BOARD.cellWidth = innerWidth / 8;
    BOARD.cellHeight = innerHeight / 9;
    
    console.log(`BOARD settings: padding(${BOARD.paddingLeft}, ${BOARD.paddingTop}), cell(${BOARD.cellWidth.toFixed(1)}x${BOARD.cellHeight.toFixed(1)}), piece=${BOARD.pieceSize}`);
    drawBoard();
};

// Hiển thị cấu hình hiện tại
window.showBoardConfig = function() {
    console.log('Current BOARD config:', BOARD);
    console.log('Canvas size:', canvas.width, 'x', canvas.height);
    if (boardImage) {
        console.log('Board image size:', boardImage.naturalWidth, 'x', boardImage.naturalHeight);
    }
};

// ============================================
// USER DROPDOWN MENU
// ============================================

/**
 * Toggle user dropdown menu
 */
function toggleUserDropdown(event) {
    if (event) event.stopPropagation();
    const dropdown = document.getElementById('userDropdownMenu');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('userDropdownMenu');
    const dropdownBtn = document.querySelector('.user-dropdown-btn');
    
    if (dropdown && dropdown.classList.contains('show')) {
        if (!dropdownBtn.contains(event.target) && !dropdown.contains(event.target)) {
            dropdown.classList.remove('show');
        }
    }
});

// Close dropdown on escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const dropdown = document.getElementById('userDropdownMenu');
        if (dropdown) {
            dropdown.classList.remove('show');
        }
    }
});

// Make toggleUserDropdown globally available
window.toggleUserDropdown = toggleUserDropdown;
