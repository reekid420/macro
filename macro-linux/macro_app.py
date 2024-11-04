import sys
import time
import json
import pyautogui
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, 
                             QWidget, QListWidget, QLineEdit, QLabel, QInputDialog, QMessageBox, QSlider)
from PyQt5.QtCore import Qt, QTimer, QEventLoop
from pynput import mouse, keyboard
import pyperclip

pyautogui.PAUSE = 0.01  # Adjust this value if needed

class MacroGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Macro GUI")
        self.setGeometry(100, 100, 400, 500)

        self.macro_actions = []
        self.is_recording = False
        self.start_time = 0
        self.playback_speed = 1.0
        self.is_playing = False
        self.pause_playback = False
        self.held_keys = set()
        self.key_press_start = {}
        
        # Set up logging
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.macro_list = QListWidget()
        layout.addWidget(self.macro_list)

        button_layout = QHBoxLayout()
        self.record_button = QPushButton("Record Macro")
        self.record_button.clicked.connect(self.toggle_record)
        button_layout.addWidget(self.record_button)

        self.play_button = QPushButton("Play Macro")
        self.play_button.clicked.connect(self.play_macro)
        button_layout.addWidget(self.play_button)

        layout.addLayout(button_layout)

        save_load_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Macro")
        self.save_button.clicked.connect(self.save_macro)
        save_load_layout.addWidget(self.save_button)

        self.load_button = QPushButton("Load Macro")
        self.load_button.clicked.connect(self.load_macro)
        save_load_layout.addWidget(self.load_button)

        layout.addLayout(save_load_layout)

        edit_layout = QHBoxLayout()
        self.edit_button = QPushButton("Edit Selected Action")
        self.edit_button.clicked.connect(self.edit_action)
        edit_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Selected Action")
        self.delete_button.clicked.connect(self.delete_action)
        edit_layout.addWidget(self.delete_button)

        layout.addLayout(edit_layout)

        # Add speed slider
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Playback Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(10)
        self.speed_slider.valueChanged.connect(self.update_speed)
        speed_layout.addWidget(self.speed_slider)
        layout.addLayout(speed_layout)

        # Add pause/resume button
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setEnabled(False)
        layout.addWidget(self.pause_button)

        # Add the countdown label
        self.countdown_label = QLabel("", self)
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet("font-size: 24pt; font-weight: bold;")
        self.countdown_label.hide()  # Hide it initially
        
        # Add the label to your layout
        layout.addWidget(self.countdown_label)

        # Add a button to input text
        self.input_text_button = QPushButton("Input Text for Macro")
        self.input_text_button.clicked.connect(self.input_text)
        layout.addWidget(self.input_text_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.mouse_listener = None
        self.keyboard_listener = None

    def toggle_record(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.logger.info("Starting recording")
        self.is_recording = True
        self.record_button.setText("Stop Recording")
        self.macro_actions.clear()
        self.macro_list.clear()
        self.start_time = time.time()
        self.held_keys.clear()
        self.key_press_start.clear()

        if self.mouse_listener is None or not self.mouse_listener.is_alive():
            self.logger.debug("Creating new mouse listener")
            self.mouse_listener = mouse.Listener(on_click=self.on_click)
            self.mouse_listener.start()
        else:
            self.logger.warning("Mouse listener already running")

        if self.keyboard_listener is None or not self.keyboard_listener.is_alive():
            self.logger.debug("Creating new keyboard listener")
            self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
            self.keyboard_listener.start()
        else:
            self.logger.warning("Keyboard listener already running")

    def stop_recording(self):
        self.logger.info("Stopping recording")
        self.is_recording = False
        self.record_button.setText("Record Macro")
        
        if self.mouse_listener:
            self.logger.debug("Stopping mouse listener")
            self.mouse_listener.stop()
            self.mouse_listener = None
        
        if self.keyboard_listener:
            self.logger.debug("Stopping keyboard listener")
            self.keyboard_listener.stop()
            self.keyboard_listener = None

    def on_click(self, x, y, button, pressed):
        if pressed and self.is_recording:
            current_time = time.time()
            delay = current_time - self.start_time
            self.start_time = current_time
            button_str = 'left' if button == mouse.Button.left else 'right' if button == mouse.Button.right else 'middle'
            action = {'type': 'click', 'x': x, 'y': y, 'button': button_str, 'delay': delay}
            self.macro_actions.append(action)
            self.update_macro_list()

    def on_press(self, key):
        if self.is_recording:
            current_time = time.time()
            delay = current_time - self.start_time
            self.start_time = current_time
            
            # Check for Ctrl key
            if key == keyboard.Key.ctrl or key == keyboard.Key.cmd:
                self.held_keys.add(key)  # Track if Ctrl is held down
                return  # Don't record this key press

            # Check for Ctrl + V
            if keyboard.Key.ctrl in self.held_keys and key.char == 'v':
                # Simulate typing the clipboard content
                try:
                    clipboard_content = pyperclip.paste()  # Get the clipboard content
                    self.type_text(clipboard_content)  # Type the text
                    return  # Don't record this as a key press
                except Exception as e:
                    self.logger.error(f"Error accessing clipboard: {e}")

            try:
                key_char = key.char
            except AttributeError:
                key_char = str(key)
            
            if key not in self.held_keys:
                self.held_keys.add(key)
                self.key_press_start[key] = current_time
                action = {'type': 'keydown', 'key': key_char, 'delay': delay}
                self.macro_actions.append(action)
                self.update_macro_list()

    def on_release(self, key):
        if self.is_recording:
            current_time = time.time()
            delay = current_time - self.start_time
            self.start_time = current_time
            
            if key in self.held_keys:
                self.held_keys.remove(key)
                hold_duration = current_time - self.key_press_start.pop(key, current_time)
                action = {'type': 'keyup', 'key': key.char if hasattr(key, 'char') else str(key), 'delay': delay, 'hold_duration': hold_duration}
                self.macro_actions.append(action)
                self.update_macro_list()

    def update_speed(self):
        self.playback_speed = self.speed_slider.value() / 100.0
        self.logger.info(f"Playback speed set to {self.playback_speed}")

    def toggle_pause(self):
        self.pause_playback = not self.pause_playback
        self.pause_button.setText("Resume" if self.pause_playback else "Pause")

    def play_macro(self):
        if not self.macro_actions:
            return

        self.is_playing = True
        self.pause_button.setEnabled(True)
        self.pause_playback = False

        try:
            for action in self.macro_actions:
                if not self.is_playing:
                    break

                while self.pause_playback:
                    QApplication.processEvents()
                    time.sleep(0.1)

                if action['type'] == 'click':
                    pyautogui.click(action['x'], action['y'], button=action['button'])
                elif action['type'] == 'keydown':
                    pyautogui.keyDown(action['key'])
                elif action['type'] == 'keyup':
                    pyautogui.keyUp(action['key'])

                delay = action['delay'] / self.playback_speed
                time.sleep(delay)

        except Exception as e:
            self.logger.error(f"Error during macro playback: {e}")
            QMessageBox.warning(self, "Error", f"Error during macro playback: {e}")

        finally:
            self.is_playing = False
            self.pause_button.setEnabled(False)
            self.pause_button.setText("Pause")
            self.statusBar().showMessage("Macro playback finished", 3000)

    def stop_macro(self):
        self.is_playing = False
        self.logger.info("Macro playback stopped by user")

    def save_macro(self):
        name, ok = QInputDialog.getText(self, 'Save Macro', 'Enter macro name:')
        if ok and name:
            with open(f"{name}.json", "w") as f:
                json.dump(self.macro_actions, f)

    def load_macro(self):
        name, ok = QInputDialog.getText(self, 'Load Macro', 'Enter macro name:')
        if ok and name:
            try:
                with open(f"{name}.json", "r") as f:
                    self.macro_actions = json.load(f)
                self.update_macro_list()
            except FileNotFoundError:
                QMessageBox.warning(self, "Error", "Macro file not found.")

    def update_macro_list(self):
        self.logger.debug("Updating macro list")
        self.macro_list.clear()
        for index, action in enumerate(self.macro_actions):
            if action['type'] == 'click':
                item_text = f"Click: ({action['x']}, {action['y']}), Button: {action['button']}, Delay: {action['delay']:.2f}s"
            elif action['type'] == 'keydown':
                item_text = f"Key Down: {action['key']}, Delay: {action['delay']:.2f}s"
            elif action['type'] == 'keyup':
                item_text = f"Key Up: {action['key']}, Delay: {action['delay']:.2f}s, Hold: {action.get('hold_duration', 0):.2f}s"
            else:
                item_text = f"Unknown action type: {action['type']}"
            
            self.macro_list.addItem(f"{index + 1}. {item_text}")
        
        self.logger.debug(f"Macro list updated with {self.macro_list.count()} items")

    def delete_action(self):
        selected_item = self.macro_list.currentItem()
        if selected_item:
            index = self.macro_list.row(selected_item)
            self.logger.debug(f"Deleting action at index {index}")
            if 0 <= index < len(self.macro_actions):
                del self.macro_actions[index]
                self.update_macro_list()
            else:
                self.logger.warning(f"Invalid index {index} for deletion")

    def edit_action(self):
        selected_item = self.macro_list.currentItem()
        if selected_item:
            index = self.macro_list.row(selected_item)
            action = self.macro_actions[index]
            if action['type'] == 'click':
                new_delay, ok = QInputDialog.getDouble(self, 'Edit Delay', 'Enter new delay:', action['delay'], 0, 100, 2)
                if ok:
                    action['delay'] = new_delay
            elif action['type'] == 'key':
                new_key, ok = QInputDialog.getText(self, 'Edit Key', 'Enter new key:', text=action['key'])
                if ok:
                    action['key'] = new_key
                new_delay, ok = QInputDialog.getDouble(self, 'Edit Delay', 'Enter new delay:', action['delay'], 0, 100, 2)
                if ok:
                    action['delay'] = new_delay
            self.update_macro_list()

    def type_text(self, text):
        for char in text:
            if char.isupper():
                # Simulate pressing Shift + key for uppercase letters
                pyautogui.keyDown('shift')
                pyautogui.press(char.lower())
                pyautogui.keyUp('shift')
            else:
                pyautogui.press(char)
            time.sleep(0.05)

    def input_text(self):
        text, ok = QInputDialog.getText(self, 'Input Text', 'Enter the text to convert to macro:')
        if ok and text:
            # Convert the input text into macro actions
            for char in text:
                action = {'type': 'keydown', 'key': char, 'delay': 0.1}
                self.macro_actions.append(action)
                self.macro_list.addItem(f"Key Down: {char}, Delay: 0.10s")
                action = {'type': 'keyup', 'key': char, 'delay': 0.1}
                self.macro_actions.append(action)
                self.macro_list.addItem(f"Key Up: {char}, Delay: 0.10s")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MacroGUI()
    window.show()
    sys.exit(app.exec_())
