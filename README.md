# Civic Stack

**94920 Corpus** — homeowner authority graph for ZIP 94920 (Tiburon, Belvedere, Paradise Cay / CSA 29, Strawberry).

Homeowners get told “the law says…” without ever seeing the law. This graph maps every statute, ordinance, and founding instrument that touches that house, shows who granted the power, and marks contradictions and takings — exact text first, not a lawyer’s paraphrase.

## Civic family

Module under the [civic.ink](https://civic.ink) umbrella (property / authority stack). Sibling to Records, Past, Eyes Off / DeFlock. Tracked on LifeOS **In Motion** (Civic lane). Owner: Civic Chief of Staff.

Public production host (DNS later, out of scope here): **stack.civic.ink**.

## Status

Public repo · Next.js App Router reconstruction of the live preview. Corpus for all four 94920 profiles is in `data/`.

Preview reference (source of truth for UX + recovered payloads):
https://temporary-fast-sirocco-y2qkj5q.vercel.app

Not legal advice. Official publishers control.

## Local run

```bash
npm install
npm run dev
```

Open http://localhost:3000. Profile switcher: `?profile=tiburon|belvedere|paradise_cay|strawberry`.

Routes: `/` home · `/corpus` laws · `/graph` authority rings · `/chain` grant walk · `/issues` flags.

```bash
npm run build
npm start
```

## Data

Public enacted-text corpus only:

- `data/corpus_{profile}.json` — instrument / provision / jurisdiction rows for each profile
- `data/issues.json` — structural flags (notes, not enacted text)
- `data/profiles.json` — profile titles and blurbs
- `data/graph.json` — full public knowledge graph (nodes, edges, authority paths)

Do not add LifeOS investigation packets, private evidence, deed/tax-lien screenshots, or CPRA drafts to this repo.

## License

MIT. See `LICENSE`.
