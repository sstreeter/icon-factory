"""
Main window for Icon Factory application.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QGroupBox, QRadioButton, QCheckBox,
    QSlider, QLineEdit, QProgressBar, QMessageBox, QColorDialog,
    QSpinBox, QTabWidget, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent
from PIL import Image, ImageChops
from pathlib import Path
import sys

from core import ImageProcessor, AutoCropper, MaskingEngine, IconExporter, EdgeProcessor, BorderMasking
from core.icon_audit import IconAuditor
from ui.audit_dialog import AuditReportDialog
from ui.widgets import TransparencyLabel
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
        self.current_mask_color_2 = (255, 255, 255) # Secondary Key (Phase 9)
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
        self.source_group = self.create_source_inspector_v2()
        studio_layout.addWidget(self.source_group, 1)
        
        # Right: Artboard
        self.artboard_group = self.create_artboard()
        studio_layout.addWidget(self.artboard_group, 1)
        
        layout.addLayout(studio_layout)
        
        # Middle section: Tabbed Settings
        self.tabs = QTabWidget()
        
        # Tab 1: Cleanup (Masking & Advanced Edge)
        self.masking_tab = QWidget()
        mask_tab_layout = QVBoxLayout()
        masking_group = self.create_masking_panel()
        mask_tab_layout.addWidget(masking_group)
        mask_tab_layout.addStretch() # Push to top
        self.masking_tab.setLayout(mask_tab_layout)
        self.tabs.addTab(self.masking_tab, "1. Cleanup")
        
        # Tab 2: Geometry (Enforcer)
        self.geometry_tab = QWidget()
        geo_tab_layout = QVBoxLayout()
        geometry_group = self.create_geometry_panel()
        geo_tab_layout.addWidget(geometry_group)
        geo_tab_layout.addStretch()
        self.geometry_tab.setLayout(geo_tab_layout)
        self.tabs.addTab(self.geometry_tab, "2. Geometry (Enforcer)")
        
        # Tab 3: Stroke & Polish (Phase 8)
        self.stroke_tab = QWidget()
        stroke_tab_layout = QVBoxLayout()
        stroke_group = self.create_stroke_panel()
        stroke_tab_layout.addWidget(stroke_group)
        stroke_tab_layout.addStretch()
        self.stroke_tab.setLayout(stroke_tab_layout)
        self.tabs.addTab(self.stroke_tab, "3. Stroke & Polish")
        
        # Tab 4: Export (Moved)
        self.export_tab = QWidget()
        export_tab_layout = QVBoxLayout()
        export_group = self.create_export_panel()
        export_tab_layout.addWidget(export_group)
        export_tab_layout.addStretch()
        self.export_tab.setLayout(export_tab_layout)
        self.tabs.addTab(self.export_tab, "4. Export")
        
        layout.addWidget(self.tabs)
        
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
        # Source viewing area (custom styled)
        self.drop_label = TransparencyLabel()
        self.drop_label.setText("Drop Source Image Here")
        self.drop_label.setMinimumSize(300, 300)
        # We don't need stylesheet border/bg anymore as TransparencyLabel handles it
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
        
        # Commit Button (Phase 7)
        self.commit_btn = QPushButton("⬆ Commit Changes")
        self.commit_btn.setToolTip("Use current Preview as the Source Image (Bake Effects)")
        self.commit_btn.clicked.connect(self.promote_preview_to_source)
        # self.commit_btn.setEnabled(False) # Logic could enable this only when changes made
        action_layout.addWidget(self.commit_btn)
        
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
        # Artboard viewing area
        # We use a scroll area to handle zooming/panning in future, 
        # but for now it's a fixed viewport style
        self.preview_label = TransparencyLabel()
        self.preview_label.setText("Preview")
        self.preview_label.setMinimumSize(300, 300)
        # Background is handled by TransparencyLabel
        layout.addWidget(self.preview_label, 1) # Stretch 1
        
        # Tool Bar
        tools_layout = QHBoxLayout()
        tools_layout.addWidget(QLabel("Overlays:"))
        
        tools_help = self.create_help_btn(
            "Artboard Overlays",
            "<b>Visual aids for perfect icons.</b><br><br>"
            "<ul>"
            "<li><b>Mask (Red):</b> Shows removed/transparent areas in Red. Use this to adjustments.</li>"
            "<li><b>Safe Zone:</b> Shows the Industry Standard 10% safety margin. Maintain key content inside the box.</li>"
            "</ul>"
        )
        tools_layout.addWidget(tools_help)
        tools_layout.addStretch() # Spacer
        
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
        
        # Color mask settings (The Masking Lab)
        # 1. Primary Key
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Primary Key:"))
        
        self.color_btn = QPushButton("🎨 Pick Color 1")
        self.color_btn.setFixedWidth(100)
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
        
        # 2. Secondary Key (Multi-Mask) - Phase 9
        color_2_layout = QHBoxLayout()
        self.enable_key_2 = QCheckBox("Secondary Key:")
        self.enable_key_2.toggled.connect(self.apply_masking)
        self.enable_key_2.toggled.connect(lambda c: self.color_btn_2.setEnabled(c))
        color_2_layout.addWidget(self.enable_key_2)
        
        self.color_btn_2 = QPushButton("🎨 Pick Color 2")
        self.color_btn_2.setFixedWidth(100)
        self.color_btn_2.setEnabled(False)
        self.color_btn_2.clicked.connect(self.pick_color_2)
        color_2_layout.addWidget(self.color_btn_2)
        
        color_2_layout.addWidget(QLabel("Tolerance:"))
        self.tolerance_spin_2 = QSpinBox()
        self.tolerance_spin_2.setRange(0, 255)
        self.tolerance_spin_2.setValue(30)
        self.tolerance_spin_2.setSuffix(" px")
        self.tolerance_spin_2.valueChanged.connect(self.apply_masking)
        color_2_layout.addWidget(self.tolerance_spin_2)
        
        color_2_layout.addStretch()
        layout.addLayout(color_2_layout)
        
        # 3. Mask Choke / Expand (Promoted to Main Panel)
        choke_layout = QHBoxLayout()
        choke_layout.addWidget(QLabel("Mask Choke:"))
        
        self.mask_choke_slider = QSlider(Qt.Orientation.Horizontal)
        self.mask_choke_slider.setRange(-5, 5)
        self.mask_choke_slider.setValue(0)
        self.mask_choke_slider.setFixedWidth(150)
        self.mask_choke_slider.setToolTip("Negative = Choke (Remove Fringe) | Positive = Expand")
        
        choke_label = QLabel("0 px")
        self.mask_choke_slider.valueChanged.connect(lambda v: choke_label.setText(f"{v} px"))
        self.mask_choke_slider.valueChanged.connect(self.apply_masking)
        
        choke_layout.addWidget(self.mask_choke_slider)
        choke_layout.addWidget(choke_label)
        
        choke_help = self.create_help_btn(
            "Mask Choke (Reduce Border)",
            "<b>Controls the mask boundary.</b><br><br>"
            "<ul>"
            "<li><b>Negative (-1 to -5):</b> Choke/Shrink. REMOVES halos and fringes.</li>"
            "<li><b>Positive (+1 to +5):</b> Expand/Grow. Recover lost edges.</li>"
            "</ul>"
        )
        choke_layout.addWidget(choke_help)
        choke_layout.addStretch()
        layout.addLayout(choke_layout)
        
        
        # Auto-crop after masking checkbox
        self.autocrop_after = QCheckBox("✂️ Auto-Crop After Masking (Crop to tight bounds after removing transparency)")
        self.autocrop_after.setChecked(True)  # Default ON for clean results
        self.autocrop_after.toggled.connect(self.apply_masking)
        layout.addWidget(self.autocrop_after)
        
        # Advanced edge processing
        
        # Header for Advanced Edge
        edge_header = QHBoxLayout()
        edge_label = QLabel("✨ Advanced Edge Processing (Optional)")
        edge_help = self.create_help_btn(
            "Advanced Edge Processing",
            "<b>Fine-tune edge quality.</b><br><br>"
            "<ul>"
            "<li><b>Defringe:</b> Removes color halos/fringing from transparent edges.</li>"
            "<li><b>Clean Edges:</b> Removes semi-transparent pixel debris.</li>"
            "<li><b>Edge Threshold:</b> Determines what opacity is considered 'solid'.</li>"
            "</ul>"
        )
        edge_header.addWidget(edge_label)
        edge_header.addWidget(edge_help)
        edge_header.addStretch()
        
        edge_group = QGroupBox()
        edge_group.setTitle("") # Custom header via layout
        edge_layout = QVBoxLayout()
        edge_layout.addLayout(edge_header)
        
        # Checkbox to enable group (simulated groupbox behavior)
        self.edge_group_check = QCheckBox("Enable Edge Processing")
        self.edge_group_check.setChecked(False)
        self.edge_group_check.toggled.connect(self.apply_masking)
        self.edge_group_check.toggled.connect(self.update_ui_state) # Update UI enable state
        edge_layout.addWidget(self.edge_group_check)
        
        # Container for controls
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        self.edge_controls = controls_widget # Store ref
        
        # Defringe checkbox
        self.defringe_check = QCheckBox("Defringe (Remove Color Halos)")
        self.defringe_check.setChecked(False)
        self.defringe_check.toggled.connect(self.apply_masking)
        controls_layout.addWidget(self.defringe_check)
        
        # Clean edges checkbox
        self.clean_edges_check = QCheckBox("Clean Edges (Remove Pixel Debris)")
        self.clean_edges_check.setChecked(True)
        self.clean_edges_check.toggled.connect(self.apply_masking)
        controls_layout.addWidget(self.clean_edges_check)
        
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
        controls_layout.addLayout(threshold_layout)
        
        edge_layout.addWidget(controls_widget)
        edge_group.setLayout(edge_layout)
        
        layout.addWidget(edge_group)
        self.edge_group = self.edge_group_check # Redirect reference for logic compatibility
        
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
        group.setLayout(layout)
        return group
        
    def create_help_btn(self, title: str, text: str):
        """Create a help button with popup info."""
        btn = QPushButton("?")
        btn.setFixedSize(20, 20)
        btn.setToolTip("Click for more info")
        btn.setStyleSheet("""
            QPushButton {
                border-radius: 10px;
                background-color: #ddd;
                color: #555;
                font-weight: bold;
                border: 1px solid #aaa;
            }
            QPushButton:hover {
                background-color: #4a90e2;
                color: white;
                border: 1px solid #357abd;
            }
        """)
        btn.clicked.connect(lambda: QMessageBox.information(self, title, text))
        return btn
        
    def create_geometry_panel(self):
        """Create Geometry Settings panel (Phase 4)."""
        group = QGroupBox("Geometry Settings (Enforce Clean Lines)")
        layout = QHBoxLayout()
        
        # 1. Smoothing (Wart Removal)
        smooth_layout = QVBoxLayout()
        
        # Header with Help
        smooth_header = QHBoxLayout()
        smooth_label = QLabel("Smoothing (Wart Removal): 50")
        self.smooth_label = smooth_label # Store ref for update
        
        smooth_help = self.create_help_btn(
            "Geometry Smoothing (Wart Removal)",
            "<b>Controls the aggression of the Smart Edge engine.</b><br><br>"
            "<ul>"
            "<li><b>0-40 (Gentle):</b> Faithful to source. Good for organic shapes.</li>"
            "<li><b>50 (Standard):</b> Removes small pixel bumps while keeping curves.</li>"
            "<li><b>60-100 (Aggressive):</b> The 'Enforcer'. Eats away warts and protrusions. "
            "Forces lines to be straight. Use this for geometric icons with dirty edges.</li>"
            "</ul>"
        )
        smooth_header.addWidget(smooth_label)
        smooth_header.addWidget(smooth_help)
        smooth_header.addStretch()
        smooth_layout.addLayout(smooth_header)
        
        self.smooth_slider = QSlider(Qt.Orientation.Horizontal)
        self.smooth_slider.setRange(0, 100)
        self.smooth_slider.setValue(50)
        self.smooth_slider.setToolTip("Aggressiveness of bump removal. Higher = Straighter lines.")
        self.smooth_slider.valueChanged.connect(lambda v: self.smooth_label.setText(f"Smoothing (Wart Removal): {v}"))
        
        smooth_layout.addWidget(self.smooth_slider)
        layout.addLayout(smooth_layout)
        
        # 2. Corner Sharpness
        sharp_layout = QVBoxLayout()
        
        # Header with Help
        sharp_header = QHBoxLayout()
        sharp_label = QLabel("Corner Sharpness: 50")
        self.sharp_label = sharp_label
        
        sharp_help = self.create_help_btn(
            "Corner Sharpness",
            "<b>Controls the rounding radius of corners.</b><br><br>"
            "<ul>"
            "<li><b>0-30 (Round):</b> Soft, friendly, rounded corners.</li>"
            "<li><b>50 (Standard):</b> Balanced anti-aliasing.</li>"
            "<li><b>80-100 (Razor):</b> Sharp, crisp corners with minimal blur. "
            "Perfect for modern, flat design.</li>"
            "</ul>"
        )
        sharp_header.addWidget(sharp_label)
        sharp_header.addWidget(sharp_help)
        sharp_header.addStretch()
        sharp_layout.addLayout(sharp_header)
        
        self.sharp_slider = QSlider(Qt.Orientation.Horizontal)
        self.sharp_slider.setRange(0, 100)
        self.sharp_slider.setValue(50)
        self.sharp_slider.setToolTip("0 = Round, 100 = Razor Sharp")
        self.sharp_slider.valueChanged.connect(lambda v: self.sharp_label.setText(f"Corner Sharpness: {v}"))
        
        sharp_layout.addWidget(self.sharp_slider)
        layout.addLayout(sharp_layout)
        
        group.setLayout(layout)
        return group
        
    def create_stroke_panel(self):
        """Phase 8: Create 'Stroke & Polish' panel."""
        group = QGroupBox("Stroke Engine & Polish")
        layout = QVBoxLayout()
        
        # Helper method for sliders to reduce code duplication
        def add_slider(name, min_val, max_val, default_val, tooltip, help_content):
            row = QHBoxLayout()
            
            # Header
            lbl_layout = QHBoxLayout()
            label = QLabel(f"{name}: {default_val}")
            lbl_layout.addWidget(label)
            lbl_layout.addWidget(self.create_help_btn("Stroke Engine", help_content))
            lbl_layout.addStretch()
            row.addLayout(lbl_layout)
            
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(default_val)
            slider.setToolTip(tooltip)
            
            # Signals
            slider.valueChanged.connect(lambda v: label.setText(f"{name}: {v}"))
            slider.valueChanged.connect(self.apply_smart_cleanup) # Auto-apply
            
            layout.addLayout(row)
            layout.addWidget(slider)
            return slider, label

        # Stroke Weight (-10 to 10)
        self.stroke_slider, self.stroke_label = add_slider(
            "Stroke Weight (Boldness)", -10, 10, 0,
            "Thicken or Thin the lines.",
            "<b>Stroke Weight (-10 to +10):</b><br>Controls line thickness reconstruction.<br><ul><li><b>Positive (+):</b> Dilate/Grow the shape (Bold). Good for restoring borders.</li><li><b>Negative (-):</b> Erode/Shrink (Thin).</li><li><b>0:</b> Faithful.</li></ul>"
        )
        
        # Post Sharpen (0-100)
        self.sharpen_slider, self.sharpen_label = add_slider(
            "Resolution Snap (Sharpen)", 0, 100, 0,
            "Contrast enhancement at edges.",
            "<b>Resolution Snap (0-100):</b><br>Applies a final Unsharp Mask pass.<br>Use this to make the icon look crisp and 'snap' to the pixel grid after resizing."
        )
        
        group.setLayout(layout)
        return group
    
    def update_ui_state(self):
        """Update UI state based on settings."""
        if hasattr(self, 'edge_controls') and hasattr(self, 'edge_group_check'):
            self.edge_controls.setEnabled(self.edge_group_check.isChecked())
            
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
            
            # Update Info Label
            w, h = self.processor.source_image.size
            self.source_info_label.setText(f"File: {file_name} | Size: {w}x{h}")
            
            self.load_source_preview()
            
            # Set default icon name (user can edit)
            self.icon_name_input.setText(file_name)
            
            # UI State Logic
            self.generate_btn.setEnabled(True)
            self.check_btn.setEnabled(True)
            if hasattr(self, 'reveal_btn'):
                self.reveal_btn.setEnabled(True)
                self.reload_btn.setEnabled(True)
                
            self.reset_ui_controls_after_commit()
            
            # Phase 11: Auto-Audit (Instant Feedback)
            issues = IconAuditor.audit_image(self.processor.source_image)
            if hasattr(self, 'approval_status_label'):
                if not issues:
                    self.approval_status_label.setText("✅ Source is Clean")
                    self.approval_status_label.setStyleSheet("color: green; font-weight: bold;")
                    # Optional: Disable Auto-Fix if clean? 
                    # self.check_btn.setEnabled(False) # Maybe let them check anyway
                else:
                    count = len(issues)
                    self.approval_status_label.setText(f"⚠️ {count} Issues Found")
                    self.approval_status_label.setStyleSheet("color: red; font-weight: bold;")
            
            # Phase 13: Update History
            if hasattr(self, 'populate_history_combo'):
                self.populate_history_combo(path)
            
            self.apply_masking()
            self.update_preview()

    def load_source_preview(self):
        """Update the Source Inspector with the current source image."""
        if not self.processor.source_image:
            return
            
        w, h = self.processor.source_image.size
        
        # Convert PIL to QPixmap
        src_img = self.processor.source_image.copy()
        if src_img.mode != 'RGBA':
            src_img = src_img.convert('RGBA')
            
        data = src_img.tobytes('raw', 'RGBA')
        qimage = QImage(data, w, h, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        
        # Scale to fit label (Keep Aspect Ratio)
        # Max size 300x300 roughly based on layout
        pixmap = pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        self.drop_label.setPixmap(pixmap)
        self.drop_label.setText("") # Clear text
            

    
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
            # Multi-Key Logic (Phase 9)
            input_colors = [self.current_mask_color]
            
            if hasattr(self, 'enable_key_2') and self.enable_key_2.isChecked():
                input_colors.append(self.current_mask_color_2)
            
            tolerance = self.tolerance_spin.value()
            img = MaskingEngine.multi_color_mask(img, input_colors, tolerance)
            
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
        
        # Mask Choke / Expand (Phase 9) - Apply BEFORE cleaning
        # This removes fringes so the cleaner doesn't get confused
        mask_adjust = self.mask_choke_slider.value()
        if mask_adjust < 0:
             # Choke (Erode) - Remove Fringe
             img = MaskingEngine.choke_mask(img, abs(mask_adjust))
        elif mask_adjust > 0:
             # Expand (Dilate) - Recover Edge
             img = EdgeProcessor.expand_mask(img, pixels=mask_adjust)
        
        # ALWAYS apply quality enhancement (Clean by Default philosophy)
        threshold = self.edge_threshold_spin.value()
        img = EdgeProcessor.clean_edges(img, threshold=threshold, blur_radius=0.3)
        
        # Apply optional advanced features
        if hasattr(self, 'edge_group') and self.edge_group.isChecked():
            if self.defringe_check.isChecked():
                img = EdgeProcessor.defringe_simple(img, strength=0.7)
            
            # Clean Edges Checkbox
            if self.clean_edges_check.isChecked():
                 # We already did basic clean, this might be extra aggressiveness?
                 # Actually clean_edges above is minimal. 
                 pass 

        self.processor.apply_processed_image(img)
        self.update_preview()
    
    def pick_color(self):
        """Open color picker dialog (Primary Key)."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_mask_color = (color.red(), color.green(), color.blue())
            self.color_btn.setStyleSheet(
                f"background-color: rgb({color.red()}, {color.green()}, {color.blue()});"
            )
            if self.mask_color.isChecked():
                self.apply_masking()

    def pick_color_2(self):
        """Open color picker dialog (Secondary Key)."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_mask_color_2 = (color.red(), color.green(), color.blue())
            self.color_btn_2.setStyleSheet(
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
        """Apply Smart Edge Cleanup (Vector Reconstruction) with Auto-Commit."""
        if not self.processor.source_image:
            return
            
        # 1. Force Strong Defaults (Make the fix visible)
        # Using blockSignals to prevent intermediate updates if desired, 
        # but actually we want the update to happen so processed_image is ready.
        self.smooth_slider.setValue(5)
        self.sharp_slider.setValue(80)
        
        # 2. Logic is triggered by signals above, updating processed_image
        # But just in case signals are blocked or queued:
        # (The actual processing happens in update_preview which is connected to valueChanged)
        # We need to ensure update_preview finishes before committing?
        # Since this is single threaded UI, the signal should fire immediately.
        
        # 3. Auto-Commit (Phase 12)
        # This saves to history/, reloads the file, and resets the pipeline.
        self.promote_preview_to_source(confirm=False)
        
        QMessageBox.information(
            self, 
            "Auto-Fix Applied", 
            "✅ Fix Applied & Committed!\n\n"
            "1. Smoothing & Sharpening applied.\n"
            "2. Result saved as new Source.\n"
            "3. Pipeline reset for next step."
        )
        
    def promote_preview_to_source(self, confirm: bool = True):
        """Phase 10: Promote current preview to be the new source (Save & Reload)."""
        if not self.processor.processed_image:
            return
            
        # Check for changes (Phase 14)
        if self.processor.source_image:
            diff = ImageChops.difference(self.processor.source_image, self.processor.processed_image)
            if not diff.getbbox():
                if confirm:
                     QMessageBox.warning(self, "No Changes", "You haven't made any changes yet!")
                return 
            
        if confirm:
            reply = QMessageBox.question(
                self, 
                "Commit Changes?",
                "This will use your current preview as the new Original Source.\n\n"
                "1. A new version of the file will be saved to 'history/'.\n"
                "2. The app will reload this new file.\n"
                "3. All sliders and masks will be reset.\n\n"
                "Proceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            should_proceed = (reply == QMessageBox.StandardButton.Yes)
        else:
            should_proceed = True
        
        if should_proceed:
            # 1. Create History Directory
            history_dir = Path("history")
            history_dir.mkdir(exist_ok=True)
            
            # 2. Generate Unique Filename
            # {original_stem}_v{timestamp}.png
            original_stem = Path(self.current_source_path).stem
            # Remove existing version suffix if present to avoid v1_v2_v3 chains
            import re
            base_stem = re.sub(r'_v\d{14}$', '', original_stem) 
            
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            new_filename = f"{base_stem}_v{timestamp}.png"
            new_path = history_dir / new_filename
            
            # 3. Save Processed Image
            try:
                self.processor.processed_image.save(new_path)
            except Exception as e:
                QMessageBox.critical(self, "Error Saving", f"Could not save history file:\n{e}")
                return
            
            # 4. Reload as New Source (True Reset)
            # This triggers load_image -> resets masking, geometry, stroke -> updates UI
            self.load_image(str(new_path.absolute()))
            
            # 5. Toast
            QMessageBox.information(self, "Changes Committed", 
                                  f"Saved version: {new_filename}\n\n"
                                  "The pipeline has been reset. You are now working on the clean, committed version.")

    def reset_ui_controls_after_commit(self):
        """Reset all processing controls to neutral state."""
        # 1. Geometry (The Enforcer) - Reset to Neutral
        # We set smoothing to 0 because the image is ALREADY smoothed.
        self.smooth_slider.blockSignals(True)
        self.smooth_slider.setValue(0) # 0 = Faithful to the new source
        self.smooth_slider.blockSignals(False)
        self.smooth_label.setText("Smoothing (Wart Removal): 0")
        
        # Sharpness stays at 50 (Neutral/Standard)
        self.sharp_slider.blockSignals(True)
        self.sharp_slider.setValue(50) 
        self.sharp_slider.blockSignals(False)
        self.sharp_label.setText("Corner Sharpness: 50")
        
        # Stroke Engine - Reset to Neutral
        self.stroke_slider.blockSignals(True)
        self.stroke_slider.setValue(0)
        self.stroke_slider.blockSignals(False)
        self.stroke_label.setText("Stroke Weight (Boldness): 0")
        
        self.sharpen_slider.blockSignals(True)
        self.sharpen_slider.setValue(0)
        self.sharpen_slider.blockSignals(False)
        self.sharpen_label.setText("Resolution Snap (Sharpen): 0")
        
        # 2. Cleanup Tab - Reset
        self.mask_none.setChecked(True) # Disable masking
        
        # Reset Masking Lab
        self.mask_choke_slider.blockSignals(True)
        self.mask_choke_slider.setValue(0)
        self.mask_choke_slider.blockSignals(False)
        if hasattr(self, 'enable_key_2'):
            self.enable_key_2.setChecked(False)
            
        self.defringe_check.setChecked(False)
        self.edge_controls.setEnabled(False)
        
        # 3. Geometry Tab - Reset (Simulated)
        # We already reset sliders above

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

    def reveal_source_file(self):
        """Reveal the current source file in Finder/Explorer (Escape Hatch)."""
        if not self.current_source_path:
            return
            
        path = str(Path(self.current_source_path).absolute())
        
        try:
            if sys.platform == 'darwin':
                import subprocess
                subprocess.run(['open', '-R', path])
            elif sys.platform == 'win32':
                import subprocess
                subprocess.run(['explorer', '/select,', path])
            else:
                # Linux fallback
                import subprocess
                subprocess.run(['xdg-open', str(Path(path).parent)])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not reveal file:\n{e}")

    def reload_source_file(self):
        """Reload the source file from disk (Pull Manual Edits)."""
        if not self.current_source_path:
            return
            
        # Verify file exists
        if not Path(self.current_source_path).exists():
            QMessageBox.warning(self, "Error", "Source file no longer exists!")
            return
            
        # Reload triggers full reset
        self.load_image(self.current_source_path)
        
        QMessageBox.information(self, "Reloaded", "File reloaded from disk.\nMasking and Filters have been reset to match the new pixels.")

    def create_source_inspector_v2(self):
        """Phase 11: Updated Source Inspector (Escape Hatch & Feedback)."""
        group = QGroupBox("Source Inspector (Original)")
        layout = QVBoxLayout()
        
        # Status Bar
        status_layout = QHBoxLayout()
        self.approval_status_label = QLabel("Waiting for Source...")
        self.approval_status_label.setStyleSheet("color: #666; font-weight: bold;")
        self.approval_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.approval_status_label)
        layout.addLayout(status_layout)
        
        # Source viewing area
        self.drop_label = TransparencyLabel()
        self.drop_label.setText("Drop Source Image Here")
        self.drop_label.setMinimumSize(300, 300)
        # Skew Fix: Force Center, No Scale
        self.drop_label.setScaledContents(False) 
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.drop_label, 1) # Stretch 1
        
        # Info readout
        self.source_info_label = QLabel("No image loaded")
        self.source_info_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.source_info_label)
        
        # History / Version Control (Phase 13)
        history_layout = QHBoxLayout()
        history_layout.addWidget(QLabel("Version:"))
        self.history_combo = QComboBox()
        self.history_combo.addItem("Current (Latest)")
        self.history_combo.setEnabled(False)
        self.history_combo.currentIndexChanged.connect(self.load_history_version)
        history_layout.addWidget(self.history_combo, 1) # Stretch
        layout.addLayout(history_layout)
        
        # Action Bar 1: Load/External
        action_layout = QHBoxLayout()
        choose_btn = QPushButton("📂 Open")
        choose_btn.clicked.connect(self.choose_file)
        action_layout.addWidget(choose_btn)
        
        self.reveal_btn = QPushButton("🔎 Reveal")
        self.reveal_btn.setToolTip("Show in Finder/Explorer for Photoshop editing")
        self.reveal_btn.setEnabled(False)
        self.reveal_btn.clicked.connect(self.reveal_source_file)
        action_layout.addWidget(self.reveal_btn)
        
        self.reload_btn = QPushButton("🔄 Reload")
        self.reload_btn.setToolTip("Reload file from disk (after external edit)")
        self.reload_btn.setEnabled(False)
        self.reload_btn.clicked.connect(self.reload_source_file)
        action_layout.addWidget(self.reload_btn)
        
        layout.addLayout(action_layout)
        
        # Action Bar 2: Audit/Commit
        audit_layout = QHBoxLayout()
        
        self.check_btn = QPushButton("🩺 Check Icon")
        self.check_btn.setEnabled(False)
        self.check_btn.clicked.connect(self.run_icon_audit)
        audit_layout.addWidget(self.check_btn)
        
        self.commit_btn = QPushButton("⬆ Commit Changes")
        self.commit_btn.setToolTip("Save new version to history/ and Reload")
        self.commit_btn.clicked.connect(self.promote_preview_to_source)
        audit_layout.addWidget(self.commit_btn)
        
        layout.addLayout(audit_layout)
        
        group.setLayout(layout)
        return group
        return group

    def populate_history_combo(self, current_path: str):
        """Populate history dropdown with ALL versions (Unified Timeline)."""
        if not hasattr(self, 'history_combo'):
            return
            
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        
        # 1. Identify Base Stem (Root of the Timeline)
        current_stem = Path(current_path).stem
        import re
        base_stem = re.sub(r'_v\d{14}$', '', current_stem)
        
        history_dir = Path("history")
        versions = []
        
        # 2. Add History Versions
        if history_dir.exists():
            for f in history_dir.glob(f"{base_stem}_v*.png"):
                try:
                    ts_str = f.stem.split('_v')[-1]
                    from datetime import datetime
                    dt = datetime.strptime(ts_str, "%Y%m%d%H%M%S")
                    display_time = dt.strftime("%H:%M:%S")
                    versions.append({
                        'path': str(f.absolute()),
                        'name': f"v.{ts_str[-6:]} ({display_time})", 
                        'ts': ts_str
                    })
                except:
                    continue
                    
        # Sort by timestamp descending (newest first)
        versions.sort(key=lambda x: x['ts'], reverse=True)
        
        # 3. Add Items to Combo (Unified List)
        # Scan list to find which one is "Current"
        current_idx = 0 
        
        # Add matches
        for i, v in enumerate(versions):
            item_name = v['name']
            item_path = v['path']
            
            # Check if this is the active file
            if item_path == str(Path(current_path).absolute()):
                 item_name += " (Active)"
                 current_idx = i
                 
            self.history_combo.addItem(item_name, item_path)
            
        # If the list is empty (first time load), or current path isn't in history logic 
        # (maybe it's the original file in root), we should append it or handle it.
        # Ideally, we want the timeline to include everything.
        
        # Check if current_path is effectively "Original" (no version in name)
        # If it's not in the versions list, it might be the root file.
        # Let's verify if current selection was found.
        found_active = False
        for i in range(self.history_combo.count()):
            if self.history_combo.itemData(i) == str(Path(current_path).absolute()):
                self.history_combo.setCurrentIndex(i)
                found_active = True
                break
                
        if not found_active:
             # Current file is likely the Original Source (root folder)
             # Add it at the end? Or beginning?
             # Let's add it as "Original Source"
             self.history_combo.addItem(f"Original Source (Active)", str(Path(current_path).absolute()))
             self.history_combo.setCurrentIndex(self.history_combo.count() - 1)
                 
        self.history_combo.setEnabled(True)
        self.history_combo.blockSignals(False)

    def load_history_version(self):
        """Load selected version from history."""
        # Get data from selected item
        path = self.history_combo.currentData()
        if path and Path(path).exists():
            # Load it (this triggers standard load pipeline)
            self.load_image(path)
            
            # Note: load_image will call populate_history_combo again via the integration step we are about to do.
            # So we don't need to manually update selection here.
