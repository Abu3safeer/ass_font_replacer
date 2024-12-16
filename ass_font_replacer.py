import sys
import os
import json
import re
import shutil
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QFileDialog, QLabel, QMessageBox, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QMenu, QAction, QCheckBox, QProgressBar, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from datetime import datetime

# Default configuration to create if JSON file is missing or corrupted
default_config = [{"fontBefore": "Default", "fontAfter": "Arial"}]

def load_fonts_config():
    try:
        if not os.path.exists('fonts_config.json'):
            with open('fonts_config.json', 'w') as json_file:
                json.dump(default_config, json_file, indent=4)
            return default_config
        with open('fonts_config.json', 'r') as json_file:
            fonts_config = json.load(json_file)
            if not fonts_config:
                with open('fonts_config.json', 'w') as json_file:
                    json.dump(default_config, json_file, indent=4)
                return default_config
            return fonts_config
    except (json.JSONDecodeError, IOError):
        shutil.copy('fonts_config.json', 'fonts_config_backup.json')
        with open('fonts_config.json', 'w') as json_file:
            json.dump(default_config, json_file, indent=4)
        return default_config

class Worker(QThread):
    progress = pyqtSignal(int)
    log_message = pyqtSignal(str)

    def __init__(self, files, font_replacements, default_font, output_dir):
        super().__init__()
        self.files = files
        self.font_replacements = font_replacements
        self.default_font = default_font
        self.output_dir = output_dir

    def run(self):
        total_files = len(self.files)
        for index, ass_file_name in enumerate(self.files):
            with open(ass_file_name, 'r', encoding='utf-8-sig') as ass_file:
                lines = ass_file.readlines()
            new_lines = []
            style_pattern = re.compile(r'^Style: (.+?),(.+?),')
            font_tag_pattern = re.compile(r'\\fn([^\\}]+)')

            for line in lines:
                style_match = style_pattern.match(line)
                if style_match:
                    font_name = style_match.group(2).strip()
                    new_font = self.font_replacements.get(font_name, self.default_font)
                    new_line = line.replace(font_name, new_font, 1)
                    new_lines.append(new_line)
                elif '\\fn' in line:
                    def replace_font(match):
                        font_name = match.group(1)
                        new_font = self.font_replacements.get(font_name, self.default_font)
                        return f'\\fn{new_font}'
                    new_line = font_tag_pattern.sub(replace_font, line)
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)

            # Save output files to the selected output directory
            output_file_name = os.path.join(self.output_dir, os.path.basename(ass_file_name))
            with open(output_file_name, 'w', encoding='utf-8-sig') as output_file:
                output_file.writelines(new_lines)

            self.log_message.emit(f'Processed {os.path.basename(ass_file_name)}')
            self.progress.emit(int((index + 1) / total_files * 100))

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'ASS Subtitle Font Replacer'
        self.initUI()
        self.loadConfig()
        self.output_dir = None  # Initialize output directory

    def initUI(self):
        self.setWindowTitle(self.title)
        
        main_layout = QVBoxLayout()
        
        self.label = QLabel('Select a Directory to Process:')
        main_layout.addWidget(self.label)
        
        self.button = QPushButton('Select Directory', self)
        self.button.clicked.connect(self.showDialog)
        main_layout.addWidget(self.button)

        self.output_button = QPushButton('Select Output Directory', self)
        self.output_button.clicked.connect(self.selectOutputDirectory)
        main_layout.addWidget(self.output_button)

        self.start_button = QPushButton('Start Processing', self)
        self.start_button.clicked.connect(self.startProcessing)
        main_layout.addWidget(self.start_button)

        self.recursive_checkbox = QCheckBox('Recursive')
        main_layout.addWidget(self.recursive_checkbox)
        
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        main_layout.addWidget(self.log_area)

        self.table = QTableWidget()
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.showContextMenu)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.MultiSelection)
        
        side_layout = QVBoxLayout()
        self.add_button = QPushButton('Add Row', self)
        self.add_button.clicked.connect(self.addRow)
        side_layout.addWidget(self.add_button)

        self.remove_button = QPushButton('Remove Row', self)
        self.remove_button.clicked.connect(self.removeRow)
        side_layout.addWidget(self.remove_button)
        
        self.save_button = QPushButton('Save Config', self)
        self.save_button.clicked.connect(self.saveConfig)
        side_layout.addWidget(self.save_button)
        
        table_layout = QHBoxLayout()
        table_layout.addWidget(self.table)
        table_layout.addLayout(side_layout)
        
        main_layout.addLayout(table_layout)
        self.setLayout(main_layout)
        
        self.show()

    def loadConfig(self):
        self.fonts_config = load_fonts_config()
        self.table.setRowCount(len(self.fonts_config))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["fontBefore", "fontAfter"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row, entry in enumerate(self.fonts_config):
            self.table.setItem(row, 0, QTableWidgetItem(entry["fontBefore"]))
            self.table.setItem(row, 1, QTableWidgetItem(entry["fontAfter"]))

    def saveConfig(self):
        rowCount = self.table.rowCount()
        colCount = self.table.columnCount()
        new_config = []
        for row in range(rowCount):
            entry = {}
            for col in range(colCount):
                header = self.table.horizontalHeaderItem(col).text()
                entry[header] = self.table.item(row, col).text()
            new_config.append(entry)
        with open('fonts_config.json', 'w') as json_file:
            json.dump(new_config, json_file, indent=4)
        QMessageBox.information(self, "Success", "Configuration has been saved.")
        self.fonts_config = new_config  # Update the loaded config to the new config
    
    def showDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", options=options)
        
        if directory:
            files = self.collectFiles(directory)
            self.file_list = files  # Store the file list for processing

    def selectOutputDirectory(self):
        self.output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not self.output_dir:
            # Create default output directory with timestamp if none is selected
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = f'output_{timestamp}'
            os.makedirs(self.output_dir, exist_ok=True)
            QMessageBox.information(self, "Output Directory", f"Output directory created: {self.output_dir}")

    def collectFiles(self, directory):
        ass_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.ass'):
                    ass_files.append(os.path.join(root, file))
            if not self.recursive_checkbox.isChecked():
                break
        return ass_files
    
    def startProcessing(self):
        if not hasattr(self, 'file_list') or not self.file_list:
            QMessageBox.warning(self, "Warning", "No files selected for processing.")
            return

        if not self.output_dir:
            # Attempt to create a default output directory if one wasn't set
            self.selectOutputDirectory()

        fonts_config = load_fonts_config()
        font_replacements = {entry["fontBefore"]: entry["fontAfter"] for entry in fonts_config}
        default_font = font_replacements.get("Default", "Arial")

        self.progress_bar.setValue(0)
        self.log_area.clear()
        self.worker = Worker(self.file_list, font_replacements, default_font, self.output_dir)
        self.worker.progress.connect(self.updateProgress)
        self.worker.log_message.connect(self.appendLog)
        self.worker.start()

    def updateProgress(self, value):
        self.progress_bar.setValue(value)

    def appendLog(self, message):
        self.log_area.append(message)

    def showContextMenu(self, pos):
        contextMenu = QMenu(self)
        add_action = QAction('Add Row', self)
        remove_action = QAction('Remove Row', self)
        
        contextMenu.addAction(add_action)
        contextMenu.addAction(remove_action)
        
        add_action.triggered.connect(self.addRow)
        remove_action.triggered.connect(self.removeRow)
        
        contextMenu.exec_(self.table.viewport().mapToGlobal(pos))
    
    def addRow(self):
        current_row_count = self.table.rowCount()
        self.table.insertRow(current_row_count)
    
    def removeRow(self):
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()))
        for row in reversed(selected_rows):
            self.table.removeRow(row)

    def closeEvent(self, event):
        if self.isConfigChanged():
            reply = QMessageBox.question(self, 'Save Changes', 'You have unsaved changes. Do you want to save them?', QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.saveConfig()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    def isConfigChanged(self):
        current_config = []
        rowCount = self.table.rowCount()
        colCount = self.table.columnCount()
        for row in range(rowCount):
            entry = {}
            for col in range(colCount):
                header = self.table.horizontalHeaderItem(col).text()
                entry[header] = self.table.item(row, col).text()
            current_config.append(entry)
        return current_config != self.fonts_config

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())