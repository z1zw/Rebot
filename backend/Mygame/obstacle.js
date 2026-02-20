// obstacle.js - Obstacle objects (cats/traps) definition with movement patterns and collision properties

class Obstacle {
    constructor(x, y, width, height, type, speed, pattern) {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        this.type = type; // 'cat' or 'trap'
        this.speed = speed;
        this.pattern = pattern; // 'horizontal', 'vertical', 'circular', 'static'
        this.active = true;
        this.angle = 0;
        this.radius = 50;
        this.centerX = x;
        this.centerY = y;
        this.direction = 1; // 1 for right/down, -1 for left/up
        this.color = type === 'cat' ? '#FF6B6B' : '#4ECDC4';
        this.collisionDamage = type === 'cat' ? 2 : 1;
    }

    update(deltaTime) {
        if (!this.active) return;

        switch (this.pattern) {
            case 'horizontal':
                this.x += this.speed * this.direction * deltaTime;
                if (this.x > 800 - this.width || this.x < 0) {
                    this.direction *= -1;
                }
                break;
            case 'vertical':
                this.y += this.speed * this.direction * deltaTime;
                if (this.y > 600 - this.height || this.y < 0) {
                    this.direction *= -1;
                }
                break;
            case 'circular':
                this.angle += this.speed * deltaTime * 0.05;
                this.x = this.centerX + Math.cos(this.angle) * this.radius;
                this.y = this.centerY + Math.sin(this.angle) * this.radius;
                break;
            case 'static':
                // No movement
                break;
            default:
                break;
        }
    }

    draw(ctx) {
        if (!this.active) return;

        ctx.save();
        ctx.fillStyle = this.color;
        ctx.fillRect(this.x, this.y, this.width, this.height);

        // Draw obstacle type indicator
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(this.type.charAt(0).toUpperCase(), this.x + this.width / 2, this.y + this.height / 2);

        // Draw pattern indicator
        ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        ctx.font = '10px Arial';
        ctx.fillText(this.pattern.charAt(0), this.x + this.width - 10, this.y + 10);
        ctx.restore();
    }

    checkCollision(player) {
        if (!this.active || !player.active) return false;

        return (
            this.x < player.x + player.width &&
            this.x + this.width > player.x &&
            this.y < player.y + player.height &&
            this.y + this.height > player.y
        );
    }

    deactivate() {
        this.active = false;
    }

    reset() {
        this.active = true;
        this.x = this.centerX;
        this.y = this.centerY;
        this.angle = 0;
        this.direction = 1;
    }
}

// Obstacle manager to handle multiple obstacles
class ObstacleManager {
    constructor() {
        this.obstacles = [];
        this.spawnTimer = 0;
        this.spawnInterval = 3000; // Spawn new obstacle every 3 seconds
    }

    initialize() {
        // Create initial obstacles
        this.obstacles = [
            new Obstacle(100, 100, 40, 40, 'cat', 0.2, 'horizontal'),
            new Obstacle(400, 200, 50, 30, 'trap', 0.15, 'vertical'),
            new Obstacle(600, 300, 35, 35, 'cat', 0.1, 'circular'),
            new Obstacle(200, 400, 45, 45, 'trap', 0, 'static'),
        ];
    }

    update(deltaTime) {
        // Update all active obstacles
        this.obstacles.forEach(obstacle => {
            if (obstacle.active) {
                obstacle.update(deltaTime);
            }
        });

        // Spawn new obstacles periodically
        this.spawnTimer += deltaTime;
        if (this.spawnTimer >= this.spawnInterval) {
            this.spawnRandomObstacle();
            this.spawnTimer = 0;
        }

        // Remove inactive obstacles (optional cleanup)
        this.obstacles = this.obstacles.filter(obstacle => obstacle.active);
    }

    draw(ctx) {
        this.obstacles.forEach(obstacle => obstacle.draw(ctx));
    }

    spawnRandomObstacle() {
        const types = ['cat', 'trap'];
        const patterns = ['horizontal', 'vertical', 'circular', 'static'];
        const speeds = [0.1, 0.15, 0.2, 0.25];
        
        const type = types[Math.floor(Math.random() * types.length)];
        const pattern = patterns[Math.floor(Math.random() * patterns.length)];
        const speed = speeds[Math.floor(Math.random() * speeds.length)];
        const width = Math.floor(Math.random() * 30) + 30;
        const height = Math.floor(Math.random() * 30) + 30;
        const x = Math.floor(Math.random() * (800 - width));
        const y = Math.floor(Math.random() * (600 - height));

        this.obstacles.push(new Obstacle(x, y, width, height, type, speed, pattern));
    }

    checkCollisions(player) {
        let collisionDetected = false;
        let totalDamage = 0;

        this.obstacles.forEach(obstacle => {
            if (obstacle.active && obstacle.checkCollision(player)) {
                collisionDetected = true;
                totalDamage += obstacle.collisionDamage;
                obstacle.deactivate();
            }
        });

        return { collisionDetected, totalDamage };
    }

    reset() {
        this.obstacles.forEach(obstacle => obstacle.reset());
        this.spawnTimer = 0;
    }

    clearAll() {
        this.obstacles = [];
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Obstacle, ObstacleManager };
}