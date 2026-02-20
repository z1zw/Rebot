class Mouse {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.x = canvas.width / 2;
        this.y = canvas.height / 2;
        this.radius = 20;
        this.speed = 5;
        this.color = '#FF6B6B';
        this.isMoving = { up: false, down: false, left: false, right: false };
        this.setupControls();
    }

    setupControls() {
        window.addEventListener('keydown', (e) => {
            switch(e.key) {
                case 'ArrowUp':
                case 'w':
                case 'W':
                    this.isMoving.up = true;
                    break;
                case 'ArrowDown':
                case 's':
                case 'S':
                    this.isMoving.down = true;
                    break;
                case 'ArrowLeft':
                case 'a':
                case 'A':
                    this.isMoving.left = true;
                    break;
                case 'ArrowRight':
                case 'd':
                case 'D':
                    this.isMoving.right = true;
                    break;
            }
        });

        window.addEventListener('keyup', (e) => {
            switch(e.key) {
                case 'ArrowUp':
                case 'w':
                case 'W':
                    this.isMoving.up = false;
                    break;
                case 'ArrowDown':
                case 's':
                case 'S':
                    this.isMoving.down = false;
                    break;
                case 'ArrowLeft':
                case 'a':
                case 'A':
                    this.isMoving.left = false;
                    break;
                case 'ArrowRight':
                case 'd':
                case 'D':
                    this.isMoving.right = false;
                    break;
            }
        });

        this.canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            this.handleTouch(touch.clientX, touch.clientY);
        });

        this.canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            this.handleTouch(touch.clientX, touch.clientY);
        });

        this.canvas.addEventListener('touchend', () => {
            this.isMoving.up = this.isMoving.down = this.isMoving.left = this.isMoving.right = false;
        });
    }

    handleTouch(touchX, touchY) {
        const rect = this.canvas.getBoundingClientRect();
        const x = touchX - rect.left;
        const y = touchY - rect.top;
        const dx = x - this.x;
        const dy = y - this.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance > this.radius) {
            this.isMoving.up = dy < 0;
            this.isMoving.down = dy > 0;
            this.isMoving.left = dx < 0;
            this.isMoving.right = dx > 0;
        } else {
            this.isMoving.up = this.isMoving.down = this.isMoving.left = this.isMoving.right = false;
        }
    }

    update() {
        if (this.isMoving.up && this.y - this.radius > 0) this.y -= this.speed;
        if (this.isMoving.down && this.y + this.radius < this.canvas.height) this.y += this.speed;
        if (this.isMoving.left && this.x - this.radius > 0) this.x -= this.speed;
        if (this.isMoving.right && this.x + this.radius < this.canvas.width) this.x += this.speed;
    }

    draw() {
        this.ctx.beginPath();
        this.ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        this.ctx.fillStyle = this.color;
        this.ctx.fill();
        this.ctx.strokeStyle = '#333';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();

        this.ctx.beginPath();
        this.ctx.arc(this.x - 8, this.y - 8, 5, 0, Math.PI * 2);
        this.ctx.arc(this.x + 8, this.y - 8, 5, 0, Math.PI * 2);
        this.ctx.fillStyle = '#333';
        this.ctx.fill();

        this.ctx.beginPath();
        this.ctx.moveTo(this.x - 5, this.y + 5);
        this.ctx.lineTo(this.x, this.y + 10);
        this.ctx.lineTo(this.x + 5, this.y + 5);
        this.ctx.strokeStyle = '#333';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
    }

    getPosition() {
        return { x: this.x, y: this.y };
    }

    reset() {
        this.x = this.canvas.width / 2;
        this.y = this.canvas.height / 2;
        this.isMoving = { up: false, down: false, left: false, right: false };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = Mouse;
}