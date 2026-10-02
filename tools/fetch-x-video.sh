#!/bin/bash
# Fetch the X video (HLS/DASH fMP4 segments) and extract 1 frame every 3 s. Runs on the host.
set -euo pipefail
BASE="https://video.twimg.com/amplify_video/2105698671270719493"
PLAYLIST="$BASE/pl/avc1/1600x1200/zmGWYT_mqZ1pbRQ-.m3u8"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0 Safari/537.36"
WORK=/tmp/nizam
rm -rf "$WORK"; mkdir -p "$WORK/seg" "$WORK/frames"; cd "$WORK"

curl -sL -A "$UA" -e https://x.com/ "$PLAYLIST" -o playlist.m3u8
echo "segments in playlist: $(grep -c '\.m4s$' playlist.m3u8)"

INIT="$(grep -oE 'URI="[^"]+"' playlist.m3u8 | head -1 | sed 's/URI="//;s/"//')"
curl -sL -A "$UA" -e https://x.com/ "https://video.twimg.com${INIT}" -o seg/init.mp4
ls -l seg/init.mp4

n=0
: > concat.txt
for s in $(grep -oE '/amplify_video/[^"]+\.m4s' playlist.m3u8); do
  n=$((n+1))
  out="seg/$(printf '%03d' $n).m4s"
  curl -sL -A "$UA" -e https://x.com/ "https://video.twimg.com${s}" -o "$out"
  echo "$out" >> concat.txt
done
echo "downloaded segments: $n ($(du -sh seg | cut -f1))"

# fMP4: init + media segments concatenate into a playable file
cp seg/init.mp4 full.mp4
while read -r f; do cat "$f" >> full.mp4; done < concat.txt
ls -l full.mp4
ffprobe -v error -show_entries format=duration,size -of default=nw=1 full.mp4

ffmpeg -y -loglevel error -i full.mp4 -vf "fps=1/3,scale=1400:-1" frames/frame_%02d.png
ls -l frames | head -12
echo "FRAMES: $(ls frames/*.png | wc -l)"
