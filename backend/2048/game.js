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
        this.board = Array(this.size).fill().map(() => Array(this.size).fill(0));
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

        // Normalize direction handling
        switch (direction) {
            case 'up':
                for (let c = 0; c < this.size; c++) {
                    moved = this.moveColumn(c, -1) || moved;
                }
                break;
            case 'down':
                for (let c = 0; c < this.size; c++) {
                    moved = this.moveColumn(c, 1) || moved;
                }
                break;
            case 'left':
                for (let r = 0; r < this.size; r++) {
                    moved = this.moveRow(r, -1) || moved;
                }
                break;
            case 'right':
                for (let r = 0; r < this.size; r++) {
                    moved = this.moveRow(r, 1) || moved;
                }
                break;
        }

        if (moved) {
            this.addRandomTile();
            this.checkGameState();
            return true;
        }
        return false;
    }

    // Move and merge tiles in a column
    moveColumn(col, dir) {
        let moved = false;
        const column = [];
        for (let r = 0; r < this.size; r++) {
            column.push(this.board[r][col]);
        }

        const newColumn = this.slideAndMerge(column, dir);
        if (JSON.stringify(column) !== JSON.stringify(newColumn)) {
            moved = true;
            for (let r = 0; r < this.size; r++) {
                this.board[r][col] = newColumn[r];
            }
        }
        return moved;
    }

    // Move and merge tiles in a row
    moveRow(row, dir) {
        let moved = false;
        const oldRow = [...this.board[row]];
        const newRow = this.slideAndMerge(oldRow, dir);
        if (JSON.stringify(oldRow) !== JSON.stringify(newRow)) {
            moved = true;
            this.board[row] = newRow;
        }
        return moved;
    }

    // Slide and merge array (row or column)
    slideAndMerge(line, direction) {
        // Filter out zeros
        let filtered = line.filter(val => val !== 0);
        
        // Reverse if moving right/down
        if (direction === 1) {
            filtered.reverse();
        }

        // Merge tiles
        for (let i = 0; i < filtered.length - 1; i++) {
            if (filtered[i] === filtered[i + 1]) {
                filtered[i] *= 2;
                this.score += filtered[i];
                if (filtered[i] === 2048) {
                    this.won = true;
                }
                filtered.splice(i + 1, 1);
            }
        }

        // Pad with zeros
        while (filtered.length < this.size) {
            filtered.push(0);
        }

        // Reverse back if needed
        if (direction === 1) {
            filtered.reverse();
        }

        return filtered;
    }

    // Check win/lose conditions
    checkGameState() {
        // Check for win
        if (!this.won) {
            for (let r = 0; r < this.size; r++) {
                for (let c = 0; c < this.size; c++) {
                    if (this.board[r][c] === 2048) {
                        this.won = true;
                        return;
                    }
                }
            }
        }

        // Check for game over
        this.over = true;
        
        // Check for empty cells
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                if (this.board[r][c] === 0) {
                    this.over = false;
                    return;
                }
            }
        }

        // Check for possible merges
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                const current = this.board[r][c];
                // Check right neighbor
                if (c < this.size - 1 && this.board[r][c + 1] === current) {
                    this.over = false;
                    return;
                }
                // Check bottom neighbor
                if (r < this.size - 1 && this.board[r + 1][c] === current) {
                    this.over = false;
                    return;
                }
            }
        }
    }

    // Get the current board state
    getBoard() {
        return this.board.map(row => [...row]);
    }

    // Get current score
    getScore() {
        return this.score;
    }

    // Check if game is won
    isWon() {
        return this.won;
    }

    // Check if game is over
    isOver() {
        return this.over;
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