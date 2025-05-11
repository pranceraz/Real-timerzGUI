import pygame
import serial
import json
import threading

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Set up the display
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('ESP32 Rhythm Game')

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

# Clock for controlling frame rat   e
clock = pygame.time.Clock()
FPS = 60

SONG_PATH = 'tequila.mp3'

# Serial setup (adjust port as needed)
try:
    ser = serial.Serial('COM4', 115200, timeout=0)  # Adjust COM port as needed
    print("Serial connection established")
except serial.SerialException:
    print("Failed to open serial port. Check connection and port name.")
    ser = None

# Game states
MENU = 0
PLAYING = 1
game_state = MENU

# Global variables for storing data from ESP32
upcoming_inputs = []
input_results = []
serial_data = ""

# Import Button class
class Button:
    def __init__(self, x, y, width, height, text='Button', on_click_function=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.on_click_function = on_click_function
        
        self.normal_color = (100, 100, 100)
        self.hover_color = (150, 150, 150)
        self.pressed_color = (50, 50, 50)
        self.current_color = self.normal_color
        
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.font = pygame.font.SysFont('Arial', 24)
        
    def process(self, events):
        mouse_pos = pygame.mouse.get_pos()
        
        # Check hover
        if self.rect.collidepoint(mouse_pos):
            self.current_color = self.hover_color
            
            # Check click
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.current_color = self.pressed_color
                    if self.on_click_function:
                        self.on_click_function()
        else:
            self.current_color = self.normal_color
            
    def draw(self, surface):
        pygame.draw.rect(surface, self.current_color, self.rect)
        text_surface = self.font.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

def play_song():
    pygame.mixer.music.load(SONG_PATH)
    pygame.mixer.music.play()


# Start button function
def start_game():
    global game_state
    if ser:
        # Send start command to ESP32
        ser.write(b'START\n')
        game_state = PLAYING

        # Start music thread
        music_thread = threading.Thread(target=play_song, daemon=True)
        music_thread.start()
    else:
        print("Serial connection not available")


# Create start button
start_button = Button(WIDTH//2 - 100, HEIGHT//2 - 50, 200, 100, "START", start_game)

def read_from_serial():
    global serial_data, upcoming_inputs, input_results
    
    while True:
        if ser and ser.in_waiting > 0:
            data = ser.read(ser.in_waiting).decode('utf-8')
            serial_data += data
            
            if '\n' in serial_data:
                lines = serial_data.split('\n')
                serial_data = lines[-1]  # Keep incomplete line
                
                for line in lines[:-1]:
                    try:
                        message = json.loads(line)
                        if "upcoming_inputs" in message:
                            upcoming_inputs = message["upcoming_inputs"]
                        if "input_result" in message:
                            input_results.append(message["input_result"])
                    except json.JSONDecodeError:
                        pass  # Ignore invalid JSON


# Main game loop
def main_game():
    global game_state
    running = True
    
    # Start serial reading thread
    if ser:
        thread = threading.Thread(target=read_from_serial, daemon=True) 
        thread.start()

    while running:
        events = pygame.event.get()
        # Handle events
        for event in events:
            if event.type == pygame.QUIT:
                running = False
        
        # Clear screen
        screen.fill(BLACK)

        if game_state == MENU:
            # Draw title
            font = pygame.font.SysFont('Arial', 48)
            title = font.render("ESP32 Rhythm Game", True, WHITE)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//4))
            
            # Process and draw start button
            start_button.process(events)
            start_button.draw(screen)

        if game_state == PLAYING: 
            
            
        # Update display
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()

if __name__ == "__main__":
    main_game()
