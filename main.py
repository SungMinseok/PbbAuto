import sys
import time
import pygetwindow as gw
import pyautogui as pag
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QLineEdit, QTextEdit, QScrollArea
from PyQt5.QtCore import Qt
import os
from datetime import datetime
import pydirectinput as pyd

class PbbAutoApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        # Layouts
        main_layout = QVBoxLayout()
        
        # Dropdown, prefix input, refresh button, and coordinate output (x, y, w, h)
        self.prefix_input = QLineEdit(self)
        self.prefix_input.setPlaceholderText("Enter window title prefix...")
        self.refresh_button = QPushButton('Refresh', self)
        self.refresh_button.clicked.connect(self.refresh_window_list)
        self.window_dropdown = QComboBox(self)
        self.coord_label = QLabel('Coordinates: (x, y, w, h)', self)

        # Refresh layout
        refresh_layout = QHBoxLayout()
        refresh_layout.addWidget(self.prefix_input)
        refresh_layout.addWidget(self.refresh_button)
        refresh_layout.addWidget(self.window_dropdown)

        # Textarea for commands
        self.textarea = QTextEdit(self)
        self.textarea.setPlaceholderText("Enter commands here...")

        # Execute button
        self.execute_button = QPushButton('Execute', self)
        self.execute_button.clicked.connect(self.execute_commands)

        # Add widgets to main layout
        main_layout.addLayout(refresh_layout)
        main_layout.addWidget(self.coord_label)
        main_layout.addWidget(self.textarea)
        main_layout.addWidget(self.execute_button)

        # Set main layout
        self.setLayout(main_layout)

        # Window properties
        self.setWindowTitle('PbbAuto - Test Automation')
        self.setGeometry(300, 300, 500, 400)

    # Refresh function to update window list
    def refresh_window_list(self):
        prefix = self.prefix_input.text()
        all_windows = gw.getAllTitles()
        filtered_windows = [w for w in all_windows if prefix in w]
        self.window_dropdown.clear()
        self.window_dropdown.addItems(filtered_windows)
        if filtered_windows:
            self.update_coordinates()

    # Function to get the coordinates of the selected window
    def update_coordinates(self):
        selected_window = self.window_dropdown.currentText()
        if selected_window:
            window_obj = gw.getWindowsWithTitle(selected_window)[0]
            x, y, width, height = window_obj.left, window_obj.top, window_obj.width, window_obj.height
            self.coord_label.setText(f"Coordinates: ({x}, {y}, {width}, {height})")

    # Function to execute commands
    def execute_commands(self):
        selected_window = self.window_dropdown.currentText()
        if selected_window:
            window_obj = gw.getWindowsWithTitle(selected_window)[0]
            window_obj.activate()  # Bring the window to the front

            commands = self.textarea.toPlainText().strip().split('\n')
            for command in commands:
                self.process_command(command.strip())

    # Create a screenshot directory if it doesn't exist and save a screenshot
    def take_screenshot(self):
        # Get current directory and define screenshot folder path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        screenshot_dir = os.path.join(current_dir, 'screenshot')

        # Create the screenshot folder if it doesn't exist
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)

        # Generate the filename using the current time
        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        screenshot_path = os.path.join(screenshot_dir, f"{timestamp}.jpg")

        # Take the screenshot and save it
        screenshot = pag.screenshot()
        screenshot.save(screenshot_path)
        print(f"Screenshot saved as {screenshot_path}")

    # Command execution logic
    def process_command(self, command):
        parts = command.split('(')
        action = parts[0].strip()
        #time.sleep(1)

        if action == "press":
            key = str(parts[1].replace(')', '').strip())
            pyd.press(key)
            #pyd.typewrite(key)
            
        elif action == "wait":
            duration = float(parts[1].replace(')', '').strip())
            time.sleep(duration)

        elif action == "screenshot":
            self.take_screenshot()  # Call the screenshot function

        try:
            print(f'{action} : {key}')
        except:
            print(f'{action}')

# Main function
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PbbAutoApp()
    ex.show()
    sys.exit(app.exec_())
