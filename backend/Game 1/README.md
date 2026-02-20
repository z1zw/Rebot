# Cheese Game

A simple, responsive browser game where you guide a mouse to collect cheese while avoiding obstacles.

## Setup

1. Clone or download this project to your local machine.
2. Ensure all files are in the same directory:
   - `index.html`
   - `style.css`
   - `script.js`
3. Open `index.html` in any modern web browser (Chrome, Firefox, Edge, Safari).

No additional dependencies, installation, or build steps required.

## Gameplay

### Objective
Guide the mouse (🐭) to collect all cheese pieces (🧀) on the game board while avoiding obstacles (🪨). Collect all cheese to win the game.

### Controls
- **Arrow Keys** (↑, ↓, ←, →) or **WASD** keys to move the mouse
- **R** key to restart the current level
- **N** key to advance to the next level (when available)

### Game Elements
- **🐭 Mouse**: Player character, moves one tile per keypress
- **🧀 Cheese**: Collectible items, need to collect all to win
- **🪨 Obstacles**: Block movement, game restarts if mouse touches them
- **🟩 Grass**: Safe tiles for movement

### Levels
The game includes multiple levels of increasing difficulty with more obstacles and cheese pieces. Complete each level to unlock the next.

## Features

- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Progressive Difficulty**: 5 levels with increasing complexity
- **Visual Feedback**: Clear indicators for game state (playing, won, game over)
- **Keyboard Controls**: Intuitive arrow/WASD controls
- **Restart Functionality**: Quick restart with R key
- **Score Tracking**: Tracks cheese collected and moves made

## Browser Compatibility

Works on all modern browsers with JavaScript enabled:
- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+

## Project Structure

```
CheeseGame/
├── index.html      # Main HTML file
├── style.css       # Styling and responsive design
├── script.js       # Game logic and controls
└── README.md       # This file
```

## Development

This is a standalone web game using vanilla JavaScript, HTML5, and CSS3. No frameworks or libraries are required.

### Key Technical Aspects:
- **Grid-based movement**: Game board is a CSS Grid layout
- **Event-driven controls**: Keyboard events for player input
- **Responsive CSS**: Flexbox, Grid, and relative units for all layouts
- **State management**: JavaScript objects track game state
- **Modular design**: Separate concerns for UI, logic, and data

## License

Free for educational and personal use.

## Troubleshooting

If the game doesn't work:
1. Ensure JavaScript is enabled in your browser
2. Check that all files are in the same directory
3. Try refreshing the page (F5)
4. Clear browser cache if experiencing display issues

Enjoy the game!