# Runbook

Use Node 22.13 or newer and Python 3.12. The application does not require an LLM API key.

```sh
npm ci
npm run build
node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0000_majestic_maverick.sql
npm run dev -- --port 5188
```

Open the printed local URL. The local-only sign-in simulator is at `/signin-with-chatgpt?return_to=/patients`. It is excluded from production. New schema changes must add a new Drizzle migration; do not replay already applied migrations.

```sh
uv sync
uv run pytest tests -q
uv run python scripts/assemble_evidence.py --check
uv run python scripts/verify_api.py
npm run typecheck
```

`verify_api.py` expects the local preview on port 5188. It creates a temporary failure trigger in the local test database, checks that audit failure withholds patient data, and removes the trigger in a `finally` block. It never operates on the deployed database. It also observes committed rows from a fresh Python process. Test access rows remain as local verification evidence.

Raw generation uses the commands and release checksums in `data/PROVENANCE.json`. Preserve the ignored `data/.deid-salt` locally to reproduce pseudonyms and shifted dates. Losing that salt changes pseudonyms and date-based sample boundaries; it must never be published. Existing committed sample parquet and measured artifacts support evaluation without raw exports.

Set `ROUNDS_RAW_CSV` to the raw CSV directory and `ROUNDS_DATA_ROOT` to a local working directory before running `pipeline/build_analytics.py`. It produces `processed/`. Evaluation defaults to committed `data/sample`; override `ROUNDS_EVALUATION_DATA` and `ROUNDS_EVALUATION_OUTPUT` for a fresh run. `ROUNDS_UCI_CSV` enables the optional local UCI benchmark. Its raw records must stay outside `public/`.

`ROUNDS_SOURCE_ROOT` points the validation script to the generation directory containing `population-2000`, `sample-300`, and `provenance.json`. Validation fixtures and raw source identifiers are never public. Review regenerated evidence before replacing the committed canonical results; run the assembler and its whole-file check afterward.

The browser SQL engine downloads its WebAssembly runtime from jsDelivr. If that host is blocked, the app offers aggregate downloads; the rest of the dashboard is independent of it. Fonts and evidence are hosted with the app.

The dashboard and GitHub repository are public for portfolio review. Patient workflow pages still require sign-in, a purpose of access, and a persisted audit receipt. Preserve the public Site audience when publishing updates. D1 migrations are applied by Sites. The source snapshot and build archive must match before saving a version. Roll back by redeploying a previous saved version; schema migrations must remain backward-compatible with that version.

## Production navigation regression check

Run `npm run build` followed by `npm run start -- --port 5188`. Test the compiled Worker rather than relying on the development server: the original Vinext client-link transitions passed development checks but threw in the deployed build.

Click each department sidebar link and confirm both the URL and department heading change. Also check the evidence links, a scorecard link, browser Back/Forward, the mobile sidebar, and a model-card fragment link such as `/models#highcost`. Confirm that the patient worklist still shows its purpose gate on a fresh visit. Check the browser console for navigation errors. Repeat representative clicks on the deployed site after publication.

Application links use the ref-forwarding `SiteLink` native anchor. Keep document navigation until the production router issue is independently resolved and these checks pass. Model fragments scroll after the asynchronous evidence bundle renders their targets.
