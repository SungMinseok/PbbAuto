import sys
import time
import pygetwindow as gw
import pyautogui as pag
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QLineEdit, QTextEdit, QScrollArea, QShortcut, QFileDialog, QMessageBox, QLineEdit, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
import os
from datetime import datetime
import pydirectinput as pyd
import pyperclip
import subprocess
import pytesseract
from PIL import Image
import csv

pytesseract.pytesseract.tesseract_cmd = fr'C:\Program Files\Tesseract-OCR\tesseract.exe'

current_dir = os.path.dirname(os.path.abspath(__file__))

screenshot_dir = os.path.join(current_dir, 'screenshot')
if not os.path.exists(screenshot_dir):
    os.makedirs(screenshot_dir)

cl_dir = os.path.join(current_dir, 'checklist')
if not os.path.exists(cl_dir):
    os.makedirs(cl_dir)

class PbbAutoApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        self.prefix_input.setText('Game')
        self.refresh_window_list()
    
    def initUI(self):
        # Layouts
        main_layout = QVBoxLayout()
        
        # Input boxes for coordinates
        self.x_input0 = QLineEdit(self)
        self.y_input0 = QLineEdit(self)
        self.x_input1 = QLineEdit(self)
        self.y_input1 = QLineEdit(self)

        self.x_pos = QLineEdit(self)
        self.y_pos = QLineEdit(self)
        self.w_pos = QLineEdit(self)
        self.h_pos = QLineEdit(self)

        # Setting placeholders for x and y
        self.x_input0.setPlaceholderText("x")
        self.y_input0.setPlaceholderText("y")
        self.x_input1.setPlaceholderText("x")
        self.y_input1.setPlaceholderText("y")

        self.x_pos.setPlaceholderText("x")
        self.y_pos.setPlaceholderText("y")
        self.w_pos.setPlaceholderText("w")
        self.h_pos.setPlaceholderText("h")

        # Adding coordinate inputs to the layout
        coord_layout0 = QHBoxLayout()
        coord_layout0.addWidget(self.x_input0)
        coord_layout0.addWidget(self.y_input0)

        # Adding widgets to main layout
        main_layout.addLayout(coord_layout0)

        # Adding coordinate inputs to the layout
        coord_layout1 = QHBoxLayout()
        coord_layout1.addWidget(self.x_input1)
        coord_layout1.addWidget(self.y_input1)

        # Adding widgets to main layout
        main_layout.addLayout(coord_layout1)

        # Adding coordinate inputs to the layout
        coord_layout2 = QHBoxLayout()
        coord_layout2.addWidget(self.x_pos)
        coord_layout2.addWidget(self.y_pos)
        coord_layout2.addWidget(self.w_pos)
        coord_layout2.addWidget(self.h_pos)

        # Adding widgets to main layout
        main_layout.addLayout(coord_layout2)

        # Setting F3 shortcut for capturing mouse coordinates
        shortcut0 = QShortcut(QKeySequence("F2"), self)
        shortcut0.activated.connect(lambda: self.capture_mouse_position(0))
        # Setting F3 shortcut for capturing mouse coordinates
        shortcut1 = QShortcut(QKeySequence("F3"), self)
        shortcut1.activated.connect(lambda: self.capture_mouse_position(1))

        # 실행파일 경로 인풋박스 및 버튼
        self.file_path_input = QLineEdit(self)
        self.file_path_input.setPlaceholderText("Select .bat file...")
        
        self.file_select_button = QPushButton("Browse", self)
        self.file_select_button.clicked.connect(self.select_bat_file)

        self.file_run_button = QPushButton("Run File", self)
        self.file_run_button.clicked.connect(self.run_bat_file)

        # Adding to layout
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_path_input)
        file_layout.addWidget(self.file_select_button)
        file_layout.addWidget(self.file_run_button)
        
        main_layout.addLayout(file_layout)

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
        self.execute_button = QPushButton('Execute (F5)', self)
        self.execute_button.setShortcut('F5')
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
                command = command.split('#')[0].strip()
                if command:  # Process only non-empty commands
                    self.process_command(command)

    def take_screenshot(self):
        """Take a full-screen screenshot."""


        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        screenshot_path = os.path.join(screenshot_dir, f"{timestamp}.jpg")

        screenshot = pag.screenshot()
        screenshot.save(screenshot_path)
        return screenshot_path

    def take_screenshot_with_coords(self, x, y, w, h):
        """Take a screenshot at specified coordinates."""

        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        screenshot_path = os.path.join(screenshot_dir, f"{timestamp}.jpg")

        screenshot = pag.screenshot(region=(x, y, w, h))
        screenshot.save(screenshot_path)
        return screenshot_path

    def image_to_text(self, lang='eng'):
        """Convert the most recent screenshot to text."""
        screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screenshot')
        if not os.path.exists(screenshot_dir):
            print("Screenshot directory does not exist.")
            return None

        screenshots = sorted(
            [f for f in os.listdir(screenshot_dir) if f.endswith('.jpg')],
            key=lambda f: os.path.getmtime(os.path.join(screenshot_dir, f)),
            reverse=True
        )

        if not screenshots:
            print("No screenshots found.")
            return None

        most_recent_screenshot = os.path.join(screenshot_dir, screenshots[0])
        return pytesseract.image_to_string(Image.open(most_recent_screenshot), lang=lang)

    # Command execution logic
    def process_command(self, command):
        parts = command.split()
        action = parts[0].strip()

        if action == "press":
            key = parts[1].strip()
            pyd.press(key)
        elif action == "write" or action == "typewrite":
            key = parts[1].strip()
            #pyd.typewrite(key)
            pyperclip.copy(key)                 # Copy the key to clipboard
            pyd.keyDown('ctrl')
            pyd.press('v')                      # Paste from clipboard
            pyd.keyUp('ctrl')
            
        elif action == "wait":
            duration = float(parts[1].strip())
            time.sleep(duration)
            
        elif action == "screenshot":
            if len(parts) == 5:  # If coordinates are provided
                try:
                    x = int(parts[1])
                    y = int(parts[2])
                    w = int(parts[3])
                    h = int(parts[4])
                    screenshot_path = self.take_screenshot_with_coords(x, y, w, h)
                    print(f"Screenshot taken and saved at {screenshot_path}")
                except (IndexError, ValueError):
                    print("Invalid coordinates for screenshot. Use: screenshot x y w h")
            else:  # No coordinates, use default take_screenshot()
                screenshot_path = self.take_screenshot()
                print(f"Screenshot taken and saved at {screenshot_path}")

        elif action == "cheat":
            key = " ".join(parts[1:]).strip()  # Treat everything after "cheat" as the key
            pyd.press('`')                     # Press ` key
            pyperclip.copy(key)                 # Copy the key to clipboard
            pyd.keyDown('ctrl')
            pyd.press('v')                      # Paste from clipboard
            pyd.keyUp('ctrl')
            pyd.press('enter')

        elif action == "click":
            # Extract x and y from the command
            try:
                x = int(parts[1].strip())
                y = int(parts[2].strip())
                self.makeclick(x,y)
                #pyd.click(x, y)  # Perform the click at specified coordinates
                #pag.click(x, y)  # Perform the click at specified coordinates
                print(f'Clicked at ({x}, {y})')
            except (IndexError, ValueError):
                print("Invalid coordinates for click command. Use: click x y")


        # Image-to-text (English)
        elif action == "i2s":
            text = self.image_to_text(lang='eng')
            if text:
                print(f"Extracted text (English): {text}")
            else:
                print("No text found in the image.")

        # Image-to-text (Korean)
        elif action == "i2skr":
            text = self.image_to_text(lang='kor')
            if text:
                print(f"Extracted text (Korean): {text}")
            else:
                print("No text found in the image.")

        # Validate extracted text with optional language selection
        elif action == "validate":
            try:
                lang = parts[1].strip()  # Language ('i2s' or 'i2skr')
                expected_text = " ".join(parts[2:]).strip()  # Expected text

                # Extract text based on language
                if lang == "i2s":
                    extracted_text = self.image_to_text(lang='eng')
                elif lang == "i2skr":
                    extracted_text = self.image_to_text(lang='kor')
                else:
                    print(f"Unsupported language command: {lang}")
                    return

                # Compare extracted text with expected text
                if extracted_text.strip() == expected_text:
                    self.last_result = "Passed"
                    print(f"Test Passed: Extracted text matches expected text: '{expected_text}'")
                else:
                    self.last_result = "Failed"
                    print(f"Test Failed: Extracted text does not match expected text.\nExpected: '{expected_text}'\nExtracted: '{extracted_text.strip()}'")
            except Exception as e:
                print(f"Error during validation: {e}")

        # Export result with custom title
        elif action == "export":
            '''
validate i2s Please select an ite
export "When entering the M Key, the facility installation UI must be opened."
            '''
            try:
                custom_title = " ".join(parts[1:]).strip().strip('"')  # Extract custom title
                filename = "checklist.csv"  # Default CSV file name
                cl_path = os.path.join(cl_dir, filename)


                # Write result to CSV
                with open(cl_path, 'a', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ["Title", "Result"]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    writer.writeheader()
                    writer.writerow({"Title": custom_title, "Result": self.last_result})

                print(f"Validation result exported to {cl_path} with title: {custom_title}")
            except Exception as e:
                print(f"Error exporting result: {e}")

        try:
            print(f'{action} : {key}')
        except:
            print(f'{action}')


    def capture_mouse_position(self, num):
        # Get current mouse position
        x, y = pag.position()
        
        if num == 0 :
            # Populate input boxes
            self.x_input0.setText(str(x))
            self.y_input0.setText(str(y))
        else:
            self.x_input1.setText(str(x))
            self.y_input1.setText(str(y))
            if self.x_input0.text() != "" and self.y_input0.text() != "":
                self.x_pos.setText(self.x_input0.text())
                self.y_pos.setText(self.y_input0.text())
                self.w_pos.setText(str(int(self.x_input1.text())- int(self.x_input0.text())))
                self.h_pos.setText(str(int(self.y_input1.text())- int(self.y_input0.text())))

    def select_bat_file(self):
        # 파일 탐색기를 통해 .bat 파일 선택
        file_path, _ = QFileDialog.getOpenFileName(self, "Select .bat file", "", "Batch Files (*.bat)")
        if file_path:
            self.file_path_input.setText(file_path)  # 파일 경로를 인풋박스에 표시

    def run_bat_file(self):
        # 실행파일 경로 가져오기
        file_path = self.file_path_input.text().strip()
        if file_path and os.path.exists(file_path) and file_path.endswith(".bat"):
            # 파일의 디렉토리 경로로 이동하여 실행
            try:
                file_dir = os.path.dirname(file_path)
                subprocess.Popen(file_path, cwd=file_dir, shell=True)  # 지정된 디렉토리에서 .bat 파일 실행
            except Exception as e:
                self.show_error_message(f"Error running file: {e}")
        else:
            self.show_error_message("Invalid file path. Please select a valid .bat file.")


    def show_error_message(self, message):
        # 경고 팝업
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Error")
        msg.exec_()

    def makeclick(self,x,y):
        pyd.moveTo(x, y)
        pyd.mouseDown()
        time.sleep(0.05)  # Optional: Add a slight delay to ensure it registers
        pyd.mouseUp()

# Main function
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PbbAutoApp()
    ex.show()
    sys.exit(app.exec_())
