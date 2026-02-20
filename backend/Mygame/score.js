// Score management system for Cheese Game
// Handles score tracking, level progression, and high score storage

class ScoreManager {
    constructor() {
        this.currentScore = 0;
        this.currentLevel = 1;
        this.highScore = this.loadHighScore();
        this.scoreMultiplier = 1;
        this.levelThreshold = 1000; // Points needed to level up
        this.levelUpSound = null;
        this.highScoreSound = null;
    }

    // Initialize audio for score events
    initAudio() {
        // Create audio context for sound effects
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                const audioContext = new AudioContext();
                
                // Level up sound
                this.levelUpSound = () => {
                    const oscillator = audioContext.createOscillator();
                    const gainNode = audioContext.createGain();
                    
                    oscillator.connect(gainNode);
                    gainNode.connect(audioContext.destination);
                    
                    oscillator.frequency.setValueAtTime(523.25, audioContext.currentTime); // C5
                    oscillator.frequency.setValueAtTime(659.25, audioContext.currentTime + 0.1); // E5
                    oscillator.frequency.setValueAtTime(783.99, audioContext.currentTime + 0.2); // G5
                    
                    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
                    
                    oscillator.start();
                    oscillator.stop(audioContext.currentTime + 0.3);
                };

                // High score sound
                this.highScoreSound = () => {
                    const oscillator = audioContext.createOscillator();
                    const gainNode = audioContext.createGain();
                    
                    oscillator.connect(gainNode);
                    gainNode.connect(audioContext.destination);
                    
                    oscillator.frequency.setValueAtTime(783.99, audioContext.currentTime); // G5
                    oscillator.frequency.setValueAtTime(1046.50, audioContext.currentTime + 0.1); // C6
                    oscillator.frequency.setValueAtTime(1318.51, audioContext.currentTime + 0.2); // E6
                    oscillator.frequency.setValueAtTime(1567.98, audioContext.currentTime + 0.3); // G6
                    
                    gainNode.gain.setValueAtTime(0.4, audioContext.currentTime);
                    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.4);
                    
                    oscillator.start();
                    oscillator.stop(audioContext.currentTime + 0.4);
                };
            }
        } catch (error) {
            console.log("Audio context not supported, continuing without sound effects");
        }
    }

    // Load high score from localStorage
    loadHighScore() {
        const savedHighScore = localStorage.getItem('cheeseGameHighScore');
        return savedHighScore ? parseInt(savedHighScore, 10) : 0;
    }

    // Save high score to localStorage
    saveHighScore() {
        localStorage.setItem('cheeseGameHighScore', this.highScore.toString());
    }

    // Add points to current score
    addPoints(points) {
        const actualPoints = Math.floor(points * this.scoreMultiplier);
        this.currentScore += actualPoints;
        
        // Check for high score
        const wasHighScore = this.currentScore > this.highScore;
        if (wasHighScore) {
            this.highScore = this.currentScore;
            this.saveHighScore();
            
            // Play high score sound if available
            if (this.highScoreSound) {
                this.highScoreSound();
            }
        }
        
        // Check for level up
        const oldLevel = this.currentLevel;
        const newLevel = Math.floor(this.currentScore / this.levelThreshold) + 1;
        
        if (newLevel > this.currentLevel) {
            this.currentLevel = newLevel;
            this.scoreMultiplier = 1 + (this.currentLevel * 0.1); // 10% multiplier increase per level
            
            // Play level up sound if available
            if (this.levelUpSound) {
                this.levelUpSound();
            }
            
            return {
                points: actualPoints,
                levelUp: true,
                oldLevel: oldLevel,
                newLevel: this.currentLevel,
                multiplier: this.scoreMultiplier,
                highScore: wasHighScore
            };
        }
        
        return {
            points: actualPoints,
            levelUp: false,
            highScore: wasHighScore
        };
    }

    // Reset score for new game
    reset() {
        this.currentScore = 0;
        this.currentLevel = 1;
        this.scoreMultiplier = 1;
    }

    // Get current score
    getScore() {
        return this.currentScore;
    }

    // Get current level
    getLevel() {
        return this.currentLevel;
    }

    // Get high score
    getHighScore() {
        return this.highScore;
    }

    // Get score multiplier
    getMultiplier() {
        return this.scoreMultiplier;
    }

    // Get points needed for next level
    getPointsToNextLevel() {
        const pointsForNextLevel = this.currentLevel * this.levelThreshold;
        return Math.max(0, pointsForNextLevel - this.currentScore);
    }

    // Get progress to next level (0 to 1)
    getLevelProgress() {
        const pointsInCurrentLevel = this.currentScore % this.levelThreshold;
        return pointsInCurrentLevel / this.levelThreshold;
    }

    // Format score with commas
    formatScore(score) {
        return score.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    // Export score data for saving/loading game state
    exportState() {
        return {
            currentScore: this.currentScore,
            currentLevel: this.currentLevel,
            highScore: this.highScore,
            scoreMultiplier: this.scoreMultiplier
        };
    }

    // Import score data from saved game state
    importState(state) {
        if (state && typeof state === 'object') {
            this.currentScore = state.currentScore || 0;
            this.currentLevel = state.currentLevel || 1;
            this.highScore = Math.max(state.highScore || 0, this.loadHighScore());
            this.scoreMultiplier = state.scoreMultiplier || 1;
            this.saveHighScore();
        }
    }

    // Update UI elements with current score information
    updateUI(scoreElement, levelElement, highScoreElement, progressElement) {
        if (scoreElement) {
            scoreElement.textContent = this.formatScore(this.currentScore);
            scoreElement.setAttribute('data-score', this.currentScore);
        }
        
        if (levelElement) {
            levelElement.textContent = `Level ${this.currentLevel}`;
            levelElement.setAttribute('data-level', this.currentLevel);
        }
        
        if (highScoreElement) {
            highScoreElement.textContent = `High Score: ${this.formatScore(this.highScore)}`;
            highScoreElement.setAttribute('data-high-score', this.highScore);
        }
        
        if (progressElement && progressElement.style) {
            const progress = this.getLevelProgress();
            progressElement.style.width = `${progress * 100}%`;
            progressElement.setAttribute('data-progress', progress.toFixed(2));
        }
    }

    // Create score display HTML
    createScoreDisplay() {
        const container = document.createElement('div');
        container.className = 'score-display';
        container.innerHTML = `
            <div class="score-section">
                <div class="score-label">SCORE</div>
                <div class="score-value" id="currentScore">0</div>
            </div>
            <div class="level-section">
                <div class="level-label">LEVEL</div>
                <div class="level-value" id="currentLevel">1</div>
                <div class="level-progress">
                    <div class="level-progress-bar" id="levelProgress"></div>
                </div>
            </div>
            <div class="high-score-section">
                <div class="high-score-label">HIGH SCORE</div>
                <div class="high-score-value" id="highScore">0</div>
            </div>
            <div class="multiplier-section">
                <div class="multiplier-label">MULTIPLIER</div>
                <div class="multiplier-value" id="scoreMultiplier">1.0x</div>
            </div>
        `;
        
        // Add CSS for score display
        if (!document.querySelector('#score-styles')) {
            const style = document.createElement('style');
            style.id = 'score-styles';
            style.textContent = `
                .score-display {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                    background: linear-gradient(135deg, #F9F9FB 0%, #F2F2F5 100%);
                    border-radius: 12px;
                    padding: 1.5rem;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.1);
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 1.5rem;
                    max-width: 600px;
                    margin: 0 auto;
                    border: 1px solid #EAECF0;
                }
                
                .score-section, .level-section, .high-score-section, .multiplier-section {
                    text-align: center;
                }
                
                .score-label, .level-label, .high-score-label, .multiplier-label {
                    font-size: 0.875rem;
                    font-weight: 600;
                    color: #667085;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    margin-bottom: 0.5rem;
                }
                
                .score-value, .level-value, .high-score-value, .multiplier-value {
                    font-size: 2rem;
                    font-weight: 700;
                    color: #1D2939;
                    line-height: 1;
                }
                
                .level-progress {
                    height: 4px;
                    background: #EAECF0;
                    border-radius: 2px;
                    margin-top: 0.75rem;
                    overflow: hidden;
                }
                
                .level-progress-bar {
                    height: 100%;
                    background: linear-gradient(90deg, #7F56D9 0%, #9E77ED 100%);
                    border-radius: 2px;
                    width: 0%;
                    transition: width 0.3s ease;
                }
                
                .multiplier-value {
                    color: #7F56D9;
                }
                
                @media (max-width: 768px) {
                    .score-display {
                        grid-template-columns: 1fr;
                        gap: 1rem;
                        padding: 1rem;
                    }
                    
                    .score-value, .level-value, .high-score-value, .multiplier-value {
                        font-size: 1.75rem;
                    }
                }
                
                @media (max-width: 480px) {
                    .score-display {
                        border-radius: 8px;
                    }
                    
                    .score-value, .level-value, .high-score-value, .multiplier-value {
                        font-size: 1.5rem;
                    }
                    
                    .score-label, .level-label, .high-score-label, .multiplier-label {
                        font-size: 0.75rem;
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        return container;
    }

    // Initialize score display and update it
    initScoreDisplay(container) {
        const scoreDisplay = this.createScoreDisplay();
        if (container) {
            container.appendChild(scoreDisplay);
        }
        
        // Update display with current values
        this.updateUI(
            scoreDisplay.querySelector('#currentScore'),
            scoreDisplay.querySelector('#currentLevel'),
            scoreDisplay.querySelector('#highScore'),
            scoreDisplay.querySelector('#levelProgress')
        );
        
        // Update multiplier display
        const multiplierElement = scoreDisplay.querySelector('#scoreMultiplier');
        if (multiplierElement) {
            multiplierElement.textContent = `${this.scoreMultiplier.toFixed(1)}x`;
        }
        
        return scoreDisplay;
    }

    // Add animation for score changes
    animateScoreChange(element, oldValue, newValue) {
        if (!element) return;
        
        element.style.transform = 'scale(1.1)';
        element.style.color = '#7F56D9';
        
        setTimeout(() => {
            element.style.transform = 'scale(1)';
            element.style.color = '';
        }, 300);
    }

    // Add animation for level up
    animateLevelUp(element) {
        if (!element) return;
        
        const originalText = element.textContent;
        element.textContent = 'LEVEL UP!';
        element.style.color = '#7F56D9';
        element.style.fontWeight = '800';
        
        setTimeout(() => {
            element.textContent = originalText;
            element.style.color = '';
            element.style.fontWeight = '';
        }, 1000);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ScoreManager;
}

// Initialize global score manager instance
window.cheeseGameScoreManager = new ScoreManager();

// Auto-initialize audio when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.cheeseGameScoreManager.initAudio();
    });
} else {
    window.cheeseGameScoreManager.initAudio();
}