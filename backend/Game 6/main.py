import pygame
import sys
from game import Game

def main():
    # Initialize pygame
    pygame.init()
    
    # Set up game window
    screen_width = 800
    screen_height = 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Cheese Game")
    
    # Create game instance
    game = Game(screen_width, screen_height)
    
    # Set up clock for controlling frame rate
    clock = pygame.time.Clock()
    fps = 60
    
    # Main game loop
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r and game.game_over:
                    # Restart game if R is pressed and game is over
                    game = Game(screen_width, screen_height)
            
            # Pass event to game for handling
            game.handle_event(event)
        
        # Update game state
        game.update()
        
        # Draw everything
        screen.fill((30, 30, 40))  # Dark blue background
        game.draw(screen)
        
        # Update display
        pygame.display.flip()
        
        # Control frame rate
        clock.tick(fps)
    
    # Clean up and quit
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()