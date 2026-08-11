# London Flip Finder

**Valuation and mispricing detection for the London residential property market, 2008–2016.**

The project predicts what a London property is worth from its physical, spatial, temporal and
macroeconomic context, then applies **conformal prediction** to derive a statistically calibrated
price floor. A listing priced below that floor is flagged as a **flip candidate** — with a
quantified margin of safety rather than a hunch.

The entire project is one notebook: [`london_flip_finder.ipynb`](london_flip_finder.ipynb).

---

## Quickstart

```bash
git clone https://github.com/GiladAviv/LondonFlipFinder.git
cd LondonFlipFinder

python3 -m venv venv
./venv/bin/pip install -U pip setuptools wheel
./venv/bin/pip install -r requirements.txt
./venv/bin/python -m ipykernel install --user \
    --name london-flip-finder --display-name "London Flip Finder"

./venv/bin/jupyter lab london_flip_finder.ipynb
```

Then run the notebook top to bottom. **No manual data setup is required** — section 3 downloads
the 220 MB dataset archive from [Releases](https://github.com/GiladAviv/LondonFlipFinder/releases/tag/v1.0.0)
and extracts it to `data/` on first run, and skips the download on every run after that.

Requires Python ≥ 3.9. Verified on 3.9.25.

### Running it headless

The notebook is also its own end-to-end test:

```bash
# ~5 minutes: reduced iteration budgets, exercises every code path
LFF_FAST_MODE=1 ./venv/bin/jupyter nbconvert --to notebook --execute \
    --inplace london_flip_finder.ipynb

# full run
./venv/bin/jupyter nbconvert --to notebook --execute --inplace london_flip_finder.ipynb
```

A non-zero exit means a stage broke or one of the section 17 self-checks failed.

### Configuration

| Variable | Effect |
|---|---|
| `LFF_DATA_DIR` | Point at an existing dataset directory instead of `./data` |
| `LFF_FAST_MODE=1` | Shrink every model's iteration budget for a fast smoke run |

Everything else — price caps, split ratios, the luxury threshold, the conformal α, the random
seed — lives in the single frozen `Config` object in section 2. On Google Colab the data
directory resolves to Google Drive automatically.

---

## The pipeline

```
GitHub Release ──► data/ ──► load ──► clean ──► spatial join ──► master table
                                                                      │
                              ┌───────────────────────────────────────┘
                              ▼
             temporal + market features (all strictly lagged)
                              │
                              ▼
              chronological split  ──  70% train / 15% val / 15% test
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  Ridge baseline      XGBoost / CatBoost      Mixture of Experts
        └─────────────────────┼─────────────────────┘
                              ▼
                  select on validation MdAPE
                              ▼
                  score once on held-out test
                              ▼
              conformal calibration ──► flip scanner
```

## Data

| Source | Grain | Contributes |
|---|---|---|
| Land-Registry-derived price history | one row per sale event | target price, physical attributes |
| Met Police crime by LSOA | LSOA × category × month | neighbourhood safety |
| Bank of England base rate | one row per rate change | cost of borrowing |
| TfL station geodata (Feb 2022 snapshot) | one row per station | transport connectivity |
| GLA borough boundaries | polygon per borough | administrative context |

**Deliberately excluded.** The source file carries `saleEstimate_*` and `rentEstimate_*` columns —
a third party's model output for the same property. Using them to predict price would be target
leakage. The 300 MB postcode-geo file and the school scorecards are not loaded either: the
original notebook read both (costing ~1 GB of RAM) without either ever reaching a feature.

**The station file is a problem the pipeline corrects, not ignores.** It is a February 2022
network snapshot applied to 2008–2016 transactions. Used raw, 41 of its 471 stations are Elizabeth
Line stops that did not open until May 2022 — crediting a 2009 sale with a rail link that arrived
thirteen years later — and another 39 are Croydon Tramlink stops with no Underground service at
all. Both are filtered out by positive selection on the Underground/Overground/DLR flags (which
correctly keeps the 6 stations, like Paddington, that later gained Elizabeth Line service too).
*Residual caveat:* some Overground/DLR extensions also post-date parts of the window; fixing that
fully needs per-station opening dates, which this dataset does not carry.

## Features

24 features (19 numeric, 5 categorical) are built to answer one question: *would a buyer standing
at the transaction date have known this?*

| Group | Features |
|---|---|
| Physical | `floorAreaSqM`, `total_rooms`, `avg_room_size`, `bathrooms` |
| Spatial | `distance_to_underground_m`, `distance_to_transit_m`, `station_zone`, `distance_to_center_m`, `latitude`, `longitude`, `borough`, `outcode` |
| Asset | `propertyType`, `tenure`, `currentEnergyRating` |
| Safety | `crime_volume` (1-month lag), `crime_volume_prev_12m` (12-month trailing sum, current month excluded) |
| Macro | `interest_rate` (BoE base rate in force on the completion date) |
| Temporal | `days_since_start`, `month_sin`, `month_cos` |
| Market | `market_median_rolling_3m`, `market_median_rolling_12m`, `lagged_borough_median_sqm` |

Distance is split into **two** measures rather than one, because they answer different questions:
`distance_to_underground_m` (is this a tube flat?) and `distance_to_transit_m` (does it have any
rail link at all — Underground, Overground or DLR?). `station_zone` comes along for free from the
same `cKDTree` query that finds the nearest Underground station. Everything is computed in
**British National Grid (EPSG:27700)**, i.e. in metres; the tree turns a 32 M-pair brute-force
comparison into a sub-second query.

Section 17 verifies the lag guarantee *causally*: it multiplies the final month's prices tenfold
and asserts that every lagged market feature for that month is unchanged.

---

## Results

79,815 sale events with size data reduce to **59,946** modelling rows after dropping properties
outside the GLA boundary, filtering symbolic transactions below £1,500/sqm, and deduplicating
repeated completions. Split chronologically into **four** slices — 60 % train / 15 % validation /
10 % calibration / 15 % test (35,967 / 8,991 / 5,994 / 8,994 rows) — because conformal calibration
needs data the model was never tuned against; see *Methodology notes* below. All models are scored
on identical rows: validation, calibration and test transactions under the £4 M cap (8,840 / 5,916
/ 8,859 rows respectively).

Models are **selected on validation** and then scored **once** on the untouched test set.

| Model | Trained on | Val MdAPE | Test MdAPE | Drift | Test MAE | Test R² |
|---|---|---:|---:|---:|---:|---:|
| 3-seed average (XGB) | cleaned | 15.50 % | **21.90 %** | +6.40 pp | £187,321 | 0.585 |
| MoE — error routing (XGB) | cleaned | 15.45 % | 21.90 % | +6.45 pp | £187,290 | 0.585 |
| CatBoost | cleaned | 15.11 % | 22.07 % | +6.96 pp | £178,608 | 0.653 |
| XGBoost | capped ← *selected on validation* | **15.07 %** | 22.21 % | +7.14 pp | £171,498 | 0.724 |
| MoE — luxury routing (XGB) | cleaned | 15.81 % | 22.21 % | +6.40 pp | £185,692 | 0.623 |
| XGBoost | raw | 15.39 % | 22.23 % | +6.84 pp | £170,401 | 0.712 |
| XGBoost | cleaned | 16.01 % | 22.67 % | +6.66 pp | £191,121 | 0.582 |
| 3-seed average (CatBoost) | cleaned | 15.34 % | 22.50 % | +7.16 pp | £177,590 | 0.670 |
| MoE — error routing (CatBoost) | cleaned | 15.33 % | 22.51 % | +7.18 pp | £177,673 | 0.669 |
| Ridge (baseline) | capped | 17.39 % | **16.62 %** | **−0.77 pp** | £168,529 | 0.277 |

**Conformal bound.** Calibrated on a dedicated calibration split at α = 0.10 (never touched by
early stopping or model selection), the safety multiplier is **q₁₀ = 0.8823** — the floor sits at
88.2 % of the predicted value. Empirical coverage on the held-out test set is **91.39 %** against a
90 % target (+1.39 pp) — closer to nominal than the previous iteration's 92.13 %, which is the
expected effect of calibrating on genuinely untouched data rather than a validation set the model
was indirectly tuned against. The scanner flags **763 of 8,859** test properties (8.61 %) as priced
below their floor, at a median margin of **£73,400**.

### Feature-group ablation: is crime worth the data it costs?

The crime file caps the whole project at 2008–2016, discarding 80 % of the available 418k-row
price history. Section 14.2 measures what that trade actually buys by retraining CatBoost with
each feature group removed:

| Removed | Test MdAPE | Δ vs. full |
|---|---:|---:|
| *(full model)* | 22.07 % | — |
| Macro (`interest_rate`) | 22.31 % | +0.24 pp |
| Crime | 22.54 % | **+0.46 pp** |
| Transport (distance + zone) | 22.68 % | +0.61 pp |
| Market lags | 24.26 % | +2.19 pp |

**Verdict: crime clears the 0.15 pp bar (+0.46 pp), so — per the decision rule this ablation was
built to test — it is not dead weight and dropping it outright is not justified.** But it is also
not the dominant signal: the market-lag features are worth roughly 5× as much. The recommended
next step is therefore *not* "drop crime, widen the window" but "source post-2016 LSOA crime data
(data.police.uk publishes monthly extracts) so the window can widen to 1995–2024 without losing
the one feature group that earned its place."

*(An earlier fast-mode smoke test — 120 boosting iterations instead of 1,000 — showed the opposite
sign on this ablation. That was a low-capacity artifact, not a real result: with too few trees to
spend on a widened feature set, adding a feature does no better than noise. The numbers above are
from the full-precision run and are what should be trusted.)*

### The headline finding: architecture choice was an artifact of evaluation design

Test MdAPE drift jumped from ~3.4 pp (previous iteration, three-way split) to **~6.4–7.2 pp**
(this iteration, four-way split) for every tree-based model, while Ridge's drift *improved* to
−0.77 pp. Ridge now beats the best tree model on test MdAPE by **5.3 percentage points** (16.62 %
vs. 21.90 %) — a far larger gap than before.

The cause is the four-way split itself, and it is worth stating plainly rather than burying it.
Introducing a dedicated calibration slice did two things: it cut training data from 70 % to 60 %,
and — because calibration sits between validation and test — it moved the validation window
further from the test window than before (an 8-month gap instead of none). XGBoost and CatBoost
choose their iteration count via early stopping *against validation*, so both changes hit them
directly: less data to fit, and a selection signal that is temporally further from what it is
being selected to predict. Ridge has no early-stopping step and is far less sensitive to either
effect, which is why it barely moved.

This is a genuine cost of the more rigorous evaluation, not a bug, and the trade was made
deliberately: the calibration split sits *immediately before* test, which is the choice that
protects conformal validity (residuals close in time to test are the most defensible stand-in for
test residuals) at the expense of how close validation sits to test. An unexplored alternative is
reordering to train → calibration → validation → test, which would restore validation's adjacency
to test at the cost of moving calibration further away — see *Where to take it next*.

### Repeat-property diagnostic

**23.8 %** of test transactions (2,112 of 8,859) are properties that also appear in training — a
consequence of splitting a price *history* by time rather than by property.

| Test subset | Rows | MdAPE | MAE | R² | Within 25 % |
|---|---:|---:|---:|---:|---:|
| Seen in training | 2,112 | 23.21 % | £165,344 | 0.727 | 57.3 % |
| Unseen property | 6,747 | 21.91 % | £173,425 | 0.723 | 58.6 % |

This flipped sign from the previous iteration (where seen properties scored 0.55 pp *better*):
here, previously-seen properties are predicted **1.30 pp worse** than genuinely new stock. With
the underlying model now the more volatile `XGBoost (capped)` rather than `CatBoost (cleaned)`,
and the training window changed, memorisation is not a stable, one-directional effect — which is
itself informative: it means the 26 % overlap is not quietly propping up the headline number in
either direction, but it also means the diagnostic should be re-read after every material change
rather than assumed stable. A group-aware split (improvement 1 below) would remove the ambiguity
entirely.

## Methodology notes

### Why the split is chronological

A random split would let the model learn from June 2016 to predict January 2016 — a situation that
never occurs in production. Sorting by date and cutting it into ordered slices reproduces the real
task: train on the past, forecast the future.

### Why MdAPE is the headline metric

MAE is quoted in pounds and is easy to explain, but it is dominated by the expensive tail: a 10 %
miss on a £3 M house contributes thirty times more than a 10 % miss on a £100 k flat, though both
are equally wrong in the only sense a buyer cares about. The **median** absolute percentage error
is robust to that tail and answers the practical question — what does a typical valuation get
wrong by?

### One evaluation universe, three training variants

Models differ only in what they were **trained** on (`raw`, `capped` at £4 M, or `cleaned` of
anomalies). Every model is **scored on identical rows** — validation/calibration/test transactions
under the cap. Anomalies are removed from training only: deleting hard cases from your own exam
inflates the score, and a production model does not get to refuse the awkward listings.

### Why calibration gets its own split

Validation drives early stopping and model selection, so a tree model's hyperparameters are
implicitly tuned to minimise error on those exact rows. Calibrating the conformal bound there too
would make `q₁₀` optimistically tight — the safety multiplier would look better than it really is.
The calibration split sits strictly between validation and test, touched by nothing except section
15, so `q₁₀` is computed on data the model genuinely never influenced.

### The conformal bound

On the calibration split we take the ratio of actual to predicted price for every property and
read off the 10th percentile, `q₁₀`. A new property's floor is `prediction × q₁₀`, and ~90 % of
properties should sit above it.

Ratios rather than differences, because absolute residuals here are heteroscedastic — one absolute
quantile would be far too loose at the bottom of the market and far too tight at the top. A
chronological split does not strictly satisfy conformal prediction's exchangeability assumption,
so the empirical coverage check is not a formality; it is the evidence, reported whether or not it
lands on target.

---

## What changed from the previous version

The previous notebook was a Colab research scratchpad. The rewrite fixed ten defects, several of
which materially changed the reported results.

| # | Defect | Consequence | Fix |
|---|---|---|---|
| 1 | `pd.to_numeric(category_of_strings, errors='coerce')` on `propertyType`, `tenure`, `borough`, `outcode` | Those four columns became **entirely NaN**; every CatBoost model and every MoE router trained on four dead features | CatBoost uses native `cat_features`; routers use train-fitted target encoding |
| 2 | The conformal cell called `expert_0`/`router_clf` directly, but a later cell had rebound them to a different backend trained on a different feature space | The "90 % guarantee" was computed from a model nobody intended to deploy, on mismatched features | Uniform `ModelBundle.predict()`; calibration and scoring share one code path |
| 3 | `IsolationForest` fitted on all data, anomalies dropped from validation and test too | Hard cases deleted from the exam — scores inflated | Fitted on the training slice, filters training only |
| 4 | Every reported metric came from the validation set | Model selection and reporting on the same data — circular | Select on validation, score once on the untouched test set |
| 5 | Two incompatible encodings (target-encoded numerics vs raw `category`) compared as equals in one table | Leaderboard compared models *and* feature spaces simultaneously | One encoding path, one evaluation universe |
| 6 | `df_tube` rebound inside an EDA cell, destroying the raw station table | Notebook could not be re-run top to bottom | Plot functions use locals; nothing rebinds global state |
| 7 | `distance_to_center` computed as Euclidean distance in **degrees** | Distorted geography along the east–west axis | Computed in BNG metres |
| 8 | Crime gaps filled with a median computed over the whole period | A statistic including the future injected into early rows | Left as NaN; each model imputes from training data |
| 9 | 300 MB postcode file + school scorecards loaded, never used; empty cell; `target_encode()` defined but never called; one cell fully redundant with the next | ~1 GB of wasted RAM and dead code | Removed |
| 10 | Chart labels said "<£5M" where the cap was £4 M; three near-identical metric functions with inconsistent key spellings (`MdAPE` vs `MDAPE`); leaderboard assembled from hand-typed literals | Silent mislabelling | Labels derive from config; one metric function; leaderboard generated from a results registry |

Two additions worth calling out:

* **A 3-seed average control.** The error-driven MoE trains three experts differing only by random
  seed, then routes between them. Averaging those same three experts costs nothing and is what the
  routing must beat to justify itself. Without that control, an MoE that beats a single model has
  proved only that ensembling works.
* **A repeat-property diagnostic.** The source is a price *history*, so a dwelling sold twice
  appears on both sides of a time-based split. Section 14.1 reports test accuracy separately for
  properties seen and unseen during training.

Also new: a versioned Parquet cache (a pipeline change invalidates it rather than silently serving
a stale table), seven automated self-checks, and persisted artifacts.

### Phase A — a follow-up review found four more issues

A second pass over the committed rewrite found problems specific enough that fixing them changed
results again:

| # | Issue | Fix |
|---|---|---|
| 1 | The station file is a Feb 2022 snapshot; 41 Elizabeth Line stations (opened May 2022) and 39 Croydon Tramlink stops (no Underground service) fed the one distance feature used for every 2008–2016 transaction | Positive selection on Underground/Overground/DLR flags; split into `distance_to_underground_m` and `distance_to_transit_m` |
| 2 | `Zone`, present for all 471 stations, had zero references in the pipeline | Nearest station's fare zone attached as `station_zone`, free from the existing `cKDTree` query |
| 3 | The conformal calibration set was the same validation set used for early stopping and model selection — calibrating on data the model was implicitly tuned against | New dedicated calibration split (60/15/10/15 train/val/calib/test); §17 gained an ordering assertion |
| 4 | `bathrooms` was loaded and only plotted; `currentEnergyRating` was not even loaded; `crime_volume` was engineered, merged, and never added to `FEATURES` | All four wired into the feature list |

Also new: **§14.2**, a feature-group ablation that quantifies whether crime is worth the 80 % of
the dataset it costs (see *Results* above) — the previous iteration only asserted this as a future
improvement; it is now measured.

The honest cost of fix #3: shrinking training data by 10 percentage points and moving validation
further from test raised tree-model test MdAPE by several points and widened Ridge's lead. See
*The headline finding* in Results — this is a direct, disclosed consequence of the fix, not a
regression to paper over.

---

## Project structure

```
london_flip_finder.ipynb   the entire project
requirements.txt           pinned direct dependencies
pyproject.toml             package metadata + ruff config
README.md
data/                      downloaded on first run (gitignored)
artifacts/                 model, manifest, leaderboard, cache (gitignored)
```

## Limitations

* **The scanner evaluates completed sales, not properties you can buy.** `TARGET` is
  `history_price` — what a property *actually sold for*. A transaction that sold below its floor
  in 2016 validates the valuation model; it is not a listing anyone can act on today. A live
  scanner needs an asking-price feed and a calibration step for the asking→sold gap, which this
  dataset does not contain.
* **A flip flag is a statistical claim, not a financial one.** It says nothing about stamp duty,
  refurbishment, holding costs, or *why* the property is cheap — and properties are usually cheap
  for a reason the data does not record (short lease, structural problems, a motivated seller).
* **Conformal coverage is marginal, not conditional** — ~90 % overall, not guaranteed within any
  given borough or price decile.
* **The 2008–2016 window ends a decade ago**, and the §14.2 ablation shows crime is worth keeping
  (+0.46 pp) at current resolution — so this is not a window that can simply be widened by
  dropping crime. It needs post-2016 crime data instead. Brexit, the 2016 stamp duty surcharge,
  the pandemic and the 2022 rate cycle all fall outside the current window regardless.
* **Gain-based importance is not causal**, and this feature set is heavily collinear — latitude,
  longitude, borough, outcode and distance-to-centre all encode "where".
* **The four-way split has a real accuracy cost**, documented in *The headline finding* above —
  tree-model test MdAPE rose several points once calibration stopped borrowing from validation.

## Where to take it next

1. **Split by property, not only by time** — group-aware splitting keyed on address, reported
   alongside the chronological number.
2. **Source post-2016 LSOA crime data** (`data.police.uk` publishes monthly extracts) so the
   window can widen toward the full 1995–2024 history (~418k rows, 5× current volume) without
   dropping the one feature group the §14.2 ablation showed earns its place.
3. **Try reordering the four-way split** to train → calibration → validation → test. The current
   order protects conformal validity (calibration sits closest to test) at the cost of validation's
   proximity to test, which the headline finding shows hurt early-stopped models materially. The
   reordering is the untested alternative trade-off — worth an explicit before/after comparison
   rather than assuming the current order is optimal.
4. **Walk-forward backtesting** — rolling-origin evaluation gives a distribution of MdAPE instead
   of a single number with no error bar, and would settle whether Ridge's current lead is real or
   an artifact of which months landed in this particular test window.
5. **Turn the margin into a P&L** — stamp duty bands (including the 3 % surcharge), refurbishment,
   financing, agent and legal fees; then rank candidates by return rather than by pounds.
6. **Conditional (Mondrian) conformal prediction** — per-borough and per-decile multipliers so
   coverage holds within the segments an investor actually shops in.
7. **Lease length** drives much of flat valuation and is absent entirely from the source data.
8. **SHAP plus location-grouped permutation importance**, so "where" is credited once rather than
   split five ways.
9. **Direct quantile regression** (`objective='reg:quantileerror'`) as an alternative to a single
   global conformal multiplier.
10. **Operational hardening** — extract the pipeline into a package with pytest fixtures over a
    sample, wire `nbstripout` into pre-commit, and schedule retraining that fails loudly when the
    section 17 self-checks do.

## License

MIT.
