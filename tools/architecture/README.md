# Architecture diagram generation

The two Mermaid sources are rendered by [Pele](https://pele.run/api) 1.6.0. The development dependency is the official [obsidianmd/pele 1.6.0 release](https://github.com/obsidianmd/pele/releases/tag/1.6.0) package tarball, retained in `vendor/` so rebuilding does not depend on a registry connection. Its SHA-256 is `0945cbff58d4c9c4959a15e18b1e6743c76ab40525de856fc478fdc4ed989a63`; the package metadata identifies `pele` 1.6.0, MIT, and `https://github.com/obsidianmd/pele`. Full license and attribution notices are preserved in `vendor/NOTICE.md`.

Vendoring the official tarball (~823KB) is preferred over standard registry resolution because it enables hermetic, fully offline builds (`npm ci --offline --ignore-scripts`) without network requests, registry authentication, or build-time external supply-chain exposure.

From this directory, run:

```sh
npm ci --offline --ignore-scripts
npm run build
```

The script writes `../../assets/workflow-architecture.en.svg` and `.ja.svg`. Each SVG contains its own background, colors, font fallbacks and accessible title/description. It has no external images, fonts, scripts or links.

The diagram illustrates the current manual operational flow:
1. **Product Owner**: direction, task scoping, and final acceptance.
2. **Dottie coordination**: task coordination (Codex is used only for handoffs and result checks).
3. **Antigravity · Gemini 3.8 Flash**: primary implementation worker.
4. **Higher-tier model**: manually invoked only when needed for difficult problems, returning immediately to Flash once resolved.
5. **Independent review (manual)**: conducted manually using MiMo V2.6 Pro in an existing Open WebUI deployment (no automated routing or auto-wiring).
6. **Tests & checks / Owner approval**: mandatory verification gates before final deliverables.
