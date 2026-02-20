# 2048 Game

## Overview
2048 is a single-player sliding block puzzle game. The objective is to slide numbered tiles on a 4×4 grid to combine them, creating a tile with the number 2048. The game ends when there are no more valid moves available.

## How to Play
- Use the **arrow keys** (↑, ↓, ←, →) to slide all tiles in that direction.
- When two tiles with the same number touch, they **merge into one** with their sum.
- After each move, a new tile (either a 2 or 4) appears in a random empty cell.
- The game is won when you create a tile with the number **2048**.
- The game is lost when the board is full and no more merges are possible.

## Controls
- **Arrow Keys** – Move tiles in the corresponding direction.
- **R Key** – Restart the game at any time.
- **ESC Key** – Pause/resume the game (if implemented).

## Scoring
- Your score increases by the value of each new tile created by a merge.
- Example: Merging two 4 tiles creates an 8 tile and adds 8 points to your score.
- The maximum possible tile is 131072, though reaching 2048 is the primary goal.

## Strategy Tips
1. **Keep your highest tile in a corner** – This gives you more space to build chains.
2. **Plan several moves ahead** – Avoid filling up rows or columns unnecessarily.
3. **Use the arrow keys deliberately** – Random moves will quickly fill the board.
4. **Prioritize merging larger tiles** – This frees up space for new tiles.

## Development Notes
- Built with HTML5, CSS3, and vanilla JavaScript.
- The game grid is implemented as a 4×4 matrix.
- Tile movements use array manipulation and collision detection.
- Responsive design ensures playability on desktop and mobile devices.
- Future enhancements may include touch gestures, score history, and difficulty levels.

## Credits
Original concept by Gabriele Cirulli. This implementation is a learning project for web development.

## License
This project is open source and available under the MIT License.