import re
channel_url = "https://www.youtube.com/@低欸死"
handle = None
if "/@" in channel_url:
    handle = "@" + channel_url.split("/@")[1].split("/")[0]

print(f"handle: {handle}")
print(f"startswith @: {handle.startswith('@')}")
