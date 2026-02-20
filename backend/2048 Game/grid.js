class Grid {
  constructor(size = 4) {
    this.size = size;
    this.cells = this.createEmptyBoard();
    this.score = 0;
  }

  createEmptyBoard() {
    const board = [];
    for (let row = 0; row < this.size; row++) {
      board[row] = [];
      for (let col = 0; col < this.size; col++) {
        board[row][col] = null;
      }
    }
    return board;
  }

  getEmptyCells() {
    const emptyCells = [];
    for (let row = 0; row < this.size; row++) {
      for (let col = 0; col < this.size; col++) {
        if (this.cells[row][col] === null) {
          emptyCells.push({ row, col });
        }
      }
    }
    return emptyCells;
  }

  getRandomEmptyCell() {
    const emptyCells = this.getEmptyCells();
    if (emptyCells.length === 0) return null;
    const randomIndex = Math.floor(Math.random() * emptyCells.length);
    return emptyCells[randomIndex];
  }

  addRandomTile() {
    const emptyCell = this.getRandomEmptyCell();
    if (emptyCell) {
      const value = Math.random() < 0.9 ? 2 : 4;
      this.cells[emptyCell.row][emptyCell.col] = value;
      return { row: emptyCell.row, col: emptyCell.col, value };
    }
    return null;
  }

  getCell(row, col) {
    if (this.isWithinBounds(row, col)) {
      return this.cells[row][col];
    }
    return null;
  }

  setCell(row, col, value) {
    if (this.isWithinBounds(row, col)) {
      this.cells[row][col] = value;
    }
  }

  isWithinBounds(row, col) {
    return row >= 0 && row < this.size && col >= 0 && col < this.size;
  }

  clearCell(row, col) {
    if (this.isWithinBounds(row, col)) {
      this.cells[row][col] = null;
    }
  }

  moveTile(fromRow, fromCol, toRow, toCol) {
    if (!this.isWithinBounds(fromRow, fromCol) || !this.isWithinBounds(toRow, toCol)) return false;
    if (this.cells[fromRow][fromCol] === null) return false;
    if (this.cells[toRow][toCol] !== null) return false;

    this.cells[toRow][toCol] = this.cells[fromRow][fromCol];
    this.cells[fromRow][fromCol] = null;
    return true;
  }

  mergeTiles(fromRow, fromCol, toRow, toCol) {
    if (!this.isWithinBounds(fromRow, fromCol) || !this.isWithinBounds(toRow, toCol)) return 0;
    const fromValue = this.cells[fromRow][fromCol];
    const toValue = this.cells[toRow][toCol];
    if (fromValue === null || toValue === null || fromValue !== toValue) return 0;

    const newValue = fromValue * 2;
    this.cells[toRow][toCol] = newValue;
    this.cells[fromRow][fromCol] = null;
    this.score += newValue;
    return newValue;
  }

  hasMovesAvailable() {
    if (this.getEmptyCells().length > 0) return true;

    for (let row = 0; row < this.size; row++) {
      for (let col = 0; col < this.size; col++) {
        const current = this.cells[row][col];
        if (current === null) continue;

        const neighbors = [
          { row: row - 1, col },
          { row: row + 1, col },
          { row, col: col - 1 },
          { row, col: col + 1 }
        ];

        for (const neighbor of neighbors) {
          if (this.isWithinBounds(neighbor.row, neighbor.col)) {
            const neighborValue = this.cells[neighbor.row][neighbor.col];
            if (neighborValue === current) return true;
          }
        }
      }
    }
    return false;
  }

  isFull() {
    return this.getEmptyCells().length === 0;
  }

  reset() {
    this.cells = this.createEmptyBoard();
    this.score = 0;
  }

  serialize() {
    return {
      size: this.size,
      cells: JSON.parse(JSON.stringify(this.cells)),
      score: this.score
    };
  }

  deserialize(data) {
    this.size = data.size;
    this.cells = data.cells;
    this.score = data.score;
  }
}