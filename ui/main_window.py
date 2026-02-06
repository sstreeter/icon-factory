"""
Main window for Icon Factory application.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QGroupBox, QRadioButton, QCheckBox,
    QSlider, QLineEdit, QProgressBar, QMessageBox, QColorDialog,
    QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent
from PIL import Image
from pathlib import Path
import sys

from core import ImageProcessor, AutoCropper, MaskingEngine, IconExporter, EdgeProcessor, BorderMasking
from core.icon_audit import IconAuditor
from ui.audit_dialog import AuditReportDialog
from utils import ArchiveManager


class IconGeneratorThread(QThread):
    """Background thread for icon generation."""
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, processor, settings):
        super().__init__()
        self.processor = processor
        self.settings = settings
    
    def run(self):
        """Generate icons in background."""
        try:
            # Generate all sizes
            images = self.processor.generate_all_sizes()
            self.progress.emit(20)
            
            # Apply masking variants if needed
            from core.masking import MaskingEngine
            
            # Create output directory
            output_dir = Path(self.settings['output_dir'])
            icon_name = self.settings['icon_name']
            
            if self.settings['create_archive']:
                icon_dir = ArchiveManager.create_organized_structure(
                    str(output_dir),
                    icon_name,
                    self.settings.get('source_path')
                )
                paths = ArchiveManager.get_output_paths(icon_dir, icon_name)
            else:
                output_dir.mkdir(parents=True, exist_ok=True)
                paths = {
                    'ico_full_alpha': output_dir / f"{icon_name}_full_alpha.ico",
                    'ico_binary_alpha': output_dir / f"{icon_name}_binary_alpha.ico",
                    'ico_with_glow': output_dir / f"{icon_name}_with_glow.ico",
                    'icns': output_dir / f"{icon_name}.icns",
                    'png_dir': output_dir / 'png'
                }
            
            self.progress.emit(40)
            
            # Export Windows ICO files
            if self.settings['export_windows']:
                # Full alpha version
                IconExporter.export_ico(images, str(paths['ico_full_alpha']))
                
                # Binary alpha version
                binary_images = {
                    size: MaskingEngine.binary_alpha(img)
                    for size, img in images.items()
                }
                IconExporter.export_ico(binary_images, str(paths['ico_binary_alpha']))
                
                # Glow version
                glow_images = {
                    size: MaskingEngine.add_glow(img)
                    for size, img in images.items()
                }
                IconExporter.export_ico(glow_images, str(paths['ico_with_glow']))
                
                self.progress.emit(60)
            
            # Export Mac ICNS
            if self.settings['export_mac']:
                IconExporter.export_icns_macos(images, str(paths['icns']))
                self.progress.emit(80)
            
            # Export PNG set
            if self.settings['export_png']:
                IconExporter.export_png_set(images, str(paths['png_dir']))
                self.progress.emit(90)
            
            # Create ZIP if requested
            if self.settings['create_archive'] and self.settings.get('create_zip'):
                zip_path = output_dir / f"{icon_name}.zip"
                ArchiveManager.create_zip_archive(str(icon_dir), str(zip_path))
            
            self.progress.emit(100)
            self.finished.emit(True, str(output_dir))
            
        except Exception as e:
            self.finished.emit(False, str(e))


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.processor = ImageProcessor()
        self.current_mask_color = (255, 255, 255)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Icon Architect - Professional Edition")
        self.setMinimumSize(900, 700)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        layout = QVBoxLayout(central)
        
        # Top section: Studio Layer (Dual Canvas)
        studio_layout = QHBoxLayout()
        
        # Left: Source Inspector
        self.source_group = self.create_source_inspector()
        studio_layout.addWidget(self.source_group, 1)
        
        # Right: Artboard
        self.artboard_group = self.create_artboard()
        studio_layout.addWidget(self.artboard_group, 1)
        
        layout.addLayout(studio_layout)
        
        # Masking options
        masking_group = self.create_masking_panel()
        layout.addWidget(masking_group)
        
        # Export options
        export_group = self.create_export_panel()
        layout.addWidget(export_group)
        
        # Icon name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Icon Name:"))
        self.icon_name_input = QLineEdit()
        self.icon_name_input.setPlaceholderText("Enter icon name (defaults to source filename)")
        name_layout.addWidget(self.icon_name_input)
        layout.addLayout(name_layout)
        
        # Output directory
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output:"))
        self.output_path = QLineEdit(str(Path.home() / "Desktop" / "icons"))
        output_layout.addWidget(self.output_path)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(browse_btn)
        layout.addLayout(output_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Generate button
        self.generate_btn = QPushButton("Generate Icons")
        self.generate_btn.setMinimumHeight(50)
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self.generate_icons)
        layout.addWidget(self.generate_btn)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
    
    def create_source_inspector(self):
        """Create the Source Inspector panel (Left Canvas)."""
        group = QGroupBox("Source Inspector (Original)")
        layout = QVBoxLayout()
        
        # Source viewing area (custom styled)
        self.drop_label = QLabel("Drop Source Image Here")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumSize(300, 300)
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #999;
                border-radius: 4px;
                background-color: #f0f0f0;
                color: #666;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.drop_label, 1) # Stretch 1 to fill space
        
        # Info readout
        self.source_info_label = QLabel("No image loaded")
        self.source_info_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.source_info_label)
        
        # Action Bar
        action_layout = QHBoxLayout()
        choose_btn = QPushButton("📂 Open...")
        choose_btn.clicked.connect(self.choose_file)
        action_layout.addWidget(choose_btn)
        
        self.check_btn = QPushButton("🩺 Check Icon")
        self.check_btn.setToolTip("Run Icon Doctor Audit")
        self.check_btn.setEnabled(False)
        self.check_btn.clicked.connect(self.run_icon_audit)
        action_layout.addWidget(self.check_btn)
        
        layout.addLayout(action_layout)
        
        group.setLayout(layout)
        return group
    
    def create_artboard(self):
        """Create the Artboard panel (Right Canvas)."""
        group = QGroupBox("Artboard (Live Preview)")
        layout = QVBoxLayout()
        
        # Artboard viewing area
        # We use a scroll area to handle zooming/panning in future, 
        # but for now it's a fixed viewport style
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(300, 300)
        # Checkerboard background via stylesheet
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 1px solid #999;
                background-color: #e0e0e0;
                background-image: linear-gradient(45deg, #ccc 25%, transparent 25%), 
                                  linear-gradient(-45deg, #ccc 25%, transparent 25%), 
                                  linear-gradient(45deg, transparent 75%, #ccc 75%), 
                                  linear-gradient(-45deg, transparent 75%, #ccc 75%);
                background-size: 20px 20px;
                background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
            }
        """)
        layout.addWidget(self.preview_label, 1) # Stretch 1
        
        # Tool Bar
        tools_layout = QHBoxLayout()
        tools_layout.addWidget(QLabel("Overlays:"))
        
        self.show_mask_overlay = QCheckBox("Mask (Red)")
        self.show_mask_overlay.setToolTip("Show removed areas in red")
        self.show_mask_overlay.toggled.connect(self.update_preview)
        tools_layout.addWidget(self.show_mask_overlay)
        
        self.show_safe_zone = QCheckBox("Safe Zone")
        self.show_safe_zone.setToolTip("Show 10% Safe Zone Grid")
        self.show_safe_zone.setChecked(True)
        self.show_safe_zone.toggled.connect(self.update_preview)
        tools_layout.addWidget(self.show_safe_zone)
        
        tools_layout.addStretch()
        layout.addLayout(tools_layout)
        
        # Background selector (for export preview)
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel("Preview BG:"))
        
        self.bg_transparent = QRadioButton("🏁 Checker")
        self.bg_transparent.setChecked(True)
        self.bg_transparent.toggled.connect(self.update_preview)
        bg_layout.addWidget(self.bg_transparent)
        
        self.bg_white = QRadioButton("⚪ White")
        self.bg_white.toggled.connect(self.update_preview)
        bg_layout.addWidget(self.bg_white)
        
        self.bg_black = QRadioButton("⚫ Black")
        self.bg_black.toggled.connect(self.update_preview)
        bg_layout.addWidget(self.bg_black)
        
        bg_layout.addStretch()
        layout.addLayout(bg_layout)
        
        group.setLayout(layout)
        return group
    
    def create_masking_panel(self):
        """Create masking options panel."""
        group = QGroupBox("Masking Options")
        layout = QVBoxLayout()
        
        # Radio buttons for masking mode
        mode_layout = QHBoxLayout()
        
        self.mask_none = QRadioButton("None (Keep Original)")
        self.mask_none.setChecked(True)
        self.mask_none.toggled.connect(self.apply_masking)
        mode_layout.addWidget(self.mask_none)
        
        self.mask_autocrop = QRadioButton("Auto-Crop (Detect Content)")
        self.mask_autocrop.toggled.connect(self.apply_masking)
        mode_layout.addWidget(self.mask_autocrop)
        
        self.mask_color = QRadioButton("Remove Color (Entire Image)")
        self.mask_color.toggled.connect(self.apply_masking)
        mode_layout.addWidget(self.mask_color)
        
        self.mask_border = QRadioButton("Remove Color (Borders Only)")
        self.mask_border.toggled.connect(self.apply_masking)
        mode_layout.addWidget(self.mask_border)
        
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # Color mask settings
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        
        self.color_btn = QPushButton("🎨 Pick")
        self.color_btn.setFixedWidth(80)
        self.color_btn.clicked.connect(self.pick_color)
        color_layout.addWidget(self.color_btn)
        
        color_layout.addWidget(QLabel("Tolerance:"))
        self.tolerance_spin = QSpinBox()
        self.tolerance_spin.setRange(0, 255)
        self.tolerance_spin.setValue(30)
        self.tolerance_spin.setSuffix(" px")
        self.tolerance_spin.valueChanged.connect(self.apply_masking)
        color_layout.addWidget(self.tolerance_spin)
        
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # Auto-crop after masking checkbox
        self.autocrop_after = QCheckBox("✂️ Auto-Crop After Masking (Crop to tight bounds after removing transparency)")
        self.autocrop_after.setChecked(True)  # Default ON for clean results
        self.autocrop_after.toggled.connect(self.apply_masking)
        layout.addWidget(self.autocrop_after)
        
        # Advanced edge processing
        edge_group = QGroupBox("✨ Advanced Edge Processing (Optional)")
        edge_group.setCheckable(True)
        edge_group.setChecked(False)
        edge_group.toggled.connect(self.apply_masking)
        edge_layout = QVBoxLayout()
        
        # Defringe checkbox
        self.defringe_check = QCheckBox("Defringe (Remove Color Halos)")
        self.defringe_check.setChecked(False)
        self.defringe_check.toggled.connect(self.apply_masking)
        edge_layout.addWidget(self.defringe_check)
        
        # Clean edges checkbox
        self.clean_edges_check = QCheckBox("Clean Edges (Remove Pixel Debris)")
        self.clean_edges_check.setChecked(True)
        self.clean_edges_check.toggled.connect(self.apply_masking)
        edge_layout.addWidget(self.clean_edges_check)
        
        # Mask expansion with spinbox
        expand_layout = QHBoxLayout()
        expand_layout.addWidget(QLabel("Mask Adjust:"))
        
        self.mask_expand_spin = QSpinBox()
        self.mask_expand_spin.setRange(-5, 5)
        self.mask_expand_spin.setValue(0)
        self.mask_expand_spin.setSuffix(" px")
        self.mask_expand_spin.setSpecialValueText("No Change")
        self.mask_expand_spin.valueChanged.connect(self.apply_masking)
        expand_layout.addWidget(self.mask_expand_spin)
        
        expand_layout.addWidget(QLabel("(- = Contract, + = Expand)"))
        expand_layout.addStretch()
        edge_layout.addLayout(expand_layout)
        
        # Edge threshold with spinbox
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Edge Threshold:"))
        
        self.edge_threshold_spin = QSpinBox()
        self.edge_threshold_spin.setRange(0, 50)
        self.edge_threshold_spin.setValue(10)
        self.edge_threshold_spin.setSuffix(" alpha")
        self.edge_threshold_spin.valueChanged.connect(self.apply_masking)
        threshold_layout.addWidget(self.edge_threshold_spin)
        
        threshold_layout.addStretch()
        edge_layout.addLayout(threshold_layout)
        
        edge_group.setLayout(edge_layout)
        layout.addWidget(edge_group)
        self.edge_group = edge_group  # Store reference
        
        group.setLayout(layout)
        return group
    
    def create_export_panel(self):
        """Create export options panel."""
        group = QGroupBox("Export Options")
        layout = QHBoxLayout()
        
        self.export_windows = QCheckBox("Windows ICO")
        self.export_windows.setChecked(True)
        layout.addWidget(self.export_windows)
        
        self.export_mac = QCheckBox("Mac ICNS")
        self.export_mac.setChecked(True)
        layout.addWidget(self.export_mac)
        
        self.export_png = QCheckBox("PNG Set")
        self.export_png.setChecked(True)
        layout.addWidget(self.export_png)
        
        self.create_archive = QCheckBox("Create Archive")
        self.create_archive.setChecked(True)
        layout.addWidget(self.create_archive)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.load_image(file_path)
    
    def choose_file(self):
        """Open file dialog to choose image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.svg)"
        )
        if file_path:
            self.load_image(file_path)
    
    def load_image(self, path: str):
        """Load an image file."""
        if self.processor.load_image(path):
            self.current_source_path = path
            file_name = Path(path).stem
            self.drop_label.setText(f"Loaded: {file_name}")
            
            # Set default icon name (user can edit)
            self.icon_name_input.setText(file_name)
            
            self.generate_btn.setEnabled(True)
            self.apply_masking()
            self.update_preview()
    
    def apply_masking(self):
        """Apply selected masking mode."""
        if not self.processor.source_image:
            return
        
        # Reset to source
        self.processor.reset_to_source()
        img = self.processor.processed_image
        
        # Apply basic masking
        if self.mask_autocrop.isChecked():
            img = AutoCropper.crop_to_content(img, padding=5)
        elif self.mask_color.isChecked():
            tolerance = self.tolerance_spin.value()
            img = MaskingEngine.color_mask(img, self.current_mask_color, tolerance)
            
            # Auto-crop after if enabled
            if self.autocrop_after.isChecked():
                img = AutoCropper.crop_to_content(img, padding=5)
        
        elif self.mask_border.isChecked():
            # Border-only masking (Magic Wand style)
            tolerance = self.tolerance_spin.value()
            img = BorderMasking.flood_fill_from_edges(img, tolerance=tolerance, start_from_corners=True)
            
            # Auto-crop after if enabled
            if self.autocrop_after.isChecked():
                img = AutoCropper.crop_to_content(img, padding=5)
        
        # ALWAYS apply quality enhancement (Clean by Default philosophy)
        threshold = self.edge_threshold_spin.value()
        img = EdgeProcessor.clean_edges(img, threshold=threshold, blur_radius=0.3)
        
        # Apply optional advanced features
        if hasattr(self, 'edge_group') and self.edge_group.isChecked():
            if self.defringe_check.isChecked():
                img = EdgeProcessor.defringe_simple(img, strength=0.7)
            
            # Apply mask expansion/contraction
            mask_adjust = self.mask_expand_spin.value()
            if mask_adjust != 0:
                img = EdgeProcessor.expand_mask(img, pixels=mask_adjust)
        
        self.processor.apply_processed_image(img)
        self.update_preview()
    
    def pick_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_mask_color = (color.red(), color.green(), color.blue())
            self.color_btn.setStyleSheet(
                f"background-color: rgb({color.red()}, {color.green()}, {color.blue()});"
            )
            if self.mask_color.isChecked():
                self.apply_masking()
    
    def update_preview(self):
        """Update the preview image."""
        if not self.processor.processed_image:
            return
            
        preview = self.processor.processed_image.copy()
        
        # 1. Apply Backgrounds (for visualization only)
        if self.bg_white.isChecked():
            preview = MaskingEngine.add_background(preview, (255, 255, 255, 255))
        elif self.bg_black.isChecked():
            preview = MaskingEngine.add_background(preview, (0, 0, 0, 255))
        # Transparent (Checkerboard) is handled by the stylesheet on the label
            
        # 2. Apply Overlays (Visual Aids)
        
        # Mask Overlay (Show removed areas in Red)
        if self.show_mask_overlay.isChecked():
            # Create a semi-transparent red layer
            red_overlay = Image.new('RGBA', preview.size, (255, 0, 0, 100))
            
            # Create mask from current alpha (where alpha is 0/transp, we show red)
            # We invert the alpha channel of the processed image
            if preview.mode != 'RGBA':
                preview = preview.convert('RGBA')
            
            alpha = preview.split()[3]
            # Invert alpha: 0 (transp) -> 255 (opaque), 255 -> 0
            from PIL import ImageChops
            mask_inv = ImageChops.invert(alpha)
            
            # Composite red overlay using inverted alpha as mask
            # We want red ONLY where it is transparent
            preview.paste(red_overlay, (0,0), mask_inv)
            
        # Safe Zone Grid (10% Margin)
        if self.show_safe_zone.isChecked():
            from PIL import ImageDraw
            draw = ImageDraw.Draw(preview)
            w, h = preview.size
            margin = int(min(w, h) * 0.10) # 10%
            
            # Draw Rectangle
            # Outline color: Magenta (high visibility)
            outline_color = (255, 0, 255, 255)
            
            # Draw rectangle (1px width)
            draw.rectangle(
                (margin, margin, w - margin, h - margin),
                outline=outline_color,
                width=2
            )
            
            # Draw Center Crosshair (subtle)
            cx, cy = w // 2, h // 2
            draw.line((cx - 10, cy, cx + 10, cy), fill=outline_color, width=1)
            draw.line((cx, cy - 10, cx, cy + 10), fill=outline_color, width=1)
        
        # Convert to QPixmap
        preview_rgb = preview.convert('RGB')
        data = preview_rgb.tobytes('raw', 'RGB')
        qimage = QImage(data, preview.width, preview.height, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        
        # Scale if necessary to fit (keep aspect ratio)
        if pixmap.width() > 512:
            pixmap = pixmap.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            
        self.preview_label.setPixmap(pixmap)
    
    def browse_output(self):
        """Browse for output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self.output_path.text()
        )
        if dir_path:
            self.output_path.setText(dir_path)
    
    
    def run_icon_audit(self):
        """Run the Icon Doctor audit."""
        if not self.processor.processed_image:
            return
            
        # Run audit
        issues = IconAuditor.audit_image(self.processor.processed_image)
        
        # Show report
        dialog = AuditReportDialog(issues, self)
        if dialog.exec():
            # If user clicked "Auto-Fix All"
            # Apply Smart Edge Cleanup
            self.apply_smart_cleanup()
            
    def apply_smart_cleanup(self):
        """Apply Smart Edge Cleanup (Vector Reconstruction)."""
        if not self.processor.source_image:
            return
            
        self.processor.reset_to_source()
        img = self.processor.processed_image
        
        # Re-apply masking if needed
        # (This is simplified - in a fuller implementation we'd persist masking state better)
        if self.mask_autocrop.isChecked():
            # Use Safe Zone logic instead of tight crop
            img = AutoCropper.apply_safe_zone(img, margin_percent=10)
        elif self.mask_color.isChecked():
            tolerance = self.tolerance_spin.value()
            img = MaskingEngine.color_mask(img, self.current_mask_color, tolerance)
            if self.autocrop_after.isChecked():
                 # Use Safe Zone logic instead of tight crop
                 img = AutoCropper.apply_safe_zone(img, margin_percent=10)
        
        # Apply Smart Cleanup
        # Note: smart_cleanup now handles internal padding to fix border artifacts
        img = EdgeProcessor.smart_cleanup(img)
        
        self.processor.apply_processed_image(img)
        self.update_preview()
        QMessageBox.information(self, "Auto-Fix Applied", "Smart Edge Cleanup has been applied!\n\nYour icon has been reconstructed with vector-like edges and Standard Safe Zone (10%).")

    def generate_icons(self):
        """Start icon generation."""
        if not self.processor.processed_image:
            return
        
        # Get icon name (use custom name if provided, otherwise use source filename)
        icon_name = self.icon_name_input.text().strip()
        if not icon_name:
            icon_name = Path(self.current_source_path).stem
        
        # Prepare settings
        settings = {
            'output_dir': self.output_path.text(),
            'icon_name': icon_name,
            'source_path': self.current_source_path,
            'export_windows': self.export_windows.isChecked(),
            'export_mac': self.export_mac.isChecked(),
            'export_png': self.export_png.isChecked(),
            'create_archive': self.create_archive.isChecked(),
            'create_zip': True
        }
        
        # Start generation thread
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.worker = IconGeneratorThread(self.processor, settings)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.generation_finished)
        self.worker.start()
    
    def generation_finished(self, success: bool, message: str):
        """Handle generation completion."""
        self.generate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(
                self,
                "Success",
                f"Icons generated successfully!\n\nOutput: {message}"
            )
        else:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to generate icons:\n{message}"
            )
