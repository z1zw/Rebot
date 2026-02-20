# 2048 Game

## Overview
2048 is a single-player sliding block puzzle game where the player combines numbered tiles on a 4×4 grid to create a tile with the number 2048. The game is won when a 2048 tile appears on the board, though players can continue playing to achieve higher scores.

## How to Play
- The game starts with two tiles (either 2 or 4) placed randomly on the grid.
- Use the arrow keys (Up, Down, Left, Right) to slide all tiles in that direction.
- When two tiles with the same number collide while moving, they merge into a tile with the total value of the two tiles.
- After each move, a new tile (2 or 4) appears in a random empty spot on the board.
- The game ends when:
  - You create a tile with the number 2048 (you win!).
  - There are no more empty spaces and no possible merges (game over).

## Controls
- **Arrow Keys**: Slide tiles in the chosen direction.
- **R Key**: Restart the game at any time.
- **ESC Key**: Exit the game.

## Scoring
- Your score increases by the value of each new tile created by merging.
- Example: Merging two 4 tiles creates an 8 tile and adds 8 points to your score.
- The highest tile value achieved is also tracked.

## Development Notes
- **Language**: JavaScript (with HTML/CSS)
- **Grid**: 4×4 matrix implementation
- **Tile Generation**: Random placement of 2 (90% probability) or 4 (10% probability)
- **Movement Logic**: Four directional movement with collision detection and merging
- **Game State**: Win condition (2048 tile), lose condition (no valid moves)
- **UI**: Responsive design with smooth tile animations
- **Data Persistence**: Local storage for high score tracking

## Strategy Tips
1. Keep your highest tile in a corner (usually bottom-right).
2. Build chains of descending tiles along one edge.
3. Avoid filling the grid unnecessarily—plan moves to keep empty spaces.
4. Use all four directions strategically, not just one or two.

## Credits
Original game concept by Gabriele Cirulli (2014). This implementation is a web-based recreation for educational and entertainment purposes.

## License
Open-source project available for modification and distribution.