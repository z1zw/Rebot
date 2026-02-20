// ui.js - 2048 Game User Interface
class UI {
    constructor(game) {
        this.game = game;
        this.gridContainer = document.getElementById('grid-container');
        this.scoreElement = document.getElementById('score');
        this.bestScoreElement = document.getElementById('best-score');
        this.messageElement = document.getElementById('message');
        this.restartButton = document.getElementById('restart-button');
        this.tiles = [];
        this.animationDuration = 150;
        this.setupEventListeners();
        this.initializeGrid();
    }

    initializeGrid() {
        this.gridContainer.innerHTML = '';
        this.tiles = [];
        
        // Create grid cells
        for (let row = 0; row < this.game.size; row++) {
            for (let col = 0; col < this.game.size; col++) {
                const cell = document.createElement('div');
                cell.className = 'grid-cell';
                cell.dataset.row = row;
                cell.dataset.col = col;
                this.gridContainer.appendChild(cell);
            }
        }
        
        // Create initial tiles
        this.update();
    }

    setupEventListeners() {
        // Keyboard controls
        document.addEventListener('keydown', (e) => {
            if (this.game.isGameOver()) return;
            
            let moved = false;
            switch(e.key) {
                case 'ArrowUp':
                    moved = this.game.move('up');
                    break;
                case 'ArrowDown':
                    moved = this.game.move('down');
                    break;
                case 'ArrowLeft':
                    moved = this.game.move('left');
                    break;
                case 'ArrowRight':
                    moved = this.game.move('right');
                    break;
            }
            
            if (moved) {
                this.update();
                if (this.game.isGameOver()) {
                    this.showMessage('Game Over!');
                } else if (this.game.hasWon()) {
                    this.showMessage('You Win!');
                }
            }
        });

        // Touch/swipe controls
        let touchStartX, touchStartY;
        
        document.addEventListener('touchstart', (e) => {
            if (this.game.isGameOver()) return;
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            if (this.game.isGameOver() || !touchStartX || !touchStartY) return;
            
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;
            
            const dx = touchEndX - touchStartX;
            const dy = touchEndY - touchStartY;
            
            // Minimum swipe distance
            if (Math.abs(dx) < 30 && Math.abs(dy) < 30) return;
            
            let moved = false;
            
            if (Math.abs(dx) > Math.abs(dy)) {
                // Horizontal swipe
                if (dx > 0) {
                    moved = this.game.move('right');
                } else {
                    moved = this.game.move('left');
                }
            } else {
                // Vertical swipe
                if (dy > 0) {
                    moved = this.game.move('down');
                } else {
                    moved = this.game.move('up');
                }
            }
            
            if (moved) {
                this.update();
                if (this.game.isGameOver()) {
                    this.showMessage('Game Over!');
                } else if (this.game.hasWon()) {
                    this.showMessage('You Win!');
                }
            }
            
            touchStartX = null;
            touchStartY = null;
        }, { passive: true });

        // Restart button
        this.restartButton.addEventListener('click', () => {
            this.game.restart();
            this.update();
            this.hideMessage();
        });
    }

    update() {
        this.updateScore();
        this.updateTiles();
    }

    updateScore() {
        this.scoreElement.textContent = this.game.getScore();
        this.bestScoreElement.textContent = this.game.getBestScore();
    }

    updateTiles() {
        // Remove old tiles
        this.tiles.forEach(tile => tile.element.remove());
        this.tiles = [];
        
        // Create new tiles
        const grid = this.game.getGrid();
        for (let row = 0; row < this.game.size; row++) {
            for (let col = 0; col < this.game.size; col++) {
                const value = grid[row][col];
                if (value !== 0) {
                    this.createTile(row, col, value);
                }
            }
        }
    }

    createTile(row, col, value) {
        const tileElement = document.createElement('div');
        tileElement.className = `tile tile-${value}`;
        tileElement.textContent = value;
        tileElement.dataset.row = row;
        tileElement.dataset.col = col;
        
        // Position tile
        const cellSize = 100; // Assuming 100px cells
        const x = col * cellSize;
        const y = row * cellSize;
        
        tileElement.style.transform = `translate(${x}px, ${y}px)`;
        
        // Add animation for new tiles
        if (this.game.wasTileAdded(row, col)) {
            tileElement.classList.add('tile-new');
            setTimeout(() => {
                tileElement.classList.remove('tile-new');
            }, this.animationDuration);
        }
        
        this.gridContainer.appendChild(tileElement);
        this.tiles.push({
            element: tileElement,
            row: row,
            col: col,
            value: value
        });
    }

    animateTileMove(fromRow, fromCol, toRow, toCol, merged = false) {
        const tile = this.tiles.find(t => 
            t.row === fromRow && t.col === fromCol
        );
        
        if (!tile) return;
        
        const cellSize = 100;
        const newX = toCol * cellSize;
        const newY = toRow * cellSize;
        
        tile.element.style.transition = `transform ${this.animationDuration}ms ease`;
        tile.element.style.transform = `translate(${newX}px, ${newY}px)`;
        
        tile.row = toRow;
        tile.col = toCol;
        
        if (merged) {
            tile.element.classList.add('tile-merged');
            setTimeout(() => {
                tile.element.classList.remove('tile-merged');
            }, this.animationDuration);
        }
        
        // Reset transition after animation
        setTimeout(() => {
            tile.element.style.transition = '';
        }, this.animationDuration);
    }

    showMessage(text) {
        this.messageElement.textContent = text;
        this.messageElement.classList.add('visible');
    }

    hideMessage() {
        this.messageElement.classList.remove('visible');
    }
}

// Initialize UI when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Assuming game.js is loaded and Game class is available
    const game = new Game(4); // 4x4 grid
    const ui = new UI(game);
});