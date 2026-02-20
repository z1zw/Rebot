class Grid {
    constructor() {
        this.size = 4;
        this.cells = this.empty();
        this.emptyCells = [];
        this.updateEmptyCells();
    }

    empty() {
        const cells = [];
        for (let x = 0; x < this.size; x++) {
            const row = [];
            for (let y = 0; y < this.size; y++) {
                row.push(null);
            }
            cells.push(row);
        }
        return cells;
    }

    updateEmptyCells() {
        this.emptyCells = [];
        for (let x = 0; x < this.size; x++) {
            for (let y = 0; y < this.size; y++) {
                if (this.cells[x][y] === null) {
                    this.emptyCells.push({ x, y });
                }
            }
        }
    }

    availableCells() {
        return this.emptyCells.length > 0;
    }

    randomAvailableCell() {
        if (!this.availableCells()) return null;
        const index = Math.floor(Math.random() * this.emptyCells.length);
        return this.emptyCells[index];
    }

    insertTile(tile) {
        if (this.cells[tile.x][tile.y] !== null) {
            throw new Error('Cell is not empty');
        }
        this.cells[tile.x][tile.y] = tile;
        this.updateEmptyCells();
    }

    removeTile(x, y) {
        if (this.cells[x][y] === null) return;
        this.cells[x][y] = null;
        this.updateEmptyCells();
    }

    getTile(x, y) {
        if (x < 0 || x >= this.size || y < 0 || y >= this.size) return null;
        return this.cells[x][y];
    }

    eachCell(callback) {
        for (let x = 0; x < this.size; x++) {
            for (let y = 0; y < this.size; y++) {
                callback(x, y, this.cells[x][y]);
            }
        }
    }

    serialize() {
        const cellState = [];
        for (let x = 0; x < this.size; x++) {
            const row = [];
            for (let y = 0; y < this.size; y++) {
                row.push(this.cells[x][y] ? this.cells[x][y].value : null);
            }
            cellState.push(row);
        }
        return {
            size: this.size,
            cells: cellState,
            emptyCells: this.emptyCells.slice()
        };
    }

    static deserialize(data) {
        const grid = new Grid();
        grid.size = data.size;
        for (let x = 0; x < grid.size; x++) {
            for (let y = 0; y < grid.size; y++) {
                const value = data.cells[x][y];
                grid.cells[x][y] = value !== null ? { x, y, value } : null;
            }
        }
        grid.updateEmptyCells();
        return grid;
    }

    clear() {
        this.cells = this.empty();
        this.updateEmptyCells();
    }
}