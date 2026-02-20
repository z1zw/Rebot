const Input = {
    keys: {
        up: false,
        down: false,
        left: false,
        right: false
    },
    touchStartX: 0,
    touchStartY: 0,
    touchEndX: 0,
    touchEndY: 0,
    minSwipeDistance: 30,

    init: function() {
        this.bindKeyboard();
        this.bindTouch();
    },

    bindKeyboard: function() {
        document.addEventListener('keydown', (e) => {
            switch(e.key) {
                case 'ArrowUp':
                    this.keys.up = true;
                    e.preventDefault();
                    break;
                case 'ArrowDown':
                    this.keys.down = true;
                    e.preventDefault();
                    break;
                case 'ArrowLeft':
                    this.keys.left = true;
                    e.preventDefault();
                    break;
                case 'ArrowRight':
                    this.keys.right = true;
                    e.preventDefault();
                    break;
            }
        });

        document.addEventListener('keyup', (e) => {
            switch(e.key) {
                case 'ArrowUp':
                    this.keys.up = false;
                    break;
                case 'ArrowDown':
                    this.keys.down = false;
                    break;
                case 'ArrowLeft':
                    this.keys.left = false;
                    break;
                case 'ArrowRight':
                    this.keys.right = false;
                    break;
            }
        });
    },

    bindTouch: function() {
        document.addEventListener('touchstart', (e) => {
            this.touchStartX = e.changedTouches[0].screenX;
            this.touchStartY = e.changedTouches[0].screenY;
        });

        document.addEventListener('touchend', (e) => {
            this.touchEndX = e.changedTouches[0].screenX;
            this.touchEndY = e.changedTouches[0].screenY;
            this.handleSwipe();
        });
    },

    handleSwipe: function() {
        const dx = this.touchEndX - this.touchStartX;
        const dy = this.touchEndY - this.touchStartY;

        if (Math.abs(dx) > Math.abs(dy)) {
            if (Math.abs(dx) > this.minSwipeDistance) {
                if (dx > 0) {
                    this.keys.right = true;
                    setTimeout(() => { this.keys.right = false; }, 100);
                } else {
                    this.keys.left = true;
                    setTimeout(() => { this.keys.left = false; }, 100);
                }
            }
        } else {
            if (Math.abs(dy) > this.minSwipeDistance) {
                if (dy > 0) {
                    this.keys.down = true;
                    setTimeout(() => { this.keys.down = false; }, 100);
                } else {
                    this.keys.up = true;
                    setTimeout(() => { this.keys.up = false; }, 100);
                }
            }
        }
    },

    getDirection: function() {
        if (this.keys.up) {
            this.keys.up = false;
            return 'up';
        }
        if (this.keys.down) {
            this.keys.down = false;
            return 'down';
        }
        if (this.keys.left) {
            this.keys.left = false;
            return 'left';
        }
        if (this.keys.right) {
            this.keys.right = false;
            return 'right';
        }
        return null;
    },

    reset: function() {
        this.keys.up = false;
        this.keys.down = false;
        this.keys.left = false;
        this.keys.right = false;
    }
};