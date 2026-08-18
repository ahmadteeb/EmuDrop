import pygame
import sys
import json
from scripts.infoscreen import InfoScreen

class JoystickMapper(InfoScreen):
    def __init__(self, settings_path):
        super().__init__()  # Initialize the parent InfoScreen class
        self.settings_path = settings_path
        # Button mapping dictionary
        self.button_names = {
            "A": "CONTROLLER_BUTTON_A",
            "B": "CONTROLLER_BUTTON_B",
            "X": "CONTROLLER_BUTTON_X",
            "Y": "CONTROLLER_BUTTON_Y",
            "L": "CONTROLLER_BUTTON_L",
            "R": "CONTROLLER_BUTTON_R",
            "SELECT": "CONTROLLER_BUTTON_SELECT",
            "START": "CONTROLLER_BUTTON_START",
            "UP": "CONTROLLER_BUTTON_UP",
            "DOWN": "CONTROLLER_BUTTON_DOWN",
            "LEFT": "CONTROLLER_BUTTON_LEFT",
            "RIGHT": "CONTROLLER_BUTTON_RIGHT"
        }
        self.button_mapping = {}
        self.current_button_keys = list(self.button_names.keys())
        self.current_button_index = 0

        self.load_settings()

    def load_settings(self):
        try:
            with open(self.settings_path, 'r') as f:
                self.settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.show_message("Error loading settings.json", duration=2)
            pygame.quit()
            sys.exit(1)

    def save_settings(self):
        # Convert the button mapping to use the full controller button names
        final_mapping = {}
        for key, value in self.button_mapping.items():
            final_mapping[self.button_names[key]] = value
            
        self.settings["keyMapping"] = final_mapping
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
            return True
        except Exception as e:
            self.show_message(f"Error saving settings: {e}", duration=2)
            return False

    def run(self):
        # Show initial instructions
        self.show_message("Welcome to Joystick Mapper! Press any button to begin", wait_for_button="any")

        while self.current_button_index < len(self.current_button_keys):
            current_key = self.current_button_keys[self.current_button_index]
            self.show_message(f"Press the button for: {current_key}")

            waiting_for_input = True
            last_pressed_button = None
            while waiting_for_input:
                for event in pygame.event.get():
                    print(f"Event: {event.type}")
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.JOYHATMOTION:
                        last_pressed_button = event.button
                        self.button_mapping[current_key] = event.button
                        # Show brief confirmation
                        self.show_message(f"Mapped {current_key} to button {event.button}\nRelease button to continue", duration=0.5)
                    elif event.type == pygame.JOYBUTTONDOWN:
                        last_pressed_button = event.button
                        self.button_mapping[current_key] = event.button
                        # Show brief confirmation
                        self.show_message(f"Mapped {current_key} to button {event.button}\nRelease button to continue", duration=0.5)
                    elif event.type == pygame.JOYBUTTONUP:
                        if event.button == last_pressed_button:
                            waiting_for_input = False
                            self.current_button_index += 1
                
                self.clock.tick(60)

        # All buttons mapped, save settings
        if self.save_settings():
            self.show_message("Button mapping completed and saved! Press any button to exit", wait_for_button="any")
        else:
            self.show_message("Error saving settings! Press any button to exit", wait_for_button="any")

        pygame.quit()
    