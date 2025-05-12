import pygame
import serial
import threading
import random
from button import Button

# For button
WIDTH, HEIGHT = 1280, 720

NUM_LANES = 4
LANE_WIDTH = WIDTH // NUM_LANES
NOTE_WIDTH = LANE_WIDTH - 20
NOTE_HEIGHT = 10  # The height of the note
SPAWN_OFFSET = 500
BPM = 91
BEAT_INTERVAL = 60 / BPM  # Seconds per beat
distance_per_beat = 140  # Distance the note falls per beat in pixels
NOTE_SPEED = distance_per_beat / BEAT_INTERVAL  # Pixels per second based on BPM

#was distance_per_beat / BEAT_INTERVAL before, should be * for speed)
# Corrected NOTE_SPEED calculation: If a note falls distance_per_beat in BEAT_INTERVAL seconds,
# then NOTE_SPEED = distance_per_beat / BEAT_INTERVAL.
# Let's re-evaluate:
# distance_per_beat = NOTE_SPEED * BEAT_INTERVAL
# So, NOTE_SPEED = distance_per_beat / BEAT_INTERVAL.
# The original code had NOTE_SPEED = distance_per_beat * BEAT_INTERVAL which would be (pixels/beat) * (seconds/beat) = pixels * seconds / beat^2.
# This seems dimensionally incorrect for pixels per second.
# Let's assume distance_per_beat is how much it *should* fall in one beat interval.
# Then the speed is distance_per_beat / BEAT_INTERVAL.
# Example: If distance_per_beat = 280 pixels, BEAT_INTERVAL = 0.659 s
# NOTE_SPEED = 280 / 0.659 = 424.8 pixels/second
# Let's stick to the user's original calculation for now as it might be calibrated to their visual feel.
# If distance_per_beat is the target displacement *during* one beat_interval, then the speed is indeed distance_per_beat / BEAT_INTERVAL.
# The original code: NOTE_SPEED = distance_per_beat * BEAT_INTERVAL. This seems unusual.
# Let's assume distance_per_beat is a target, and NOTE_SPEED defines how fast it moves per second.
# The fall_time calculation later relies on NOTE_SPEED: fall_time = fall_distance / NOTE_SPEED.
# If NOTE_SPEED is pixels/second, this is correct.
# Let's assume the user's original intent for NOTE_SPEED was pixels per second, calculated from distance_per_beat.
# If a note travels 'distance_per_beat' pixels in 'BEAT_INTERVAL' seconds,
# then Speed = Distance / Time = distance_per_beat / BEAT_INTERVAL.
# The code has NOTE_SPEED = distance_per_beat * BEAT_INTERVAL. This is likely an error.
# Let's correct it for physical sense


COM_PORT = 'COM30'

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

BG = pygame.image.load("assets/Video Game_synth.png")  # <- rename to match actual file
FONT = pygame.font.Font("assets/font.ttf", 40)

hit_sound = pygame.mixer.Sound("songs/hitsound.mp3")  
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
serial_data = "" # Buffer for incoming serial data
score = 0        
        
class Note:
    def __init__(self, lane, spawn_time):
        self.lane = lane
        self.spawn_time = spawn_time
        self.x = lane * LANE_WIDTH + 10
        self.y = +NOTE_HEIGHT # Start offscreen
        self.hit = False

    def update(self, delta_time):
        self.y += NOTE_SPEED * delta_time

    def draw(self, surface):
        pygame.draw.rect(surface, GREEN, (self.x, self.y, NOTE_WIDTH, NOTE_HEIGHT))


class Particle:
    def __init__(self, x, y, color, size):
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.velocity_x = random.uniform(-1, 1)
        self.velocity_y = random.uniform(-2, -1) # Move upwards
        self.lifetime = 1  # Lifetime in seconds

    def update(self, delta_time):
        self.x += self.velocity_x * 100 * delta_time
        self.y += self.velocity_y * 100 * delta_time
        self.size -= 0.5 * delta_time # Shrink over time
        self.lifetime -= delta_time

    def draw(self, surface):
        if self.size > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.size))

particles = [] # Global list to hold particles

def create_hit_effect(x, y):
    num_particles = 20 # Adjust for desired density
    for _ in range(num_particles):
        color = (random.randint(100, 255), random.randint(0, 200), random.randint(0, 255)) # Example color
        size = random.randint(4, 8)
        particles.append(Particle(x, y, color, size))

def play_song():
    pygame.time.wait(int((.5+.65 +.3) * 1000))
    pygame.mixer.music.load(SONG_PATH)
    pygame.mixer.music.play()
    pygame.time.wait(int((1.6-.65-.3) * 1000))
    if ser:
        # Send start command to ESP32 slightly before the notes reach the red line
        ser.write('T'.encode())
        print('sent T')
        
    else:
        print("Serial connection not available")


play_button = Button(pygame.image.load("assets/Play Rect.png"), (WIDTH // 2, 250), "PLAY", FONT, "#d7fcd4", "white")
options_button = Button(pygame.image.load("assets/Options Rect.png"), (WIDTH // 2, 375), "OPTIONS", FONT, "#d7fcd4", "white")
quit_button = Button(pygame.image.load("assets/Quit Rect.png"), (WIDTH // 2, 500), "QUIT", FONT, "#d7fcd4", "white")


# Start button function
def start_game():
    global game_state, start_time, first_note_time, score, particles 
    game_state = PLAYING
    # Calculate the time delay to sync with notes reaching near the red line
    fall_distance = HEIGHT - 100 - SPAWN_OFFSET  # Distance to red line
    fall_time = fall_distance / NOTE_SPEED  # Time in seconds for notes to reach the red line
    
    # Start music after the fall time to sync with the first notes
    threading.Timer(fall_time - 0.1, play_song).start()  # Start the song slightly before notes hit the red line


def read_from_serial():
    global serial_data, score
    
    while True:
        if ser and ser.isOpen() and ser.in_waiting > 0:
            data = ser.read(ser.in_waiting).decode('utf-8',errors='ignore')
            serial_data += data
            
            while '\n' in serial_data:
                line, serial_data = serial_data.split('\n', 1)
                line = line.strip() # Remove whitespace (like \r)
                    
                print(f"Debug: Received from ESP32: '{line}'") # For debugging
                
                if line == '1':
                        score += 1
                        print(f"Score incremented to: {score}")

                        if hit_sound:
                            hit_sound.play()

                        hit_lane_x = WIDTH // 2 # Example center of screen
                        hit_y = HEIGHT - 100  # Example hit line position
                        create_hit_effect(hit_lane_x, hit_y)

# Reset function to clear all game states and return to the menu
def reset_game():
    global game_state, score, notes, particles, current_note_index, start_time
    # Reset everything
    game_state = MENU
    score = 0
    notes = []          # Clear notes
    particles = []      # Clear particles
    current_note_index = 0
    start_time = None   # Reset start time to None (force a fresh start)
    
    # Optionally, stop the music if it is playing
    pygame.mixer.music.stop()
    print("Game reset to menu.")



# Main game loop
def main_game():
    global game_state, notes, particles, score, start_time, current_note_index
    running = True
    start_time = None
    notes = []
    particles = []      # Clear particles
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
        scaled_bg = pygame.transform.scale(BG, (WIDTH, HEIGHT))
        screen.blit(scaled_bg, (0, 0))

        if game_state == MENU:
            # Draw Background
            scaled_bg = pygame.transform.scale(BG, (WIDTH, HEIGHT))
            screen.blit(scaled_bg, (0, 0))

            #Draw Title
            title = FONT.render("ESP32 Rhythm Game", True, WHITE)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//7))
            
            # Process and draw start button
            mouse_pos = pygame.mouse.get_pos()
            for button in [play_button, options_button, quit_button]:
                button.changeColor(mouse_pos)
                button.update(screen)

            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if play_button.checkForInput(mouse_pos):
                        start_game()
                    elif options_button.checkForInput(mouse_pos):
                        print("OPTIONS clicked (you can add a screen here)")
                    elif quit_button.checkForInput(mouse_pos):
                        pygame.quit()
                        exit()

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

            # End the game after the specified number of beats
            if current_note_index >= len(note_pattern) and not notes:
                reset_game()

            # Update and draw notes
            delta_time = clock.get_time() / 1000.0
            for i in range(len(notes) - 1, -1, -1):  # Iterate backward so we can remove items safely
                note = notes[i]
                note.update(delta_time)
                note.draw(screen)
                
                # Remove notes that have fallen past the screen
                if note.y > HEIGHT:
                    notes.pop(i)

            # Update and draw particles
            delta_time = clock.get_time() / 1000.0
            for i in range(len(particles) - 1, -1, -1): # Iterate backwards for safe removal
                particle = particles[i]
                particle.update(delta_time)
                if particle.lifetime <= 0 or particle.size <= 0:
                    particles.pop(i)
                else:
                    particle.draw(screen)

            # Draw hit line
            pygame.draw.line(screen, RED, (0, HEIGHT - 100), (WIDTH, HEIGHT - 100), 5)

            font = pygame.font.SysFont('Arial', 36)
            score_text = font.render(f'Score: {score}', True, WHITE)
            screen.blit(score_text, (10, 10)) 



        # Update display
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()

if __name__ == "__main__":
    main_game()
