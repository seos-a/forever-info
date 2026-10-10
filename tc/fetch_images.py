"""Download any icon the site needs but the repo doesn't have yet (new talents or spells from a beta sync).

Run from inside tc/ after build.py:  py fetch_images.py
Reads ../web/image-list.txt ("url|local path" lines) and fetches each missing file into the repo root.
"""
import os, urllib.request

def main():
    got, failed = [], []
    for line in open('../web/image-list.txt', encoding='utf-8'):
        if '|' not in line: continue
        url, path = line.strip().split('|', 1)
        dest = os.path.join('..', path)
        if os.path.exists(dest): continue
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req, timeout=30).read()
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, 'wb').write(data); got.append(path)
        except Exception:
            failed.append(path)
    for p in got: print(f'new image: {p}')
    for p in failed: print(f'could not download: {p}')
    if not got and not failed: print('no new images')

if __name__ == '__main__':
    main()
