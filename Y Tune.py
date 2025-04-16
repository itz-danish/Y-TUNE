import tkinter as tk
from tkinter import Entry, Button, Label, Frame, Listbox, Scrollbar, END, Scale, HORIZONTAL
import pygame
import os
from mutagen.mp3 import MP3
import yt_dlp
import json
import sys
import time
import random
import threading
from queue import Queue
from tenacity import retry, stop_after_attempt, wait_fixed

# Ensure UTF-8 encoding for console output
sys.stdout.reconfigure(encoding='utf-8')

# Global variables for tracking player state
is_playing = False
is_paused = False
music_length = 0
seek_offset = 0
current_playlist_index = -1
current_song = None
playback_mode = "off"
last_click_time = 0  # For debouncing listbox clicks
is_seeking = False  # Track if user is dragging the progress bar
last_seek_time = 0  # For debouncing seek events

# Thread-safe queue for UI updates from threads
ui_queue = Queue()

# Initialize cache and data directories
CACHE_DIR = os.path.join(".cache", ".downloaded")
DATA_DIR = ".data"
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Lock for thread-safe file operations
file_lock = threading.Lock()

# In-memory caches for JSON data
favorites_cache = []
recent_cache = []
search_cache = []

# Check UI queue for updates
def check_ui_queue():
    try:
        while not ui_queue.empty():
            callback, args = ui_queue.get_nowait()
            callback(*args)
    except:
        pass
    root.after(100, check_ui_queue)

# Play or pause the current song
def play():
    global is_playing, is_paused, music_length, current_song, seek_offset
    song_files = [f for f in os.listdir(CACHE_DIR) if os.path.isfile(os.path.join(CACHE_DIR, f))]
    if not song_files:
        set_status("No song file found!")
        return

    song_path = os.path.join(CACHE_DIR, song_files[0])

    if not is_playing:
        if not os.path.exists(song_path):
            set_status(f"Music file not found: {song_path}")
            return

        try:
            pygame.mixer.init(buffer=2048)  # Larger buffer for smoother seeking
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.play(start=seek_offset)
            song_name(os.path.basename(song_path))
            progress_var.set(0)  # Reset progress bar
            seek_offset = 0

            audio = MP3(song_path)
            music_length = audio.info.length
            progress_bar.config(to=music_length)
            update_time_display(0)

            update_progress_bar()
            is_playing = True
            is_paused = False
            play_button.config(text="⏸")
            pygame.mixer.music.set_endevent(pygame.USEREVENT)
            set_status("Playing")
        except Exception as e:
            set_status(f"Error playing song: {e}")

    elif is_playing and not is_paused:
        pygame.mixer.music.pause()
        is_paused = True
        play_button.config(text="▶")
        set_status("Paused")

    elif is_playing and is_paused:
        pygame.mixer.music.unpause()
        is_paused = False
        play_button.config(text="⏸")
        set_status("Playing")

# Display the song name in the UI
def song_name(name):
    song_title.config(text=name[:50] + "..." if len(name) > 50 else name)

# Update the time display (MM:SS)
def update_time_display(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    total_mins = int(music_length // 60)
    total_secs = int(music_length % 60)
    song_duration.config(text=f"Time: {mins}:{secs:02d} / {total_mins}:{total_secs:02d}")

# Update the progress bar and check for song end
def update_progress_bar():
    global is_playing, is_paused, current_playlist_index, is_seeking
    if is_playing and not is_paused and pygame.mixer.music.get_busy() and not is_seeking:
        current_time = pygame.mixer.music.get_pos() / 1000
        total_time = seek_offset + current_time
        if total_time <= music_length:
            progress_var.set(total_time)
            update_time_display(total_time)
        else:
            progress_var.set(music_length)
            update_time_display(music_length)
    
    for event in pygame.event.get():
        if event.type == pygame.USEREVENT and is_playing and not is_paused:
            handle_song_end()
    
    root.after(1000, update_progress_bar)

# Handle song end based on playback mode
def handle_song_end():
    global current_playlist_index, playback_mode
    if playback_mode == "repeat_one":
        download_play(current_song['url'], current_song['title'])
    else:
        playlist = search_cache
        if not playlist:
            stop_current_song()
            set_status("Playlist is empty")
            return

        if playback_mode == "shuffle":
            current_playlist_index = random.randint(0, len(playlist) - 1)
        elif playback_mode == "repeat_all" or current_playlist_index < len(playlist) - 1:
            current_playlist_index = (current_playlist_index + 1) % len(playlist) if playback_mode == "repeat_all" else current_playlist_index + 1
        else:
            stop_current_song()
            set_status("Playback stopped")
            return

        if 0 <= current_playlist_index < len(playlist):
            song = playlist[current_playlist_index]
            current_song = {'title': song['title'], 'url': song['url']}
            download_play(song['url'], song['title'])
            update_favorite_button_state(song['title'])
        else:
            stop_current_song()
            set_status("Invalid playlist index")

# Seek to a specific position in the song
def on_seek(val, update_audio=True):
    global seek_offset, is_seeking, last_seek_time
    if not is_playing:
        return
    
    current_time = time.time()
    if current_time - last_seek_time < 0.1:  # Debounce seek events
        return
    last_seek_time = current_time

    try:
        seek_offset = float(val)
        progress_var.set(seek_offset)
        update_time_display(seek_offset)
        
        if update_audio and not is_paused:
            pygame.mixer.music.play(start=seek_offset)
    except Exception as e:
        set_status(f"Seek error: {e}")

# Handle progress bar dragging
def on_seek_drag(event):
    global is_seeking
    if not is_playing:
        return
    is_seeking = True
    if not is_paused:
        pygame.mixer.music.pause()
    val = progress_var.get()
    on_seek(val, update_audio=False)

# Handle progress bar release
def on_seek_release(event):
    global is_seeking
    if not is_playing:
        return
    is_seeking = False
    val = progress_var.get()
    on_seek(val, update_audio=True)
    if not is_paused:
        pygame.mixer.music.unpause()
        set_status("Playing")

# Search for songs by name
def search_by_name():
    query = search_entry.get().strip()
    if not query:
        set_status("Please enter a search query")
        return

    set_status("Searching...")
    threading.Thread(target=perform_search, args=(query,), daemon=True).start()

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def perform_search(query):
    max_results = 50
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'default_search': 'ytsearch',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        
        video_list = []
        if search_results and 'entries' in search_results:
            for entry in search_results['entries']:
                if entry:
                    title = entry.get('title', 'Unknown Title')
                    video_id = entry.get('id', '')
                    url = f"https://www.youtube.com/watch?v={video_id}" if video_id else "N/A"
                    duration = entry.get('duration', 0) or 0
                    video_list.append({
                        'title': title,
                        'url': url,
                        'duration': f"{duration // 60} min {duration % 60} sec"
                    })

        global search_cache
        with file_lock:
            search_cache = video_list
            os.makedirs('.cache', exist_ok=True)
            with open(os.path.join('.cache', 'search.json'), 'w', encoding='utf-8') as f:
                json.dump(video_list, f, indent=2, ensure_ascii=False)

        ui_queue.put((update_search_results, (video_list,)))
    except Exception as e:
        ui_queue.put((set_status, (f"Search error: {e}",)))

def update_search_results(video_list):
    playlist_listbox.delete(0, END)
    for video in video_list:
        add_to_listbox(section="playlist", item=video["title"])
    set_status(f"Found {len(video_list)} songs")

# Stop the current song
def stop_current_song():
    global is_playing, is_paused, is_seeking, seek_offset
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        is_playing = False
        is_paused = False
        is_seeking = False
        seek_offset = 0
        progress_var.set(0)
        update_time_display(0)
        play_button.config(text="▶")
        set_status("Stopped")
    except Exception as e:
        set_status(f"Error stopping music: {e}")

# Delete the current song file
def delete_current_song_file():
    folder = CACHE_DIR
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            for _ in range(3):
                try:
                    with file_lock:
                        os.remove(file_path)
                    break
                except PermissionError:
                    time.sleep(0.5)
                except Exception as e:
                    set_status(f"Error deleting file {file_path}: {e}")
                    break

# Toggle favorite status for the current song
def toggle_favorite():
    global current_song, favorites_cache
    if not current_song:
        set_status("No song selected")
        return
    
    song_title = current_song['title']
    song_url = current_song['url']
    
    song_data = {'title': song_title, 'url': song_url}
    if song_data not in favorites_cache:
        favorites_cache.append(song_data)
        add_to_listbox("favorites", song_title)
        favorite_button.config(text="♥")
        set_status(f"Added '{song_title}' to favorites")
    else:
        favorites_cache[:] = [f for f in favorites_cache if f['title'] != song_title]
        fav_listbox.delete(0, END)
        for f in favorites_cache:
            add_to_listbox("favorites", f['title'])
        favorite_button.config(text="♡")
        set_status(f"Removed '{song_title}' from favorites")
    
    with file_lock:
        with open(os.path.join(DATA_DIR, 'favorites.json'), 'w', encoding='utf-8') as f:
            json.dump(favorites_cache, f, indent=2)

# Play the next song
def play_next():
    global current_playlist_index, current_song, playback_mode
    playlist = search_cache
    if not playlist:
        set_status("Playlist is empty")
        return
    
    if playback_mode == "shuffle":
        current_playlist_index = random.randint(0, len(playlist) - 1)
    elif playback_mode != "repeat_one" and current_playlist_index < len(playlist) - 1:
        current_playlist_index += 1
    else:
        current_playlist_index = 0 if playback_mode == "repeat_all" else -1
        if playback_mode != "repeat_all":
            stop_current_song()
            set_status("No more songs")
            return
    
    if 0 <= current_playlist_index < len(playlist):
        song = playlist[current_playlist_index]
        current_song = {'title': song['title'], 'url': song['url']}
        download_play(song['url'], song['title'])
        update_favorite_button_state(song['title'])
    else:
        stop_current_song()
        set_status("Invalid playlist index")

# Play the previous song
def play_previous():
    global current_playlist_index, current_song, playback_mode
    playlist = search_cache
    if not playlist:
        set_status("Playlist is empty")
        return
    
    if playback_mode == "shuffle":
        current_playlist_index = random.randint(0, len(playlist) - 1)
    elif playback_mode != "repeat_one" and current_playlist_index > 0:
        current_playlist_index -= 1
    else:
        current_playlist_index = len(playlist) - 1 if playback_mode == "repeat_all" else -1
        if playback_mode != "repeat_all":
            stop_current_song()
            set_status("No previous songs")
            return
    
    if 0 <= current_playlist_index < len(playlist):
        song = playlist[current_playlist_index]
        current_song = {'title': song['title'], 'url': song['url']}
        download_play(song['url'], song['title'])
        update_favorite_button_state(song['title'])
    else:
        stop_current_song()
        set_status("Invalid playlist index")

# Update the favorite button state
def update_favorite_button_state(song_title):
    favorite_button.config(text="♥" if any(f['title'] == song_title for f in favorites_cache) else "♡")

# Cycle through playback modes
def cycle_playback_mode():
    global playback_mode
    modes = ["off", "shuffle", "repeat_one", "repeat_all"]
    current_index = modes.index(playback_mode)
    playback_mode = modes[(current_index + 1) % len(modes)]
    update_mode_button()
    set_status(f"Playback mode: {playback_mode.replace('_', ' ').title()}")

# Update the mode button text
def update_mode_button():
    mode_texts = {
        "off": "Off",
        "shuffle": "🔀 Shuffle",
        "repeat_one": "🔁 One",
        "repeat_all": "🔄 All"
    }
    mode_button.config(text=mode_texts[playback_mode])

# Play all songs starting from the first
def play_all():
    global current_playlist_index, current_song
    playlist = search_cache
    if not playlist:
        set_status("Playlist is empty")
        return

    current_playlist_index = 0
    song = playlist[current_playlist_index]
    current_song = {'title': song['title'], 'url': song['url']}
    download_play(song['url'], song['title'])
    update_favorite_button_state(song['title'])
    set_status("Playing all songs")

# Add placeholder text to the search entry
def add_placeholder(entry, placeholder_text):
    entry.insert(0, placeholder_text)
    entry.config(fg='#c2c2c2')

    def on_focus_in(event):
        if entry.get() == placeholder_text:
            entry.delete(0, tk.END)
            entry.config(fg='black')

    def on_focus_out(event):
        if not entry.get():
            entry.insert(0, placeholder_text)
            entry.config(fg='grey')

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)

# Handle listbox selection with debouncing
def on_listbox_click(event, section):
    global current_playlist_index, current_song, last_click_time
    current_time = time.time()
    if current_time - last_click_time < 0.5:  # 500ms debounce
        return
    last_click_time = current_time

    widget = event.widget
    selection = widget.curselection()
    if not selection:
        return

    index = selection[0]
    value = widget.get(index)
    song_name("Loading song...")
    set_status("Loading song...")

    if section == "playlist":
        playlist = search_cache
        for i, video in enumerate(playlist):
            if video["title"] == value:
                current_playlist_index = i
                current_song = {'title': video["title"], 'url': video["url"]}
                add_recent(title=value, url=video["url"])
                add_to_listbox(section="recent", item=value)
                download_play(video["url"], value)
                update_favorite_button_state(value)
                break
        else:
            set_status("Song not found in playlist")

    elif section == "recent":
        for video in recent_cache:
            if video["title"] == value:
                current_song = {'title': video["title"], 'url': video["url"]}
                download_play(video["url"], value)
                update_favorite_button_state(value)
                playlist = search_cache
                for i, p in enumerate(playlist):
                    if p['title'] == value:
                        current_playlist_index = i
                        break
                else:
                    current_playlist_index = -1
                break
        else:
            set_status("Song not found in recent")

    elif section == "favorites":
        for video in favorites_cache:
            if video["title"] == value:
                current_song = {'title': video["title"], 'url': video["url"]}
                download_play(video["url"], value)
                update_favorite_button_state(value)
                playlist = search_cache
                for i, p in enumerate(playlist):
                    if p['title'] == value:
                        current_playlist_index = i
                        break
                else:
                    current_playlist_index = -1
                break
        else:
            set_status("Song not found in favorites")

# Download and play a song
def download_play(video_url, name):
    global current_song, seek_offset
    stop_current_song()
    delete_current_song_file()
    seek_offset = 0
    progress_var.set(0)  # Reset progress bar

    try:
        with file_lock:
            with open(os.path.join('.cache', 'current_url.txt'), 'w', encoding='utf-8') as f:
                f.write(video_url)
    except Exception as e:
        set_status(f"Error saving URL: {e}")

    ffmpeg_path = os.path.join(os.getcwd(), 'ffmpeg')
    if not os.path.exists(ffmpeg_path):
        ui_queue.put((set_status, ("FFmpeg not found in directory",)))
        return

    options = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(CACHE_DIR, f'{name}.%(ext)s'),
        'ffmpeg_location': ffmpeg_path,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }
        ],
        'postprocessor_args': ['-vn'],
        'quiet': True,
        'noplaylist': True,
        'keepvideo': False,
    }

    threading.Thread(target=perform_download, args=(video_url, options, name), daemon=True).start()

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def perform_download(video_url, options, name):
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([video_url])
        ui_queue.put((play, ()))
    except Exception as e:
        ui_queue.put((set_status, (f"Download error: {e}",)))

# Add items to listboxes
def add_to_listbox(section, item):
    if section == "favorites":
        if item not in set(fav_listbox.get(0, END)):
            fav_listbox.insert(END, item)
    elif section == "playlist":
        playlist_listbox.insert(END, item)
    elif section == "recent":
        if item not in set(recent_listbox.get(0, END)):
            recent_listbox.insert(0, item)
            if recent_listbox.size() > 50:
                recent_listbox.delete(END)

# Save a song to the recent list
def add_recent(title, url):
    global recent_cache
    new_item = {"title": title, "url": url}
    
    recent_cache[:] = [item for item in recent_cache if item['title'] != title]
    recent_cache.insert(0, new_item)
    recent_cache = recent_cache[:50]
    
    with file_lock:
        with open(os.path.join(DATA_DIR, 'recent.json'), 'w', encoding='utf-8') as f:
            json.dump(recent_cache, f, indent=2)

# Display status messages
def set_status(message):
    status_label.config(text=message)
    root.after(5000, lambda: status_label.config(text="Ready") if status_label.cget("text") == message else None)

# Create the main window
root = tk.Tk()
root.title("Y TUNE")
root.geometry("700x550")
root.configure(bg="#333333")

# Title label
title_label = Label(root, text="Y TUNE", font=("Arial", 18, "bold"), fg="#ff0000", bg="#333333")
title_label.pack(pady=10)

# Search bar frame
search_frame = Frame(root, bg="#222222")
search_frame.pack(pady=5, fill="x", padx=10)

search_entry = Entry(search_frame, font=("Arial", 12), bg="#888888", fg="white", bd=0, insertbackground="white")
search_entry.pack(side="left", fill="x", expand=True, padx=(10, 5), ipady=5)
add_placeholder(search_entry, "Search for songs...")

search_button = Button(search_frame, text="🔍", font=("Arial", 12), bg="#aaaaaa", fg="black", command=search_by_name)
search_button.pack(side="right", padx=(5, 10))

# Status label for feedback
status_label = Label(root, text="Ready", font=("Arial", 10), fg="white", bg="#333333")
status_label.pack(pady=5)

# Main content frame for listboxes
main_frame = Frame(root, bg="#444444", height=300)
main_frame.pack(fill="x", padx=10, pady=5)
main_frame.pack_propagate(False)

main_frame.grid_columnconfigure(1, weight=3)
main_frame.grid_columnconfigure(0, weight=1)
main_frame.grid_columnconfigure(2, weight=1)

# Favorites section
favorites_frame = Frame(main_frame, bg="#555555", width=150, height=250)
favorites_frame.grid(row=0, column=0, sticky="ns")
favorites_frame.pack_propagate(False)

fav_label = Label(favorites_frame, text="Favorites", font=("Arial", 12, "bold"), fg="white", bg="#777777")
fav_label.pack(fill="x", pady=5)

fav_scroll = Scrollbar(favorites_frame)
fav_scroll.pack(side="right", fill="y")

fav_listbox = Listbox(favorites_frame, yscrollcommand=fav_scroll.set, bg="#666666", fg="white", font=("Arial", 10))
fav_listbox.pack(fill="both", expand=True)

fav_scroll.config(command=fav_listbox.yview)

# Playlist section
playlist_frame = Frame(main_frame, bg="#666666", height=250)
playlist_frame.grid(row=0, column=1, sticky="nsew", padx=10)
playlist_frame.pack_propagate(False)

playlist_scroll = Scrollbar(playlist_frame)
playlist_scroll.pack(side="right", fill="y")

playlist_listbox = Listbox(playlist_frame, yscrollcommand=playlist_scroll.set, bg="#777777", fg="white", font=("Arial", 10))
playlist_listbox.pack(fill="both", expand=True)

playlist_scroll.config(command=playlist_listbox.yview)

# Recent section
recent_frame = Frame(main_frame, bg="#555555", width=150, height=250)
recent_frame.grid(row=0, column=2, sticky="ns")
recent_frame.pack_propagate(False)

recent_label = Label(recent_frame, text="Recent", font=("Arial", 12, "bold"), fg="white", bg="#777777")
recent_label.pack(fill="x", pady=5)

recent_scroll = Scrollbar(recent_frame)
recent_scroll.pack(side="right", fill="y")

recent_listbox = Listbox(recent_frame, yscrollcommand=recent_scroll.set, bg="#666666", fg="white", font=("Arial", 10))
recent_listbox.pack(fill="both", expand=True)

recent_scroll.config(command=recent_listbox.yview)

# Bottom frame for controls
bottom_frame = Frame(root, bg="#222222")
bottom_frame.pack(fill="x", side="bottom", pady=10)

song_title = Label(bottom_frame, text="No song selected", font=("Arial", 12), fg="white", bg="#222222")
song_title.pack(pady=(10, 0))

song_duration = Label(bottom_frame, text="Time: 0:00 / 0:00", font=("Arial", 10), fg="white", bg="#222222")
song_duration.pack()

progress_var = tk.DoubleVar()
progress_bar = Scale(
    bottom_frame, variable=progress_var, from_=0, to=100,
    orient=HORIZONTAL, showvalue=0, sliderlength=15,
    troughcolor="#555555", bg="#920000", activebackground="#ff0000",
    highlightthickness=0, length=600, resolution=0.1
)
progress_bar.pack(fill="x", pady=(10, 5))

# Control buttons frame
controls_frame = Frame(bottom_frame, bg="#222222")
controls_frame.pack(pady=10)

prev_button = Button(controls_frame, text="⏮", font=("Arial", 12), bg="white", width=5, command=play_previous)
prev_button.pack(side="left", padx=5)

play_button = Button(controls_frame, text="▶", font=("Arial", 12, "bold"), bg="white", width=5, command=play)
play_button.pack(side="left", padx=5)

next_button = Button(controls_frame, text="⏭", font=("Arial", 12), bg="white", width=5, command=play_next)
next_button.pack(side="left", padx=5)

favorite_button = Button(controls_frame, text="♡", font=("Arial", 12), bg="white", width=5, command=toggle_favorite)
favorite_button.pack(side="left", padx=5)

mode_button = Button(controls_frame, text="Off", font=("Arial", 12), bg="white", width=8, command=cycle_playback_mode)
mode_button.pack(side="left", padx=5)

play_all_button = Button(controls_frame, text="▶ All", font=("Arial", 12), bg="white", width=6, command=play_all)
play_all_button.pack(side="left", padx=5)

# Bind progress bar events
progress_bar.bind("<B1-Motion>", on_seek_drag)
progress_bar.bind("<ButtonRelease-1>", on_seek_release)

# Bind listbox events
fav_listbox.bind("<<ListboxSelect>>", lambda e: on_listbox_click(e, "favorites"))
playlist_listbox.bind("<<ListboxSelect>>", lambda e: on_listbox_click(e, "playlist"))
recent_listbox.bind("<<ListboxSelect>>", lambda e: on_listbox_click(e, "recent"))

# Bind shortcut keys
search_entry.bind("<Return>", lambda event: search_by_name())

def handle_space(event):
    if event.widget != search_entry and current_song:
        play()
    return "break"

root.bind("<space>", handle_space)

# Initialize pygame for audio and event handling
pygame.init()

# Load initial data into memory
recent_file = os.path.join(DATA_DIR, 'recent.json')
if not os.path.exists(recent_file) or os.path.getsize(recent_file) == 0:
    with file_lock:
        with open(recent_file, 'w', encoding='utf-8') as f:
            json.dump([], f)

with file_lock:
    with open(recent_file, 'r', encoding='utf-8') as f:
        try:
            recent_cache = json.load(f)
        except json.JSONDecodeError:
            recent_cache = []
for song in recent_cache:
    add_to_listbox("recent", song["title"])

favorites_file = os.path.join(DATA_DIR, 'favorites.json')
if not os.path.exists(favorites_file) or os.path.getsize(favorites_file) == 0:
    with file_lock:
        with open(favorites_file, 'w', encoding='utf-8') as f:
            json.dump([], f)

with file_lock:
    with open(favorites_file, 'r', encoding='utf-8') as f:
        try:
            favorites_cache = json.load(f)
        except json.JSONDecodeError:
            favorites_cache = []
for song in favorites_cache:
    add_to_listbox("favorites", song["title"])

# Start UI queue checker
root.after(100, check_ui_queue)

# Clean up on exit
def on_closing():
    stop_current_song()
    try:
        pygame.quit()
    except:
        pass
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

# Start the main loop
root.mainloop()