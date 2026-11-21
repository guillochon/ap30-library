"""Survey a music library: FLAC stream info, metadata block layout and artwork."""
import sys, os, io, collections
from mutagen.flac import FLAC
from PIL import Image

def img_info(data):
    try:
        im = Image.open(io.BytesIO(data))
        prog = im.info.get('progressive') or im.info.get('progression')
        return f"{im.format} {im.size[0]}x{im.size[1]} {im.mode}{' PROGRESSIVE' if prog else ''} {len(data)//1024}KB"
    except Exception as e:
        return f"unreadable ({e})"

root = sys.argv[1]
rates = collections.Counter()
for d, _, files in sorted(os.walk(root)):
    flacs = sorted(f for f in files if f.lower().endswith('.flac'))
    if not flacs:
        continue
    print(f"\n== {os.path.relpath(d, root)} ({len(flacs)} tracks)")
    for f in files:
        if f.lower().endswith(('.jpg', '.jpeg', '.png')):
            with open(os.path.join(d, f), 'rb') as fh:
                print(f"   folder art {f}: {img_info(fh.read())}")
    for i, f in enumerate(flacs):
        a = FLAC(os.path.join(d, f))
        si = a.info
        rates[(si.sample_rate, si.bits_per_sample, si.channels)] += 1
        if i == 0:  # details for the first track of each album
            blocks = [(type(b).__name__, getattr(b, 'length', None)) for b in a.metadata_blocks]
            pad = sum(len(b.data) if hasattr(b,'data') else 0 for b in a.metadata_blocks if type(b).__name__=='Padding')
            print(f"   {f}: {si.sample_rate}Hz/{si.bits_per_sample}bit/{si.channels}ch")
            print(f"   blocks: {[b[0] for b in blocks]}")
            print(f"   tag keys: {sorted(a.keys())}")
            for p in a.pictures:
                print(f"   embedded pic type={p.type} mime={p.mime}: {img_info(p.data)}")
        pics = len(a.pictures)
        if i > 0 and pics != len(FLAC(os.path.join(d, flacs[0])).pictures):
            print(f"   ! {f} has {pics} pictures")
print("\nformats:", dict(rates))
