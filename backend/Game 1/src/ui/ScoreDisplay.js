// ScoreDisplay.js - UI component for displaying and updating game score
class ScoreDisplay {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with id "${containerId}" not found`);
            return;
        }

        this.options = {
            initialScore: 0,
            scorePrefix: 'Cheese: ',
            scoreSuffix: '',
            showHighScore: true,
            highScoreLabel: 'High Score: ',
            animationDuration: 300,
            ...options
        };

        this.score = this.options.initialScore;
        this.highScore = this.loadHighScore();
        this.isAnimating = false;

        this.init();
    }

    init() {
        this.container.innerHTML = '';
        this.container.className = 'score-display-container';

        // Create score element
        this.scoreElement = document.createElement('div');
        this.scoreElement.className = 'score-value';
        this.scoreElement.textContent = `${this.options.scorePrefix}${this.score}${this.options.scoreSuffix}`;

        // Create high score element if enabled
        if (this.options.showHighScore) {
            this.highScoreElement = document.createElement('div');
            this.highScoreElement.className = 'high-score-value';
            this.highScoreElement.textContent = `${this.options.highScoreLabel}${this.highScore}`;
            this.container.appendChild(this.highScoreElement);
        }

        this.container.appendChild(this.scoreElement);
        this.applyStyles();
    }

    applyStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .score-display-container {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: #F9F9FB;
                border: 1px solid #EAECF0;
                border-radius: 12px;
                padding: 1rem 1.5rem;
                display: inline-flex;
                flex-direction: column;
                gap: 0.5rem;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
                min-width: 180px;
                transition: all 0.2s ease;
            }

            .score-value {
                font-size: clamp(1.5rem, 2.5vw, 2rem);
                font-weight: 700;
                color: #1A1A1A;
                line-height: 1.2;
                transition: transform 0.3s ease;
            }

            .high-score-value {
                font-size: clamp(0.875rem, 1.5vw, 1rem);
                color: #666;
                font-weight: 500;
                line-height: 1.4;
            }

            /* Animation for score updates */
            .score-value.score-update {
                transform: scale(1.1);
                color: #2E7D32;
            }

            /* Responsive adjustments */
            @media (max-width: 768px) {
                .score-display-container {
                    padding: 0.75rem 1rem;
                    min-width: 160px;
                }
                
                .score-value {
                    font-size: 1.75rem;
                }
            }

            @media (max-width: 480px) {
                .score-display-container {
                    padding: 0.5rem 0.75rem;
                    min-width: 140px;
                    gap: 0.25rem;
                }
                
                .score-value {
                    font-size: 1.5rem;
                }
                
                .high-score-value {
                    font-size: 0.8125rem;
                }
            }

            /* Tablet landscape */
            @media (min-width: 769px) and (max-width: 1024px) {
                .score-display-container {
                    padding: 1rem 1.25rem;
                }
            }
        `;

        // Only add style once
        if (!document.querySelector('style[data-score-display]')) {
            style.setAttribute('data-score-display', '');
            document.head.appendChild(style);
        }
    }

    updateScore(newScore) {
        if (typeof newScore !== 'number' || newScore < 0) {
            console.error('Invalid score value');
            return;
        }

        const oldScore = this.score;
        this.score = newScore;

        // Update high score if needed
        if (this.score > this.highScore) {
            this.highScore = this.score;
            this.saveHighScore(this.highScore);
            if (this.highScoreElement) {
                this.highScoreElement.textContent = `${this.options.highScoreLabel}${this.highScore}`;
            }
        }

        // Update display with animation
        this.animateScoreUpdate(oldScore);
    }

    animateScoreUpdate(oldScore) {
        if (this.isAnimating) return;

        this.isAnimating = true;
        this.scoreElement.classList.add('score-update');
        this.scoreElement.textContent = `${this.options.scorePrefix}${this.score}${this.options.scoreSuffix}`;

        setTimeout(() => {
            this.scoreElement.classList.remove('score-update');
            this.isAnimating = false;
        }, this.options.animationDuration);
    }

    incrementScore(amount = 1) {
        this.updateScore(this.score + amount);
    }

    resetScore() {
        this.score = this.options.initialScore;
        this.scoreElement.textContent = `${this.options.scorePrefix}${this.score}${this.options.scoreSuffix}`;
        this.scoreElement.classList.remove('score-update');
    }

    loadHighScore() {
        try {
            const saved = localStorage.getItem('cheeseGameHighScore');
            return saved ? parseInt(saved, 10) : 0;
        } catch (e) {
            console.warn('Could not load high score from localStorage');
            return 0;
        }
    }

    saveHighScore(score) {
        try {
            localStorage.setItem('cheeseGameHighScore', score.toString());
        } catch (e) {
            console.warn('Could not save high score to localStorage');
        }
    }

    getCurrentScore() {
        return this.score;
    }

    getHighScore() {
        return this.highScore;
    }

    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
            this.container.className = '';
        }
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ScoreDisplay;
}