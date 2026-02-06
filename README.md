# Icon Factory

A professional icon creation utility with Mac-like ease of use and powerful masking capabilities.

## Features

- **Drag & Drop Interface**: Simply drag an image to get started
- **Auto-Crop**: Automatically crop to tight borders around content
- **Color Masking**: Remove background colors with adjustable tolerance
- **Advanced Edge Processing**:
  - **Defringe**: Remove color halos from transparent edges
  - **Clean Edges**: Remove pixel debris and artifacts (enabled by default)
  - **Mask Expansion/Contraction**: Dynamically adjust mask size (-3 to +3 pixels)
  - **Edge Threshold**: Adjustable sensitivity for debris removal
- **Multi-Format Export**:
  - Windows ICO (3 variants: full alpha, binary alpha, with glow)
  - Mac ICNS (native iconutil support)
  - PNG set (all standard sizes)
- **Organized Output**: Creates structured directories with metadata
- **Archive Support**: Optional ZIP packaging
- **Real-time Preview**: See changes instantly with background options

## Quality Philosophy

**Icon Factory follows a "Clean by Default" philosophy:**

Icons are designed to be professional, with clean lines and no artifacts. Quality enhancement (clean edges, anti-aliasing) is **always applied** to ensure professional output.

- ✅ **Clean Edges**: Always removes pixel debris and artifacts
- ✅ **Smooth Edges**: Always applies anti-aliasing for professional quality
- ✅ **Adjustable**: Edge threshold can be fine-tuned (0-50 alpha)
- ⚠️ **Philosophy**: If output is garbage, it's because you chose that, not because Icon Factory failed to clean it

Advanced users can access optional features like Defringe and Mask Adjust in Advanced Options.

## Installation

```bash
cd icon-factory
pip install -r requirements.txt
```

## Usage

```bash
python icon_factory.py
```

### Quick Start

1. Drag and drop an image or click "Choose File..."
2. **Edit the icon name** if desired (defaults to source filename)
3. Select masking mode (None, Auto-Crop, or Color Mask)
4. Choose export formats (Windows ICO, Mac ICNS, PNG Set)
5. Click "Generate Icons"

### Masking Modes

- **None (Keep Original)**: Use image as-is
- **Auto-Crop (Detect Content)**: Automatically crop to content bounds
- **Remove Color (Entire Image)**: Remove a specific color from entire image
  - ✂️ **Auto-Crop After Masking**: Automatically crop to tight bounds after removal (default ON)
- **Remove Color (Borders Only)**: Magic wand - remove color from edges only
  - ✂️ **Auto-Crop After Masking**: Automatically crop to tight bounds after removal (default ON)

### Export Options

- **Windows ICO**: Creates 3 variants for maximum compatibility
  - Full alpha (best quality)
  - Binary alpha (Windows-compatible)
  - With glow (enhanced visibility)
- **Mac ICNS**: Native macOS icon format (requires macOS)
- **PNG Set**: Individual PNG files at all standard sizes

### Output Structure

When "Create Archive" is enabled:

```
icon-name/
├── metadata.json
├── source/
│   └── original.png
├── windows/
│   ├── icon_full_alpha.ico
│   ├── icon_binary_alpha.ico
│   └── icon_with_glow.ico
├── mac/
│   └── icon.icns
└── png/
    ├── icon_16.png
    ├── icon_32.png
    ├── icon_48.png
    ├── icon_64.png
    ├── icon_100.png  # Perfect for web forms
    ├── icon_128.png
    ├── icon_256.png
    ├── icon_512.png
    └── icon_1024.png
```

## Requirements

- Python 3.8+
- PyQt6
- Pillow
- numpy
- macOS (for ICNS export via iconutil)

## License

**Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**

- ✅ **Free for personal and educational use**
- ✅ **Requires attribution** (credit to Spencer Streeter)
- ❌ **Commercial use prohibited** without permission

For commercial licensing inquiries, please contact the author.

See [LICENSE](LICENSE) file for full details.

Copyright (c) 2026 Spencer Streeter
