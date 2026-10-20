import os
import subprocess
import time
from playwright.sync_api import sync_playwright

WORKSPACE_DIR = os.path.abspath(os.path.dirname(__file__))
HTML_PATH = os.path.join(WORKSPACE_DIR, "index.html")
AUDIO_PATH = os.path.join(WORKSPACE_DIR, "voice_kofe.mp3")
RAW_VIDEO_DIR = os.path.join(WORKSPACE_DIR, "raw_record")
OUTPUT_MP4 = os.path.join(WORKSPACE_DIR, "reel-kofe.mp4")

os.makedirs(RAW_VIDEO_DIR, exist_ok=True)

# Clean previous raw videos
for f in os.listdir(RAW_VIDEO_DIR):
    try:
        os.remove(os.path.join(RAW_VIDEO_DIR, f))
    except Exception:
        pass

print("1. Launching Playwright Chromium...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        record_video_dir=RAW_VIDEO_DIR,
        record_video_size={"width": 1080, "height": 1920},
        viewport={"width": 1080, "height": 1920}
    )
    page = context.new_page()

    file_url = "file:///" + HTML_PATH.replace("\\", "/") + "?autoplay=1"
    print(f"2. Navigating to {file_url}...")
    page.goto(file_url)

    # Total duration of voice is 50.35s + 1s safety buffer
    duration = 51.5
    print(f"3. Recording in real-time for {duration} seconds...")
    start_time = time.time()
    
    # We poll and ensure playback runs smoothly
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        page.evaluate(f"window.seekTime({elapsed})")
        time.sleep(0.05)

    print("4. Closing browser context to finalize video recording...")
    context.close()
    browser.close()

# Find recorded webm file
webm_files = [os.path.join(RAW_VIDEO_DIR, f) for f in os.listdir(RAW_VIDEO_DIR) if f.endswith(".webm")]
if not webm_files:
    raise RuntimeError("No recorded webm file found in raw_record directory!")

raw_webm = webm_files[0]
print(f"5. Found recorded raw video: {raw_webm} ({os.path.getsize(raw_webm)} bytes)")

# Merge with ffmpeg
print("6. Merging video with audio using FFmpeg...")
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-i", raw_webm,
    "-i", AUDIO_PATH,
    "-map", "0:v:0",
    "-map", "1:a:0",
    "-c:v", "libx264",
    "-preset", "medium",
    "-crf", "18",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    OUTPUT_MP4
]

result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("FFmpeg stderr:", result.stderr)
    raise RuntimeError("FFmpeg encoding failed!")

print(f"7. SUCCESS! Video saved to: {OUTPUT_MP4}")
print(f"File size: {os.path.getsize(OUTPUT_MP4)} bytes")
