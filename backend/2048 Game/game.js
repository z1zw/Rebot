const GRID_SIZE = 4;
const WINNING_VALUE = 2048;

class Game2048 {
    constructor() {
        this.board = [];
        this.score = 0;
        this.gameOver = false;
        this.won = false;
        this.initBoard();
    }

    initBoard() {
        this.board = Array.from({ length: GRID_SIZE }, () => Array(GRID_SIZE).fill(0));
        this.addRandomTile();
        this.addRandomTile();
    }

    addRandomTile() {
        const emptyCells = [];
        for (let r = 0; r < GRID_SIZE; r++) {
            for (let c = 0; c < GRID_SIZE; c++) {
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

    move(direction) {
        if (this.gameOver) return false;

        const oldBoard = JSON.parse(JSON.stringify(this.board));
        let moved = false;

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

    moveUp() {
        let moved = false;
        for (let c = 0; c < GRID_SIZE; c++) {
            const column = [];
            for (let r = 0; r < GRID_SIZE; r++) {
                column.push(this.board[r][c]);
            }
            const { newArray, merged } = this.slideAndMerge(column);
            if (merged > 0) moved = true;
            for (let r = 0; r < GRID_SIZE; r++) {
                if (this.board[r][c] !== newArray[r]) moved = true;
                this.board[r][c] = newArray[r];
            }
        }
        return moved;
    }

    moveDown() {
        let moved = false;
        for (let c = 0; c < GRID_SIZE; c++) {
            const column = [];
            for (let r = GRID_SIZE - 1; r >= 0; r--) {
                column.push(this.board[r][c]);
            }
            const { newArray, merged } = this.slideAndMerge(column);
            if (merged > 0) moved = true;
            for (let r = 0; r < GRID_SIZE; r++) {
                if (this.board[GRID_SIZE - 1 - r][c] !== newArray[r]) moved = true;
                this.board[GRID_SIZE - 1 - r][c] = newArray[r];
            }
        }
        return moved;
    }

    moveLeft() {
        let moved = false;
        for (let r = 0; r < GRID_SIZE; r++) {
            const row = [...this.board[r]];
            const { newArray, merged } = this.slideAndMerge(row);
            if (merged > 0) moved = true;
            for (let c = 0; c < GRID_SIZE; c++) {
                if (this.board[r][c] !== newArray[c]) moved = true;
                this.board[r][c] = newArray[c];
            }
        }
        return moved;
    }

    moveRight() {
        let moved = false;
        for (let r = 0; r < GRID_SIZE; r++) {
            const row = [...this.board[r]].reverse();
            const { newArray, merged } = this.slideAndMerge(row);
            if (merged > 0) moved = true;
            for (let c = 0; c < GRID_SIZE; c++) {
                if (this.board[r][GRID_SIZE - 1 - c] !== newArray[c]) moved = true;
                this.board[r][GRID_SIZE - 1 - c] = newArray[c];
            }
        }
        return moved;
    }

    slideAndMerge(line) {
        const filtered = line.filter(val => val !== 0);
        let merged = 0;
        const newArray = [];

        for (let i = 0; i < filtered.length; i++) {
            if (i < filtered.length - 1 && filtered[i] === filtered[i + 1]) {
                const mergedValue = filtered[i] * 2;
                newArray.push(mergedValue);
                this.score += mergedValue;
                merged++;
                i++;
            } else {
                newArray.push(filtered[i]);
            }
        }

        while (newArray.length < GRID_SIZE) {
            newArray.push(0);
        }

        return { newArray, merged };
    }

    checkGameState() {
        for (let r = 0; r < GRID_SIZE; r++) {
            for (let c = 0; c < GRID_SIZE; c++) {
                if (this.board[r][c] === WINNING_VALUE) {
                    this.won = true;
                }
            }
        }

        if (this.won) {
            return;
        }

        if (this.isBoardFull()) {
            this.gameOver = !this.hasPossibleMoves();
        }
    }

    isBoardFull() {
        for (let r = 0; r < GRID_SIZE; r++) {
            for (let c = 0; c < GRID_SIZE; c++) {
                if (this.board[r][c] === 0) {
                    return false;
                }
            }
        }
        return true;
    }

    hasPossibleMoves() {
        for (let r = 0; r < GRID_SIZE; r++) {
            for (let c = 0; c < GRID_SIZE; c++) {
                const current = this.board[r][c];
                if (current === 0) return true;

                if (c < GRID_SIZE - 1 && current === this.board[r][c + 1]) {
                    return true;
                }
                if (r < GRID_SIZE - 1 && current === this.board[r + 1][c]) {
                    return true;
                }
            }
        }
        return false;
    }

    reset() {
        this.board = [];
        this.score = 0;
        this.gameOver = false;
        this.won = false;
        this.initBoard();
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

    isWon() {
        return this.won;
    }
}