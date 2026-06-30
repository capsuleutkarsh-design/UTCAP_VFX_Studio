import os
import urllib.request
import zipfile
import io
import sys

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFPROBE_DEST = "V0040/ut_vfx/bin/ffprobe.exe"

def format_size(bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0

def download_and_extract_ffprobe():
    os.makedirs(os.path.dirname(FFPROBE_DEST), exist_ok=True)
    if os.path.exists(FFPROBE_DEST):
        print("✅ ffprobe.exe already exists. Skipping FFprobe download.")
        return

    print("📥 Downloading FFmpeg/FFprobe from gyan.dev...")
    try:
        req = urllib.request.Request(FFMPEG_URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        total_size = int(response.headers.get('content-length', 0))
        
        zip_data = io.BytesIO()
        downloaded = 0
        while True:
            buffer = response.read(8192)
            if not buffer:
                break
            zip_data.write(buffer)
            downloaded += len(buffer)
            if total_size > 0:
                percent = int(50 * downloaded / total_size)
                sys.stdout.write(f"\r[{'=' * percent}{' ' * (50 - percent)}] {format_size(downloaded)} / {format_size(total_size)}")
                sys.stdout.flush()
                
        print("\n⏳ Extracting ffprobe.exe...")
        with zipfile.ZipFile(zip_data) as z:
            for file_info in z.infolist():
                if file_info.filename.endswith("ffprobe.exe"):
                    with z.open(file_info) as source, open(FFPROBE_DEST, "wb") as target:
                        target.write(source.read())
                    print(f"✅ Successfully extracted ffprobe.exe to {FFPROBE_DEST}")
                    return
    except Exception as e:
        print(f"\n❌ Failed to download/extract ffprobe: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print(" UTCAP VFX Studio - First Setup Helper")
    print("=" * 60 + "\n")
    
    download_and_extract_ffprobe()
    
    print("\n" + "=" * 60)
    print(" ⚠️ IMPORTANT MANUAL SETUP REQUIRED ⚠️")
    print("=" * 60)
    print("The PostgreSQL management tool 'pgAdmin4.exe' could not be ")
    print("bundled due to GitHub's 100MB file limit.\n")
    print("Missing File: V0040/ut_server/bin/pgsql/pgAdmin 4/runtime/pgAdmin4.exe")
    print("\nPlease download and install pgAdmin4 manually, or ask the ")
    print("maintainer to provide the raw pgAdmin4.exe file.\n")
    print("=" * 60)
