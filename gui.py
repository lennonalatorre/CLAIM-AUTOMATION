# gui.py - Modern PyQt6 interface for Claim Processor (Simplified & Styled)
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QLineEdit,
    QFileDialog, QMessageBox, QGroupBox, QGridLayout, QFrame,
    QDialog, QListWidget, QDialogButtonBox, QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

import config
import claim_processor


class ProcessingThread(QThread):
    """Background thread for claim processing to prevent GUI freezing."""
    finished = pyqtSignal(dict)
    log_message = pyqtSignal(str)
    
    def __init__(self, image_path, counselor, counselors_list):
        super().__init__()
        self.image_path = image_path
        self.counselor = counselor
        self.counselors_list = counselors_list
    
    def run(self):
        try:
            self.log_message.emit(f"\n{'─' * 80}")
            self.log_message.emit(f"⏳ Processing: {os.path.basename(self.image_path)}")
            self.log_message.emit(f"   └─ Counselor: {self.counselor}")
            
            result = claim_processor.process_claim(
                self.image_path, 
                self.counselors_list,
                counselor=self.counselor,
                insurance="",
                copay="",
                deductible=""
            )
            
            self.finished.emit(result)
            
        except Exception as e:
            self.log_message.emit(f"\n❌ ERROR: {str(e)}")
            self.finished.emit({"success": False, "message": str(e)})


class DropZone(QFrame):
    """Custom drag-and-drop widget for file uploads."""
    files_dropped = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.setStyleSheet("""
            DropZone {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 3px dashed #4a90e2;
                border-radius: 12px;
                min-height: 200px;
            }
            DropZone:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e3f2fd, stop:1 #bbdefb);
                border-color: #2196F3;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)
        
        icon_label = QLabel("📁")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFont(QFont("Segoe UI", 48))
        
        text_label = QLabel("Drop ERA screenshots here")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        text_label.setStyleSheet("color: #2c3e50;")
        
        subtitle = QLabel("or click Browse below")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet("color: #7f8c8d;")
        
        format_label = QLabel("Supported: PNG, JPG, JPEG")
        format_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        format_label.setFont(QFont("Segoe UI", 9))
        format_label.setStyleSheet("color: #95a5a6;")
        
        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(format_label)
        
        self.setLayout(layout)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.png', '.jpg', '.jpeg']:
                    files.append(file_path)
        
        if files:
            self.files_dropped.emit(files)
        
        event.acceptProposedAction()


class CounselorDialog(QDialog):
    """Dialog for managing counselors."""
    
    def __init__(self, counselors, parent=None):
        super().__init__(parent)
        self.counselors = counselors
        self.setWindowTitle("Manage Counselors")
        self.setModal(True)
        self.resize(450, 500)
        
        # Modern styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QListWidget {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 5px;
                background-color: white;
                font-size: 11pt;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 10pt;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Title
        title = QLabel("👥 Counselor Management")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50; padding: 10px;")
        layout.addWidget(title)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.addItems(self.counselors)
        layout.addWidget(self.list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add Counselor")
        delete_btn = QPushButton("🗑️ Delete Selected")
        
        add_btn.setStyleSheet("background-color: #28a745; color: white;")
        delete_btn.setStyleSheet("background-color: #dc3545; color: white;")
        
        add_btn.clicked.connect(self.add_counselor)
        delete_btn.clicked.connect(self.delete_counselor)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)
        
        # Close button
        close_btn = QPushButton("✓ Done")
        close_btn.setStyleSheet("background-color: #6c757d; color: white;")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def add_counselor(self):
        name, ok = QInputDialog.getText(self, "Add Counselor", "Enter counselor name:")
        if ok and name.strip():
            name = name.strip()
            if name in self.counselors:
                QMessageBox.information(self, "Duplicate", f"'{name}' already exists.")
                return
            
            self.counselors.append(name)
            self.counselors.sort()
            config.save_counselors(self.counselors)
            self.list_widget.clear()
            self.list_widget.addItems(self.counselors)
    
    def delete_counselor(self):
        current = self.list_widget.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a counselor to delete.")
            return
        
        name = current.text()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete counselor '{name}'?\n\nNote: This will NOT delete their Excel/Word files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.counselors.remove(name)
            config.save_counselors(self.counselors)
            self.list_widget.clear()
            self.list_widget.addItems(self.counselors)


class ClaimGUI(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("💼 Insurance Claim Processor")
        self.resize(1100, 850)
        
        # Load data
        self.counselors = config.get_counselors()
        
        # Processing state
        self.processing_thread = None
        
        # Apply modern theme
        self.apply_modern_theme()
        self.init_ui()
        self.log_welcome()
    
    def apply_modern_theme(self):
        """Apply a professional modern theme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f2f5;
            }
            QGroupBox {
                background-color: white;
                border: 2px solid #e1e4e8;
                border-radius: 10px;
                margin-top: 12px;
                padding: 15px;
                font-weight: bold;
                font-size: 11pt;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: #2c3e50;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                background-color: white;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
            }
            QLineEdit:read-only {
                background-color: #f8f9fa;
                color: #495057;
            }
            QComboBox {
                padding: 8px;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                background-color: white;
                font-size: 10pt;
            }
            QComboBox:focus {
                border-color: #4a90e2;
            }
            QTextEdit {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
                background-color: white;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 10pt;
                border: none;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
            QPushButton:pressed {
                padding: 11px 19px 9px 21px;
            }
        """)
    
    def init_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)
        
        # Header
        header_layout = QVBoxLayout()
        header = QLabel("💼 Insurance Claim Processor")
        header.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; padding: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Automated OCR • Financial Calculations • Excel & Word Export")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet("color: #7f8c8d; padding-bottom: 10px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(header)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)
        
        # Content in two columns
        content_layout = QHBoxLayout()
        
        # Left column - Input
        left_column = QVBoxLayout()
        left_column.setSpacing(15)
        
        # Counselor selection
        counselor_group = QGroupBox("👤 Step 1: Select Counselor")
        counselor_layout = QVBoxLayout()
        
        counselor_input_layout = QHBoxLayout()
        self.counselor_combo = QComboBox()
        self.counselor_combo.addItems(self.counselors)
        self.counselor_combo.setMinimumHeight(40)
        counselor_input_layout.addWidget(self.counselor_combo, 3)
        
        manage_btn = QPushButton("⚙️")
        manage_btn.setMaximumWidth(45)
        manage_btn.setStyleSheet("background-color: #6c757d; color: white;")
        manage_btn.setToolTip("Manage Counselors")
        manage_btn.clicked.connect(self.manage_counselors)
        counselor_input_layout.addWidget(manage_btn)
        
        counselor_layout.addLayout(counselor_input_layout)
        counselor_group.setLayout(counselor_layout)
        left_column.addWidget(counselor_group)
        
        # File upload
        upload_group = QGroupBox("📁 Step 2: Upload ERA Screenshot")
        upload_layout = QVBoxLayout()
        
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self.handle_dropped_files)
        upload_layout.addWidget(self.drop_zone)
        
        browse_btn = QPushButton("📂 Browse Files")
        browse_btn.setMinimumHeight(45)
        browse_btn.setStyleSheet("background-color: #17a2b8; color: white; font-size: 11pt;")
        browse_btn.clicked.connect(self.browse_files)
        upload_layout.addWidget(browse_btn)
        
        upload_group.setLayout(upload_layout)
        left_column.addWidget(upload_group)
        
        # Extracted info
        extracted_group = QGroupBox("📋 Extracted Information")
        extracted_layout = QGridLayout()
        extracted_layout.setSpacing(10)
        
        extracted_layout.addWidget(QLabel("Client:"), 0, 0)
        self.client_field = QLineEdit()
        self.client_field.setReadOnly(True)
        extracted_layout.addWidget(self.client_field, 0, 1)
        
        extracted_layout.addWidget(QLabel("Date:"), 1, 0)
        self.date_field = QLineEdit()
        self.date_field.setReadOnly(True)
        extracted_layout.addWidget(self.date_field, 1, 1)
        
        extracted_layout.addWidget(QLabel("Insurance Payment:"), 2, 0)
        self.insurance_payment_field = QLineEdit()
        self.insurance_payment_field.setReadOnly(True)
        extracted_layout.addWidget(self.insurance_payment_field, 2, 1)
        
        extracted_group.setLayout(extracted_layout)
        left_column.addWidget(extracted_group)
        
        # Process button
        self.process_btn = QPushButton("▶️ Process Claim")
        self.process_btn.setMinimumHeight(55)
        self.process_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 13pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #adb5bd;
            }
        """)
        self.process_btn.clicked.connect(self.process_current_file)
        self.process_btn.setEnabled(False)
        left_column.addWidget(self.process_btn)
        
        left_column.addStretch()
        
        # Right column - Output
        right_column = QVBoxLayout()
        right_column.setSpacing(15)
        
        # Financial summary
        summary_group = QGroupBox("💰 Financial Summary")
        summary_layout = QGridLayout()
        summary_layout.setSpacing(8)
        
        summary_layout.addWidget(QLabel("Contracted Rate (G):"), 0, 0)
        self.contracted_rate_field = QLineEdit()
        self.contracted_rate_field.setReadOnly(True)
        summary_layout.addWidget(self.contracted_rate_field, 0, 1)
        
        summary_layout.addWidget(QLabel("65% Counselor (H):"), 1, 0)
        self.counselor_65_field = QLineEdit()
        self.counselor_65_field.setReadOnly(True)
        summary_layout.addWidget(self.counselor_65_field, 1, 1)
        
        summary_layout.addWidget(QLabel("Amount to Counselor (I):"), 2, 0)
        self.total_payout_field = QLineEdit()
        self.total_payout_field.setReadOnly(True)
        summary_layout.addWidget(self.total_payout_field, 2, 1)
        
        summary_layout.addWidget(QLabel("35% GWC (J):"), 3, 0)
        self.gwc_35_field = QLineEdit()
        self.gwc_35_field.setReadOnly(True)
        summary_layout.addWidget(self.gwc_35_field, 3, 1)
        
        summary_group.setLayout(summary_layout)
        right_column.addWidget(summary_group)
        
        # Log
        log_group = QGroupBox("📊 Processing Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        right_column.addWidget(log_group)
        
        # Add columns to content
        content_layout.addLayout(left_column, 1)
        content_layout.addLayout(right_column, 1)
        main_layout.addLayout(content_layout)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)
        
        excel_btn = QPushButton("📊 Excel Folder")
        word_btn = QPushButton("📄 Word Folder")
        clear_btn = QPushButton("🔄 Clear Log")
        exit_btn = QPushButton("❌ Exit")
        
        excel_btn.setStyleSheet("background-color: #007bff; color: white;")
        word_btn.setStyleSheet("background-color: #6f42c1; color: white;")
        clear_btn.setStyleSheet("background-color: #ffc107; color: black;")
        exit_btn.setStyleSheet("background-color: #dc3545; color: white;")
        
        excel_btn.clicked.connect(self.open_excel_folder)
        word_btn.clicked.connect(self.open_word_folder)
        clear_btn.clicked.connect(self.clear_logs)
        exit_btn.clicked.connect(self.close)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(excel_btn)
        bottom_layout.addWidget(word_btn)
        bottom_layout.addWidget(clear_btn)
        bottom_layout.addWidget(exit_btn)
        
        main_layout.addLayout(bottom_layout)
        
        central_widget.setLayout(main_layout)
    
    def log_welcome(self):
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
            }
        """)
        self.log_text.append("<span style='color: #4a90e2; font-weight: bold;'>╔" + "═" * 78 + "╗</span>")
        self.log_text.append("<span style='color: #4a90e2; font-weight: bold;'>║" + " " * 22 + "🎯 CLAIM PROCESSOR READY" + " " * 33 + "║</span>")
        self.log_text.append("<span style='color: #4a90e2; font-weight: bold;'>╚" + "═" * 78 + "╝</span>\n")
        self.log_text.append("<span style='color: #28a745;'>📌 STEPS:</span>")
        self.log_text.append("<span style='color: #d4d4d4;'>   1️⃣  Select counselor</span>")
        self.log_text.append("<span style='color: #d4d4d4;'>   2️⃣  Drop or browse ERA screenshot</span>")
        self.log_text.append("<span style='color: #d4d4d4;'>   3️⃣  Click Process Claim</span>")
        self.log_text.append("<span style='color: #d4d4d4;'>   4️⃣  Review results & open Excel\n</span>")
        self.log_text.append("<span style='color: #6c757d;'>" + "─" * 80 + "</span>\n")
    
    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select ERA Screenshot",
            "",
            "Image Files (*.png *.jpg *.jpeg);;All Files (*.*)"
        )
        
        if files:
            self.handle_dropped_files(files)
    
    def handle_dropped_files(self, files):
        if not files:
            return
        
        self.current_file = files[0]
        self.log_text.append(f"<span style='color: #28a745;'>✓ Loaded: {os.path.basename(self.current_file)}</span>")
        self.process_btn.setEnabled(True)
    
    def process_current_file(self):
        if not hasattr(self, 'current_file'):
            QMessageBox.warning(self, "No File", "Please select a file to process.")
            return
        
        counselor = self.counselor_combo.currentText().strip()
        if not counselor:
            QMessageBox.warning(self, "Missing Counselor", "Please select a counselor first.")
            return
        
        # Disable UI during processing
        self.process_btn.setEnabled(False)
        self.process_btn.setText("⏳ Processing...")
        
        # Start processing thread
        self.processing_thread = ProcessingThread(
            self.current_file,
            counselor,
            self.counselors
        )
        self.processing_thread.log_message.connect(lambda msg: self.log_text.append(f"<span style='color: #d4d4d4;'>{msg}</span>"))
        self.processing_thread.finished.connect(self.handle_processing_result)
        self.processing_thread.start()
    
    def handle_processing_result(self, result):
        self.process_btn.setEnabled(True)
        self.process_btn.setText("▶️ Process Claim")
        
        if result.get("success"):
            data = result.get("data", {})
            calc = result.get("calculations", {})
            
            # Update extracted fields
            self.client_field.setText(data.get('Client', 'N/A'))
            self.date_field.setText(data.get('Date', 'N/A'))
            self.insurance_payment_field.setText(data.get('Insurance Payment', 'N/A'))
            
            # Update summary fields
            if calc:
                self.contracted_rate_field.setText(f"${calc.get('contracted_rate', 0):.2f}")
                self.counselor_65_field.setText(f"${calc.get('counselor_65_percent', 0):.2f}")
                self.total_payout_field.setText(f"${calc.get('total_payout', 0):.2f}")
                self.gwc_35_field.setText(f"${calc.get('gwc_35_percent', 0):.2f}")
            
            self.log_text.append("\n<span style='color: #28a745; font-weight: bold;'>✅ SUCCESS!</span>")
            self.log_text.append(f"<span style='color: #4a90e2;'>   📊 Files saved to: {self.counselor_combo.currentText()}.xlsx & .docx</span>")
            
            QMessageBox.information(self, "✅ Success", f"Claim processed successfully!\n\nFiles saved for {self.counselor_combo.currentText()}")
        else:
            self.log_text.append(f"\n<span style='color: #dc3545; font-weight: bold;'>❌ ERROR: {result.get('message', 'Unknown error')}</span>")
            QMessageBox.critical(self, "Processing Error", result.get('message', 'Unknown error'))
    
    def manage_counselors(self):
        dialog = CounselorDialog(self.counselors, self)
        if dialog.exec():
            current = self.counselor_combo.currentText()
            self.counselor_combo.clear()
            self.counselor_combo.addItems(self.counselors)
            
            index = self.counselor_combo.findText(current)
            if index >= 0:
                self.counselor_combo.setCurrentIndex(index)
            
            self.log_text.append("<span style='color: #28a745;'>✓ Counselor list updated</span>")
    
    def open_excel_folder(self):
        path = config.EXCEL_DIR
        if os.path.exists(path):
            if os.name == 'nt':
                os.startfile(path)
            else:
                os.system(f'open "{path}"')
            self.log_text.append(f"<span style='color: #4a90e2;'>📊 Opened Excel folder</span>")
        else:
            QMessageBox.information(self, "Folder Not Found", "No Excel files have been created yet.")
    
    def open_word_folder(self):
        path = config.WORD_DIR
        if os.path.exists(path):
            if os.name == 'nt':
                os.startfile(path)
            else:
                os.system(f'open "{path}"')
            self.log_text.append(f"<span style='color: #6f42c1;'>📄 Opened Word folder</span>")
        else:
            QMessageBox.information(self, "Folder Not Found", "No Word files have been created yet.")
    
    def clear_logs(self):
        self.log_text.clear()
        self.log_welcome()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = ClaimGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()