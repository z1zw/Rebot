// game.js - Core 2048 Game Logic

class Game2048 {
    constructor(size = 4) {
        this.size = size;
        this.board = [];
        this.score = 0;
        this.gameOver = false;
        this.won = false;
        this.init();
    }

    init() {
        // Initialize empty board
        this.board = Array(this.size).fill().map(() => Array(this.size).fill(0));
        this.score = 0;
        this.gameOver = false;
        this.won = false;
        
        // Add two initial tiles
        this.addRandomTile();
        this.addRandomTile();
    }

    addRandomTile() {
        const emptyCells = [];
        
        // Find all empty cells
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                if (this.board[r][c] === 0) {
                    emptyCells.push({r, c});
                }
            }
        }
        
        if (emptyCells.length === 0) return;
        
        // Pick random empty cell
        const cell = emptyCells[Math.floor(Math.random() * emptyCells.length)];
        
        // 90% chance for 2, 10% chance for 4
        this.board[cell.r][cell.c] = Math.random() < 0.9 ? 2 : 4;
    }

    move(direction) {
        if (this.gameOver) return false;
        
        const oldBoard = this.board.map(row => [...row]);
        let moved = false;
        
        switch(direction) {
            case 'up':
                moved = this.moveUp();
                break;
            case 'down':
                moved = this.moveDown();
                break;
            case 'left':
                moved = this.moveLeft();
                break;
            case 'right':
                moved = this.moveRight();
                break;
        }
        
        if (moved) {
            this.addRandomTile();
            this.checkGameOver();
        }
        
        return moved;
    }

    moveUp() {
        let moved = false;
        
        for (let c = 0; c < this.size; c++) {
            const column = [];
            
            // Extract column
            for (let r = 0; r < this.size; r++) {
                column.push(this.board[r][c]);
            }
            
            // Process column
            const result = this.processLine(column);
            
            // Update column
            for (let r = 0; r < this.size; r++) {
                if (this.board[r][c] !== result[r]) {
                    moved = true;
                }
                this.board[r][c] = result[r];
            }
        }
        
        return moved;
    }

    moveDown() {
        let moved = false;
        
        for (let c = 0; c < this.size; c++) {
            const column = [];
            
            // Extract column (reverse order)
            for (let r = this.size - 1; r >= 0; r--) {
                column.push(this.board[r][c]);
            }
            
            // Process column
            const result = this.processLine(column);
            
            // Update column (reverse back)
            for (let r = 0; r < this.size; r++) {
                if (this.board[this.size - 1 - r][c] !== result[r]) {
                    moved = true;
                }
                this.board[this.size - 1 - r][c] = result[r];
            }
        }
        
        return moved;
    }

    moveLeft() {
        let moved = false;
        
        for (let r = 0; r < this.size; r++) {
            const row = [...this.board[r]];
            const result = this.processLine(row);
            
            if (JSON.stringify(this.board[r]) !== JSON.stringify(result)) {
                moved = true;
            }
            this.board[r] = result;
        }
        
        return moved;
    }

    moveRight() {
        let moved = false;
        
        for (let r = 0; r < this.size; r++) {
            const row = [...this.board[r]].reverse();
            const result = this.processLine(row).reverse();
            
            if (JSON.stringify(this.board[r]) !== JSON.stringify(result)) {
                moved = true;
            }
            this.board[r] = result;
        }
        
        return moved;
    }

    processLine(line) {
        // Remove zeros
        let filtered = line.filter(cell => cell !== 0);
        const result = [];
        
        // Merge tiles
        for (let i = 0; i < filtered.length; i++) {
            if (i < filtered.length - 1 && filtered[i] === filtered[i + 1]) {
                const mergedValue = filtered[i] * 2;
                result.push(mergedValue);
                this.score += mergedValue;
                
                // Check for win
                if (mergedValue === 2048 && !this.won) {
                    this.won = true;
                }
                
                i++; // Skip next tile since it was merged
            } else {
                result.push(filtered[i]);
            }
        }
        
        // Pad with zeros
        while (result.length < this.size) {
            result.push(0);
        }
        
        return result;
    }

    checkGameOver() {
        // Check for empty cells
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                if (this.board[r][c] === 0) {
                    return false; // Game can continue
                }
            }
        }
        
        // Check for possible merges
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                const current = this.board[r][c];
                
                // Check right neighbor
                if (c < this.size - 1 && this.board[r][c + 1] === current) {
                    return false;
                }
                
                // Check bottom neighbor
                if (r < this.size - 1 && this.board[r + 1][c] === current) {
                    return false;
                }
            }
        }
        
        this.gameOver = true;
        return true;
    }

    getBoard() {
        return this.board;
    }

    getScore() {
        return this.score;
    }

    isGameOver() {
        return this.gameOver;
    }

    hasWon() {
        return this.won;
    }

    reset() {
        this.init();
    }

    // Utility method for debugging
    printBoard() {
        console.log('Score:', this.score);
        console.log('Game Over:', this.gameOver);
        console.log('Won:', this.won);
        for (let r = 0; r < this.size; r++) {
            console.log(this.board[r].map(cell => cell.toString().padStart(4)).join(' '));
        }
        console.log('---');
    }
}

// Export for use in browser or Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Game2048;
}