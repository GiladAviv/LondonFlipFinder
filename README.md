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
| TfL station geodata | one row per station | transport connectivity |
| GLA borough boundaries | polygon per borough | administrative context |

**Deliberately excluded.** The source file carries `saleEstimate_*` and `rentEstimate_*` columns —
a third party's model output for the same property. Using them to predict price would be target
leakage. The 300 MB postcode-geo file and the school scorecards are not loaded either: the
previous version read both (costing ~1 GB of RAM) without either ever reaching a feature.

## Features

All 19 features are built to answer one question: *would a buyer standing at the transaction date
have known this?*

| Group | Features |
|---|---|
| Physical | `floorAreaSqM`, `total_rooms`, `avg_room_size` |
| Spatial | `distance_to_nearest_tube_m`, `distance_to_center_m`, `latitude`, `longitude`, `borough`, `outcode` |
| Asset | `propertyType`, `tenure` |
| Safety | `crime_volume_prev_12m` (12-month trailing sum, current month excluded) |
| Macro | `interest_rate` (BoE base rate in force on the completion date) |
| Temporal | `days_since_start`, `month_sin`, `month_cos` |
| Market | `market_median_rolling_3m`, `market_median_rolling_12m`, `lagged_borough_median_sqm` |

Distances are computed in **British National Grid (EPSG:27700)**, i.e. in metres. Nearest-station
lookup uses a `cKDTree`, turning a 33 M-pair brute-force comparison into a sub-second query.

Section 17 verifies the lag guarantee *causally*: it multiplies the final month's prices tenfold
and asserts that every lagged market feature for that month is unchanged.

---

## Results

79,815 sale events with size data reduce to **59,946** modelling rows after dropping properties
outside the GLA boundary, filtering symbolic transactions below £1,500/sqm, and deduplicating
repeated completions. Split chronologically: 41,962 train / 8,992 validation / 8,992 test. All
models are scored on identical rows — validation and test transactions under the £4 M cap (8,861
and 8,857 rows respectively).

Models are **selected on validation** and then scored **once** on the untouched test set.

| Model | Trained on | Val MdAPE | Test MdAPE | Drift | Test MAE | Test R² |
|---|---|---:|---:|---:|---:|---:|
| MoE — error routing (CatBoost) | cleaned | 14.21 % | **17.49 %** | +3.28 pp | £155,575 | 0.708 |
| 3-seed average (CatBoost) | cleaned | 14.20 % | 17.55 % | +3.35 pp | £155,560 | 0.709 |
| CatBoost ← *selected on validation* | cleaned | **14.18 %** | 17.63 % | +3.45 pp | £159,148 | 0.681 |
| XGBoost | raw | 14.26 % | 17.66 % | +3.40 pp | £148,743 | 0.764 |
| XGBoost | capped | 14.34 % | 17.85 % | +3.51 pp | £149,124 | 0.775 |
| MoE — error routing (XGB) | cleaned | 14.64 % | 17.94 % | +3.30 pp | £170,081 | 0.615 |
| 3-seed average (XGB) | cleaned | 14.65 % | 17.98 % | +3.33 pp | £170,169 | 0.614 |
| XGBoost | cleaned | 14.74 % | 18.03 % | +3.29 pp | £172,480 | 0.606 |
| MoE — luxury routing (XGB) | cleaned | 14.92 % | 18.45 % | +3.53 pp | £173,374 | 0.621 |
| Ridge (baseline) | capped | 16.16 % | 16.03 % | **−0.13 pp** | £170,993 | 0.277 |

**Conformal bound.** Calibrated on validation at α = 0.10, the safety multiplier is
**q₁₀ = 0.7818** — the floor sits at 78.2 % of the predicted value. Empirical coverage on the
held-out test set is **92.13 %** against a 90 % target (+2.13 pp), so the guarantee holds, slightly
conservatively, despite the chronological split not strictly satisfying exchangeability. The
scanner flags **697 of 8,857** test properties (7.87 %) as priced below their floor, at a median
margin of **£71,780**.

### Four findings worth reading carefully

**1 — The Mixture of Experts does not work.** This is the headline result, and it only became
visible once the 3-seed average control was added. The error-driven MoE beats a plain average of
its own three experts by **0.06 pp** (CatBoost) and **0.04 pp** (XGBoost) — noise. On validation
the CatBoost average actually *beats* its MoE. The router, the per-sample error labelling and the
soft-weighted combination contribute nothing over averaging the identical models; the gain
previously attributed to "expert specialisation" is ordinary ensembling. The luxury-routed MoE is
the **worst** tree model of the ten. Note also that the error-driven router is trained on
*in-sample* errors, where the three seeds differ mostly by which points each happened to overfit —
so the "specialisation" it learns is largely noise, which is consistent with the near-even
11.8k/11.9k/11.7k split of expert wins.

**2 — Removing anomalies makes the model worse.** XGBoost trained on `cleaned` data scores 18.03 %
on test versus 17.85 % (`capped`) and 17.66 % (`raw`). The previous version reported the opposite
because it deleted `IsolationForest` outliers from validation and test as well as training —
scoring itself on an exam with the hard questions removed. Once the evaluation set is held fixed,
discarding 6,200 training rows simply costs information.

**3 — Validation-only reporting was optimistic by ~3.4 pp.** Every tree model drifts from ~14.2 %
on validation to ~17.6 % on test, because validation is also what early stopping and model
selection consumed. The previous version reported only the validation figure.

**4 — The linear baseline is the most stable model, and on the headline metric it wins the test
set.** Ridge drifts −0.13 pp between validation and test, while every gradient-boosted model
drifts +3.3 pp or more, and its 16.03 % test MdAPE is the lowest of any model. It is not simply
"the best model": its R² of 0.277 and £170,993 MAE are far worse than CatBoost's 0.681 and
£159,148 — Ridge is well-behaved for the typical property and badly wrong on the tails, where the
trees make their money. The honest reading is that the boosted models absorbed structure specific
to the 2008–2014 regime that did not survive into 2016, and that **model selection on validation
picked a model that lost to the baseline on the metric it was selected by.** That is an argument
for walk-forward backtesting (improvement 2 below), not for shipping Ridge.

### Repeat-property diagnostic

**26.1 %** of test transactions (2,308 of 8,857) are properties that also appear in training — a
consequence of splitting a price *history* by time rather than by property.

| Test subset | Rows | MdAPE | MAE | R² | Within 25 % |
|---|---:|---:|---:|---:|---:|
| Seen in training | 2,308 | 17.27 % | £141,018 | 0.720 | 72.8 % |
| Unseen property | 6,549 | 17.82 % | £165,537 | 0.671 | 68.6 % |

Properties the model has already seen are predicted **0.55 pp better** than genuinely new stock,
so there is a memorisation effect — but a small one. On entirely unseen properties the selected
model scores 17.82 % against its 17.63 % blended headline, meaning the headline overstates
performance on new stock by roughly 0.2 pp. That is a real caveat and not a fatal one, and it is
something the previous version had no way to measure. A group-aware split (improvement 1) would
remove the ambiguity.

## Methodology notes

### Why the split is chronological

A random split would let the model learn from June 2016 to predict January 2016 — a situation that
never occurs in production. Sorting by date and cutting 70/15/15 reproduces the real task: train on
the past, forecast the future.

### Why MdAPE is the headline metric

MAE is quoted in pounds and is easy to explain, but it is dominated by the expensive tail: a 10 %
miss on a £3 M house contributes thirty times more than a 10 % miss on a £100 k flat, though both
are equally wrong in the only sense a buyer cares about. The **median** absolute percentage error
is robust to that tail and answers the practical question — what does a typical valuation get
wrong by?

### One evaluation universe, three training variants

Models differ only in what they were **trained** on (`raw`, `capped` at £4 M, or `cleaned` of
anomalies). Every model is **scored on identical rows** — validation/test transactions under the
cap. Anomalies are removed from training only: deleting hard cases from your own exam inflates the
score, and a production model does not get to refuse the awkward listings.

### The conformal bound

On validation we take the ratio of actual to predicted price for every property and read off the
10th percentile, `q₁₀`. A new property's floor is `prediction × q₁₀`, and ~90 % of properties
should sit above it.

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

* **A flip flag is a statistical claim, not a financial one.** It says the price is below a
  calibrated floor. It says nothing about stamp duty, refurbishment, holding costs, or *why* the
  property is cheap — and properties are usually cheap for a reason the data does not record
  (short lease, structural problems, a motivated seller).
* **Conformal coverage is marginal, not conditional** — ~90 % overall, not guaranteed within any
  given borough or price decile.
* **The 2008–2016 window ends a decade ago.** Brexit, the 2016 stamp duty surcharge, the pandemic
  and the 2022 rate cycle all fall outside it.
* **Gain-based importance is not causal**, and this feature set is heavily collinear — latitude,
  longitude, borough, outcode and distance-to-centre all encode "where".

## Where to take it next

1. **Split by property, not only by time** — group-aware splitting keyed on address, reported
   alongside the chronological number.
2. **Walk-forward backtesting** — rolling-origin evaluation gives a distribution of MdAPE instead
   of a single number with no error bar.
3. **Turn the margin into a P&L** — stamp duty bands (including the 3 % surcharge), refurbishment,
   financing, agent and legal fees; then rank candidates by return rather than by pounds.
4. **Conditional (Mondrian) conformal prediction** — per-borough and per-decile multipliers so
   coverage holds within the segments an investor actually shops in.
5. **Features the data already supports** — `bathrooms` and `currentEnergyRating` sit unused in the
   source file; crime is available at LSOA level (a 30× resolution gain) but consumed per borough;
   lease length drives much of flat valuation and is absent entirely.
6. **SHAP plus location-grouped permutation importance**, so "where" is credited once rather than
   split five ways.
7. **Direct quantile regression** (`objective='reg:quantileerror'`) as an alternative to a single
   global conformal multiplier.
8. **Operational hardening** — extract the pipeline into a package with pytest fixtures over a
   sample, wire `nbstripout` into pre-commit, and schedule retraining that fails loudly when the
   section 17 self-checks do.

## License

MIT.
