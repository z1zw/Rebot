class GameState {
    constructor(gridSize = 4) {
        this.gridSize = gridSize;
        this.grid = Array(gridSize).fill().map(() => Array(gridSize).fill(0));
        this.score = 0;
        this.gameOver = false;
        this.won = false;
        this.moved = false;
        this.addNewTile();
        this.addNewTile();
    }

    reset() {
        this.grid = Array(this.gridSize).fill().map(() => Array(this.gridSize).fill(0));
        this.score = 0;
        this.gameOver = false;
        this.won = false;
        this.moved = false;
        this.addNewTile();
        this.addNewTile();
    }

    addNewTile() {
        const emptyCells = [];
        for (let r = 0; r < this.gridSize; r++) {
            for (let c = 0; c < this.gridSize; c++) {
                if (this.grid[r][c] === 0) {
                    emptyCells.push({ r, c });
                }
            }
        }
        if (emptyCells.length > 0) {
            const { r, c } = emptyCells[Math.floor(Math.random() * emptyCells.length)];
            this.grid[r][c] = Math.random() < 0.9 ? 2 : 4;
        }
    }

    move(direction) {
        this.moved = false;
        const oldGrid = this.grid.map(row => [...row]);
        const oldScore = this.score;

        switch (direction) {
            case 'up':
                this.moveUp();
                break;
            case 'down':
                this.moveDown();
                break;
            case 'left':
                this.moveLeft();
                break;
            case 'right':
                this.moveRight();
                break;
        }

        if (this.gridChanged(oldGrid)) {
            this.moved = true;
            this.addNewTile();
            this.checkGameState();
        } else {
            this.score = oldScore;
        }
    }

    moveUp() {
        for (let c = 0; c < this.gridSize; c++) {
            const column = [];
            for (let r = 0; r < this.gridSize; r++) {
                if (this.grid[r][c] !== 0) {
                    column.push(this.grid[r][c]);
                }
            }
            const merged = this.mergeTiles(column);
            for (let r = 0; r < this.gridSize; r++) {
                this.grid[r][c] = merged[r] || 0;
            }
        }
    }

    moveDown() {
        for (let c = 0; c < this.gridSize; c++) {
            const column = [];
            for (let r = this.gridSize - 1; r >= 0; r--) {
                if (this.grid[r][c] !== 0) {
                    column.push(this.grid[r][c]);
                }
            }
            const merged = this.mergeTiles(column);
            for (let r = this.gridSize - 1; r >= 0; r--) {
                this.grid[r][c] = merged[this.gridSize - 1 - r] || 0;
            }
        }
    }

    moveLeft() {
        for (let r = 0; r < this.gridSize; r++) {
            const row = [];
            for (let c = 0; c < this.gridSize; c++) {
                if (this.grid[r][c] !== 0) {
                    row.push(this.grid[r][c]);
                }
            }
            const merged = this.mergeTiles(row);
            for (let c = 0; c < this.gridSize; c++) {
                this.grid[r][c] = merged[c] || 0;
            }
        }
    }

    moveRight() {
        for (let r = 0; r < this.gridSize; r++) {
            const row = [];
            for (let c = this.gridSize - 1; c >= 0; c--) {
                if (this.grid[r][c] !== 0) {
                    row.push(this.grid[r][c]);
                }
            }
            const merged = this.mergeTiles(row);
            for (let c = this.gridSize - 1; c >= 0; c--) {
                this.grid[r][c] = merged[this.gridSize - 1 - c] || 0;
            }
        }
    }

    mergeTiles(line) {
        const result = [];
        for (let i = 0; i < line.length; i++) {
            if (i < line.length - 1 && line[i] === line[i + 1]) {
                const mergedValue = line[i] * 2;
                result.push(mergedValue);
                this.score += mergedValue;
                if (mergedValue === 2048 && !this.won) {
                    this.won = true;
                }
                i++;
            } else {
                result.push(line[i]);
            }
        }
        while (result.length < this.gridSize) {
            result.push(0);
        }
        return result;
    }

    gridChanged(oldGrid) {
        for (let r = 0; r < this.gridSize; r++) {
            for (let c = 0; c < this.gridSize; c++) {
                if (oldGrid[r][c] !== this.grid[r][c]) {
                    return true;
                }
            }
        }
        return false;
    }

    checkGameState() {
        if (this.won) {
            return;
        }

        for (let r = 0; r < this.gridSize; r++) {
            for (let c = 0; c < this.gridSize; c++) {
                if (this.grid[r][c] === 0) {
                    return;
                }
                if (c < this.gridSize - 1 && this.grid[r][c] === this.grid[r][c + 1]) {
                    return;
                }
                if (r < this.gridSize - 1 && this.grid[r][c] === this.grid[r + 1][c]) {
                    return;
                }
            }
        }
        this.gameOver = true;
    }

    getTileAnimations(oldGrid) {
        const animations = [];
        for (let r = 0; r < this.gridSize; r++) {
            for (let c = 0; c < this.gridSize; c++) {
                if (this.grid[r][c] !== oldGrid[r][c]) {
                    if (oldGrid[r][c] === 0) {
                        animations.push({ type: 'appear', row: r, col: c, value: this.grid[r][c] });
                    } else if (this.grid[r][c] === 0) {
                        animations.push({ type: 'disappear', row: r, col: c, value: oldGrid[r][c] });
                    } else if (this.grid[r][c] > oldGrid[r][c]) {
                        animations.push({ type: 'merge', row: r, col: c, value: this.grid[r][c] });
                    } else {
                        animations.push({ type: 'move', row: r, col: c, value: this.grid[r][c] });
                    }
                }
            }
        }
        return animations;
    }

    getState() {
        return {
            grid: this.grid.map(row => [...row]),
            score: this.score,
            gameOver: this.gameOver,
            won: this.won,
            moved: this.moved
        };
    }
}

export default GameState;