# Cheese Game - README

## Overview
Cheese Game is a simple, interactive browser-based game where players collect cheese while avoiding obstacles. The game features responsive design, smooth animations, and complete game logic including scoring, win/lose conditions, and restart functionality.

## Game Instructions
1. **Objective**: Collect as many cheese pieces as possible while avoiding obstacles.
2. **Controls**:
   - **Desktop**: Use arrow keys (↑, ↓, ←, →) or WASD keys to move the player character
   - **Mobile/Touch**: Tap or swipe in the direction you want to move
3. **Game Elements**:
   - **Player**: Yellow circle that you control
   - **Cheese**: Orange squares that increase your score when collected
   - **Obstacles**: Red squares that end the game if touched
4. **Scoring**: Each cheese collected adds 10 points to your score
5. **Game Over**: The game ends when you touch an obstacle or collect all cheese pieces

## Setup Guide
1. **Prerequisites**: A modern web browser (Chrome, Firefox, Safari, Edge)
2. **Installation**: No installation required - simply open `index.html` in your browser
3. **Running the Game**:
   - Double-click `index.html` to open in your default browser
   - Or right-click and select "Open with" to choose a specific browser
4. **File Structure**:
   ```
   CheeseGame/
   ├── index.html      # Main game file
   └── README.md       # This file
   ```

## Game Features
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Complete Game Loop**: Smooth animations using requestAnimationFrame
- **Input Handling**: Keyboard, mouse, and touch controls
- **Score Tracking**: Real-time score display
- **Win/Lose Conditions**: Clear game over states
- **Restart Functionality**: One-click game restart
- **Visual Feedback**: Animations and sound effects (where supported)

## Controls in Detail
- **Movement**: Arrow keys or WASD for precise control
- **Touch Controls**: On mobile, tap near the player to move in that direction
- **Restart**: Click the "Restart Game" button after game over
- **Pause**: Click anywhere on the game screen to pause/resume

## Technical Details
- **Framework**: Pure HTML5, CSS3, and JavaScript (no external dependencies)
- **Graphics**: Canvas-based rendering for smooth performance
- **Responsive Units**: Uses vw, vh, %, and rem for flexible layouts
- **Event Handling**: Comprehensive event listeners for all interactions
- **Game Loop**: Optimized requestAnimationFrame implementation
- **State Management**: Complete game state tracking and management

## Troubleshooting
1. **Game not loading**: Ensure JavaScript is enabled in your browser
2. **Controls not working**: Check if another application is capturing keyboard input
3. **Poor performance**: Close other tabs or applications to free up system resources
4. **Display issues**: Refresh the page (F5) to reset the game

## Development Notes
The game is built with:
- Vanilla JavaScript for maximum compatibility
- CSS Grid and Flexbox for responsive layouts
- Canvas API for game rendering
- Modern ES6+ JavaScript features
- Mobile-first responsive design approach

## License
This game is provided for educational and entertainment purposes. Feel free to modify and distribute as needed.

## Support
For issues or questions, check the game controls and ensure your browser is up to date. The game is designed to work on all modern browsers without additional plugins or extensions.

Enjoy playing the Cheese Game!