class Grid {
  constructor(size = 4) {
    this.size = size;
    this.cells = this.buildEmptyGrid();
    this.emptyCells = this.size * this.size;
  }

  buildEmptyGrid() {
    const grid = [];
    for (let r = 0; r < this.size; r++) {
      grid[r] = [];
      for (let c = 0; c < this.size; c++) {
        grid[r][c] = null;
      }
    }
    return grid;
  }

  getEmptyCells() {
    const empty = [];
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        if (this.cells[r][c] === null) {
          empty.push({ row: r, col: c });
        }
      }
    }
    return empty;
  }

  updateEmptyCount() {
    let count = 0;
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        if (this.cells[r][c] === null) count++;
      }
    }
    this.emptyCells = count;
    return count;
  }

  getCell(row, col) {
    if (this.isWithinBounds(row, col)) {
      return this.cells[row][col];
    }
    return null;
  }

  setCell(row, col, value) {
    if (this.isWithinBounds(row, col)) {
      const previous = this.cells[row][col];
      this.cells[row][col] = value;
      if (previous === null && value !== null) {
        this.emptyCells--;
      } else if (previous !== null && value === null) {
        this.emptyCells++;
      }
      return true;
    }
    return false;
  }

  isWithinBounds(row, col) {
    return row >= 0 && row < this.size && col >= 0 && col < this.size;
  }

  clear() {
    this.cells = this.buildEmptyGrid();
    this.emptyCells = this.size * this.size;
  }

  hasEmptyCells() {
    return this.emptyCells > 0;
  }

  isFull() {
    return this.emptyCells === 0;
  }

  clone() {
    const newGrid = new Grid(this.size);
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        newGrid.cells[r][c] = this.cells[r][c];
      }
    }
    newGrid.emptyCells = this.emptyCells;
    return newGrid;
  }

  serialize() {
    const flat = [];
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        flat.push(this.cells[r][c]);
      }
    }
    return flat;
  }

  deserialize(data) {
    if (data.length !== this.size * this.size) return false;
    let idx = 0;
    let emptyCount = 0;
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        this.cells[r][c] = data[idx];
        if (data[idx] === null) emptyCount++;
        idx++;
      }
    }
    this.emptyCells = emptyCount;
    return true;
  }
}