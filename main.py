import pygame
import serial
import json
import threading

# For button
WIDTH, HEIGHT = 800, 600

NUM_LANES = 4
LANE_WIDTH = WIDTH // NUM_LANES
NOTE_WIDTH = LANE_WIDTH - 20
NOTE_HEIGHT = 20
NOTE_SPEED = 300  # Pixels per second (tweak based on hit timing)
BPM = 120
BEAT_INTERVAL = 60 / BPM  # Seconds per beat

COM_PORT = 'COM4'

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

FPS = 60
SONG_PATH = 'songs/tequila.mp3'

# Game states
MENU = 0
PLAYING = 1

tequila_beat_vals = [
    15, 15, 15, 15,
    15, 15, 15, 15,
    15, 15, 15, 15,
    15, 15, 15, 15,
    12, 3, 12, 3,
    12, 3, 12, 3,
    12, 3, 12, 3,
    12, 3, 12, 3,
    8, 4, 2, 14,
    8, 4, 2,
    8, 4, 2, 14,
    8, 4, 2,
    8, 4, 2, 14,
    8, 4, 2,
    8, 4, 2, 14,
    8, 4, 2,
    8, 8, 4, 4,
    8, 4, 2, 2,
    1, 1, 12, 3,
    15
]

# Bitmask to lane mapping (pointer = lane 0, pinky = lane 3)
def bitmask_to_lanes(val):
    return [i for i, bit in enumerate([8, 4, 2, 1]) if val & bit]

note_pattern = [(i, bitmask_to_lanes(tequila_beat_vals[i])) for i in range(len(tequila_beat_vals))]

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Set up the display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('ESP32 Rhythm Game')

# Clock for controlling frame rat   e
clock = pygame.time.Clock()

# Serial setup (adjust port as needed)
try:
    ser = serial.Serial(COM_PORT, 115200, timeout=0)  # Adjust COM port as needed
    print("Serial connection established")
except serial.SerialException:
    print("Failed to open serial port. Check connection and port name.")
    ser = None

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

class Note:
    def __init__(self, lane, spawn_time):
        self.lane = lane
        self.spawn_time = spawn_time
        self.x = lane * LANE_WIDTH + 10
        self.y = -NOTE_HEIGHT  # Start offscreen
        self.hit = False

    def update(self, delta_time):
        self.y += NOTE_SPEED * delta_time

    def draw(self, surface):
        pygame.draw.rect(surface, GREEN, (self.x, self.y, NOTE_WIDTH, NOTE_HEIGHT))

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
    start_time = None
    notes = []
    current_note_index = 0
    
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
            if start_time is None:
                start_time = pygame.time.get_ticks() / 1000.0  # Convert to seconds

            current_time = pygame.time.get_ticks() / 1000.0 - start_time

            # Spawn notes at the right time
            while (current_note_index < len(note_pattern) and
                current_time >= note_pattern[current_note_index][0] * BEAT_INTERVAL):
                
                beat, lanes = note_pattern[current_note_index]
                
                for lane in lanes:
                    notes.append(Note(lane, current_time))  # lane is now correctly an int
                
                current_note_index += 1


            # Update and draw notes
            delta_time = clock.get_time() / 1000.0
            for note in notes:
                note.update(delta_time)
                note.draw(screen)

            # Draw hit line
            pygame.draw.line(screen, RED, (0, HEIGHT - 100), (WIDTH, HEIGHT - 100), 5)

            
            
        # Update display
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()

if __name__ == "__main__":
    main_game()
