import urllib3
import pygame
import sys
from pathlib import Path

# Initialize Pygame
pygame.init()
pygame.joystick.init()  # Initialize joystick module

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Screen settings
SCREEN_WIDTH = pygame.display.Info().current_w
SCREEN_HEIGHT = pygame.display.Info().current_h
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
FONT_SIZE = int(SCREEN_HEIGHT * 0.05)  # Scale font size based on screen height

class InfoScreen:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        pygame.display.set_caption("InfoScreen")
        self.font = pygame.font.Font(None, FONT_SIZE)
        self.clock = pygame.time.Clock()
        
        # Initialize joystick
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Joystick initialized: {self.joystick.get_name()}")
        
        # Create a gradient background
        self.background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(SCREEN_HEIGHT):
            # Create a smooth gradient from dark blue to darker blue
            color = (
                int(20 + (y / SCREEN_HEIGHT) * 10),  # R
                int(30 + (y / SCREEN_HEIGHT) * 20),  # G
                int(50 + (y / SCREEN_HEIGHT) * 30)   # B
            )
            pygame.draw.line(self.background, color, (0, y), (SCREEN_WIDTH, y))

    def show_message(self, message, duration=0, wait_for_button=None):
        # Draw the gradient background
        self.screen.blit(self.background, (0, 0))
        
        # Split message into multiple lines if it's too long
        words = message.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            if self.font.size(test_line)[0] > SCREEN_WIDTH * 0.8:  # 80% of screen width
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Calculate total height of all lines
        total_height = len(lines) * FONT_SIZE * 1.5
        start_y = (SCREEN_HEIGHT - total_height) / 2  # Center vertically
        
        # Render each line
        for i, line in enumerate(lines):
            text = self.font.render(line, True, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH/2, start_y + i * FONT_SIZE * 1.5))
            self.screen.blit(text, text_rect)
        
        pygame.display.flip()
        
        if wait_for_button is not None:
            waiting = True
            while waiting:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            pygame.quit()
                            sys.exit()
                    elif event.type == pygame.JOYBUTTONDOWN:
                        if event.button == wait_for_button:
                            waiting = False
                            return
                        
                self.clock.tick(60)  # Limit to 60 FPS while waiting
        elif duration > 0:
            pygame.time.wait(int(duration * 1000))
        else:
            pygame.time.wait(100)  # Small delay to prevent CPU overuse

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:  # Allow escape key to exit
                    pygame.quit()
                    sys.exit()
                    
    def quit(self):
        pygame.quit()