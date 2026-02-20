// Score.js - Score management for 2048 game
class ScoreManager {
    constructor() {
        this.currentScore = 0;
        this.bestScore = this.loadBestScore();
    }

    // Load best score from localStorage
    loadBestScore() {
        const savedScore = localStorage.getItem('2048-best-score');
        return savedScore ? parseInt(savedScore, 10) : 0;
    }

    // Save best score to localStorage
    saveBestScore() {
        localStorage.setItem('2048-best-score', this.bestScore.toString());
    }

    // Add points to current score
    add(points) {
        this.currentScore += points;
        
        // Update best score if current exceeds it
        if (this.currentScore > this.bestScore) {
            this.bestScore = this.currentScore;
            this.saveBestScore();
        }
        
        return this.currentScore;
    }

    // Reset current score (keeps best score)
    reset() {
        this.currentScore = 0;
        return this.currentScore;
    }

    // Reset both current and best scores
    resetAll() {
        this.currentScore = 0;
        this.bestScore = 0;
        localStorage.removeItem('2048-best-score');
        return { current: this.currentScore, best: this.bestScore };
    }

    // Get current score
    getCurrent() {
        return this.currentScore;
    }

    // Get best score
    getBest() {
        return this.bestScore;
    }

    // Update scores from external source (e.g., game state load)
    updateScores(current, best) {
        this.currentScore = current || 0;
        this.bestScore = best || this.loadBestScore();
        
        // Ensure best score is saved if provided
        if (best !== undefined && best > this.loadBestScore()) {
            this.saveBestScore();
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ScoreManager;
}