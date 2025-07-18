import asyncio
from playwright.async_api import async_playwright
import aiohttp
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import platform

API_URL = "https://ppv.to/api/streams"

CUSTOM_HEADERS = [
    '#EXTVLCOPT:http-origin=https://veplay.top',
    '#EXTVLCOPT:http-referrer=https://veplay.top/',
    '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0'
]

ALLOWED_CATEGORIES = {
    "24/7 Streams", "Wrestling", "Football", "Basketball", "Baseball",
    "Combat Sports", "Motorsports", "Miscellaneous", "Boxing", "Darts"
}

CATEGORY_LOGOS = {
    "24/7 Streams": "http://drewlive24.duckdns.org:9000/Logos/247.png",
    "Wrestling": "http://drewlive24.duckdns.org:9000/Logos/Wrestling.png",
    "Football": "http://drewlive24.duckdns.org:9000/Logos/Soccer2.png",
    "Basketball": "http://drewlive24.duckdns.org:9000/Logos/Basketball-2.png",
    "Baseball": "http://drewlive24.duckdns.org:9000/Logos/Baseball.png",
    "Combat Sports": "http://drewlive24.duckdns.org:9000/Logos/Boxing.png",
    "Motorsports": "http://drewlive24.duckdns.org:9000/Logos/F12.png",
    "Miscellaneous": "http://drewlive24.duckdns.org:9000/Logos/247.png",
    "Boxing": "http://drewlive24.duckdns.org:9000/Logos/Boxing.png",
    "Darts": "http://drewlive24.duckdns.org:9000/Logos/Darts.png"
}

CATEGORY_TVG_IDS = {
    "24/7 Streams": "24.7.Dummy.us",
    "Football": "Soccer.Dummy.us",
    "Wrestling": "PPV.EVENTS.Dummy.us",
    "Combat Sports": "PPV.EVENTS.Dummy.us",
    "Baseball": "MLB.Baseball.Dummy.us",
    "Basketball": "Basketball.Dummy.us",
    "Motorsports": "Racing.Dummy.us",
    "Miscellaneous": "PPV.EVENTS.Dummy.us",
    "Boxing": "PPV.EVENTS.Dummy.us",
    "Darts": "Darts.Dummy.us"
}

GROUP_RENAME_MAP = {
    "24/7 Streams": "PPVLand - Live Channels 24/7",
    "Wrestling": "PPVLand - Wrestling Events",
    "Football": "PPVLand - Global Football Streams",
    "Basketball": "PPVLand - Basketball Hub",
    "Baseball": "PPVLand - Baseball Action HD",
    "Combat Sports": "PPVLand - MMA & Fight Nights",
    "Motorsports": "PPVLand - Motorsport Live",
    "Miscellaneous": "PPVLand - Random Events",
    "Boxing": "PPVLand - Boxing",
    "Darts": "PPVLand - Darts"
}

def parse_backend_time(timestr):
    try:
        h, m, s = map(int, timestr.strip().split(":"))
        now_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        return now_utc.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=h, minutes=m, seconds=s)
    except Exception as e:
        print(f"❌ Failed to parse time '{timestr}': {e}")
        return None

def convert_to_local_str(dt_obj):
    try:
        local_tz = ZoneInfo("America/Denver")
        dt_local = dt_obj.astimezone(local_tz)
        is_windows = platform.system() == "Windows"
        format_str = "%b %#d, %Y %#I:%M %p" if is_windows else "%b %-d, %Y %-I:%M %p"
        return dt_local.strftime(format_str)
    except Exception as e:
        print(f"❌ Failed to format time: {e}")
        return None

async def check_m3u8_url(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                return resp.status == 200
    except Exception:
        return False

async def get_streams():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL) as resp:
            resp.raise_for_status()
            return await resp.json()

async def grab_m3u8_from_iframe(page, iframe_url):
    found_streams = set()

    def handle_response(response):
        url = response.url
        if ".m3u8" in url:
            found_streams.add(url)

    page.on("response", handle_response)
    print(f"🌐 Navigating to iframe: {iframe_url}")
    try:
        await page.goto(iframe_url, timeout=15000)
    except Exception as e:
        print(f"❌ Failed to load iframe: {e}")
        page.remove_listener("response", handle_response)
        return set()

    await asyncio.sleep(2)

    viewport = page.viewport_size or {"width": 1280, "height": 720}
    center_x = viewport["width"] / 2
    center_y = viewport["height"] / 2

    for i in range(5):
        if found_streams:
            break
        print(f"🖱️ Click #{i + 1} at center")
        try:
            await page.mouse.click(center_x, center_y)
        except Exception as e:
            print(f"❌ Click failed: {e}")
        await asyncio.sleep(0.2)

    print("⏳ Waiting 5s for streams to load...")
    await asyncio.sleep(5)
    page.remove_listener("response", handle_response)

    valid_urls = set()
    for url in found_streams:
        if await check_m3u8_url(url):
            valid_urls.add(url)
        else:
            print(f"❌ Invalid or unreachable URL: {url}")

    return valid_urls

def build_m3u(streams, url_map):
    lines = ['#EXTM3U url-tvg="https://tinyurl.com/DrewLive002-epg"']
    added_urls = set()

    for s in streams:
        # Use unique key to avoid duplicates, composed from name+category+iframe (variant)
        unique_key = f"{s['name']}::{s['category']}::{s['iframe']}"

        urls = url_map.get(unique_key, [])
        if not urls:
            print(f"⚠️ No working URLs for {s['name']}")
            continue

        orig_category = s["category"].strip()
        final_group_title = GROUP_RENAME_MAP.get(orig_category, orig_category)
        logo = CATEGORY_LOGOS.get(orig_category, "")
        tvg_id = CATEGORY_TVG_IDS.get(orig_category, "Sports.Dummy.us")

        for url in urls:
            if url in added_urls:
                continue
            added_urls.add(url)

            # Append variant info (part of iframe url) to distinguish duplicates
            variant = s["iframe"].split("//")[-1].split("/")[0]  # hostname part
            display_name = f"{s['name']} [{variant}]"

            lines.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" group-title="{final_group_title}",{display_name}')
            lines.extend(CUSTOM_HEADERS)
            lines.append(url)

    return "\n".join(lines)

async def main():
    data = await get_streams()
    streams = []

    for category in data.get("streams", []):
        cat_name = category.get("category", "").strip()
        if cat_name not in ALLOWED_CATEGORIES:
            continue
        for stream in category.get("streams", []):
            iframe = stream.get("iframe")
            channel = stream.get("channel", "")
            event_name = stream.get("name", "Unnamed Event")

            if any(c.isdigit() for c in channel):
                time_part = channel.strip().split()[-1]
                dt_utc = parse_backend_time(time_part)
                if dt_utc:
                    local_time = convert_to_local_str(dt_utc)
                    if local_time:
                        event_name += f" ({local_time})"

            if iframe:
                streams.append({
                    "name": event_name,
                    "iframe": iframe,
                    "category": cat_name
                })

    if not streams:
        print("🚫 No valid streams found.")
        return

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        url_map = {}
        for s in streams:
            unique_key = f"{s['name']}::{s['category']}::{s['iframe']}"
            print(f"\n🔍 Scraping: {s['name']} ({s['category']}) - iframe host: {unique_key.split('::')[2].split('//')[-1].split('/')[0]}")
            found_urls = await grab_m3u8_from_iframe(page, s["iframe"])
            if found_urls:
                print(f"✅ Got {len(found_urls)} URL(s) for {s['name']}")
            url_map[unique_key] = found_urls

        await browser.close()

    print("\n💾 Writing final playlist to PPVLand.m3u8 ...")
    playlist = build_m3u(streams, url_map)
    with open("PPVLand.m3u8", "w", encoding="utf-8") as f:
        f.write(playlist)

    print(f"✅ Done! Playlist saved as PPVLand.m3u8 at {datetime.utcnow().isoformat()} UTC")

if __name__ == "__main__":
    asyncio.run(main())
