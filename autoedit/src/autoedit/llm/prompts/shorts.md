# Task: pick Shorts

Score candidate windows of this transcript for vertical Shorts of 15-60 seconds. A Short must start
on its strongest line, be a self-contained idea with a payoff, and end on a line that loops well
into its own start.

## Channel profile
{profile_block}

## Transcript (sentence id, source time range, energy, text)
{transcript_block}

## Energy peaks (loudest sentences)
{peaks_block}

Return up to {max_candidates} candidates ranked by hook strength, self-containment and payoff, with
from/to sentence ids giving a window of {min_s}-{max_s} seconds, the hook sentence it starts on, a
title, and a 2-5 word context label for a cold viewer.
