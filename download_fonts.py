import urllib.request
import os

fonts_map = {
    "Titan One": "https://raw.githubusercontent.com/google/fonts/main/ofl/titanone/TitanOne-Regular.ttf",
    "Ranchers": "https://raw.githubusercontent.com/google/fonts/main/ofl/ranchers/Ranchers-Regular.ttf",
    "Rampart One": "https://raw.githubusercontent.com/google/fonts/main/ofl/rampartone/RampartOne-Regular.ttf",
    "Permanent Marker": "https://raw.githubusercontent.com/google/fonts/main/apache/permanentmarker/PermanentMarker-Regular.ttf",
    "Open Sans": "https://raw.githubusercontent.com/google/fonts/main/ofl/opensans/OpenSans%5Bwdth%2Cwght%5D.ttf",
    "Montserrat": "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",
    "Luckiest Guy": "https://raw.githubusercontent.com/google/fonts/main/apache/luckiestguy/LuckiestGuy-Regular.ttf",
    "Knewave": "https://raw.githubusercontent.com/google/fonts/main/ofl/knewave/Knewave-Regular.ttf",
    "Jua": "https://raw.githubusercontent.com/google/fonts/main/ofl/jua/Jua-Regular.ttf",
    "Creepster": "https://raw.githubusercontent.com/google/fonts/main/ofl/creepster/Creepster-Regular.ttf",
    "Caveat": "https://raw.githubusercontent.com/google/fonts/main/ofl/caveat/Caveat%5Bwght%5D.ttf",
    "Bungee": "https://raw.githubusercontent.com/google/fonts/main/ofl/bungee/Bungee-Regular.ttf",
    "Bebas Neue": "https://raw.githubusercontent.com/google/fonts/main/ofl/bebasneue/BebasNeue-Regular.ttf",
    "Bangers": "https://raw.githubusercontent.com/google/fonts/main/ofl/bangers/Bangers-Regular.ttf",
    "Bakbak One": "https://raw.githubusercontent.com/google/fonts/main/ofl/bakbakone/BakbakOne-Regular.ttf"
}

output_dir = r"c:\Users\olade\Documents\GitHub\ytvidauto\core\assets\fonts"
os.makedirs(output_dir, exist_ok=True)

for font_name, url in fonts_map.items():
    print(f"Downloading {font_name}...")
    file_name = font_name.replace(" ", "") + ".ttf"
    output_path = os.path.join(output_dir, file_name)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())
        print(f"Saved {font_name}")
    except Exception as e:
        print(f"Failed to download {font_name}: {e}")

print("Done!")
