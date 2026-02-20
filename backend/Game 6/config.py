"""
Cheese Game Configuration
Contains all constants for screen dimensions, colors, game parameters, and asset paths.
"""

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors (RGB tuples)
BACKGROUND_COLOR = (240, 240, 245)
GRID_COLOR = (220, 220, 230)
PLAYER_COLOR = (65, 105, 225)  # Royal Blue
CHEESE_COLOR = (255, 215, 0)   # Gold
ENEMY_COLOR = (220, 20, 60)    # Crimson Red
WALL_COLOR = (180, 180, 190)
TEXT_COLOR = (40, 40, 50)
UI_BACKGROUND = (250, 250, 252, 200)  # Semi-transparent
BUTTON_COLOR = (75, 130, 255)
BUTTON_HOVER_COLOR = (95, 150, 275)
BUTTON_TEXT_COLOR = (255, 255, 255)

# Game parameters
GRID_SIZE = 40
PLAYER_SIZE = 30
CHEESE_SIZE = 25
ENEMY_SIZE = 28
PLAYER_SPEED = 5
ENEMY_SPEED_MIN = 2
ENEMY_SPEED_MAX = 4
ENEMY_COUNT = 3
INITIAL_CHEESE_COUNT = 5
MAX_CHEESE_COUNT = 20
SCORE_PER_CHEESE = 100
LIVES_START = 3
LEVEL_UP_SCORE = 500

# Game states
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_GAME_OVER = "game_over"
STATE_WIN = "win"

# Font sizes
FONT_SMALL = 16
FONT_MEDIUM = 24
FONT_LARGE = 36
FONT_XLARGE = 48

# Asset paths (relative to game directory)
FONT_PATH = "assets/fonts/PressStart2P-Regular.ttf"
SOUND_CHEESE_PATH = "assets/sounds/cheese_collect.wav"
SOUND_HIT_PATH = "assets/sounds/hit.wav"
SOUND_WIN_PATH = "assets/sounds/win.wav"
SOUND_LOSE_PATH = "assets/sounds/lose.wav"
SOUND_BACKGROUND_PATH = "assets/sounds/background_music.mp3"

# UI dimensions
UI_PADDING = 20
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 50
BUTTON_SPACING = 15

# Game area boundaries (with margins for UI)
GAME_AREA_LEFT = 50
GAME_AREA_TOP = 100
GAME_AREA_RIGHT = SCREEN_WIDTH - 50
GAME_AREA_BOTTOM = SCREEN_HEIGHT - 50

# Animation parameters
ANIMATION_SPEED = 0.2
CHEESE_ROTATION_SPEED = 2
ENEMY_BLINK_DURATION = 0.5

# Difficulty scaling
DIFFICULTY_INCREMENT = 0.1
MAX_DIFFICULTY = 3.0

# Control keys (pygame key constants)
KEY_UP = 273    # Up arrow
KEY_DOWN = 274  # Down arrow
KEY_LEFT = 276  # Left arrow
KEY_RIGHT = 275 # Right arrow
KEY_RESTART = 114  # 'r' key
KEY_ESCAPE = 27   # ESC key
KEY_SPACE = 32    # Space bar

# Game version
VERSION = "1.0.0"

# Debug mode
DEBUG = False