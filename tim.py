import requests
import re
from datetime import datetime

UPSTREAM_URL = "https://pigzillaaa-scraper.vercel.app/tims"
EPG_URL = "https://tinyurl.com/DrewLive002-epg"
OUTPUT_FILE = "Tims247.m3u8"
FORCED_GROUP = "Tims247"
FORCED_TVG_ID = "24.7.Dummy.us"

def force_group_and_tvgid(line):
    if line.startswith("#EXTINF"):
        # Remove existing tvg-id and group-title attributes
        line = re.sub(r'tvg-id="[^"]*"', '', line)
        line = re.sub(r'group-title="[^"]*"', '', line)

        # Ensure spacing is correct and insert new attributes
        line = line.replace('#EXTINF:', f'#EXTINF:-1 tvg-id="{FORCED_TVG_ID}" group-title="{FORCED_GROUP}" ', 1)
    return line.strip()

def main():
    res = requests.get(UPSTREAM_URL, timeout=15)
    res.raise_for_status()
    lines = res.text.strip().splitlines()

    output_lines = [
        f'#EXTM3U url-tvg="{EPG_URL}"',
        f'# Last forced update: {datetime.utcnow().isoformat()}Z'
    ]

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#EXTM3U"):
            continue
        output_lines.append(force_group_and_tvgid(line))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")

    print(f"[✅] Playlist saved to {OUTPUT_FILE} with tvg-id='{FORCED_TVG_ID}' and group-title='{FORCED_GROUP}'.")

if __name__ == "__main__":
    main()
