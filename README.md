# Y Tune - YouTube Music Player 🎶

**Y Tune** is a feature-rich desktop application for streaming and playing music from YouTube. Built with Python, Tkinter 🐍, and `pygame`, it offers a sleek interface for searching, playing, and managing music, with `ffmpeg` for high-quality audio processing. 🚀

## Features ✨

- 🔍 **Search YouTube**: Find songs by name and stream them instantly.
- 🎵 **Playback Controls**: Play, pause, skip, and seek through songs with a progress bar.
- 🔄 **Playback Modes**: Choose from shuffle, repeat one, repeat all, or sequential play.
- ❤️ **Favorites**: Save and manage your favorite songs.
- 🕒 **Recent Tracks**: Keep track of recently played songs.
- 📜 **Playlist Support**: Browse and play from search results as a playlist.
- 🖱️ **Intuitive GUI**: Search bar with placeholder text, listboxes for playlists, favorites, and recent tracks.
- ⚡ **Smooth Performance**: Threading and retry logic ensure non-blocking and reliable downloads.
- 🌐 **Cross-platform**: Works on Windows, macOS, and Linux.

> 📝 *Note: Y Tune is actively developed, with plans for volume control and enhanced playlist management.*

## Prerequisites ✅

- 🐍 **Python 3.6 or higher** installed.
- 🌍 A stable internet connection for streaming from YouTube.
- 🎵 **FFmpeg** installed and accessible:
  - 📂 Included in the project as `ffmpeg/` (with the `ffmpeg` executable).
  - 🔄 Alternatively, install `ffmpeg` globally and add to your system PATH (see [FFmpeg Setup](#ffmpeg-setup)).

## Installation 🛠️

1. **Clone the Repository** 📥

   ```bash
   git clone https://github.com/<your-username>/y-tune.git
   cd y-tune
   ```

2. **Install Dependencies** 📦

   Install required Python libraries listed in `requirements.txt`:

   ```bash
   pip install -r requirements.txt
   ```

   > ℹ️ *Dependencies include* `yt_dlp` *for YouTube streaming,* `pygame` *for audio playback,* `mutagen` *for MP3 metadata, and* `tenacity` *for retry logic.* `tkinter` *is included with Python.*

## FFmpeg Setup 🎬

Y Tune requires the `ffmpeg` executable for audio processing. The project includes the `ffmpeg` executable in the `ffmpeg/` folder, but configuration is needed:

- **Windows** 🪟:
  - ✅ Ensure `ffmpeg.exe` is in the `y-tune/ffmpeg/` folder, located in the same directory as `Y Tune.py` or the generated `.exe`.
  - 🔧 The app uses this local copy by default.
- **macOS/Linux** 🍎🐧:
  - ✅ Ensure the `ffmpeg` executable is in the `y-tune/ffmpeg/` folder, located in the same directory as `Y Tune.py` or the generated `.exe`.
  - 🔑 Grant executable permissions:

    ```bash
    chmod +x ffmpeg/ffmpeg
    ```

- **Global FFmpeg** (Optional) 🌍:
  - 📥 Download from [FFmpeg's official site](https://ffmpeg.org/download.html).
  - 🛠️ Install and add to your system PATH, then verify:

    ```bash
    ffmpeg -version
    ```

> ⚠️ **Important**: When running `Y Tune.py` or the generated `.exe`, ensure the `ffmpeg/` folder (containing `ffmpeg.exe` on Windows or `ffmpeg` on macOS/Linux) is in the same directory as `Y Tune.py` or the `.exe`. The app will not work without it.

## Usage 🎵

1. ✅ Set up `ffmpeg` (see [FFmpeg Setup](#ffmpeg-setup)).

2. 🚀 Run the application:

   ```bash
   python "Y Tune.py"
   ```

   > ℹ️ Ensure the `ffmpeg/` folder is in the same directory as `Y Tune.py`.

3. 🖥️ Explore the interface:

   - **Search Bar** 🔍: Enter a song name or query (placeholder: "Search for songs..."). Press `Enter` or click the 🔍 button to search.
   - **Playlist** 📜: View search results in the central listbox. Click a song to play it.
   - **Favorites** ❤️: Add songs to favorites with the ♡/♥ button. View and play from the left listbox.
   - **Recent** 🕒: Recently played songs appear in the right listbox.
   - **Controls** 🎮:
     - ▶/⏸: Play or pause the current song.
     - ⏮/⏭: Skip to previous or next song.
     - 🔀/🔁/🔄: Cycle through playback modes (Off, Shuffle, Repeat One, Repeat All).
     - ▶ All: Play all songs in the playlist from the start.
     - Progress Bar: Drag to seek or click to jump to a specific time.
   - **Shortcuts** ⌨️: Press `Space` to play/pause (except in the search bar).
   - **Status Messages**: Temporary feedback (e.g., "Playing") appears and reverts to "Ready" after 5 seconds.

4. 🎧 Play music:

   - Search for a song or select from favorites/recent.
   - `yt_dlp` fetches the audio stream with retry logic (up to 3 attempts) for reliability.
   - `ffmpeg` processes it for playback.
   - Songs are cached in `.cache/.downloaded/` to reduce redundant downloads.

## How It Works 🛠️

- **GUI** 🖼️: Tkinter-based interface with a search bar, listboxes (Playlist, Favorites, Recent), and playback controls.
- **Search** 🔍: Uses `yt_dlp` to query YouTube and display up to 50 results, with `tenacity` for retrying failed searches.
- **Playback** 🎵: `pygame` handles audio playback, with `mutagen` for reading MP3 duration.
- **Audio Processing** 🎬: `ffmpeg` extracts audio from YouTube streams in MP3 format (192 kbps).
- **Threading** ⚡: Non-blocking downloads and searches run in separate threads for a responsive UI.
- **Retry Logic** 🔄: `tenacity` retries failed searches and downloads (up to 3 attempts, 2-second wait).
- **Data Management** 📂:
  - Favorites and recent songs are saved in `.data/favorites.json` and `.data/recent.json` with thread-safe operations.
  - Search results are cached in `.cache/search.json`.
- **Playback Modes** 🔄: Supports shuffle, repeat one, repeat all, or sequential playback.
- **Seeking** ⏩: Drag the progress bar to seek, with debouncing for smooth performance and reset on new song playback.

## Building an Executable 📦

To create a standalone `.exe` (e.g., for Windows), use PyInstaller:

1. 📥 Install PyInstaller:

   ```bash
   pip install pyinstaller
   ```

2. 🛠️ Create the executable:

   ```bash
   pyinstaller --onefile "Y Tune.py"
   ```

3. 📂 Copy the `ffmpeg/` folder:

   - After generating the `.exe`, copy the `ffmpeg/` folder (containing `ffmpeg.exe` on Windows or `ffmpeg` on macOS/Linux) to the `dist/` folder, so it is in the same directory as the `.exe`.

4. ✅ Run the `.exe`:

   - Ensure the `ffmpeg/` folder is in the same directory as the `.exe` when running it.

> ⚠️ **Note**: The `ffmpeg/` folder must be manually placed in the same directory as the `.exe` after building, as it is not automatically included by PyInstaller. The app requires `ffmpeg` to function.

## Project Structure 📂

```
y-tune/
│
├── Y Tune.py            # Main application script 🐍
├── ffmpeg/              # Folder with ffmpeg executable 🎬
├── .cache/              # Cached songs and search results 📥
├── .data/               # Favorites and recent song data 📋
├── requirements.txt     # Python dependencies 📦
├── README.md            # Project documentation 📝
└── dist/                # (Generated) Folder for .exe output 📦
```

## Contributing 🤝

We welcome contributions! To get started:

1. 🍴 Fork the repository.
2. 🌿 Create a branch (`git checkout -b feature-branch`).
3. ✍️ Commit changes (`git commit -m "Add feature"`).
4. 🚀 Push to your fork (`git push origin feature-branch`).
5. 📬 Open a pull request.

## License 📜

Licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact 📬

For questions or feedback, open an issue on the [GitHub repository](https://github.com/<your-username>/y-tune) or contact <your-contact-info>.

---

Happy listening with Y Tune! 🎧🎵
