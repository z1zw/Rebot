class Tile {
    constructor(value, row, col) {
        this.value = value || 0;
        this.row = row;
        this.col = col;
        this.previousPosition = null;
        this.mergedFrom = null; // Tracks tiles that merged into this one
        this.newTile = false; // Flag for new tile animation
        this.mergedTile = false; // Flag for merge animation
    }

    // Save current position as previous
    savePosition() {
        this.previousPosition = { row: this.row, col: this.col };
    }

    // Update tile position
    updatePosition(row, col) {
        this.row = row;
        this.col = col;
    }

    // Get CSS class based on value
    getTileClass() {
        return `tile tile-${this.value}`;
    }

    // Get display text (empty for 0)
    getDisplayText() {
        return this.value === 0 ? '' : this.value.toString();
    }

    // Check if tile is empty
    isEmpty() {
        return this.value === 0;
    }

    // Check if tile can merge with another tile
    canMergeWith(otherTile) {
        return !this.isEmpty() && 
               !otherTile.isEmpty() && 
               this.value === otherTile.value && 
               !this.mergedFrom && 
               !otherTile.mergedFrom;
    }

    // Merge with another tile and return new value
    mergeWith(otherTile) {
        if (this.canMergeWith(otherTile)) {
            this.value += otherTile.value;
            this.mergedFrom = [this, otherTile];
            this.mergedTile = true;
            return this.value;
        }
        return 0;
    }

    // Reset merge flags for next move
    resetMergeFlags() {
        this.mergedFrom = null;
        this.mergedTile = false;
        this.newTile = false;
    }

    // Clone tile (useful for board state management)
    clone() {
        const tile = new Tile(this.value, this.row, this.col);
        tile.previousPosition = this.previousPosition ? { ...this.previousPosition } : null;
        tile.mergedFrom = this.mergedFrom;
        tile.newTile = this.newTile;
        tile.mergedTile = this.mergedTile;
        return tile;
    }
}