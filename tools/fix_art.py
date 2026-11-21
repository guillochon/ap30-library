"""Normalise album artwork for the Hidizs AP30.

For every folder that holds FLAC files:
  * pick the best source image (largest of the embedded covers and the folder images),
  * re-encode it as a small baseline (non-progressive) RGB JPEG,
  * embed that one image as the front cover of every track (replacing what was there),
  * write it as cover.jpg in the folder and remove the other folder images.

Usage: python fix_art.py ROOT [--size 500] [--dry-run]
Make a backup first; this rewrites the files in place.
"""
import argparse, io, os, sys
from mutagen.flac import FLAC, Picture
from PIL import Image, ImageFile

# Some downloaded covers are progressive JPEGs cut short; they still decode to a usable picture.
ImageFile.LOAD_TRUNCATED_IMAGES = True

IMG_EXT = ('.jpg', '.jpeg', '.png')


def load(data):
    im = Image.open(io.BytesIO(data))
    im.load()
    return im


def encode(im, size):
    im = im.convert('RGB')
    if max(im.size) > size:
        im.thumbnail((size, size), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, 'JPEG', quality=88, progressive=False, optimize=False, subsampling='4:2:0')
    return out.getvalue(), im.size


def process(d, flacs, imgs, size, dry):
    candidates = []
    for f in imgs:
        with open(os.path.join(d, f), 'rb') as fh:
            data = fh.read()
        try:
            candidates.append((load(data), f'folder:{f}'))
        except Exception as e:
            print(f'   skip unreadable {f}: {e}')
    for f in flacs:
        for p in FLAC(os.path.join(d, f)).pictures:
            if p.type in (3, 0):
                try:
                    candidates.append((load(p.data), f'embedded:{f}'))
                except Exception:
                    pass
                break
        if any(c[1].startswith('embedded') for c in candidates):
            break
    if not candidates:
        print('   NO ARTWORK FOUND, left as is')
        return
    # Prefer colour over greyscale, then the largest.
    src, name = max(candidates, key=lambda c: (c[0].mode not in ('L', '1'), c[0].size[0] * c[0].size[1]))
    data, wh = encode(src, size)
    print(f'   source {name} {src.size[0]}x{src.size[1]} {src.mode} -> {wh[0]}x{wh[1]} baseline {len(data)//1024} KB')
    if dry:
        return
    pic = Picture()
    pic.type, pic.mime, pic.desc = 3, 'image/jpeg', ''
    pic.width, pic.height, pic.depth = wh[0], wh[1], 24
    pic.data = data
    for f in flacs:
        a = FLAC(os.path.join(d, f))
        a.clear_pictures()
        a.add_picture(pic)
        a.save()
    for f in imgs:
        os.remove(os.path.join(d, f))
    with open(os.path.join(d, 'cover.jpg'), 'wb') as fh:
        fh.write(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--size', type=int, default=500)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    for d, _, files in sorted(os.walk(args.root)):
        flacs = sorted(f for f in files if f.lower().endswith('.flac'))
        if not flacs:
            continue
        imgs = sorted(f for f in files if f.lower().endswith(IMG_EXT))
        print(f'== {os.path.relpath(d, args.root)}')
        process(d, flacs, imgs, args.size, args.dry_run)


if __name__ == '__main__':
    main()
