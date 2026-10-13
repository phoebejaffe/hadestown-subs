# Hadestown Cast Changes Tracker

Tracks which understudies/swings cover which roles per Hadestown (Broadway)
performance, sourced from atthisplaybill.com/hadestown ("View Prior Hadestown
Cast Changes").

## Re-scraping

When the user says **"sing the song"**, refresh the saved performance data,
regenerate the graph, and open the generated page:

```
python3 scrape.py
python3 fetch_headshots.py
python3 build_graph.py
open index.html
```

The scraper is incremental, so it preserves existing history and fetches only
missing performances.

Manual refresh commands:

```
python3 scrape.py
```

Pure stdlib, no deps. Takes ~30s.

## Scheduled publishing

- Live site: https://phoebejaffe.github.io/hadestown-subs/
- `.github/workflows/update.yml` runs daily at 1:30 PM and 6:30 PM Eastern and
  can also be run manually with GitHub's `workflow_dispatch` button.
- The workflow runs `scrape.py`, `fetch_headshots.py`, and `build_graph.py`,
  records `data/last_run.txt`, then commits the updated data and generated
  `index.html`.
- GitHub Pages serves the repository root. `.nojekyll` disables Jekyll so the
  generated files and headshots are served unchanged.

## Important site quirks

- Pages are `?perf=<id>`, but Cloudflare + Craft serve aggressively cached
  pages — every request MUST include a random cache-buster param (`&_=...`),
  which the scraper does. Without it you get stale pages.
- The site only retains ~30 days of performance records. Older `perf` IDs
  silently fall back to rendering the CURRENT performance. The scraper detects
  this by comparing the rendered date to the modal's label and marks
  `date_match: false` (recording the bogus served date in `served_date`).
- Re-running `scrape.py` is incremental: it preserves saved records, fetches only
  missing performance IDs, and promotes a saved `current` record when its ID
  appears in the prior-performance list.
- Re-run regularly to capture performances before they age out; local data
  is the permanent record.

## Data

- `data/performances.json` — one record per performance: `perf_id`,
  `datetime`, `changes[]` (`role`, `performer`, `bio`, `headshot`).
- `data/cast.json` — baseline cast, home tracks, understudy info, and the
  femme/masc Worker slot groups used to narrow substitution assignments.
- `data/cast_changes.csv` — flat `datetime, perf_id, role, performer`.
- `data/raw/perf_<id>.html` — raw HTML snapshots.

Note: the site reports only *changes* from the principal cast (e.g. "The role
of Fate will be played by X"). The principal/baseline cast is not in this data.
Worker group matches are used when the source permits; unresolved cover
assignments stay stacked in one unidentified Worker row rather than being
guessed. Ayla Ciccone-Burton is femme; Aryn Bohannon prefers Sydney Parra's
Worker track when available. For ambiguous swaps, arrows run from the known
vacant track cell to the moved primary's new role; swings use a blue dashed
portrait border to indicate offstage origin.
