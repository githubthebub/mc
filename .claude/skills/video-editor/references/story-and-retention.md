# Story, clarity, and retention

Read this when planning what to cut, keep, reorder, or add voiceover to, and
when critiquing why viewers leave. It's distilled from four Learn By Leo
videos: 18 retention tactics, a Dream "Minecraft Manhunt" breakdown (1.5B
views), "six components" of high retention, and the growth handbook. Many
examples are from creators he studies (MrBeast, Ryan Trann, Vsauce, Mark
Rober, MKBHD, Johnny Harris).

## Contents
1. The one-sentence theory
2. The editor's litmus test (what to cut, what to voice over)
3. Green/purple structure
4. Intros and hooks
5. Conflict, stakes, and pacing
6. Clarity above everything
7. Delivery
8. Tactic checklist

---

## 1. The one-sentence theory

> Maintain constant clarity in the viewer's mind as to what they'll miss
> out on if they stop watching.

**Intrigue comes from uncertainty,** but **confusion destroys immersion.**
Keep these three states distinct:

- **Clarity:** "I know what's happening." You always want this.
- **Uncertainty:** "I don't know what'll happen next." You want this.
- **Confusion:** "I don't know what's happening." You never want this.

## 2. The editor's litmus test

After footage is shot, Ryan Trann checks every moment against three
questions. **The viewer must always know:**

1. **What's happening.**
2. **Why it's important.**
3. **What could go wrong.**

If all three are known, viewers will watch whatever follows. Applying it
to an edit:

- **When the footage already says it** (he says "I'm so scared right now"
  on camera), keep it.
- **When it doesn't, write a voiceover line** for the creator to record
  and place it before the moment. In the jump-to-the-island example, the
  voiceover about fear, danger, inexperience, freezing water, and possibly
  falling was all added in the edit, and it's what makes the jump
  gripping. → Write the lines with timestamps, then mix recordings in with
  `mix_audio.py --vo line.wav@T`.
- **When a stretch has no chance of failure and no curiosity can be
  created, cut it.** If you can't create curiosity or expectations, cut
  it. Summarize it in a sentence or two of voiceover, or compress it into
  a montage. Mark Rober's year of planning and two months of building
  became "a 20-second build montage." → `montage.py`
- **Add a voiceover for clarity** whenever the story's state has changed
  and the viewer might not know where they are ("The duck woke me up and
  now it's time to turn off the lights").

## 3. Green/purple structure

Leo color-codes scripts. **Green** sections give the reason to care (a
problem, mystery, question, or expectation). **Purple** sections deliver
the answer or payoff. Don't get straight into information or action
without a green first, or it's just boring information instead of an
answer to the viewer's question.

There are four ways to create a green:

1. **A mystery, problem, question, or obstacle** that lacks an answer.
2. **Something counterintuitive** ("it's the small asteroids you should
   worry about").
3. **Someone knows a secret.**
4. **A missing component** the viewer hasn't considered.

For informative videos, alternate problem → solution or question → answer.
For doing-stuff videos, stakes and what could go wrong are the green
before each purple.

**Connect beats with "but" and "therefore," never "and then"** (the
South Park rule). "This happened and then this happened" is repetitive and
leaves exit points. "We tried this, but that got in the way, therefore we
had to do this..." creates a seamless path. This applies to scenes,
explanation topics, and even sentences.

**In the edit:** when sections feel disconnected, reorder so each one
answers the previous one's problem, or suggest a bridging line ("but
there's a catch...").

## 4. Intros and hooks

**Why roughly 90% of retention graphs drop at the start: disappointment.**
The title and thumbnail created expectations, and the intro didn't deliver
them fast enough, so viewers go looking for something better. An average
video loses over a third of its audience in the first 30 s for this reason.

- **Make the title, thumbnail, and intro together.** Ask what reason to
  watch and what expectations the packaging creates, then make the intro
  deliver them immediately. If it's in the title or thumbnail, show it in
  the intro. When editing, always get the title and thumbnail first and
  check the first seconds against them.
- **Meet three expectations: information, pacing, and mood.** A thumbnail
  promises a *feeling* as well as content. MrBeast's train-crash intro
  delivers both the promised content and the action feeling within 5 s:
  a rushing zoom, the train emerging, horn SFX, and five words in the first
  second. The frog-pool robot intro takes 22 s just to explain the problem,
  but it's light-hearted like its thumbnail, so it works. **Match the intro's
  pacing to the genre and to the style promised by the thumbnail.**
- **Confirm, then deliver.** Confirm the video is what they expected, then
  start delivering right away. **Never ask for likes, subscriptions, or
  money in the intro;** that isn't what viewers came for.
- **Show it, don't just say it.** A voiceover over changing footage (a
  camera switch about every 4 s) delivers strong audio and strong visuals
  at once, which is ideal for intros.
- **Tell it as a story.** Introduce the element, then reveal the twist
  ("this is a frog... it's dead... they keep drowning in my pool"). A bare
  description is weaker even when shorter.
- **The edit matters as much as the script.** The same intro stripped of
  graphics, SFX, captions, transitions, and good music feels dead. Add a
  couple of these every few seconds, according to the genre.
- **Every sentence counts.** Leo rewrites intros up to five times, working
  on adjectives, sentence structure, level of detail, and order.
- **Exceed expectations.** Once the promise is met, add *extra* value the
  viewer didn't expect ("we're also crashing... starting with a house full
  of 100,000 fireworks"). It raises the bar for the whole video. Leave
  something out of the title so the intro can surprise.

- **Proof, not promise.** Put the most extraordinary thing as close to
  the start as possible. "Watch to the end to see X" loses about 80% of
  viewers before the end. Showing that the video is special beats
  promising it.
- **The Manhunt intro formula** (clean window onto the premise):
  1. Repeat the premise from the title and thumbnail, verbally and
     visually, so it's obvious what this video is. Starting mid-action
     with no framing is disorienting.
  2. Add context or social proof ("the last video got 1M likes in a day"),
     and/or a question that highlights the core conflict and uncertain
     outcome ("Can they stop me, or will I survive?").
  3. Add a call to action (subscribe) only once the viewer is excited.
- **Open with the most broadly appealing question** (MKBHD: "What is using
  the Apple Vision Pro actually like?"), then layer in the specifics.
- **Name a common pain point** and show you understand it before teaching.
  This works in the intro and throughout the video.
- **Aim for immediate conflict and an early payoff.** Something unresolved
  right away, and something awesome, helpful, or funny early. Set it up
  before recording if possible ("What can we do now to maximize the chance
  something awesome happens once we start recording?").
- **Mystery in the hook.** Lead with the most intriguing detail, like Mark
  Rober's feet in shark-infested water with a bucket of blood.

## 5. Conflict, stakes, and pacing

- **The leaking water tank.** Attention drains constantly and refills only
  when you give value: something interesting, important, helpful, or
  something that makes them smile. The drain speed varies by niche and age
  (around 20 s for some audiences, 2–3 min for others), so spread key
  points evenly and never let the tank run dry.
- **Pockets of dopamine.** Plan small breaks (a quick edit, a montage, a
  joke) between dense points. Without them, the video flies by and
  overwhelms the viewer.
- **Energy contrast.** A hyper-edited section that abruptly drops into a
  calm A-roll stretch (or the reverse) forces the viewer to refocus.
- **Concise, not soulless.** A 3-minute video that feels like 10 beats a
  10-minute video that could have been 3. But over-trimming feels chaotic;
  keep the spirit of a natural conversation.
- **Add, don't stretch.** Legitimate length comes from additions such as
  personality, jokes, and asides (Ryan Trahan's joke about the lab
  founder's two-word emails), never from padding what's already there.
- **No such thing as an outro.** Keep the second half as good as the
  first; no credits or winding down. End on value, then hand off to the
  next video with an end screen. Binge-watching is the strongest signal.

- **Maximize screen time of conflict.** 72% of the analyzed Manhunt video
  is active conflict, far above typical. In the edit, prune every second
  that lacks conflict or is unnecessary, even inside a chase.
- **But keep the progression points.** Each cut in the chase lands in a
  new biome, showing where he's going. Non-conflict stretches become a
  highlight reel of progress. Cutting progress entirely ("stone tools, then
  suddenly full iron") causes confusion.
- **Breathing room is deliberate:**
  - **Before a big fight:** about 20 s of "nothing happening" after the
    premise is clear lets anticipation build ("how will he escape?").
    Then the music kicks in and the action starts with the viewer already
    on the edge of their seat.
  - **After a big payoff:** calm stretches (mellow music, banter) prevent
    tolerance. Constant high intensity numbs the viewer; contrast makes the
    extremes felt.
- **Music tracks the feeling.** Upbeat music cuts to dead quiet when the
  hunters spot him, then tense stealth music kicks in as he escapes.
  Choose music to make viewers feel exactly how the creator felt in that
  moment. For informative content, choose music that expresses how you
  feel about what you're saying. Switch tracks when the mood switches, as
  Vsauce does for a turn to "you will be forgotten."
- **Stakes and threats** (tactics to spot and emphasize in the edit):
  - An antagonist or opposition.
  - A time limit (show the timer).
  - What's at stake and why it matters to this person.
  - What could go wrong, stated right before it might (MrBeast stepping
    in to explain "if that was you, you'd get nothing").
  - An underdog framing: outnumbered, inexperienced, unprepared, or
    under-equipped.
  - Competition.
  - A new challenge when things get stale.
- **Something to look forward to, with clear progression:** escalating
  rooms or difficulty, a top-10 countdown, or a stated goal.
- **Mysteries planted and paid off later.** Ryan's mysterious room at
  3:45 gets brought back 6 minutes later, so leaving early means
  unanswered questions.
- **Iconic moments.** Surprising, memorable moments (Dream's tricks at
  life-or-death moments) create compilations and binge-watching. In the
  edit, give these moments room: build-up, stakes stated, reaction shots,
  and the payoff held a beat. In critique, ask what people would clip from
  this video.

## 6. Clarity above everything

- **Confusion was the #1 mistake** Leo found across dozens of viewer
  submissions, more common than bad editing, weak storytelling, or
  monotone delivery. Creators are biased because they have all the
  context; the viewer has none. Leo revisits every part of a video about
  100 times to make it easier to understand.
- **Make ideas tangible** with an analogy or example.
- **Show a visual for everything mentioned.** Fast pacing makes details
  easy to miss, so every noun gets a visual. Then direct focus: zoom and
  pan to exactly what the viewer should look at.
- **Get a fresh viewer to watch before publishing.** Every time, someone
  finds a boring or confusing moment. As the editor, you're partly that
  fresh viewer: flag anything you, without the creator's context, didn't
  follow.
- **Familiar premises need less explaining.** The more the audience
  already understands the activity (beating Minecraft), the more time goes
  to fun instead of setup.

## 7. Delivery

Critique this; you can't fix it in the edit, beyond cutting flubs.

- **Infectious enthusiasm** creates trust and curiosity, even for unknown
  creators (Vsauce naming the colors of a Rubik's cube is compelling on
  delivery alone). Emotion is contagious: monotone delivery feels boring,
  and discomfort on camera makes viewers uncomfortable.
- **Vocal variety:** louder for excitement, lower for suspense, pauses for
  anticipation and emphasis.
- **Body language:** raised eyebrows, a slight squint for detail, head
  movement in sync with words, hands separating ideas, wide arms for big
  things, a pinch for precise things.
- **Fixing camera shyness:** don't memorize word for word, since focusing
  on the words produces monotone. Talk to the camera like an interested
  friend. Energetic takes with ums beat flawless monotone takes, and the
  ums get cut in the edit anyway.
- **Genuine fun can't be faked.** If the script bores the creator, it'll
  bore the viewer.

## 8. Tactic checklist

Use this for critique; name the ones present and the missing ones that
would fit:

1. The most extraordinary moment first (proof, not promise).
2. Infectious enthusiasm.
3. The viewer never feels they know enough (tell them what they're
   missing before explaining, and pose questions between facts).
4. An antagonist or opposition.
5. Non-conflict parts go by fast (montage or summary).
6. The broadly appealing question opens the discussion.
7. A common pain point is named before the lesson.
8. A time limit.
9. A mystery planted and paid off later.
10. Stakes, and why they matter to this person.
11. A new challenge when things get stale.
12. Music and editing enhance each tone shift.
13. Something to look forward to, with clear progression.
14. What might go wrong is stated.
15. Perfect clarity (voiceover to reorient).
16. Competition.
17. Something counterintuitive or surprising.
18. A highlight reel of the best moments or information (long projects
    packaged as a tight emotional ride).
