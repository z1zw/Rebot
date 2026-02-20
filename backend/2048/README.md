# 2048 Game

## Overview
A browser-based implementation of the popular 2048 puzzle game. Combine numbered tiles to reach the elusive 2048 tile!

## How to Play
- **Objective**: Slide numbered tiles on a 4×4 grid to combine them and create a tile with the number 2048.
- **Gameplay**: Tiles with the same number merge into one when they collide. After each move, a new tile (either 2 or 4) appears in a random empty cell.
- **Game Over**: The game ends when no more moves are possible (grid is full and no adjacent tiles can merge).

## Controls
- **Arrow Keys** (↑, ↓, ←, →): Slide tiles in the corresponding direction
- **Touch Swipe** (Mobile/Tablet): Swipe in any direction to move tiles
- **R Key**: Restart the game at any time

## Scoring
- Each merge adds the value of the new tile to your score
- Example: Merging two 4 tiles creates an 8 tile and adds 8 points to your score
- Try to achieve the highest possible score!

## Development Notes
- Built with vanilla JavaScript, HTML5, and CSS3
- Responsive design works on desktop, tablet, and mobile devices
- No external dependencies or libraries required
- Game state is preserved during the same session (refreshing the page resets the game)
- The game follows the original 2048 mechanics created by Gabriele Cirulli

## Tips & Strategies
1. Keep your highest-value tile in a corner (usually bottom-right)
2. Try to build chains of descending values along one edge
3. Avoid filling the grid unnecessarily - plan moves ahead
4. Use all four directions strategically, not just one or two

## Browser Compatibility
Works on all modern browsers including:
- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+

## License
This implementation is for educational purposes. The original 2048 game concept was created by Gabriele Cirulli.

---
*Enjoy the game! Try to beat your high score!*