// input.js - Keyboard and touch event handlers for controlling the 2048 game
// Dependencies: game.js, ui.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize input handlers after DOM is fully loaded
    initInputHandlers();
});

// Main function to initialize all input handlers
function initInputHandlers() {
    initKeyboardHandlers();
    initTouchHandlers();
    initButtonHandlers();
}

// Keyboard input handler
function initKeyboardHandlers() {
    document.addEventListener('keydown', function(event) {
        // Prevent default behavior for arrow keys to avoid scrolling
        if ([37, 38, 39, 40].includes(event.keyCode)) {
            event.preventDefault();
        }

        // Handle arrow keys and WASD
        switch(event.keyCode) {
            case 37: // Left arrow
            case 65: // A key
                if (typeof handleMove === 'function') {
                    handleMove('left');
                }
                break;
            case 38: // Up arrow
            case 87: // W key
                if (typeof handleMove === 'function') {
                    handleMove('up');
                }
                break;
            case 39: // Right arrow
            case 68: // D key
                if (typeof handleMove === 'function') {
                    handleMove('right');
                }
                break;
            case 40: // Down arrow
            case 83: // S key
                if (typeof handleMove === 'function') {
                    handleMove('down');
                }
                break;
            case 82: // R key - Restart game
                if (typeof restartGame === 'function') {
                    restartGame();
                }
                break;
            case 27: // ESC key - Pause/Resume game
                if (typeof togglePause === 'function') {
                    togglePause();
                }
                break;
        }
    });
}

// Touch/swipe input handler for mobile devices
function initTouchHandlers() {
    let touchStartX = null;
    let touchStartY = null;
    const minSwipeDistance = 30; // Minimum distance in pixels to register as a swipe

    document.addEventListener('touchstart', function(event) {
        const touch = event.touches[0];
        touchStartX = touch.clientX;
        touchStartY = touch.clientY;
    }, { passive: true });

    document.addEventListener('touchmove', function(event) {
        event.preventDefault(); // Prevent scrolling while swiping
    }, { passive: false });

    document.addEventListener('touchend', function(event) {
        if (touchStartX === null || touchStartY === null) {
            return;
        }

        const touch = event.changedTouches[0];
        const touchEndX = touch.clientX;
        const touchEndY = touch.clientY;

        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;

        // Reset touch coordinates
        touchStartX = null;
        touchStartY = null;

        // Check if it's a valid swipe (minimum distance)
        if (Math.abs(deltaX) < minSwipeDistance && Math.abs(deltaY) < minSwipeDistance) {
            return; // Not a significant swipe
        }

        // Determine swipe direction based on larger movement
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
            // Horizontal swipe
            if (deltaX > 0 && typeof handleMove === 'function') {
                handleMove('right');
            } else if (deltaX < 0 && typeof handleMove === 'function') {
                handleMove('left');
            }
        } else {
            // Vertical swipe
            if (deltaY > 0 && typeof handleMove === 'function') {
                handleMove('down');
            } else if (deltaY < 0 && typeof handleMove === 'function') {
                handleMove('up');
            }
        }
    }, { passive: true });
}

// Button handlers for on-screen controls (mobile/accessibility)
function initButtonHandlers() {
    // Wait for UI to be ready
    setTimeout(function() {
        // Direction buttons
        const leftBtn = document.getElementById('left-btn');
        const upBtn = document.getElementById('up-btn');
        const rightBtn = document.getElementById('right-btn');
        const downBtn = document.getElementById('down-btn');
        
        // Control buttons
        const restartBtn = document.getElementById('restart-btn');
        const pauseBtn = document.getElementById('pause-btn');

        // Direction button handlers
        if (leftBtn) {
            leftBtn.addEventListener('click', function() {
                if (typeof handleMove === 'function') {
                    handleMove('left');
                }
            });
        }

        if (upBtn) {
            upBtn.addEventListener('click', function() {
                if (typeof handleMove === 'function') {
                    handleMove('up');
                }
            });
        }

        if (rightBtn) {
            rightBtn.addEventListener('click', function() {
                if (typeof handleMove === 'function') {
                    handleMove('right');
                }
            });
        }

        if (downBtn) {
            downBtn.addEventListener('click', function() {
                if (typeof handleMove === 'function') {
                    handleMove('down');
                }
            });
        }

        // Control button handlers
        if (restartBtn) {
            restartBtn.addEventListener('click', function() {
                if (typeof restartGame === 'function') {
                    restartGame();
                }
            });
        }

        if (pauseBtn) {
            pauseBtn.addEventListener('click', function() {
                if (typeof togglePause === 'function') {
                    togglePause();
                }
            });
        }
    }, 100); // Small delay to ensure DOM is ready
}

// Public API for other modules to control input
const InputManager = {
    enable: function() {
        // Re-enable all input handlers if they were disabled
        initInputHandlers();
    },
    
    disable: function() {
        // Temporarily disable input (e.g., during animations or game over)
        document.removeEventListener('keydown', initKeyboardHandlers);
        document.removeEventListener('touchstart', initTouchHandlers);
        document.removeEventListener('touchend', initTouchHandlers);
    },
    
    // Function to handle move commands from input
    handleMove: function(direction) {
        // This function should be implemented in game.js
        console.log('Move command received:', direction);
        // The actual implementation will be in game.js
    }
};

// Make InputManager available globally
window.InputManager = InputManager;