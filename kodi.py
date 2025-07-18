import urllib.parse

input_file = "MergedPlaylist.m3u8"
output_file = "MergedPlaylist_Kodi.m3u8"

def convert_to_kodi_format(lines):
    result = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            # Write EXTINF line
            result.append(line)
            i += 1

            # Collect headers from following #EXTVLCOPT lines
            headers = {}
            while i < len(lines) and lines[i].strip().startswith("#EXTVLCOPT:"):
                hdr_line = lines[i].strip()[len("#EXTVLCOPT:"):]  # e.g. "http-referrer=https://..."
                if "=" in hdr_line:
                    key, value = hdr_line.split("=", 1)
                    # Normalize keys to capitalized form for Kodi (optional)
                    # e.g. http-referrer -> Referer
                    key_map = {
                        "http-referrer": "Referer",
                        "http-user-agent": "User-Agent",
                        "http-origin": "Origin"
                    }
                    # Use .get() with a default of the original key if not found in map
                    key = key_map.get(key.lower(), key)
                    headers[key] = value
                i += 1

            # Next line should be the stream URL
            if i < len(lines):
                stream_url = lines[i].strip()
                i += 1

                # If headers found, append them as url-encoded params after pipe
                if headers:
                    params = []
                    for k, v in headers.items():
                        # Ensure value is properly URL-encoded.
                        # urllib.parse.quote will handle special characters.
                        params.append(f"{k}={urllib.parse.quote(v, safe='')}")
                    stream_url += "|" + "&".join(params)

                result.append(stream_url)
            else:
                # If #EXTINF was the last line and no stream URL followed,
                # we should probably just append the EXTINF and move on.
                # Or, if you prefer, you could skip appending the EXTINF if it's incomplete.
                # For now, this will effectively stop processing if the URL is missing.
                # If you want to include the EXTINF line even without a URL,
                # you'd need to re-think this `else` block.
                pass # No stream URL found after EXTINF, just continue to next line in outer loop.
        else:
            # Other lines pass through unchanged
            result.append(line)
            i += 1

    return result

try:
    with open(input_file, "r", encoding="utf-8") as infile:
        lines = infile.readlines()

    converted = convert_to_kodi_format(lines)

    with open(output_file, "w", encoding="utf-8") as outfile:
        # Join lines and ensure a newline at the very end if not already present
        outfile.write("\n".join(converted))
        if not converted[-1].endswith('\n'): # Add newline if the last line doesn't have one
            outfile.write("\n")

    print(f"Successfully converted '{input_file}' to '{output_file}' for Kodi.")

except FileNotFoundError:
    print(f"Error: The input file '{input_file}' was not found.")
except Exception as e:
    print(f"An error occurred: {e}")
