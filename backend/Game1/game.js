// 2048 Game Logic
class Game2048 {
    constructor(size = 4) {
        this.size = size;
        this.board = [];
        this.score = 0;
        this.won = false;
        this.over = false;
        this.init();
    }

    // Initialize the game board
    init() {
        this.board = Array.from({ length: this.size }, () => Array(this.size).fill(0));
        this.score = 0;
        this.won = false;
        this.over = false;
        this.addRandomTile();
        this.addRandomTile();
    }

    // Add a random tile (2 or 4) to an empty cell
    addRandomTile() {
        const emptyCells = [];
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                if (this.board[r][c] === 0) {
                    emptyCells.push({ r, c });
                }
            }
        }
        if (emptyCells.length > 0) {
            const { r, c } = emptyCells[Math.floor(Math.random() * emptyCells.length)];
            this.board[r][c] = Math.random() < 0.9 ? 2 : 4;
        }
    }

    // Move tiles in a specified direction
    move(direction) {
        if (this.over) return false;

        let moved = false;
        const oldBoard = this.board.map(row => [...row]);

        // Define movement vectors
        const vectors = {
            'up': { dr: -1, dc: 0 },
            'down': { dr: 1, dc: 0 },
            'left': { dr: 0, dc: -1 },
            'right': { dr: 0, dc: 1 }
        };
        const { dr, dc } = vectors[direction] || { dr: 0, dc: 0 };

        // Helper to perform slide and merge
        const slide = (startRow, startCol, rowStep, colStep) => {
            for (let i = 0; i < this.size; i++) {
                let row = startRow + i * rowStep;
                for (let j = 0; j < this.size; j++) {
                    let col = startCol + j * colStep;
                    if (this.board[row][col] !== 0) {
                        let value = this.board[row][col];
                        let newRow = row;
                        let newCol = col;

                        // Slide as far as possible
                        while (
                            newRow + dr >= 0 && newRow + dr < this.size &&
                            newCol + dc >= 0 && newCol + dc < this.size &&
                            this.board[newRow + dr][newCol + dc] === 0
                        ) {
                            newRow += dr;
                            newCol += dc;
                        }

                        // Merge if possible
                        if (
                            newRow + dr >= 0 && newRow + dr < this.size &&
                            newCol + dc >= 0 && newCol + dc < this.size &&
                            this.board[newRow + dr][newCol + dc] === value &&
                            !this.board[newRow + dr][newCol + dc].merged
                        ) {
                            newRow += dr;
                            newCol += dc;
                            this.board[newRow][newCol] = value * 2;
                            this.board[newRow][newCol].merged = true;
                            this.score += value * 2;
                            if (this.board[newRow][newCol] === 2048) {
                                this.won = true;
                            }
                            this.board[row][col] = 0;
                            moved = true;
                        } else if (newRow !== row || newCol !== col) {
                            this.board[newRow][newCol] = value;
                            this.board[row][col] = 0;
                            moved = true;
                        }
                    }
                }
            }
        };

        // Clear merged flags
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                if (this.board[r][c] !== 0 && this.board[r][c].merged) {
                    this.board[r][c] = this.board[r][c];
                }
            }
        }

        // Determine slide order based on direction
        if (direction === 'up') {
            slide(0, 0, 1, 1);
        } else if (direction === 'down') {
            slide(this.size - 1, 0, -1, 1);
        } else if (direction === 'left') {
            slide(0, 0, 1, 1);
        } else if (direction === 'right') {
            slide(0, this.size - 1, 1, -1);
        }

        // Clear merged flags after move
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                if (typeof this.board[r][c] === 'object') {
                    this.board[r][c] = this.board[r][c];
                }
            }
        }

        // Add a new tile if the board changed
        if (moved) {
            this.addRandomTile();
            if (!this.hasMoves()) {
                this.over = true;
            }
        }

        // Check if board actually changed
        const boardChanged = !this.boardsEqual(oldBoard, this.board);
        return boardChanged;
    }

    // Check if two boards are equal
    boardsEqual(board1, board2) {
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                const val1 = typeof board1[r][c] === 'object' ? board1[r][c] : board1[r][c];
                const val2 = typeof board2[r][c] === 'object' ? board2[r][c] : board2[r][c];
                if (val1 !== val2) return false;
            }
        }
        return true;
    }

    // Check if there are any valid moves left
    hasMoves() {
        // Check for empty cells
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                if (this.board[r][c] === 0) return true;
            }
        }

        // Check for possible merges
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                const value = this.board[r][c];
                if (value !== 0) {
                    // Check adjacent cells
                    if (r > 0 && this.board[r - 1][c] === value) return true;
                    if (r < this.size - 1 && this.board[r + 1][c] === value) return true;
                    if (c > 0 && this.board[r][c - 1] === value) return true;
                    if (c < this.size - 1 && this.board[r][c + 1] === value) return true;
                }
            }
        }

        return false;
    }

    // Get the current game state
    getState() {
        return {
            board: this.board.map(row => row.map(cell => typeof cell === 'object' ? cell : cell)),
            score: this.score,
            won: this.won,
            over: this.over,
            size: this.size
        };
    }

    // Reset the game
    reset() {
        this.init();
    }
}

// Export for use in browser or Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Game2048;
}