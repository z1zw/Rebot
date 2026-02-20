// ui.js - UI rendering functions for 2048 game
// Dependencies: game.js

class GameUI {
    constructor(game) {
        this.game = game;
        this.boardElement = document.getElementById('game-board');
        this.scoreElement = document.getElementById('score');
        this.bestScoreElement = document.getElementById('best-score');
        this.messageElement = document.getElementById('game-message');
        this.restartButton = document.getElementById('restart-button');
        this.tileContainer = document.getElementById('tile-container');
        
        this.tileSize = 100;
        this.tileSpacing = 10;
        this.animationDuration = 150;
        
        this.init();
    }
    
    init() {
        this.createBoard();
        this.updateScore();
        this.setupEventListeners();
    }
    
    createBoard() {
        this.boardElement.innerHTML = '';
        this.tileContainer.innerHTML = '';
        
        const gridSize = this.game.gridSize;
        const boardSize = (this.tileSize * gridSize) + (this.tileSpacing * (gridSize + 1));
        this.boardElement.style.width = `${boardSize}px`;
        this.boardElement.style.height = `${boardSize}px`;
        
        // Create grid cells
        for (let row = 0; row < gridSize; row++) {
            for (let col = 0; col < gridSize; col++) {
                const cell = document.createElement('div');
                cell.className = 'grid-cell';
                cell.style.width = `${this.tileSize}px`;
                cell.style.height = `${this.tileSize}px`;
                cell.style.top = `${this.getPosition(row)}px`;
                cell.style.left = `${this.getPosition(col)}px`;
                this.boardElement.appendChild(cell);
            }
        }
    }
    
    getPosition(index) {
        return index * (this.tileSize + this.tileSpacing) + this.tileSpacing;
    }
    
    renderBoard() {
        // Remove all existing tiles
        const existingTiles = this.tileContainer.querySelectorAll('.tile');
        existingTiles.forEach(tile => tile.remove());
        
        // Create new tiles
        const grid = this.game.getGrid();
        for (let row = 0; row < grid.length; row++) {
            for (let col = 0; col < grid[row].length; col++) {
                const value = grid[row][col];
                if (value !== 0) {
                    this.createTile(row, col, value);
                }
            }
        }
    }
    
    createTile(row, col, value) {
        const tile = document.createElement('div');
        tile.className = `tile tile-${value}`;
        tile.textContent = value;
        tile.dataset.row = row;
        tile.dataset.col = col;
        tile.dataset.value = value;
        
        // Position the tile
        tile.style.width = `${this.tileSize}px`;
        tile.style.height = `${this.tileSize}px`;
        tile.style.top = `${this.getPosition(row)}px`;
        tile.style.left = `${this.getPosition(col)}px`;
        
        // Add animation class for new tiles
        if (this.game.isNewTile(row, col)) {
            tile.classList.add('tile-new');
        }
        
        this.tileContainer.appendChild(tile);
    }
    
    updateScore() {
        this.scoreElement.textContent = this.game.score;
        this.bestScoreElement.textContent = this.game.bestScore;
    }
    
    showMessage(message, isError = false) {
        this.messageElement.textContent = message;
        this.messageElement.className = `game-message ${isError ? 'error' : 'info'}`;
        this.messageElement.style.display = 'block';
        
        if (!isError) {
            setTimeout(() => {
                this.messageElement.style.display = 'none';
            }, 2000);
        }
    }
    
    animateMove(fromRow, fromCol, toRow, toCol, merged = false) {
        const tile = this.tileContainer.querySelector(`.tile[data-row="${fromRow}"][data-col="${fromCol}"]`);
        if (!tile) return;
        
        tile.style.transition = `all ${this.animationDuration}ms ease`;
        tile.style.top = `${this.getPosition(toRow)}px`;
        tile.style.left = `${this.getPosition(toCol)}px`;
        
        if (merged) {
            tile.classList.add('tile-merged');
            setTimeout(() => {
                tile.remove();
            }, this.animationDuration);
        } else {
            tile.dataset.row = toRow;
            tile.dataset.col = toCol;
        }
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
                this.updateGameState();
            }
        });
        
        // Touch/swipe controls for mobile
        let touchStartX = 0;
        let touchStartY = 0;
        
        document.addEventListener('touchstart', (e) => {
            if (this.game.isGameOver()) return;
            
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        });
        
        document.addEventListener('touchmove', (e) => {
            e.preventDefault();
        }, { passive: false });
        
        document.addEventListener('touchend', (e) => {
            if (this.game.isGameOver()) return;
            
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;
            
            const dx = touchEndX - touchStartX;
            const dy = touchEndY - touchStartY;
            
            if (Math.abs(dx) > 20 || Math.abs(dy) > 20) {
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
                    this.updateGameState();
                }
            }
        });
        
        // Restart button
        this.restartButton.addEventListener('click', () => {
            this.game.restart();
            this.updateGameState();
            this.showMessage('Game restarted!');
        });
    }
    
    updateGameState() {
        // Animate moves if available
        const moves = this.game.getLastMove();
        if (moves && moves.length > 0) {
            moves.forEach(move => {
                this.animateMove(move.fromRow, move.fromCol, move.toRow, move.toCol, move.merged);
            });
            
            // Wait for animations to complete before rendering new tiles
            setTimeout(() => {
                this.renderBoard();
                this.updateScore();
                this.checkGameStatus();
            }, this.animationDuration);
        } else {
            this.renderBoard();
            this.updateScore();
            this.checkGameStatus();
        }
    }
    
    checkGameStatus() {
        if (this.game.isGameOver()) {
            this.showMessage('Game Over!', true);
        } else if (this.game.hasWon()) {
            this.showMessage('You Win!');
        }
    }
    
    resizeBoard() {
        // Adjust tile size based on container width for responsiveness
        const containerWidth = this.boardElement.parentElement.clientWidth;
        const gridSize = this.game.gridSize;
        const maxBoardSize = Math.min(500, containerWidth - 40);
        
        this.tileSize = Math.floor((maxBoardSize - (this.tileSpacing * (gridSize + 1))) / gridSize);
        this.createBoard();
        this.renderBoard();
    }
}

// Initialize UI when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Game instance should be created in main.js
    // const game = new Game(4);
    // const ui = new GameUI(game);
    
    // Handle window resize for responsiveness
    window.addEventListener('resize', () => {
        // ui.resizeBoard();
    });
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GameUI;
}