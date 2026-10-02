# ffmpeg recipes for the reference style

These recipes were tested on this environment's ffmpeg with libass. Fonts
include Poppins (closest to the reference) and DejaVu Sans. Re-encode with
`-c:v libx264 -crf 18 -preset fast` unless stated otherwise.

## Kinetic text with an accent-highlighted phrase

Write an ASS file. Colors are `&HBBGGRR&`; `&HFFC83C&` is the cyan-blue
accent.

```
[Script Info]
PlayResX: 1920
PlayResY: 1080
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Kinetic,Poppins,64,&H00FFFFFF,&H00000000,&H64000000,1,1,2,0,2,80,80,120
[Events]
Format: Layer, Start, End, Style, Text
Dialogue: 0,0:00:01.00,0:00:04.00,Kinetic,{\fad(150,150)}how do I get {\c&HFFC83C&\blur2}as many people{\c&HFFFFFF&\blur0} interested
```

`ffmpeg -i in.mp4 -vf "ass=text.ass" -c:a copy out.mp4`

Use `Alignment` 5 for centered (text-only cards) and 2 for lower-middle. The
`\blur2` on the accent phrase gives a soft glow.

## Color treatments

- **Flashback or "before" (black and white):** `-vf "hue=s=0,eq=contrast=1.1"`
- **Negative or failure (red wash):** `-vf "colorchannelmixer=rr=1:gg=0.45:bb=0.45,eq=brightness=-0.05"`
- **Moody grade:** `-vf "eq=brightness=-0.04:saturation=0.9:gamma=0.95,vignette=PI/5"`

To apply a treatment to only part of the video, add
`enable='between(t,A,B)'` to each filter.

## B-roll or image cutaway over talking head (audio continues)

```
ffmpeg -i main.mp4 -i broll.mp4 -filter_complex \
 "[1:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setpts=PTS-STARTPTS+12/TB[b];\
  [0:v][b]overlay=enable='between(t,12,16)':eof_action=pass[v]" \
 -map "[v]" -map 0:a -c:a copy out.mp4
```

Scale the B-roll to the main video's resolution. For a still image, add
`-loop 1 -t 4` before its `-i`.

## Zoom into part of a screen recording

To crop a region and scale it back to full frame, use
`-vf "crop=iw*0.5:ih*0.5:iw*0.3:ih*0.2,scale=1920:1080"`. The crop values
are width, height, x, and y.

For a slow push-in on a still or graphic (Ken Burns style), use
`-vf "zoompan=z='min(zoom+0.0008,1.15)':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30"`.

## Numbered title card (dark textured background, accent glow)

```
ffmpeg -f lavfi -i "color=c=0x141414:s=1920x1080:d=3,noise=alls=12:allf=t" -vf "ass=card.ass" card.mp4
```

Put each list item in its own Dialogue line with staggered start times, and
color the current item with the accent.

## Joining clips

Normalize every clip to the same resolution, fps, and audio rate first, then
use `ffmpeg -f concat -safe 0 -i list.txt -c copy out.mp4`. If parameters
differ, use the `concat` filter instead.

## Vertical 9:16 version for Shorts

```
-vf "split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
```

## Abrupt emphasis zoom on A-roll (for an important line)

This is tested. It punches in 1.3× between 5 s and 8 s:

```
-filter_complex "[0:v]split[a][b];[b]crop=iw/1.3:ih/1.3,scale=W:H,setsar=1[z];[a][z]overlay=enable='between(t,5,8)'[v]"
```

Replace W and H with the source resolution. Adjust the crop's x and y to
keep the face centered if it isn't in the middle.

## Graphic slides into frame (never just appear)

This is tested. The graphic eases in from the right over 0.35 s, starting at
2 s, and settles at x=400:

```
[0:v][1:v]overlay=x='if(lt(t,2),W,if(lt(t,2.35),W-(W-400)*(1-pow(1-(t-2)/0.35,3)),400))':y=40
```

Add a whoosh at 2.0 s. If the graphic pops in without motion, add a
shutter or pop sound at the exact frame instead.

## Guided-attention still

Use `scripts/focus_image.py` rather than hand-building the filter graph. It
combines a push-in, darkened or blurred surroundings, glow, a red, green,
or yellow tint, and a box or underline in one pass.
