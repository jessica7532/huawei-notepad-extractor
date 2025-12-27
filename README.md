# Huawei Notepad Extractor / 华为备忘录提取工具

A Python script for batch extracting Huawei phone notepad content with support for text extraction and screenshot saving.

[中文文档](README_CN.md) | English

## ⚠️ Disclaimer

This tool is for **personal learning and backup purposes only**. **Commercial use is strictly prohibited.**
- The author assumes no responsibility for any issues arising from the use of this tool
- Ensure you have the right to access and back up your own data
- Huawei may update the UI at any time, which could cause the script to fail
- It is recommended to test on a small amount of data first
- **Reselling or redistributing this tool for profit is prohibited**

## ✨ Features

- ✅ **Three extraction modes**: Full auto / Last screen / With screenshots
- ✅ **Smart deduplication**: Content-based deduplication, supports multiple entries on the same day
- ✅ **Complete extraction**: Extracts title, timestamp, and body content
- ✅ **Handwriting support**: Save screenshots of handwritten/image notes
- ✅ **Auto-naming**: Automatically names output files based on notepad folder name
- ✅ **Non-destructive**: Read-only, does not modify/delete original notes

## 📋 System Requirements

### Required Software
- **Python 3.7+**
- **ADB (Android Debug Bridge)**
- **Huawei/Honor Phone** (using Huawei Notepad app)

### Tested Devices
- Huawei budget model (circa 2020, Android version unknown)

*Theoretically supports all devices using the Huawei Notepad app*

## 🚀 Quick Start

### 1. Install Python

#### Windows:
1. Visit [Python Official Website](https://www.python.org/downloads/)
2. Download the latest Python 3.x
3. **Important**: Check "Add Python to PATH" during installation
4. Verify installation: Open Command Prompt and type `python --version`

#### macOS:
```bash
# Install using Homebrew
brew install python3

# Verify installation
python3 --version
```

#### Linux:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip

# Verify installation
python3 --version
```

### 2. Install ADB

#### Windows:
This repository includes ADB tools (platform-tools folder), no additional installation required.

Or download the latest version from [Google Official](https://developer.android.com/studio/releases/platform-tools).

#### macOS:
```bash
brew install android-platform-tools
```

#### Linux:
```bash
sudo apt install android-tools-adb
```

Verify installation:
```bash
adb version
```

### 3. Phone Setup

1. **Enable Developer Options**:
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times
   - Return to Settings and find "Developer Options"

2. **Enable USB Debugging**:
   - Enter Developer Options
   - Enable "USB Debugging"
   - Authorize "Allow USB debugging" on your phone when connected to computer

3. **Verify Connection**:
   ```bash
   adb devices
   ```
   You should see your device listed

### 4. Run the Script

1. **Download this repository**:
   ```bash
   git clone https://github.com/yourusername/huawei-notepad-extractor.git
   cd huawei-notepad-extractor
   ```

2. **Enter ADB tools directory** (if using the bundled version):
   ```bash
   cd platform-tools
   ```

3. **Open Huawei Notepad app**, navigate to the folder you want to extract (e.g., "Dream Records")

4. **Run the script**:
   ```bash
   python auto_extract_notes_ultimate.py
   ```

5. **Select mode**:
   ```
   Mode selection:
     1. Full auto mode - Extract from top to bottom (Recommended)
     2. Last screen mode - Extract current screen only
     3. With screenshots mode - Extract text + save screenshots
   Choose mode (1/2/3): 
   ```

## 📖 Usage Guide

### Mode 1: Full Auto (Recommended)
- **Use case**: Extract all notes from an entire folder
- **Steps**:
  1. Manually scroll to the **top** of the notepad list
  2. Select mode 1 and press Enter
  3. Script automatically extracts until the last entry
- **Output**: `FolderName.txt`

### Mode 2: Last Screen
- **Use case**: Fill in missing entries, extract the last few notes
- **Steps**:
  1. Manually scroll to the **bottom** of the notepad list
  2. Select mode 2 and press Enter
  3. Script extracts 5 entries from current screen
- **Output**: `FolderName.txt`

### Mode 3: With Screenshots
- **Use case**: Notes with handwriting/images
- **Steps**:
  1. Enter folder containing handwritten notes
  2. Manually scroll to the **top** of the list
  3. Select mode 3 and press Enter
  4. Script extracts text + screenshots
- **Output**:
  - `FolderName.txt` - Text content
  - `FolderName_screenshots/` - Screenshot folder

### Output File Example

```
==================================================
Note #1 - Dream Records - December 27 03:14
==================================================
Today I dreamed of a very strange scene...
(Note content)

[📸 Screenshot: Dream_Records_screenshots/note_0001.png]  (if mode 3)
```

## 🔧 Coordinate Adjustment (If Click Position is Inaccurate)

Due to different **screen resolutions** on different devices, click coordinates may need adjustment.

### Symptoms
- Script clicks in wrong position during execution
- Doesn't open note detail page
- Clicks other locations

### Solution

#### Method 1: Measure Coordinates Using Online Tools
1. **Screenshot current screen**:
   ```bash
   adb shell screencap -p /sdcard/screen.png
   adb pull /sdcard/screen.png .
   ```

2. **Use these tools to measure coordinates** (choose one):
   - [Photopea](https://www.photopea.com/) - Free online Photoshop, shows coordinates when mouse moves
   - [GIMP](https://www.gimp.org/) - Free open-source image editor
   - [Paint.NET](https://www.getpaint.net/) - Free Windows tool
   - [Pixlr](https://pixlr.com/) - Online image editor
   - Windows built-in **Paint**: Open image, coordinates shown in bottom left when mouse moves

3. **Measure center coordinates of**:
   - Center point of first note (usually upper 1/4 of list)
   - Center points of 5 notes on last screen (from top to bottom)

4. **Modify script**:
   - Open `auto_extract_notes_ultimate.py`
   - Search for `tap(350, 560)` 
   - Replace with your measured coordinates `tap(your_x, your_y)`
   - Search for `POSITIONS = [640, 880, 1140, 1395, 1654]`
   - Replace with your measured 5 y-coordinates

#### Method 2: View Real-time Coordinates Using ADB
```bash
# Enable pointer location display
adb shell settings put system pointer_location 1

# Tap on phone and observe coordinates at top of screen
# Record coordinates of first note

# Disable pointer location
adb shell settings put system pointer_location 0
```

## ⚠️ Important Notes

### Before Use
- ✅ Ensure phone has sufficient battery (avoid interruption)
- ✅ Disable auto screen lock (Settings → Display → Sleep → Never)
- ✅ Keep USB connection stable
- ✅ Test on small amount of data first

### During Use
- ⚠️ **Do not touch phone screen** (interferes with script)
- ⚠️ **Do not disconnect USB**
- ⚠️ If interruption needed, close command line window directly
- ⚠️ Script pauses for 3 seconds every 30 clicks (normal behavior)

### Special Cases
- 📝 **Pure handwritten notes**: Content is empty but screenshot is saved (mode 3)
- 📝 **Duplicate content**: Automatically detects bottom when same content found 3 times consecutively
- 📝 **Timestamp**: Automatically extracts creation/modification time
- 📝 **Folder name**: Automatically recognizes Huawei notepad folder name as output filename

### Known Limitations
- ❌ Does not support voice memos
- ❌ Screenshots only capture first screen (long content requires manual scrolling)
- ❌ Images/handwriting can only be screenshotted, original images cannot be extracted
- ❌ Does not support notepad apps from other brands (OPPO, Xiaomi, etc.)

## 🐛 FAQ

### Q: Error "adb is not recognized as an internal or external command"
**A:** ADB not properly installed or not in PATH
- Windows: Ensure script is run from within platform-tools folder
- Or add platform-tools folder path to system environment variables

### Q: Error "no devices/emulators found"
**A:** Phone not properly connected
1. Check if USB cable is connected
2. Check if USB debugging is authorized on phone
3. Run `adb devices` to view device list

### Q: Script clicks wrong position
**A:** Coordinates need adjustment, see "Coordinate Adjustment" section

### Q: Extracted content is empty
**A:** Possible reasons:
1. Note itself is pure handwriting (use mode 3)
2. UI structure changed (Huawei updated app)
3. Click position wrong, didn't enter detail page

### Q: Can I extract multiple folders?
**A:** Need to manually switch folders, extract one folder at a time

### Q: Will the script delete my notes?
**A:** **No!** Script only reads data, does not modify/delete anything

### Q: How long to extract 1000+ notes?
**A:** 
- Mode 1/2: About 20-30 minutes (~1 second per note)
- Mode 3: About 40-60 minutes (requires screenshots)

## 🤝 Contributing

Issues and Pull Requests are welcome!

### When submitting an Issue, please provide:
- Phone model and Android version
- Error message screenshot
- `window_dump.xml` file (if coordinate issue)

### When submitting a PR, please:
- Specify new device model adapted
- Provide test screenshots

## 👥 Authors

**Jessica & Claude**
- Jessica: Original concept, testing, and iteration
- Claude (Anthropic): Development assistance and optimization

This project demonstrates the collaboration between human creativity and AI capabilities. Jessica identified the problem, designed the solution approach, and provided iterative feedback, while Claude implemented the technical details and optimizations.

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

**⚠️ Important**: This is a **non-commercial tool**. Any commercial use, resale, or redistribution for profit is **strictly prohibited** and violates the license terms.

## 🙏 Acknowledgments

Thanks to all users who tested and provided feedback!

---

**Note**: This project is not affiliated with Huawei. It is a personal data backup tool only.
