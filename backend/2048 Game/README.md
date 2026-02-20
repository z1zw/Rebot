# 2048 Game

## Overview
2048 is a single-player sliding block puzzle game where players combine numbered tiles on a 4×4 grid to create a tile with the number 2048. The game is won when a tile with a value of 2048 appears on the board, though players can continue playing to achieve higher scores.

## Game Instructions

### Objective
- Combine tiles with the same number to create a tile with the number 2048.
- Each move slides all tiles on the grid in the chosen direction (up, down, left, or right).
- When two tiles with the same number collide while moving, they merge into a tile with the total value of the two tiles.
- After each move, a new tile (either a 2 or 4) appears in a random empty cell.
- The game ends when there are no more valid moves (the grid is full and no adjacent tiles can merge).

### Scoring
- Your score increases by the value of each new tile created by merging.
- Example: Merging two 4 tiles creates an 8 tile, adding 8 points to your score.

## Controls
- **Arrow Keys** (↑, ↓, ←, →) – Slide tiles in the corresponding direction.
- **W, A, S, D Keys** – Alternative controls for up, left, down, and right respectively.
- **R Key** – Restart the game at any time.
- **ESC Key** – Pause the game or bring up the menu.

## Setup Guide

### Prerequisites
- A modern web browser (Chrome, Firefox, Safari, Edge, etc.)
- No additional software or plugins required.

### Installation
1. Download or clone the project files to your local machine.
2. Ensure all files (index.html, style.css, script.js, and any assets) are in the same directory.
3. Open `index.html` in your web browser.
4. The game will load automatically and be ready to play.

### How to Play
1. Use the arrow keys or WASD keys to move the tiles.
2. Plan your moves to combine tiles strategically.
3. Try to keep the highest-value tile in a corner for better control.
4. Avoid filling the grid randomly; think ahead to create merging opportunities.
5. Press R to restart if you get stuck or want to try again.

## Game Features
- Clean, responsive interface that works on desktop and mobile devices.
- Score tracking and best score saved locally.
- Smooth animations for tile movements and merges.
- Game state saved automatically, so you can resume later.
- Win/loss detection with appropriate messages.

## Tips and Strategies
- **Corner Strategy:** Keep your highest tile in one corner and build descending values away from it.
- **Row/Column Management:** Try to keep one row or column non‑merged to use as a “buffer.”
- **Avoid the Up Arrow (or W) Early:** Moving up often creates disorganized tiles; focus on horizontal moves first.
- **Plan Merges:** Look ahead to set up chains of merges rather than moving randomly.

## Troubleshooting
- If the game does not load, check that all files are present and the browser supports JavaScript.
- If controls are unresponsive, ensure the browser window is active and no other extensions are interfering.
- Clear your browser’s local storage if the saved score seems incorrect.

## Credits
Original game concept by Gabriele Cirulli.  
This implementation is a web‑based clone created for educational and entertainment purposes.

Enjoy the game!