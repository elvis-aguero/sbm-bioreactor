# Running the deck

This must be run from inside this `slides/` directory, using this project's
own pinned Slidev version — not a globally-installed `slidev` CLI, and not
from the repo root. Slidev computes where `public/` assets (the videos)
live relative to how it's invoked, and a mismatched invocation is the
likely cause of `/phi.mp4` (or similar) failing to load with an
`Import ... resolves outside of Vite server.fs.allow` error.

```sh
cd slides
npm install
npm run dev
```

Then open the printed `http://localhost:3030/` URL.

To build a static export instead:

```sh
npm run build
```
