// Player character class with movement controls and collision detection
class Player {
    constructor(x, y, width, height, color = '#4A90E2') {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        this.color = color;
        this.velocityX = 0;
        this.velocityY = 0;
        this.speed = 5;
        this.isJumping = false;
        this.gravity = 0.5;
        this.jumpPower = -12;
        this.grounded = false;
        this.friction = 0.85;
        this.maxSpeed = 8;
        
        // Movement state
        this.keys = {
            left: false,
            right: false,
            up: false
        };
        
        // Bind event listeners
        this.bindControls();
    }
    
    // Bind keyboard controls
    bindControls() {
        window.addEventListener('keydown', (e) => {
            switch(e.key.toLowerCase()) {
                case 'arrowleft':
                case 'a':
                    this.keys.left = true;
                    break;
                case 'arrowright':
                case 'd':
                    this.keys.right = true;
                    break;
                case 'arrowup':
                case 'w':
                case ' ':
                    this.keys.up = true;
                    break;
            }
        });
        
        window.addEventListener('keyup', (e) => {
            switch(e.key.toLowerCase()) {
                case 'arrowleft':
                case 'a':
                    this.keys.left = false;
                    break;
                case 'arrowright':
                case 'd':
                    this.keys.right = false;
                    break;
                case 'arrowup':
                case 'w':
                case ' ':
                    this.keys.up = false;
                    break;
            }
        });
        
        // Touch controls for mobile
        this.setupTouchControls();
    }
    
    // Setup touch controls for mobile devices
    setupTouchControls() {
        const leftBtn = document.getElementById('leftBtn');
        const rightBtn = document.getElementById('rightBtn');
        const jumpBtn = document.getElementById('jumpBtn');
        
        if (leftBtn && rightBtn && jumpBtn) {
            leftBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                this.keys.left = true;
            });
            leftBtn.addEventListener('touchend', (e) => {
                e.preventDefault();
                this.keys.left = false;
            });
            
            rightBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                this.keys.right = true;
            });
            rightBtn.addEventListener('touchend', (e) => {
                e.preventDefault();
                this.keys.right = false;
            });
            
            jumpBtn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                this.keys.up = true;
            });
            jumpBtn.addEventListener('touchend', (e) => {
                e.preventDefault();
                this.keys.up = false;
            });
        }
    }
    
    // Update player position and physics
    update(platforms = []) {
        // Apply horizontal movement
        if (this.keys.left) {
            this.velocityX = Math.max(this.velocityX - this.speed * 0.5, -this.maxSpeed);
        }
        if (this.keys.right) {
            this.velocityX = Math.min(this.velocityX + this.speed * 0.5, this.maxSpeed);
        }
        
        // Apply friction
        this.velocityX *= this.friction;
        
        // Apply gravity
        if (!this.grounded) {
            this.velocityY += this.gravity;
        } else {
            this.velocityY = 0;
        }
        
        // Handle jumping
        if (this.keys.up && this.grounded) {
            this.velocityY = this.jumpPower;
            this.grounded = false;
            this.isJumping = true;
        }
        
        // Update position
        const newX = this.x + this.velocityX;
        const newY = this.y + this.velocityY;
        
        // Check collisions with platforms
        let collision = this.checkCollisions(newX, newY, platforms);
        
        if (collision.horizontal) {
            this.velocityX = 0;
            this.x = collision.horizontalCorrection;
        } else {
            this.x = newX;
        }
        
        if (collision.vertical) {
            this.velocityY = 0;
            this.y = collision.verticalCorrection;
            this.grounded = collision.grounded;
            this.isJumping = false;
        } else {
            this.y = newY;
            this.grounded = false;
        }
        
        // Keep player within screen bounds (optional - can be handled by game world)
        this.x = Math.max(0, Math.min(this.x, 800 - this.width));
        this.y = Math.max(0, Math.min(this.y, 600 - this.height));
    }
    
    // Check collisions with platforms
    checkCollisions(newX, newY, platforms) {
        let result = {
            horizontal: false,
            vertical: false,
            horizontalCorrection: newX,
            verticalCorrection: newY,
            grounded: false
        };
        
        // Create player bounds for new position
        const playerBounds = {
            left: newX,
            right: newX + this.width,
            top: newY,
            bottom: newY + this.height
        };
        
        // Check each platform
        for (const platform of platforms) {
            const platformBounds = {
                left: platform.x,
                right: platform.x + platform.width,
                top: platform.y,
                bottom: platform.y + platform.height
            };
            
            // Check if player intersects with platform
            if (playerBounds.right > platformBounds.left &&
                playerBounds.left < platformBounds.right &&
                playerBounds.bottom > platformBounds.top &&
                playerBounds.top < platformBounds.bottom) {
                
                // Calculate overlap on each side
                const overlapLeft = playerBounds.right - platformBounds.left;
                const overlapRight = platformBounds.right - playerBounds.left;
                const overlapTop = playerBounds.bottom - platformBounds.top;
                const overlapBottom = platformBounds.bottom - playerBounds.top;
                
                // Find smallest overlap
                const minOverlap = Math.min(
                    overlapLeft, overlapRight, overlapTop, overlapBottom
                );
                
                // Resolve collision based on smallest overlap
                if (minOverlap === overlapLeft) {
                    // Collision from left
                    result.horizontal = true;
                    result.horizontalCorrection = platformBounds.left - this.width;
                } else if (minOverlap === overlapRight) {
                    // Collision from right
                    result.horizontal = true;
                    result.horizontalCorrection = platformBounds.right;
                } else if (minOverlap === overlapTop) {
                    // Collision from top (landing on platform)
                    result.vertical = true;
                    result.verticalCorrection = platformBounds.top - this.height;
                    result.grounded = true;
                } else if (minOverlap === overlapBottom) {
                    // Collision from bottom (hitting head)
                    result.vertical = true;
                    result.verticalCorrection = platformBounds.bottom;
                    this.velocityY = 0;
                }
            }
        }
        
        return result;
    }
    
    // Draw player on canvas context
    draw(ctx) {
        ctx.save();
        
        // Draw player body
        ctx.fillStyle = this.color;
        ctx.fillRect(this.x, this.y, this.width, this.height);
        
        // Draw player details
        ctx.fillStyle = '#2C5282';
        ctx.fillRect(this.x + 5, this.y + 5, this.width - 10, 10); // Eyes
        ctx.fillRect(this.x + this.width/2 - 5, this.y + this.height - 15, 10, 5); // Mouth
        
        // Draw shadow
        ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
        ctx.fillRect(this.x, this.y + this.height, this.width, 5);
        
        ctx.restore();
    }
    
    // Reset player to initial position
    reset(x, y) {
        this.x = x;
        this.y = y;
        this.velocityX = 0;
        this.velocityY = 0;
        this.grounded = false;
        this.isJumping = false;
    }
    
    // Get player bounds for external collision detection
    getBounds() {
        return {
            x: this.x,
            y: this.y,
            width: this.width,
            height: this.height,
            left: this.x,
            right: this.x + this.width,
            top: this.y,
            bottom: this.y + this.height
        };
    }
    
    // Check collision with another rectangle
    collidesWith(rect) {
        return this.x < rect.x + rect.width &&
               this.x + this.width > rect.x &&
               this.y < rect.y + rect.height &&
               this.y + this.height > rect.y;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Player;
}