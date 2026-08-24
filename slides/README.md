# The deck

This presentation is a single Manim/manim-slides scene, not a Slidev deck --
Slidev's iframe-embedding of external video fought its own asset-serving
rules at every turn, so the whole talk (title, schematic, full equation
derivation, judgment calls, implementation, verification, results video,
takeaways) now lives natively in one keystroke-triggered Manim scene:
`manim/presentation.py`.

## Setup

```sh
cd manim
python3 -m venv .venv
source .venv/bin/activate
pip install manim==0.21.0 manim-slides==5.6.0
```

Requires a LaTeX toolchain (`latex`, `dvisvgm`) and `ffmpeg` on PATH.

## Render, present, export

```sh
cd manim
source .venv/bin/activate

# Render every animation (only needed after editing presentation.py):
manim-slides render -q h presentation.py Presentation

# Present interactively, keystroke-driven (arrow keys / space to advance,
# "s" for speaker notes):
manim-slides present Presentation

# Export a self-contained, offline HTML player (what's committed at
# public/presentation.html + public/presentation_assets/):
manim-slides convert Presentation ../public/presentation.html --offline
```

Then open `public/presentation.html` directly in a browser (or serve
`public/` with any static file server) and use the arrow keys / space to
advance. Press "s" to open the speaker-notes window -- every slide's talking
points live there via `next_slide(notes=...)`, not on-screen; on-screen
content stays deliberately compact.

Always export with `--offline`, never `--one-file`: `--offline` bundles
reveal.js locally (no CDN dependency) with one small mp4 per animation step
in `presentation_assets/`; `--one-file` was found to corrupt the embedded
video streams.

## The results video

`manim/results_combined.mp4` is a side-by-side composite of `public/phi.mp4`
(particle concentration) and `public/velocity.mp4` (flow speed) with
captions burned in, built once via:

```sh
ffmpeg -y -i public/phi.mp4 -i public/velocity.mp4 -filter_complex "
[0:v]scale=640:427,pad=640:480:0:26:color=black,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='Φ(t) — particle concentration':x=(w-text_w)/2:y=h-32:fontsize=22:fontcolor=white[left];
[1:v]scale=640:427,pad=640:480:0:26:color=black,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='|u|(t) — flow speed':x=(w-text_w)/2:y=h-32:fontsize=22:fontcolor=white[right];
[left][right]hstack=inputs=2[stacked];
[stacked]pad=1280:520:0:0:color=black,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='buoyancy artificially scaled ~10⁶× to be visible on this clip — real Stokes settling is ~nm/s':x=(w-text_w)/2:y=h-30:fontsize=18:fontcolor=gray[out]
" -map "[out]" -c:v libx264 -pix_fmt yuv420p -movflags +faststart manim/results_combined.mp4
```

It's embedded as its own slide via manim-slides' `next_slide(src=...)`
mechanism, which copies an arbitrary external video file in as that slide's
entire content -- no manim-side video decoding/re-encoding needed.
