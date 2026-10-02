# Reference editing philosophy (Learn By Leo)

Companion references: `story-and-retention.md` (story, clarity, hooks,
conflict pacing, delivery) and `packaging.md` (thumbnails, titles, ideas).

Distilled from three videos by the creator, who grew Learn By Leo to 100k
subscribers in five videos, working solo, after 7 years of making videos
(a previous channel reached 60k subscribers and 24M views):

- **"Addictive editing" handbook (his early upload):** the four-pillar
  formula of experience fit, visual variety, visual continuity, and
  immersive audio.
- **"Sound design" video (~16 min):** the four layers of sound design.
- **"How I grew" video (~18 min):** what makes a great video, and how to
  study, compare, and stand out.

This is built from the transcripts plus frame and audio measurements. His
own words carry more weight than the measurements, which show what he does,
not why.

## Contents
0. Experience first: pick the editing style
0a. Visual variety
0b. Visual continuity
1. The core idea: sound
2. Sound layer 1: Music (five music tricks)
3. Sound layer 2: Soundscape (three SFX rules)
4. Sound layer 3: Audio cues
5. Sound layer 4: Pauses ("shut up and show it")
6. Voice recording
7. Picture and structure
8. Growth philosophy as editing judgment
9. Measured benchmarks
10. Critique rubric

---

## 0. Experience first: pick the editing style

> A great editing style can get perfect watch time and millions of views,
> or terrible view counts, depending on whether it fits what the viewer
> came for.

A creator with a 26-minute car-and-gym vlog, 17 cuts, and about 90 seconds
between cuts can still have a huge audience, because his viewers want to
feel like they're **hanging out with someone**. Quick cuts and flashy
animation would ruin that authenticity. MrBeast does the opposite for
viewers who want **entertainment**. Both work. **Disrupting what the viewer
came for is the fastest way to make them stop watching.**

So before any edit, decide the experience:

| Experience | Pauses | Visual changes | Graphics and SFX | `cut_silence.py --style` |
|---|---|---|---|---|
| Hangout / authentic (vlogs, podcasts, day-in-the-life) | Keep natural ones; cut only boring parts and bad takes | Sparse | Minimal | `hangout` |
| Informative / educational (Leo's own) | Remove empty ones, add filled beats | Every few seconds in the hook, then as content demands | Motion graphics to explain; sound design throughout | `standard` |
| Entertainment / high-stimulation | Remove nearly all; constant speech | Very frequent | Heavy | `entertainment` |

Cutting out every pause so you're speaking constantly is the single most
important move for entertainment, but it takes away authenticity. **Ask
the user what their viewers come for** if it isn't obvious from the
footage and the channel. Every other technique in this guide is a dial to
set according to this answer, not a rule to max out.

## 0a. Visual variety

The eye is drawn to change. A timeline where cuts only remove tangents,
pauses, and bad takes (say, three different things to look at in a minute)
underuses the visuals. Switch between footage types every few seconds to
hold attention, but know what each type is for:

- **A-roll** (you see and hear the subject): personal and holds attention
  well *if delivered with confidence*. Use it in short stretches, for
  important statements.
- **B-roll** (footage showing what's being said): clearer, faster, and more
  interesting than a face. Use as much as possible.
  - *Stock footage* is the lazy version. It's acceptable, but it's weaker
    than footage made for the video.
  - *Motion graphics* are the most powerful for explanation. For an
    **essential but boring** story beat (Dude Perfect explaining a puzzle's
    rules), A-roll is too slow and normal B-roll too confusing, but a quick
    animation makes it crystal clear and fast.

**Pacing floor:** even a slow nature documentary changes shots about every
5 s. A single clip lingering 10–20 s with no change (no cut, zoom, or
overlay) needs a reason. When shooting, get as many clips and angles as
possible; one continuous shot can't carry a video. Leo recorded about 10
hours of footage to switch clips every 5 s. The core of editing is pacing,
while the *style* should follow the best creators in the niche. (His later
experience-first guidance in section 0 refines "as fast as possible": fast
for the experience, not faster than the audience wants.)

**Don't create visual mush.** Minimizing shot length for its own sake
confuses viewers and hurts engagement. A clip can stay 10 seconds if it's
interesting for 10 seconds. You can add engagement without cutting:

- **Movement on stills:** slowly change the scale or position, or better,
  the perspective. Never leave a still static.
- **Abrupt zoom-ins on A-roll** when saying something important subtly
  tells the viewer to listen up. (Wiggle or shake keyframes exist, but Leo
  doesn't use them; they don't fit his look.)
- **Overlays**, but not captions as filler. Captions used to fill dead space
  get obnoxious and waste a chance for a better visual. Use them when
  specific words deserve attention, keep them to **three words or fewer at
  a time**, and fall back on them only when there's nothing better to show.
- **Guide attention within images.** Showing a whole image plainly is
  boring and confusing. Point the eye at the focus:
  1. Animate the key text or area.
  2. Darken or blur the surroundings.
  3. Shift the hue: **red = negative**, **yellow or green = positive**.
  4. Add circles, arrows, or underlines.
  5. Make the subject glow.
  6. Scale or reposition toward it.

  → `scripts/focus_image.py` does all six in one pass.
- **Make it look good:** color grading, a vignette, subtle particles.

## 0b. Visual continuity

Variety grabs attention; continuity keeps the viewer immersed. The goal is
a seamless feed where every moment blends into the next, no rough edges,
no point where distraction builds up. **The editing should be invisible.**

- **Graphics can't just appear.** They need to move into frame (slide,
  scale, or fade in with easing). Or, if something does pop in, explain it
  with a sound: a **shutter** sound (his choice) or a **pop**.
- **Eye-trace across cuts** is the most important cut rule. If the viewer
  is looking at the eyes on the left of the last frame, the first frame of
  the next clip shouldn't demand attention on the far right. Keep the focal
  point of consecutive shots in roughly the same place.
- **Full-screen transitions** can smooth cuts. Leo prefers subtle ones.
- **Break continuity on purpose, occasionally.** A jarring cut jolts the
  viewer and grabs attention. It's a spice, not a style.

---

## 1. The core idea: sound

> Sound is the foundation. If your videos don't sound immersive, they can't
> be immersive.

Most videos are "just content": information narrated, then music and
B-roll laid over it. Sound design turns information into an **experience**
the viewer is immersed in. Every decision below serves immersion, and
immersion serves retention.

## 2. Sound layer 1: Music

Found music isn't finished. A film score is composed to match the action
and emotion of each moment; a stock track dragged in and left alone will be
out of sync with the video most of the time, which breaks immersion. The
goal is to make found music behave like a score. He uses five tricks:

1. **Match emotion per section.** Each piece of information has its own
   inherent emotion. If one upbeat, mellow track runs under everything, it
   fights the content. Move, cut, and add tracks so each section's music
   matches what's being said.
   → `mix_audio.py --music a.mp3@0-45 --music b.mp3@45-120`

   Split the video at subject changes, decide the mood for each, and spend
   real time finding music that fits. Leo's go-tos are songs that create
   **anticipation** (the viewer keeps feeling something important is about
   to be said), and an **innovative, exciting** track under his most
   groundbreaking advice.
2. **Cut the music for emphasis.** On an important point, drop the music
   for a few seconds. It's startling, grabs attention, and isolates the
   voice. Also use this for **intimate or relatable moments, punchlines, and
   takeaways**.
   → `--dropout A-B`
3. **Use volume to signal progress.**
   - **Fade out over about 20 seconds** as a section ends. This promises the
     section is wrapping up, creating curiosity about what's next and
     preventing the "stuck on one long stretch" feeling that makes viewers
     leave.
     → `--fadeout A-B`
   - **Slowly raise the volume** to build anticipation toward a climax or
     payoff.
     → `--swell A-B:+6`
   - **Sync the song's hits and dips to the video.** Line up the moment the
     music picks up with a topic shift (for example, where the problem
     ends and the solution begins). The pickup marks the transition and
     makes the new segment more exciting.
     → `music_points.py song.mp3` to find pickups, then
     `--music song.mp3@S-E~OFF` with `OFF = pickup − (shift − S)`
4. **Control the parts of the song.** Mute drums that are too loud, solo
   the melody for intimate moments, raise specific parts to build
   excitement, and change a track's mood (make it more ethereal or
   mysterious). This needs music stems (separate drum, bass, and melody
   tracks). Many music libraries provide them; if the user has stems, mix
   them as separate `--music` tracks with their own gain and timing. Without
   stems, whole-track moves (tricks 1–3) still do most of the work.
5. **Music first, script second.** Music is hard to change, but narration
   is easy to speed up, slow down, expand, or trim. "Don't make the music
   dance to the script. Make the script dance to the music." It's like
   choreographing a dance: you pick the song first. The process is:
   - Outline the video and decide the mood of each section.
   - Place the chosen song in the timeline and mark its mood shifts.
   - Build the script around those mood shifts.

   This is advice for the user's *next* video. When editing existing
   narration, apply tricks 1–4.

## 3. Sound layer 2: Soundscape

Rule of thumb: add the sound of everything the viewer would hear if they
were *inside* the video. Imagine a soundscape, then build it in the
timeline.

1. **Atmospheric sound.** Give still images and footage an environment:
   dance-studio ambience over stock dance footage, film-projector noise over
   archival footage, environmental sound over drone shots, muffled crowd
   noise over a crowd photo, fire crackle. It brings the audience there.
2. **Every movement on screen makes a noise:** a whoosh when something
   moves, and a highlight sound when something is highlighted. This applies to B-roll,
   stock footage, animations, and motion graphics, **but not the A-roll**
   (no whoosh every time the host moves their hands).
   - **Go by feeling, not realism.** He used a lightsaber sound for moving
     eyes.
   - **SFX define the style.** A futuristic look pairs with whooshes; an
     analog look pairs with paper-collage rustles. Keep the palette
     consistent with the visual style.
3. **Never use the same SFX twice in a row.** An obvious pattern gets
   noticed and breaks immersion. Use variants, or make your own by changing
   pitch, speed, or EQ.
   → `mix_audio.py` automatically varies pitch and speed when the same file
   is used back to back. Still prefer genuinely different files when
   available.

## 4. Sound layer 3: Audio cues

These are sounds not coming from anything on screen. They tell the viewer
what to **feel** about what's on screen; they add emotion.

| Cue | Effect |
|---|---|
| Riser | Suspense and anticipation: "something important is about to happen" |
| Hit | Releases tension; emphasis like an exclamation point. Use alone or after a riser |
| Braaam | A bigger, more cinematic hit |
| Drone | Unease or tension |
| Motif (leitmotif) | Musical stings with a wide emotional range; experiment |
| Meme SFX | Comedic punctuation (genre-dependent; use sparingly) |

Place risers so they **end** on the moment, and hits **on** the word or cut.
**Only use a riser if something important actually follows.** Otherwise
risers lose their credibility and stop working. Don't overdo hits either.
Drones are best reserved for darker moods. These cues work because
emotional investment drives engagement.

## 5. Sound layer 4: Pauses ("shut up and show it")

Narration that goes straight from script to video is usually **too
dense**. A reader absorbs at their own pace, but a video "crawls forward
whether the viewer is absorbing everything or not." So slow down, but plain
pauses are boring. The fix:

- **Short beats ("shut up and show it").** Pause the voice after a key
  phrase and fill the pause with a quick visual layer plus a matching SFX.
  In a Johnny Harris example, he pauses after "from selling drugs" and
  "report it to the government" and illustrates each. Each point becomes
  up close and tangible, and the viewer gets a break to absorb without
  being under-stimulated.
  → `insert_beats.py --at T:DUR`, then overlay a visual and SFX in the gap.
- **Longer breaks for emotion.** After an emotionally charged line, stop
  talking and let the music carry the feeling for several seconds (as in
  Let Me Know's Venus-probe example). This works for positive moments too:
  let a happy track dominate briefly. When you stop talking, viewers don't
  get bored; they anticipate what you'll say next.
- **Longer breaks for complexity.** Split a complicated explanation
  partway through with a break. One long explanation becomes digestible
  chunks, which also creates a sense of progression.

**How this relates to dead-air removal:** remove *empty* pauses (hesitation,
restarts, nothing on screen). Keep or create *filled* pauses (a visual plus
SFX, or music carrying emotion). This is why his videos measure almost zero
silence even though he pauses deliberately: the pauses are never silent.

## 6. Voice recording

Tell users this when their voice audio is roomy, noisy, or popping. You
don't need an expensive mic, just good technique:

- Keep the mic about **6 inches (15 cm)** from the mouth. More than a foot
  away sounds distant and picks up the room.
- Angle the mic about **45° to the side**, pointed at the mouth, to avoid
  plosives (breath pops).

Editing can't fully fix a distant, roomy recording, so re-recording often
beats processing.

## 7. Picture and structure

These come from the frames of both videos.

- **Cold open, then proof.** He opens on camera, then within about 10 s
  cuts to credibility: subscriber counts, press headlines, and screenshots
  of successful videos.
- **Open with the demonstration.** The sound video opens by playing the
  intro, then replaying it *with bad sound design*. Show the before and
  after instead of describing it.
- **Signpost progress.** Name the structure ("four layers", "three rules",
  "tip number three") and use chapter or title cards. Combined with the
  20-second music fadeouts, the viewer always feels the video moving.
- **Concrete visuals for abstract ideas.** He uses metaphor graphics (a
  chef with an empty fridge for ideas, puzzle pieces for novelty, audience
  silhouettes for "who is this for") and a recurring flat cartoon
  character.
- **Look:** dim, warm, practical-lit room; shallow depth of field; dark
  grade; moody B-roll. Graphics use a dark textured background with one
  glowing cyan/blue accent. Kinetic text highlights key words in the
  accent color, black and white marks a "before" or flashback, and a red
  wash marks failure.
- **Keep the eye centered across cuts.** If every cut forces the viewer to
  refocus from one side of the screen to the other, it's an unimmersive
  experience. Keep the subject of consecutive shots near the same area.
- **Integrate CTAs and sponsors.** Mid-video calls to action are short and
  recapped ("real quick to recap... back to the video"). The end screen
  hands off to a recommended video instead of a long outro.

## 8. Growth philosophy as editing judgment

This is how he decides what's "good." Use it to frame critique:

- **The algorithm serves the most engaging experience.** Ignore everything
  else and make the video the most engaging experience possible, with the
  title, thumbnail, and intro making it obvious it's worth the viewer's
  time.
- **Be your own target audience.** Every one of the thousands of small
  decisions is "whatever I felt was most entertaining." Quoting Rick Rubin:
  there's no more valid metric for what others will enjoy than liking it
  yourself. Your taste must be *trained*, though, by studying popular
  videos you love.
- **Compare against favorites to find the single biggest gap.** Put the
  user's cut next to a favorite popular video in their niche and ask what
  most sets it apart. Fix that first; learn skills as needed, not all at
  once. This is the most useful critique move available: ask the user for
  a reference video they love.
- **Self-study questions** (use them as critique prompts): Why did this
  thumbnail get my attention? Why would I click this over the others? Why
  do I feel like clicking off at 25 seconds? Why do I feel good watching
  this? Why did I watch to the end?
- **Be unique or die early.** A new creator's video is first shown to
  diehard fans of the niche, who have "heard it all before." If it's
  generic, they don't engage and the algorithm stops showing it. Push for a
  distinctive style, format, intro, or perspective, both visually and
  sonically.
- **Make it interesting to as many people as possible.** Understand *why*
  something interests you, then design the edit so others feel it too.

## 9. Measured benchmarks

These come from `scripts/analyze.py` on his videos. Cut counts are a lower
bound.

| Metric | Growth video (talking head) | Sound video (cinematic) |
|---|---|---|
| Visual changes per minute, overall | ≥5.5 | ~17 |
| Visual changes per minute, first 60 s | ≥7 (≈12 by eye) | ~51 (demo cold open) |
| Average shot length | ≤11 s | ~3.5 s |
| *Silent* gaps > 0.5 s | 3 | 5 |
| Integrated loudness | −20.6 LUFS | −17.8 LUFS |

The pacing front-loads. YouTube lowers loud videos to about −14 LUFS but
doesn't raise quiet ones, so −14 is the default; −16 is fine for a quieter,
cinematic feel.

## 10. Critique rubric

Score each area, and give the timestamp, the problem, why it hurts
immersion or retention, and the fix (then offer to apply it). Lead with the
two or three biggest issues.

**Experience fit (check first)**
- What do these viewers come for: hangout, learning, or entertainment?
  Does the editing serve it, or disrupt it (for example, over-cut pauses
  on an authentic vlog, or a slow static talking head on an entertainment
  video)?

**Visual variety and continuity**
- Are A-roll, B-roll, and graphics used for their jobs? Do essential but
  boring beats get motion graphics? Is the result visual mush?
- Are stills static? Are images shown plainly instead of guiding the eye?
- Are captions used as filler, or longer than three words at a time?
- Do graphics pop in with no motion or sound? Does the eye jump across the
  frame at cuts?

**Sound**
- **Music:** Does the emotion match each section, or does one track run
  under everything? Are there dropouts on key lines, punchlines, and
  takeaways? Do sections end with a fadeout? Do swells lead into payoffs?
  Does a music pickup land on the biggest topic shift?
- **Soundscape:** Do B-roll, graphics, and stills have atmosphere and
  movement sounds? Is the A-roll free of gratuitous SFX? Are there
  back-to-back repeats of the same sound?
- **Audio cues:** Are risers, hits, or drones used where emotion should
  land? Does every riser pay off?
- **Pauses:** Is the narration too dense? Where would a "shut up and show
  it" beat help? Is there a long break after the emotional peak? Are empty
  pauses removed?
- **Voice:** Is it close, clean, and free of plosives? Does it stay above
  the music? Is loudness between −16 and −14 LUFS?

**Picture and structure**
- **Hook (0–30 s):** Is there a demonstration or proof? Does the picture
  change every few seconds?
- **Progress:** Are sections signposted? Is there any stretch that feels
  stuck on one thing?
- **Visuals:** Are abstract ideas made concrete? Is the eye position
  consistent across cuts?

**Story and clarity** (details in `story-and-retention.md`)
- Does the viewer always know what's happening, why it matters, and what
  could go wrong?
- Is the most extraordinary thing shown early?
- Do non-conflict stretches drag?
- Is there breathing room before big moments and after payoffs?

**Big picture**
- Compared with the user's favorite popular video in the niche, what is the
  single biggest gap?
- Would a diehard fan of the niche find something new here?
