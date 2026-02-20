// input.js - Keyboard and touch/swipe input handling for 2048 game

class InputHandler {
    constructor(game) {
        this.game = game;
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchEndX = 0;
        this.touchEndY = 0;
        this.minSwipeDistance = 30;
        this.isTouchDevice = 'ontouchstart' in window;
        
        this.init();
    }
    
    init() {
        // Keyboard event listener
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
        
        // Touch events for mobile
        if (this.isTouchDevice) {
            const gameContainer = document.getElementById('game-container') || document.body;
            gameContainer.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
            gameContainer.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
            gameContainer.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
        }
        
        // Prevent default touch behaviors that might interfere
        this.preventTouchScrolling();
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
                    this.game.restart();
                }
                break;
            case 'Escape':
                this.game.togglePause();
                break;
        }
    }
    
    handleTouchStart(event) {
        const touch = event.touches[0];
        this.touchStartX = touch.clientX;
        this.touchStartY = touch.clientY;
        this.touchEndX = touch.clientX;
        this.touchEndY = touch.clientY;
        
        // Prevent default to avoid scrolling
        event.preventDefault();
    }
    
    handleTouchMove(event) {
        if (event.touches.length > 0) {
            const touch = event.touches[0];
            this.touchEndX = touch.clientX;
            this.touchEndY = touch.clientY;
        }
        event.preventDefault();
    }
    
    handleTouchEnd(event) {
        if (!this.touchStartX || !this.touchStartY) return;
        
        const dx = this.touchEndX - this.touchStartX;
        const dy = this.touchEndY - this.touchStartY;
        
        // Calculate absolute distance
        const absDx = Math.abs(dx);
        const absDy = Math.abs(dy);
        
        // Only process if swipe distance is sufficient
        if (Math.max(absDx, absDy) < this.minSwipeDistance) return;
        
        // Determine primary direction
        if (absDx > absDy) {
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
        
        // Reset touch coordinates
        this.touchStartX = 0;
        this.touchStartY = 0;
        
        event.preventDefault();
    }
    
    preventTouchScrolling() {
        // Prevent elastic scrolling on iOS
        document.addEventListener('touchmove', function(event) {
            if (event.scale !== 1) {
                event.preventDefault();
            }
        }, { passive: false });
        
        // Prevent pull-to-refresh on mobile
        document.body.style.overscrollBehavior = 'none';
    }
    
    // Public method to enable/disable input
    setEnabled(enabled) {
        if (enabled) {
            this.init();
        } else {
            this.destroy();
        }
    }
    
    destroy() {
        document.removeEventListener('keydown', this.handleKeyDown);
        
        if (this.isTouchDevice) {
            const gameContainer = document.getElementById('game-container') || document.body;
            gameContainer.removeEventListener('touchstart', this.handleTouchStart);
            gameContainer.removeEventListener('touchmove', this.handleTouchMove);
            gameContainer.removeEventListener('touchend', this.handleTouchEnd);
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InputHandler;
}