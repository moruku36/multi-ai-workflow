# Architecture diagram generation

The four Mermaid sources are rendered by [Pele](https://pele.run/api) 1.6.0. The development dependency is the official [obsidianmd/pele 1.6.0 release](https://github.com/obsidianmd/pele/releases/tag/1.6.0) package tarball, retained in `vendor/` so rebuilding does not depend on a registry connection. Its SHA-256 is `0945cbff58d4c9c4959a15e18b1e6743c76ab40525de856fc478fdc4ed989a63`; the package metadata identifies `pele` 1.6.0, MIT, and `https://github.com/obsidianmd/pele`. Full license and attribution notices are preserved in `vendor/NOTICE.md`.

Vendoring the official tarball (~823KB) is preferred over standard registry resolution because it enables hermetic, fully offline builds (`npm ci --offline --ignore-scripts`) without network requests, registry authentication, or build-time external supply-chain exposure.

From this directory, run:

```sh
npm ci --offline --ignore-scripts
npm run build
```

The script writes the English and Japanese workflow and dashboard SVGs to `../../assets/`. Each SVG contains its own background, colors, font fallbacks and accessible title/description. It has no external images, fonts, scripts or links.

The two diagram concepts are task/review flow and dashboard record boundary, each in English and Japanese. Edit `workflow.*.mmd` or `dashboard.*.mmd`, then run the commands above. The build generates four SVGs in `assets/`. The dated `assets/workflow-architecture-2026-10-19*.mmd` files preserve an earlier snapshot and are not inputs to this build.

The SVGs include a white background and dark text and lines for consistent light/dark host display. Use the full-size links for narrow screens. Do not edit generated SVGs directly. After rebuilding, compare outputs with the committed SVGs and inspect a static render at desktop and narrow widths. A browser check must be recorded separately if performed.
