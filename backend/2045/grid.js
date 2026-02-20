class Grid {
  constructor(size) {
    this.size = size;
    this.cells = this.buildEmptyGrid();
    this.empties = this.buildEmptiesSet();
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

  buildEmptiesSet() {
    const empties = new Set();
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        empties.add(`${r},${c}`);
      }
    }
    return empties;
  }

  getEmptyCells() {
    return Array.from(this.empties).map(pos => {
      const [r, c] = pos.split(',').map(Number);
      return { row: r, col: c };
    });
  }

  getRandomEmptyCell() {
    const empties = this.getEmptyCells();
    if (empties.length === 0) return null;
    return empties[Math.floor(Math.random() * empties.length)];
  }

  insertTile(tile) {
    const { row, col } = tile;
    if (this.cells[row][col] !== null) {
      console.warn('Overwriting existing tile at', row, col);
    }
    this.cells[row][col] = tile;
    this.empties.delete(`${row},${col}`);
  }

  removeTile(row, col) {
    if (this.cells[row][col] === null) return;
    this.cells[row][col] = null;
    this.empties.add(`${row},${col}`);
  }

  getTile(row, col) {
    if (row < 0 || row >= this.size || col < 0 || col >= this.size) {
      return null;
    }
    return this.cells[row][col];
  }

  moveTile(tile, newRow, newCol) {
    const { row, col } = tile;
    if (this.cells[row][col] !== tile) {
      console.warn('Tile not found at original position');
      return;
    }
    this.removeTile(row, col);
    tile.row = newRow;
    tile.col = newCol;
    this.insertTile(tile);
  }

  mergeTiles(sourceTile, targetTile) {
    const { row: sr, col: sc } = sourceTile;
    const { row: tr, col: tc } = targetTile;
    if (this.cells[sr][sc] !== sourceTile || this.cells[tr][tc] !== targetTile) {
      console.warn('Invalid merge: tiles not at expected positions');
      return;
    }
    targetTile.value *= 2;
    targetTile.mergedFrom = sourceTile;
    this.removeTile(sr, sc);
  }

  clearMergedFlags() {
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        const tile = this.cells[r][c];
        if (tile) {
          tile.mergedFrom = null;
        }
      }
    }
  }

  serialize() {
    const grid = [];
    for (let r = 0; r < this.size; r++) {
      grid[r] = [];
      for (let c = 0; c < this.size; c++) {
        const tile = this.cells[r][c];
        grid[r][c] = tile ? { value: tile.value, mergedFrom: tile.mergedFrom } : null;
      }
    }
    return {
      size: this.size,
      grid: grid,
      empties: Array.from(this.empties)
    };
  }

  deserialize(data) {
    this.size = data.size;
    this.cells = this.buildEmptyGrid();
    this.empties = new Set(data.empties);
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        const tileData = data.grid[r][c];
        if (tileData) {
          const tile = { row: r, col: c, value: tileData.value, mergedFrom: tileData.mergedFrom };
          this.cells[r][c] = tile;
        }
      }
    }
  }

  isFull() {
    return this.empties.size === 0;
  }

  hasMoves() {
    if (!this.isFull()) return true;
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        const tile = this.cells[r][c];
        if (!tile) continue;
        const neighbors = [
          this.getTile(r - 1, c),
          this.getTile(r + 1, c),
          this.getTile(r, c - 1),
          this.getTile(r, c + 1)
        ];
        for (const neighbor of neighbors) {
          if (neighbor && neighbor.value === tile.value) {
            return true;
          }
        }
      }
    }
    return false;
  }

  clear() {
    this.cells = this.buildEmptyGrid();
    this.empties = this.buildEmptiesSet();
  }
}