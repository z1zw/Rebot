# Cheese Game

A fun and interactive browser-based game where you collect cheese while avoiding obstacles. Built with HTML5, CSS3, and vanilla JavaScript.

## Game Overview

You control a mouse character that must collect as much cheese as possible while avoiding dangerous traps. The game features dynamic difficulty progression, score tracking, and responsive controls for both desktop and mobile devices.

## How to Play

### Objective
- Collect yellow cheese pieces to increase your score
- Avoid red traps that will end your game
- Survive as long as possible to achieve high scores

### Controls

**Desktop:**
- **Arrow Keys** or **WASD**: Move the mouse character
- **Spacebar**: Pause/Resume game
- **R**: Restart game after game over
- **ESC**: Return to main menu

**Mobile/Touch:**
- **On-screen D-pad**: Tap directional buttons to move
- **Pause Button**: Tap to pause/resume
- **Restart Button**: Tap to restart after game over

### Game Elements
- 🐭 **Mouse Player**: Your character (gray circle)
- 🧀 **Cheese**: Collectible items (+10 points, yellow squares)
- ⚠️ **Traps**: Avoid these obstacles (red squares)
- 📊 **Score Display**: Current score and high score
- ⏱️ **Timer**: Game duration

## Setup and Running

### Quick Start
1. Download or clone the repository
2. Open `index.html` in any modern web browser
3. The game will start automatically

### No Installation Required
This game runs entirely in the browser with no:
- Server requirements
- Package installations
- Build steps
- External dependencies

### Browser Compatibility
- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+
- Mobile Safari (iOS 11+)
- Chrome for Android

## Game Features

### Complete Game Logic
- Smooth 60 FPS game loop using `requestAnimationFrame`
- Collision detection for cheese collection and trap avoidance
- Progressive difficulty (speed increases with score)
- Random item generation with boundary constraints
- Score persistence using localStorage

### Responsive Design
- Adapts to desktop, tablet, and mobile screens
- Touch-friendly controls for mobile devices
- Flexible layout using CSS Grid and Flexbox
- Relative units (rem, vw, vh) for consistent scaling

### User Experience
- Visual feedback for all interactions
- Smooth animations and transitions
- Clear game states (playing, paused, game over)
- High score tracking
- Intuitive controls with on-screen instructions

## File Structure

```
CheeseGame/
├── index.html          # Main game file (contains all code)
└── README.md           # This instructions file
```

The game is contained within a single HTML file with embedded CSS and JavaScript for portability.

## Game States

1. **Main Menu**: Initial screen with game instructions
2. **Playing**: Active gameplay with score tracking
3. **Paused**: Game temporarily stopped
4. **Game Over**: Player hit a trap, shows final score
5. **High Scores**: View best performances

## Scoring System

- **Cheese Collected**: +10 points each
- **Time Bonus**: +1 point per second survived
- **High Score**: Automatically saved between sessions
- **Difficulty Multiplier**: Score rate increases with game duration

## Tips for Success

1. **Plan Your Route**: Look ahead to avoid getting trapped
2. **Prioritize Safety**: Sometimes it's better to avoid cheese than risk a trap
3. **Use the Whole Area**: Traps spawn randomly, so keep moving
4. **Watch the Timer**: Game speed increases over time
5. **Practice Controls**: Get comfortable with both keyboard and touch controls

## Troubleshooting

### Game Won't Start
- Ensure JavaScript is enabled in your browser
- Try refreshing the page (F5 or Ctrl+R)
- Check browser console for errors (F12)

### Controls Not Working
- Click on the game area first to ensure focus
- For mobile: ensure you're not zoomed in too far
- Try both control methods (keyboard and on-screen)

### Performance Issues
- Close other browser tabs
- Update your browser to latest version
- Ensure adequate system resources

## Development Notes

The game is built with:
- **HTML5**: Semantic structure and canvas-free rendering
- **CSS3**: Flexbox, Grid, CSS variables, and animations
- **Vanilla JavaScript**: No frameworks or libraries
- **Modern Web APIs**: localStorage, requestAnimationFrame, touch events

All code is contained within a single file for easy distribution and runs entirely client-side.

## License

Free to play, modify, and distribute. Created for educational and entertainment purposes.

## Support

For issues or suggestions:
1. Check the browser console for error messages
2. Ensure you're using a supported browser version
3. Refresh the page to reset game state

Enjoy the game! 🧀🐭