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

    // Move tiles in a given direction
    move(direction) {
        if (this.over) return false;
        let moved = false;
        const oldBoard = this.board.map(row => [...row]);

        switch (direction) {
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
            this.checkGameState();
        }
        return moved;
    }

    // Move tiles up
    moveUp() {
        let moved = false;
        for (let c = 0; c < this.size; c++) {
            const column = [];
            for (let r = 0; r < this.size; r++) {
                column.push(this.board[r][c]);
            }
            const { newArray, changed } = this.slideAndMerge(column);
            if (changed) {
                moved = true;
                for (let r = 0; r < this.size; r++) {
                    this.board[r][c] = newArray[r];
                }
            }
        }
        return moved;
    }

    // Move tiles down
    moveDown() {
        let moved = false;
        for (let c = 0; c < this.size; c++) {
            const column = [];
            for (let r = this.size - 1; r >= 0; r--) {
                column.push(this.board[r][c]);
            }
            const { newArray, changed } = this.slideAndMerge(column);
            if (changed) {
                moved = true;
                for (let r = 0; r < this.size; r++) {
                    this.board[this.size - 1 - r][c] = newArray[r];
                }
            }
        }
        return moved;
    }

    // Move tiles left
    moveLeft() {
        let moved = false;
        for (let r = 0; r < this.size; r++) {
            const row = [...this.board[r]];
            const { newArray, changed } = this.slideAndMerge(row);
            if (changed) {
                moved = true;
                this.board[r] = newArray;
            }
        }
        return moved;
    }

    // Move tiles right
    moveRight() {
        let moved = false;
        for (let r = 0; r < this.size; r++) {
            const row = [...this.board[r]].reverse();
            const { newArray, changed } = this.slideAndMerge(row);
            if (changed) {
                moved = true;
                this.board[r] = newArray.reverse();
            }
        }
        return moved;
    }

    // Slide and merge a single row/column
    slideAndMerge(arr) {
        const filtered = arr.filter(val => val !== 0);
        const newArray = [];
        let changed = false;
        let i = 0;

        while (i < filtered.length) {
            if (i + 1 < filtered.length && filtered[i] === filtered[i + 1]) {
                const mergedValue = filtered[i] * 2;
                newArray.push(mergedValue);
                this.score += mergedValue;
                if (mergedValue === 2048) this.won = true;
                i += 2;
                changed = true;
            } else {
                newArray.push(filtered[i]);
                i += 1;
            }
        }

        while (newArray.length < this.size) {
            newArray.push(0);
        }

        if (filtered.length !== newArray.length) changed = true;
        for (let j = 0; j < arr.length; j++) {
            if (arr[j] !== newArray[j]) changed = true;
        }

        return { newArray, changed };
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

        // Check for possible moves
        if (this.hasEmptyCells()) return;

        // Check for adjacent equal tiles
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                const current = this.board[r][c];
                if (c + 1 < this.size && current === this.board[r][c + 1]) return;
                if (r + 1 < this.size && current === this.board[r + 1][c]) return;
            }
        }

        this.over = true;
    }

    // Check if there are empty cells
    hasEmptyCells() {
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                if (this.board[r][c] === 0) return true;
            }
        }
        return false;
    }

    // Get current game state
    getState() {
        return {
            board: this.board.map(row => [...row]),
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