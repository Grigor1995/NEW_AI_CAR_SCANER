# NEO AUTOMOTIVE DIAGNOSTIC design system

| Token | Dark value |
|---|---|
| Background / secondary | #070D18 / #0D1726 |
| Card / elevated | #122136 / #192B43 |
| Neon / cyan / secondary blue | #00BFFF / #29DFFF / #126EFF |
| Main / secondary text | #EDF7FF / #9CB5CC |
| Border | #25415C |
| Success / warning / error | #20D79A / #FFB547 / #FF596D |

ui/themes/Neo.qml is the shared token source. Cards use 16 px corners, 8 px spacing multiples, restrained hover animations and explicit state text. The desktop uses a top bar and home-card navigation, no expanded sidebar. A narrow layout uses two home columns and one diagnostic/form column. Dark/light/system themes are persistent; dark is the default. Color never replaces measurement-quality text.

Qt controls provide keyboard semantics; icon buttons/cards carry accessibility labels. Full accessibility and native touch/safe-area validation are NOT RUN. Current actual screenshot: testing/desktop-foundation.png. Planned pages must remain visibly labeled and must not show production placeholders as real metrics.
