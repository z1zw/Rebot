// input.js - Keyboard and touch input handlers for 2048 game
// Depends on game.js for game control functions

class InputHandler {
    constructor(game) {
        this.game = game;
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchEndX = 0;
        this.touchEndY = 0;
        this.minSwipeDistance = 30; // Minimum pixels for swipe detection
        
        this.init();
    }
    
    init() {
        this.bindKeyboardEvents();
        this.bindTouchEvents();
        this.bindButtonEvents();
    }
    
    bindKeyboardEvents() {
        document.addEventListener('keydown', (event) => {
            this.handleKeyDown(event);
        });
    }
    
    bindTouchEvents() {
        const gameContainer = document.getElementById('game-container') || document.body;
        
        gameContainer.addEventListener('touchstart', (event) => {
            this.handleTouchStart(event);
        }, { passive: true });
        
        gameContainer.addEventListener('touchend', (event) => {
            this.handleTouchEnd(event);
        }, { passive: true });
    }
    
    bindButtonEvents() {
        // New Game button
        const newGameBtn = document.getElementById('new-game-btn');
        if (newGameBtn) {
            newGameBtn.addEventListener('click', () => {
                this.game.newGame();
            });
        }
        
        // Undo button
        const undoBtn = document.getElementById('undo-btn');
        if (undoBtn) {
            undoBtn.addEventListener('click', () => {
                this.game.undo();
            });
        }
        
        // Directional buttons for mobile/touch devices
        this.bindDirectionalButtons();
    }
    
    bindDirectionalButtons() {
        const upBtn = document.getElementById('up-btn');
        const downBtn = document.getElementById('down-btn');
        const leftBtn = document.getElementById('left-btn');
        const rightBtn = document.getElementById('right-btn');
        
        if (upBtn) {
            upBtn.addEventListener('click', () => {
                this.game.move('up');
            });
        }
        
        if (downBtn) {
            downBtn.addEventListener('click', () => {
                this.game.move('down');
            });
        }
        
        if (leftBtn) {
            leftBtn.addEventListener('click', () => {
                this.game.move('left');
            });
        }
        
        if (rightBtn) {
            rightBtn.addEventListener('click', () => {
                this.game.move('right');
            });
        }
    }
    
    handleKeyDown(event) {
        // Prevent default behavior for arrow keys to avoid scrolling
        if ([37, 38, 39, 40].includes(event.keyCode)) {
            event.preventDefault();
        }
        
        switch(event.key) {
            case 'ArrowUp':
            case 'w':
            case 'W':
                this.game.move('up');
                break;
                
            case 'ArrowDown':
            case 's':
            case 'S':
                this.game.move('down');
                break;
                
            case 'ArrowLeft':
            case 'a':
            case 'A':
                this.game.move('left');
                break;
                
            case 'ArrowRight':
            case 'd':
            case 'D':
                this.game.move('right');
                break;
                
            case 'r':
            case 'R':
                if (event.ctrlKey || event.metaKey) {
                    this.game.newGame();
                }
                break;
                
            case 'z':
            case 'Z':
                if (event.ctrlKey || event.metaKey) {
                    this.game.undo();
                }
                break;
                
            case ' ':
                // Space for new game
                this.game.newGame();
                break;
        }
    }
    
    handleTouchStart(event) {
        const touch = event.touches[0];
        this.touchStartX = touch.clientX;
        this.touchStartY = touch.clientY;
    }
    
    handleTouchEnd(event) {
        if (!this.touchStartX || !this.touchStartY) {
            return;
        }
        
        const touch = event.changedTouches[0];
        this.touchEndX = touch.clientX;
        this.touchEndY = touch.clientY;
        
        this.handleSwipe();
        
        // Reset touch coordinates
        this.touchStartX = 0;
        this.touchStartY = 0;
    }
    
    handleSwipe() {
        const dx = this.touchEndX - this.touchStartX;
        const dy = this.touchEndY - this.touchStartY;
        
        // Check if swipe distance is sufficient
        if (Math.abs(dx) < this.minSwipeDistance && Math.abs(dy) < this.minSwipeDistance) {
            return; // Not a significant swipe
        }
        
        // Determine primary swipe direction
        if (Math.abs(dx) > Math.abs(dy)) {
            // Horizontal swipe
            if (dx > 0) {
                this.game.move('right');
            } else {
                this.game.move('left');
            }
        } else {
            // Vertical swipe
            if (dy > 0) {
                this.game.move('down');
            } else {
                this.game.move('up');
            }
        }
    }
    
    // Public method to enable/disable input
    setEnabled(enabled) {
        if (enabled) {
            this.init();
        } else {
            // Remove event listeners (simplified - in production you'd track listeners)
            document.removeEventListener('keydown', this.handleKeyDown);
            const gameContainer = document.getElementById('game-container') || document.body;
            gameContainer.removeEventListener('touchstart', this.handleTouchStart);
            gameContainer.removeEventListener('touchend', this.handleTouchEnd);
        }
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InputHandler;
}