const GRID_SIZE = 4;
const WIN_VALUE = 2048;

class Game2048 {
    constructor() {
        this.board = [];
        this.score = 0;
        this.gameOver = false;
        this.won = false;
        this.initBoard();
        this.addRandomTile();
        this.addRandomTile();
    }

    initBoard() {
        this.board = Array.from({ length: GRID_SIZE }, () => Array(GRID_SIZE).fill(0));
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

        const oldBoard = this.board.map(row => [...row]);
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
            const { arr, scoreChange } = this.slideAndMerge(column);
            if (scoreChange > 0) {
                this.score += scoreChange;
                moved = true;
            }
            for (let r = 0; r < GRID_SIZE; r++) {
                if (this.board[r][c] !== arr[r]) moved = true;
                this.board[r][c] = arr[r];
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
            const { arr, scoreChange } = this.slideAndMerge(column);
            if (scoreChange > 0) {
                this.score += scoreChange;
                moved = true;
            }
            for (let r = 0; r < GRID_SIZE; r++) {
                if (this.board[GRID_SIZE - 1 - r][c] !== arr[r]) moved = true;
                this.board[GRID_SIZE - 1 - r][c] = arr[r];
            }
        }
        return moved;
    }

    moveLeft() {
        let moved = false;
        for (let r = 0; r < GRID_SIZE; r++) {
            const row = [...this.board[r]];
            const { arr, scoreChange } = this.slideAndMerge(row);
            if (scoreChange > 0) {
                this.score += scoreChange;
                moved = true;
            }
            if (JSON.stringify(this.board[r]) !== JSON.stringify(arr)) moved = true;
            this.board[r] = arr;
        }
        return moved;
    }

    moveRight() {
        let moved = false;
        for (let r = 0; r < GRID_SIZE; r++) {
            const row = [...this.board[r]].reverse();
            const { arr, scoreChange } = this.slideAndMerge(row);
            if (scoreChange > 0) {
                this.score += scoreChange;
                moved = true;
            }
            const newRow = arr.reverse();
            if (JSON.stringify(this.board[r]) !== JSON.stringify(newRow)) moved = true;
            this.board[r] = newRow;
        }
        return moved;
    }

    slideAndMerge(line) {
        const filtered = line.filter(val => val !== 0);
        const merged = [];
        let scoreChange = 0;
        let i = 0;

        while (i < filtered.length) {
            if (i + 1 < filtered.length && filtered[i] === filtered[i + 1]) {
                const mergedValue = filtered[i] * 2;
                merged.push(mergedValue);
                scoreChange += mergedValue;
                if (mergedValue === WIN_VALUE) this.won = true;
                i += 2;
            } else {
                merged.push(filtered[i]);
                i++;
            }
        }

        while (merged.length < GRID_SIZE) {
            merged.push(0);
        }

        return { arr: merged, scoreChange };
    }

    checkGameState() {
        if (this.won) {
            this.gameOver = true;
            return;
        }

        // Check for empty cells
        for (let r = 0; r < GRID_SIZE; r++) {
            for (let c = 0; c < GRID_SIZE; c++) {
                if (this.board[r][c] === 0) return;
            }
        }

        // Check for possible merges
        for (let r = 0; r < GRID_SIZE; r++) {
            for (let c = 0; c < GRID_SIZE; c++) {
                const current = this.board[r][c];
                if (r + 1 < GRID_SIZE && this.board[r + 1][c] === current) return;
                if (c + 1 < GRID_SIZE && this.board[r][c + 1] === current) return;
            }
        }

        this.gameOver = true;
    }

    reset() {
        this.board = [];
        this.score = 0;
        this.gameOver = false;
        this.won = false;
        this.initBoard();
        this.addRandomTile();
        this.addRandomTile();
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