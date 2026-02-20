class Tile {
    constructor(value, row, col) {
        this.value = value;
        this.row = row;
        this.col = col;
        this.element = this.createTileElement();
        this.updateDisplay();
    }

    createTileElement() {
        const tile = document.createElement('div');
        tile.classList.add('tile');
        tile.dataset.row = this.row;
        tile.dataset.col = this.col;
        tile.textContent = this.value === 0 ? '' : this.value;
        return tile;
    }

    updatePosition(newRow, newCol) {
        this.row = newRow;
        this.col = newCol;
        this.element.dataset.row = newRow;
        this.element.dataset.col = newCol;
    }

    updateValue(newValue) {
        this.value = newValue;
        this.updateDisplay();
    }

    updateDisplay() {
        this.element.textContent = this.value === 0 ? '' : this.value;
        this.element.className = 'tile'; // Reset classes
        this.element.classList.add('tile');
        if (this.value > 0) {
            this.element.classList.add(`tile-${this.value}`);
        }
        // Add merged animation class temporarily if value changed recently
        if (this.merged) {
            this.element.classList.add('merged');
            setTimeout(() => {
                this.element.classList.remove('merged');
                this.merged = false;
            }, 200);
        }
    }

    markForMerge() {
        this.merged = true;
    }

    removeFromDOM() {
        if (this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
    }
}