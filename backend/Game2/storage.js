// Local storage keys
const STORAGE_KEYS = {
    HIGH_SCORE: '2048_high_score',
    GAME_STATE: '2048_game_state',
    STATS: '2048_stats'
};

// Default statistics
const DEFAULT_STATS = {
    gamesPlayed: 0,
    totalScore: 0,
    highestTile: 0,
    moves: 0
};

/**
 * Save high score to local storage
 * @param {number} score - The score to save
 */
export function saveHighScore(score) {
    const currentHighScore = getHighScore();
    if (score > currentHighScore) {
        localStorage.setItem(STORAGE_KEYS.HIGH_SCORE, score.toString());
    }
}

/**
 * Get high score from local storage
 * @returns {number} The high score
 */
export function getHighScore() {
    const score = localStorage.getItem(STORAGE_KEYS.HIGH_SCORE);
    return score ? parseInt(score, 10) : 0;
}

/**
 * Save game state to local storage
 * @param {Object} gameState - The game state object
 */
export function saveGameState(gameState) {
    try {
        const stateToSave = {
            grid: gameState.grid,
            score: gameState.score,
            gameOver: gameState.gameOver,
            won: gameState.won,
            timestamp: Date.now()
        };
        localStorage.setItem(STORAGE_KEYS.GAME_STATE, JSON.stringify(stateToSave));
    } catch (error) {
        console.error('Failed to save game state:', error);
    }
}

/**
 * Load game state from local storage
 * @returns {Object|null} The saved game state or null if not found/expired
 */
export function loadGameState() {
    try {
        const savedState = localStorage.getItem(STORAGE_KEYS.GAME_STATE);
        if (!savedState) return null;

        const state = JSON.parse(savedState);
        
        // Check if state is older than 24 hours
        const TWENTY_FOUR_HOURS = 24 * 60 * 60 * 1000;
        if (Date.now() - state.timestamp > TWENTY_FOUR_HOURS) {
            clearGameState();
            return null;
        }

        return state;
    } catch (error) {
        console.error('Failed to load game state:', error);
        clearGameState();
        return null;
    }
}

/**
 * Clear saved game state from local storage
 */
export function clearGameState() {
    localStorage.removeItem(STORAGE_KEYS.GAME_STATE);
}

/**
 * Update game statistics
 * @param {Object} stats - Statistics from completed game
 */
export function updateStats(stats) {
    try {
        const savedStats = getStats();
        
        const updatedStats = {
            gamesPlayed: savedStats.gamesPlayed + 1,
            totalScore: savedStats.totalScore + stats.score,
            highestTile: Math.max(savedStats.highestTile, stats.highestTile),
            moves: savedStats.moves + stats.moves
        };

        localStorage.setItem(STORAGE_KEYS.STATS, JSON.stringify(updatedStats));
    } catch (error) {
        console.error('Failed to update stats:', error);
    }
}

/**
 * Get game statistics
 * @returns {Object} Game statistics
 */
export function getStats() {
    try {
        const stats = localStorage.getItem(STORAGE_KEYS.STATS);
        return stats ? JSON.parse(stats) : { ...DEFAULT_STATS };
    } catch (error) {
        console.error('Failed to get stats:', error);
        return { ...DEFAULT_STATS };
    }
}

/**
 * Clear all game data from local storage
 */
export function clearAllData() {
    localStorage.removeItem(STORAGE_KEYS.HIGH_SCORE);
    localStorage.removeItem(STORAGE_KEYS.GAME_STATE);
    localStorage.removeItem(STORAGE_KEYS.STATS);
}

/**
 * Check if local storage is available
 * @returns {boolean} True if local storage is available
 */
export function isStorageAvailable() {
    try {
        const testKey = '__storage_test__';
        localStorage.setItem(testKey, testKey);
        localStorage.removeItem(testKey);
        return true;
    } catch (error) {
        return false;
    }
}