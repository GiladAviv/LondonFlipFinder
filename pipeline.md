# `london_flip_finder.ipynb` — reconstructed pipeline

**Source:** `london_flip_finder.ipynb`, 83 cells (0-based indices, as stored in the `.ipynb`).
Nothing below comes from any other file. Section numbers (§) are the notebook's own headings.

**Tags:** `central` = a load-bearing step the argument depends on · `secondary` = real work, but the
deck survives compressing it · `unclear to me` = I could not determine its purpose or status from
the notebook alone.

> **State-of-run warning (important).** The notebook's stored outputs stop at cell 67. That cell
> (`prior_sale_study`, §14.6) raised `AttributeError: 'DataFrame' object has no attribute 'dtype'`
> after printing one line, and every cell below it — 68, 71, 73, 76, 78 — has **no output at all**.
> So §14.6's table, all of §15 (conformal multiplier, empirical coverage, flip count, the flip-margin
> figure), §16 and §17 have no recorded numbers. What *is* recorded about them appears in prose in
> cells 61, 69, 80 and 81. Flagged again in §S12/§S13 below and in the questions at the end.

---

## S0 — Framing (cells 0–2) · `central`

**What was done.** Three markdown cells set the problem, a UK-vocabulary glossary, and a
seven-phase reading map.

**The problem as stated (cell 0).** A sale record carries floor area, room counts, tenure, property
type, energy rating, postcode and price. The work is assembling *context* around it: distance to
the nearest station and that station's fare zone, crime recorded in the months *before* the sale,
borough, what citywide prices were doing beforehand, what the borough fetched per m² a month
earlier, the Bank of England base rate on the completion date, and what the property itself last
sold for (61 % of sales). One rule governs everything: **only use what a buyer standing at the
transaction date could have known.**

**The headline table (cell 0), stated up front.** 59,946 in-window transactions.
`CatBoost detrended-market (cleaned)` at **13.88 % test MdAPE**; Ridge 16.62 %; plain boosted trees
18–20 % test, *worse than the linear baseline*; strongest feature group = the property's own prior
sale at +0.93 pp; weakest = crime at +0.11 pp, below the 0.15 pp bar; a multiplicative conformal
floor at a 90 % target. **The stated headline is not the architecture — it is that the target had
to be reframed.**

**Repo layout (cell 0).** Notebook = the argument; `src/lff/` = the machinery; `tests/` = leakage
probes over a committed 500-row fixture.

---

## S1 — Imports and environment, §1 (cells 3–4) · `secondary`

**What was done.** `src/` is put on `sys.path` so a clone runs with no install step; the whole
pipeline is imported from `lff.*` (13 modules, one per stage — `config`, `ingest`, `clean`,
`spatial`, `master`, `features`, `split`, `metrics`, `models`, `analysis`, `conformal`,
`plots`/`maps`, `persist`). `apply_notebook_theme()` installs the chart theme plus **two narrow
warning filters rather than a blanket `filterwarnings('ignore')`**, so genuine problems still surface.

**Result (cell 4 output).** python 3.9.25 · numpy 1.26.4 · pandas 2.3.3 · geopandas 1.0.1 ·
xgboost 2.1.4 · sklearn 1.6.1 · catboost 1.2.10 · lff 3.0.0.

---

## S2 — Configuration, §2 (cells 5–6) · `secondary`

**What was done.** One frozen `Config` object is the single source of truth for paths, filters,
split ratios and hyper-parameters; nothing below hardcodes a threshold. `set_seeds(CONFIG.seed)`.

**Real values (cell 6 output).** `fast_mode False`; split **60 % train / 15 % val / 10 % calib /
15 % test**. `LFF_FAST_MODE=1` shrinks every iteration budget for a smoke run. Data dir resolves
`$LFF_DATA_DIR` → `./data/data_for_ds_project`.

**`ABLATION_GATE_PP = 0.15`** is defined *here*, not at its point of use, because §14.5 and §14.6
must apply the same bar (cell 6 comment).

---

## S3 — Data acquisition, §3 (cells 7–8) · `secondary`

**What was done.** `ensure_dataset(CONFIG)` — the datasets total ~1.8 GB, past GitHub's file limit,
so they ship as a release asset; the cell downloads and extracts if missing, else does nothing.
Makes the notebook self-bootstrapping on a fresh machine.

**Result.** `All 5 required inputs present in .../data/data_for_ds_project`.

---

## S4 — Loading the raw sources, §4 (cells 9–10) · `central`

**What was done.** `load_raw(CONFIG)` reads four sources; two extra frames are read for §8.2.

| Source | Grain | Contributes | Rows loaded |
|---|---|---|---|
| Land-Registry-derived price history | one row per sale event | target + physical attributes | 418,201 × 14 (225 MB) |
| Met Police crime by LSOA | LSOA × category × month | neighbourhood safety | 13,490,604 × 4 (108 MB) |
| Bank of England base rate | one row per rate change | cost of borrowing | 246 × 2 |
| TfL station geodata (Feb 2022 snapshot) | one row per station | transport connectivity | 471 × 14 |
| GLA borough boundaries | polygon per borough | administrative/spatial context | — |

Plus `fetch_lsoa_boundaries(CONFIG)` → **5,901 cached LSOA areas** (ONS, cached under
`data/external/`), and a second read of the crime CSV at native LSOA grain with explicit dtypes
(`lsoa_code`/`major_category` as `category`, `value` `int16`, `year` `int16`, `month` `int8`).

**Why the deliberate exclusion (cell 9).** The source file carries `saleEstimate_*` and
`rentEstimate_*` — a third party's *model output* for the same property. Using them would be
**target leakage dressed up as a feature**, so they are never read.

**Why crime is read twice.** Borough grain for the pipeline; native LSOA grain for §8.2, which
tests whether the borough aggregation is throwing away the signal.

**Result.** `Loaded 4 sources in 7.6s`.

---

## S5 — Cleaning and per-source features, §5 (cells 11–12) · `central`

**What was done.** Three independent pure transforms, no joining yet.

- `clean_houses(RAW["houses"], CONFIG)` → **82,122 rows in 2008–2016 → 79,815 with size data.**
- `build_crime_features(RAW["crime"])` → **3,564 borough-months, 33 boroughs.** Two lags, never
  contemporaneous: `crime_volume` = the month immediately *before* the sale (short-term signal);
  `crime_volume_prev_12m` = rolling 12-month sum with **`closed='left'`**, excluding the current
  month (stable "reputation" signal). Both strictly backward-looking.
- `build_rate_curve(RAW["boe"], CONFIG)` → **3,288 days, 0.25 %–5.50 %.** Sparse change dates
  forward-filled onto a daily calendar so every sale matches the rate in force on completion day.
- `build_crime_features_lsoa(...)` → **522,180 LSOA-months, 4,835 LSOAs, 4 category groups**;
  printed diagnostic: *median crime per LSOA-month: 9 total, 1 burglary — sparse, which is why the
  12-month window leads.*

---

## S6 — Spatial engineering, §6 (cells 13–14) · `central`

**What was done, and why.**

1. **Projection first — EPSG:27700 (British National Grid)** before any distance is computed.
   Rationale given: at London's latitude a degree of longitude covers only ~62 % of the ground a
   degree of latitude does, so degrees distort geography east–west; BNG is metric.
2. **Nearest-station lookup with a k-d tree (`cKDTree`).** ~80,000 properties × ~400 stations =
   32 M brute-force distance computations; the tree answers each query in `O(log n)`, finishes in
   under a second, and returns the neighbour's index — which hands over the station's **fare zone**
   for free.
3. **The station file had to be cleaned first.** `Stations_20220221.csv` is a Feb 2022 snapshot but
   every transaction is pre-2017, so used as-is it credits properties with links that did not exist:

| Group | Count | Treatment |
|---|---:|---|
| London Underground | 270 | kept (incl. the 6 that *later also* gained Elizabeth Line service) |
| London Overground | 113 | kept in the wider transit measure |
| DLR | 45 | kept in the wider transit measure |
| Elizabeth-Line-only | 33 | **excluded** — line opened May 2022 |
| Tramlink-only | 39 | **excluded** — street trams, not a connectivity-changing rail link |

   Filtering on the Underground/Overground/DLR flags handles both in one pass **and avoids a subtler
   mistake**: Paddington and a handful of others were Underground stops for a century and merely
   *gained* Elizabeth Line service in 2022; excluding anything tagged "Elizabeth Line" outright would
   erase a link that genuinely existed at sale time.
4. **Two distance features, not one.** `distance_to_underground_m` (Underground specifically) and
   `distance_to_transit_m` (any rail mode). An earlier undifferentiated measure across all 471
   stations treated a suburban tram stop as equivalent to a central Underground station.

**Result (cell 14).** `Stations: 270 Underground, 399 heavy rail (72 Elizabeth-only/tram stops
excluded as post-window or non-rail)`.

**Known limitation stated in the notebook.** Several Overground/DLR extensions opened *during*
2008–2016, so transit distance is likely overstated for early-window sales; a correct treatment
needs station opening dates the dataset does not carry. Kept anyway — affected extensions are a
small minority, the bias is one-directional and partial rather than a fabricated link, and dropping
transit entirely would discard a materially stronger signal than the one it corrects.

---

## S7 — Building the master table, §7 (cells 15–16) · `central`

**What was done.** `build_master_table(CONFIG, HOUSES, CRIME, RATES, RAW["stations"],
lsoa_crime=LSOA_CRIME, lsoa_boundaries=LSOA_BOUNDS)` — the single orchestration function that chains
§4–§6, deliberately the only place that writes `df_master`, taking no globals but `CONFIG`.

**Row filters applied here, and why:**
- **`price_per_sqm >= 1500`** — removes symbolic transfers that are legally sales but economically
  meaningless: £1 family transfers, parking spaces, lease extensions (a leaseholder buying years
  back onto their term, which the register logs as a sale). A **ratio** filter, so genuinely
  expensive homes survive if their price-to-size ratio is plausible.
- **Deduplication** on date + geometry + size + price — the same completion sometimes appears twice.
- **Chronological sort** — mandatory before any rolling window or time-based split.

**Result.** `Loaded cached master table: (59946, 37)` — cached to Parquet so later runs skip the
~1 GB crime read. 37 columns incl. `distance_to_underground_m`, `station_zone`,
`distance_to_transit_m`, `distance_to_center_m`, `borough`, `lsoa_code`, `price_per_sqm`,
`interest_rate`, the borough-grain crime pair, and 11 LSOA-grain crime columns.

**Caveat the notebook flags for §18.** Both the £1,500/m² floor here and the £4 M cap in §10 are
defined *using the target* — defensible as definitions of "the standard market this product serves",
but not identifiable at prediction time.

---

## S8 — EDA, §8 intro + price/property figures (cells 17–21) · `central`

**What was done.** Four questions before any modelling: what the price distribution looks like, what
physical attributes move it, what external forces move it, what structure the file itself has.

**Discipline stated (cell 17).** Every figure is a function of a DataFrame, called once; nothing
mutates `df_master` or rebinds a source frame — an EDA cell that reassigns a name like `df_tube`
silently destroys the raw station table for every cell below.

**Chart conventions (cell 17).** Validated categorical palette in fixed slot order so a colour always
means the same series; single-series charts get one flat hue and no legend; the correlation matrix
gets a diverging blue↔red ramp with a neutral grey midpoint because its data has a meaningful zero.

**Clipping (cell 17–19).** Charts clip at the **95th percentile of price** — a *display* choice only;
models see untruncated data. **Cell 18, `plot_price_clip_comparison`** shows both versions side by
side: full data (59,946) vs clipped (56,966), so the effect is visible rather than asserted.

**Cell 20, `plot_property_characteristics`** — 4 panels: price distribution, price by total rooms,
median price by property type, correlation matrix. Takeaways as written:
- Price heavily right-skewed even after clipping — peak ~£250k–£300k, long tail. **This is why every
  model trains in log space (§11).**
- Price rises with room count (median ~£320k at 2 rooms to ~£950k at 8) but boxes widen and overlap
  heavily at the top.
- Detached tops the median-price ranking, roughly double the cheapest terraced categories.
- Strongest correlates: `floorAreaSqM` r = 0.57, `bathrooms` r = 0.52; negatives
  `distance_to_center_m` r = −0.36, `distance_to_underground_m` r = −0.30.
- **Heavy collinearity:** `floorAreaSqM` ↔ `total_rooms` **r = 0.85**. Explicitly flagged as the
  reason §14.5 later finds that removing whole feature groups costs almost nothing.

---

## S9 — §8.1 external drivers (cells 22–24) · `central`

**What was done.** Four figures from one cell (cell 23, five images):
`plot_tube_premium` · `plot_crime_and_market` (2 figures) · `plot_price_vs_area` ·
`plot_price_per_sqm_by_borough`.

**Design decision stated (cell 22).** The price-vs-rate figure uses **two stacked panels sharing one
x-axis rather than twin y-axes**, because a dual-axis chart lets whoever draws it choose where the
lines appear to cross, manufacturing a visual correlation.

**Takeaways as written (cell 24).**
- **Tube premium is steep:** mean price £900k–£950k within 500 m of a station → under £350k beyond
  3 km. The 0–250 m band is *not* the cheapest — likely a shorter walk traded against living next to
  the station itself.
- Price tracks floor area closely on log-log, spread widening at the top end.
- **Borough spans roughly 5×** in median £/m²: >£11,000 in Kensington and Chelsea → ~£2,300 in
  Bexley. "The centre-to-edge gradient of the city in a single number", and why `borough` carries so
  much location signal.
- **The crime panel is backwards, and that is the interesting part.** Median price *climbs* from
  `Low` to `Severe`, topping out over £470k against ~£390k in `Low`. → §8.2.
- Base rate collapses 5.5 % → 0.5 % across 2008–2009 while price dips then climbs for years.

**Warning the notebook attaches.** These are ***marginal* associations, not evidence the model relies
on them.** Every chart answers "does price vary with this?", a different question from "does this add
anything the other features do not already carry?" — §14.5 asks the second, and for **transport** and
**interest rate** the answers diverge sharply.

---

## S10 — §8.2 Does crime price into London property? (cells 25–30) · `central` (but see Q1)

**The question.** The boxplot says higher-crime neighbourhoods carry *higher* prices — backwards.
Either crime does not price in, or something drives both at once.

**Why it matters far beyond one feature (cell 25).** The crime file only covers 2008–2016, and
**that single constraint is why the entire modelling window stops there** — 59,946 in-window sales
out of 314,895 distinct sales in the full history, so **81 % of the available record is discarded to
accommodate one dataset.**

**Three measurement defects fixed first, because each stacks against crime:**
1. **Resolution.** The raw file carries 4,835 LSOA codes; `build_crime_features` sums to 33 boroughs
   — a **147× loss**. Concretely: one borough mean averages Hampstead with Kilburn a mile away. Any
   safety↔price relationship is overwhelmingly *within*-borough — exactly what a borough mean erases.
2. **Count, not rate.** `crime_volume` is a raw count, so a more populous borough scores high
   automatically. Because every LSOA holds ~1,500 residents by construction, an LSOA count is already
   close to a per-capita rate.
3. **One series.** Burglary and drug offences summed together, assuming buyers price them identically.

Stated purpose: *"crime does not matter"* and *"crime measured 147× too coarsely, as an unnormalised
count, does not matter"* are different claims, and only the second had been tested.

**Cell 26 — `plot_crime_and_price_maps`.** Two LSOA choropleths of Greater London, price left
(blue), crime density right (orange), one hue each so they cannot be misread as sharing a scale.
`LSOA price summary: 2,562 of 2,863 LSOAs with >= 5 sales`. Printed verdict: *both maps run darkest
in the centre — central London is simultaneously the most expensive and the most crime-recording part
of the city, so a raw crime-price correlation largely measures centrality.*

**Cell 28 — `plot_crime_within_borough`.** De-mean both variables within borough.
**`Across boroughs r = +0.30; within borough r = +0.00.`**

**Cell 29 — `plot_crime_change`.** Difference over time (2008–2010 → 2014–2016), removing every fixed
feature of a place at once. **`r = -0.01 over 863 LSOAs.`**

**Verdict (cell 30).** The association survives neither treatment; the entire apparent relationship
is *which borough a property sits in*. Explicitly scoped: this is the **exploratory** answer — a
feature can carry no marginal correlation and still earn its place by interacting inside a model, so
§14.5 puts the same question to the fitted model.

---

## S11 — §8.3 The repeat-sales structure of the file (cell 31) · `central`

**What was done.** A markdown-only cell stating one structural fact none of the charts surface.

**The fact.** The source is a price *history*, not a transaction list. 418,201 rows cover 137,760
unique addresses. Removing the **24.5 %** exact-duplicate rows leaves 315,674, and collapsing the 779
same-day price conflicts leaves **314,895 distinct sales**, and
**66.0 % of addresses record two or more**. In-window, **61.1 % of sales have an earlier sale of the
same property**, typically ~7 years earlier.

**Why it is called the most important cell in §8.** Every other feature asks *what is a property like
this worth?* A prior sale asks a different and much easier question: *what was this exact property
worth last time, and how far has the market moved?* Quality, layout, aspect, street and lease are
held fixed between the two observations — the logic of the repeat-sales index literature
(Bailey, Muth & Nourse 1963).

---

## S12 — §9 Temporal, market and prior-sale features (cells 32–34) · `central`

**Design rule.** Every feature answers one question: *would a buyer standing at the transaction date
have known this?*

**Temporal / market features (cell 32 table):**

| Feature | Construction | Why it cannot leak |
|---|---|---|
| `days_since_start` | days since the first transaction | from the row's own date |
| `month_sin`, `month_cos` | cyclic encoding of calendar month | December and January end up adjacent |
| `market_median_rolling_3m` / `_12m` | market-wide monthly median, **`.shift(1)` then rolled** | the shift drops the current month before the window opens |
| `lagged_borough_median_sqm` | borough £/m² median stamped onto the *following* month | a month's own price never informs its own prediction |
| `avg_room_size` | floor area ÷ total rooms | a within-row ratio |

**A deliberate non-imputation.** `total_rooms` can be 0, so `avg_room_size` yields ±∞; those are
converted to NaN and **left as NaN**. Filling with the column median here would leak — the function
runs on the whole table before the split, so that median would be computed over val/calib/test and
baked into a training feature. "Small, but real." Imputation is deferred to each model, inside a
pipeline fitted on the training split alone.

**Prior-sale features (cell 32 table):** `prev_sale_price` (most recent sale of the *same address*,
strictly before this row's date, via an **as-of merge with a strict `<` bound**),
`years_since_prev_sale`, `prev_sale_days_since_start` (*when* that sale happened, on the same clock as
`days_since_start`), `has_prev_sale` (presence, not price).

**History is read from the whole 1995–2024 file, not the modelling window** — a 2009 sale's previous
sale is usually pre-2008, so clipping first would discard most of the signal.

**"Strictly before" is load-bearing; three things could break it, all handled:** the 102,527 duplicate
rows are removed first (or an as-of merge can return the very row it is meant to predict); same-day
conflicting prices are collapsed to a median; `assert_no_lookahead` runs as a hard check here and
again in the §17 self-checks.

**Two candidate columns deliberately not carried:** `log_prev_sale_price` and `n_prior_sales` —
§14.6 shows they earn nothing.

**Result (cell 33 output).**
```
Sale history: 418,201 rows -> 315,674 after exact duplicates (102,527 removed, 24.5%)
   779 same-day price conflicts collapsed to their median
   314,895 sales across 137,760 addresses; 66.0% of addresses sold more than once (1995 to 2024)
Prior-sale features: 36,609 of 59,946 rows (61.1%) have an earlier sale of the same property
   years since that sale: median 6.9 (p10 2.2, p90 13.8)
Modelling table: (59946, 52)
Features: 23 numeric + 5 categorical
```
Missing-value rates (top 6): `prev_sale_days_since_start` / `years_since_prev_sale` /
`prev_sale_price` **0.3893** · `currentEnergyRating` 0.2523 · `bathrooms` 0.1596 · `avg_room_size`
0.1249.

**Interpretation (cell 34).** The modelling table is **59,946 × 28 features**. `prev_sale_*` is
**38.9 % missing by construction** — *informative* missingness, not a defect, which is why
`has_prev_sale` is carried alongside: it lets the model treat "never sold before" as its own case
rather than a hole to impute. GBTs handle NaN natively; Ridge imputes inside a pipeline fitted on
train only. `assert_no_lookahead` passed.

---

## S13 — §10 Chronological split, training variants, encoding (cells 35–38) · `central`

**The split is by time, not at random** — a random split would let the model learn from June 2016 to
predict January 2016, which never happens in production.

**Result (cell 36 output).**
```
train  35,967 rows   2008-01-01 -> 2014-04-17
val     8,991 rows   2014-04-17 -> 2015-04-30
calib   5,994 rows   2015-04-30 -> 2015-12-17
test    8,994 rows   2015-12-17 -> 2016-12-31
Evaluation universe (price <= £4,000,000): 8,840 validation, 5,916 calibration, 8,859 test rows
```

**Why calibration gets its own slice.** One validation set cannot serve early stopping, model
selection *and* conformal calibration without the "90 % guarantee" being partly calibrated on data
the model was tuned against — circular. The ordering of the two middle slices **was tested both
ways**; validation-then-calibration is kept because it produces smaller validation-to-test drift for
the tree models, at the cost of a little exchangeability on calibration. (§18 records that this
comparison was itself made by scoring on test — a protocol breach the notebook discloses.)

**One fixed evaluation universe, three training variants.** Comparing "raw"/"capped"/"cleaned" is
only meaningful if all three are scored on the same rows; letting the evaluation set vary alongside
the training set compares models and test sets at once. Only the **training** data varies:

| Variant | Training rows (cell 38) |
|---|---|
| `raw` | 35,967 — every transaction, including £4 M+ |
| `capped` | 35,693 — at or below the £4 M cap |
| `cleaned` | 35,075 — capped, minus multivariate anomalies |

`IsolationForest scored 30,853 of 35,693 capped training rows (4,840 skipped for missing values,
kept as-is) and flagged 618 anomalies (2% target rate); validation and test are untouched.`

**Anomalies removed from training only** — fitting IsolationForest on everything and dropping flagged
rows everywhere is "marking your own exam after removing the difficult questions".

**Encoding, both fitted on training only.**
- **Native categoricals** (`category` dtype) for XGBoost: `propertyType`, `tenure`, `borough`,
  `outcode`. Level set pinned from train so a category means the same integer code everywhere.
  CatBoost gets raw strings via `cat_features`. Explicit warning: these must never be coerced with
  `pd.to_numeric(..., errors='coerce')`, which turns all four **entirely NaN** and leaves the CatBoost
  models and every MoE router training on dead columns *(this is recorded as a bug that actually
  happened — see §17 check #2)*.
- **Smoothed target encoding** for models needing numeric input (the routers); smoothing pulls
  low-frequency categories toward the global mean so a borough with three sales does not get a
  confident estimate.

---

## S14 — §11 Loss, metrics and decision rules (cells 39–40) · `central`

**Stated purpose.** Nothing is trained yet; this fixes what each model **optimises**, what everything
is **scored** on, and what rule **decides** — "because deciding them afterwards is how a project talks
itself into a result".

**Log space for everything** (`log1p` in, `expm1` out): prices are right-skewed, a squared-pound loss
is dominated by the expensive tail (one £3 M house outweighs thirty £100k flats); in log space the
loss is approximately *proportional*.

| Model | Trained on | Objective | Why |
|---|---|---|---|
| Ridge | `log1p(price)` | squared error, `alpha=1.0` | closed-form, hard to overfit — a baseline should not need tuning to be fair |
| XGBoost (plain) | `log1p(price)` | `reg:squarederror` (default) | the untuned starting point, kept so §12.1's fix has something to improve on |
| CatBoost (plain) | `log1p(price)` | `MAE` | already median-aligned |
| XGBoost detrended | `log(price / market level)` | `reg:absoluteerror` | matches the reported metric |
| CatBoost detrended | `log(price / market level)` | `MAE` | unchanged — **isolates** the deflator's effect from the objective's |

**Why absolute error.** Squared error in log space fits the conditional *mean* of log price
(≈ geometric mean); the headline metric is the *median* of relative errors. Different estimands, so a
squared-error model optimises one thing and is judged by another.

**Metrics** — one `regression_metrics()` implementation used everywhere ("near-identical variants
defined across several cells are how a leaderboard silently mixes two spellings of one metric"):
**MdAPE (headline)**, MAPE, MAE, RMSE, R², `within_25pct`.

**Why MdAPE is the headline.** MAE is in pounds and intuitive but dominated by the expensive tail; the
median of percentage errors is robust to it and answers *what does a typical valuation get wrong by?*

**The four decision rules, fixed in advance:**

| Rule | Value | Applied in | Decides |
|---|---|---|---|
| Model selection | lowest **validation** MdAPE | §13, §14 | which model becomes `BEST` |
| Feature-group gate | `ABLATION_GATE_PP` = **0.15 pp** | §14.5, §14.6 | whether a feature group earns the data it costs |
| Seed-noise floor | gain > **2 × mean sd** across seeds | §14.5, §14.6 | whether an effect is resolvable at all |
| Coverage target | **90 %** (`1 - conformal_alpha`) | §15, §17 | whether the safety bound holds empirically |

**Standing protocol:** decisions read validation; test is read only to report. §18 records the two
points where that was not followed.

Cell 40 instantiates `RESULTS = ResultsRegistry()`.

---

## S15 — §12 The model ladder (cell 41) · `central`

**Fourteen models, framed as a ladder where each rung exists because the rung below failed in a
specific, diagnosable way:**

1. **Ridge, the linear baseline** — sets the floor and doubles as a sanity check: if a GBT ensemble
   cannot beat a straight-line model on tabular data of this shape, the problem is the setup.
2. **XGBoost and CatBoost on `log(price)`** — the standard answer for tabular hedonic data; price
   responds non-linearly and interactively (the value of a second bathroom depends on borough).
   CatBoost specifically for native categorical handling.
3. **The failure** — the boosters **lose to Ridge by five points of MdAPE or more.** Framed as a
   symptom, not a verdict on gradient boosting.
4. **The detrended target** — predict price *relative to the market level* so trees interpolate
   instead of extrapolating. **Two deflator candidates** enter the pool; §14.3 decides on validation.
5. **Mixture of Experts: luxury routing** — splits standard from luxury stock, soft-weights one expert
   each. Asks: does segmenting this market beat modelling it whole?
6. **The 3-seed average** — the same recipe fit three times differing only by seed, predictions
   averaged. Exists as the plain-ensembling comparison point the MoE has to beat: "without it, a
   'Mixture of Experts' that merely beats a single model has proved only that ensembling works."

**Both the MoE and the 3-seed average are also trained on the detrended recipe**, so neither is
credited for a fix it did not make.

**Why no neural network (explicit, "deliberate, not an oversight").** ~60k rows of tabular data, no
free text, images or sequence structure; GBTs are better suited at this scale, need far less tuning,
and handle the categorical/continuous mix natively. A neural approach would earn its place if the
project gained listing descriptions or photographs.

**One uniform interface.** Every trainer returns a `ModelBundle` exposing the same `predict(X)`, which
is what lets the leaderboard, test evaluation and conformal calibration run through one code path —
and closes off a class of error where a conformal step reaching for `expert_0.predict(X_test)`
computes its guarantee from whatever that name happens to point at.

---

## S16 — §12.1 Detrending the target (cells 42–46) · `central` — the headline result

**Symptom.** Plain Ridge beating GBTs by five points of MdAPE.

**Mechanism.** Plain models train on `log1p(price)`. A tree's prediction is a **constant per leaf**,
so once a trending feature (`days_since_start`, `market_median_rolling_3m`) exceeds anything seen in
training, every such row lands in the same boundary leaf and the model **flat-lines at the last price
level it learned**. It cannot extrapolate a rising market. Ridge suffers less because it multiplies by
a coefficient instead of splitting.

**A testable prediction:** the plain trees should under-predict by a large, *positive* mean residual —
a one-directional level error, not symmetric noise. Measured on validation.

**The fix.** Predict the ratio to the lagged whole-market median:
`y = log(price / market_median_rolling_3m)` — already a leakage-safe feature from §9. "How much is
this worth relative to where the market already is" is close to stationary across time, so a tree only
has to *interpolate*. The market level is multiplied back at inference.

**A second change rides along:** XGBoost's objective moves to `reg:absoluteerror`. CatBoost already
trains with MAE, so only the detrending applies there — **which isolates which change is doing the
work.**

**Two deflators, not one:** `market_median_rolling_3m` (one number per calendar month, shared) vs
`lagged_borough_median_sqm × floorAreaSqM` (size- and location-scaled, per row). Both trained for both
backends; §14.3 decides. They are registered in `train_all()` like every other model, so whichever
wins validation becomes `BEST` and flows through the whole downstream.

**Cell 43 — `train_all(...)`, 14 models in 199s. Validation MdAPE:**
Ridge 17.09 % · XGB raw 13.88 / capped 14.33 / cleaned 14.60 · CatBoost cleaned 13.20 ·
**XGB detrended-market 12.19 · CatBoost detrended-market 11.94** · XGB detrended-borough 12.98 ·
CatBoost detrended-borough 12.63 · MoE luxury 14.05 · 3-seed avg XGB 14.23 · 3-seed avg CatBoost 13.26
· MoE luxury detrended 12.49 · 3-seed avg detrended 12.12.
Router diagnostics printed: `luxury router: temperature 0.835, 3,001 luxury / 32,074 standard` (plain)
and `temperature 0.763, 3,541 luxury / 32,152 standard` (detrended).

**Cell 45 — `extrapolation_bias`, signed residuals on VALIDATION only:**

| Model | Mean residual (val) | Median residual | Under-predicted % |
|---|---:|---:|---:|
| XGBoost (capped) | £74,679 | £38,198 | 70.4 % |
| XGBoost detrended-market (capped) | £24,331 | £8,626 | 54.8 % |
| Ridge (baseline) | £51,754 | £36,073 | 65.6 % |

**Takeaways (cell 46).** The signature reproduces on validation, so the fix did not require the test
set. **Ridge complicates the story rather than confirming it:** Ridge *also* under-predicts, because
the market rose faster than any linear projection of its training window. What separates the models is
the **size** of the level error, not its presence. **The accurate claim: a non-stationary target
biases every model here and punishes trees hardest, and detrending — not architecture — removes most
of it.**

---

## S17 — §13 Validation leaderboard (cells 47–49) · `central`

**What was done.** `val_board = RESULTS.frame("val")`, `plot_leaderboard(...)`, plus a styled table
with `background_gradient` on MdAPE and MAE. Generated **from the results registry** — every row was
appended by `evaluate()` at training time, so the leaderboard cannot disagree with what the models
scored. "A hand-assembled table … is how a £4 M cap ends up labelled '<£5M'."

**Result — 14 rows, ranked by validation MdAPE** (top: `CatBoost detrended-market (cleaned)` 11.94 %,
MAE £115,177, R² 0.824, within_25pct 80.8 %; bottom: `Ridge (baseline)` 17.09 %, MAE £163,715,
R² 0.539, 68.7 %).

**Takeaways (cell 49).** The detrended models **sweep the top** — every model on `log(price/market
level)` outranks every model on `log(price)`; the single largest effect in the leaderboard. MdAPE and
MAE do not always agree on ordering — different questions; selection uses MdAPE, MAE is reported so
disagreements are visible. **Nothing has read the test split yet.**

---

## S18 — §14 Held-out test evaluation (cells 50–52) · `central`

**Procedure.** Pick the winner by **validation** MdAPE, then score on test. The gap is the honest
measure of how much validation performance was selection effect.

**How often test is read, stated precisely.** Every model is scored once here so the drift column
exists; §14.1 reads it for the selected model; §15 reads it once more to report coverage. That is
*reporting*, not selection — every **decision** in 14.3–14.6 is made on validation.

**Result (cell 51).** `Selected on validation MdAPE: CatBoost detrended-market (cleaned)`.
Test board sorted by test MdAPE:

| Model | MdAPE (val) | MdAPE (test) | drift |
|---|---:|---:|---:|
| 3-seed average detrended (XGB) | 12.12 % | **13.62 %** | +1.50 pp |
| XGBoost detrended-market (capped) | 12.19 % | 13.88 % | +1.68 pp |
| **CatBoost detrended-market (cleaned)** ← selected | 11.94 % | **13.88 %** | +1.94 pp |
| MoE — luxury routing detrended (XGB) | 12.49 % | 14.31 % | +1.83 pp |
| XGBoost detrended-borough (capped) | 12.98 % | 14.32 % | +1.34 pp |
| CatBoost detrended-borough (cleaned) | 12.63 % | 16.00 % | +3.37 pp |
| Ridge (baseline) | 17.09 % | 16.62 % | −0.47 pp |
| CatBoost (cleaned) | 13.20 % | 18.03 % | +4.83 pp |
| 3-seed average (CatBoost) | 13.26 % | 18.47 % | +5.21 pp |
| MoE — luxury routing (XGB) | 14.05 % | 18.99 % | +4.94 pp |
| XGBoost (raw) | 13.88 % | 19.57 % | +5.69 pp |
| 3-seed average (XGB) | 14.23 % | 19.75 % | +5.52 pp |
| XGBoost (capped) | 14.33 % | 19.92 % | +5.59 pp |
| XGBoost (cleaned) | 14.60 % | 20.25 % | +5.66 pp |

Ridge's test R² is **−180.118** (printed in the stream output) against 0.539 on validation.

**Takeaways (cell 52).** The detrended family holds up out of sample. **The selected model is not the
test winner** — validation picked CatBoost detrended-market (13.88 %), best test is the 3-seed average
detrended (13.62 %); that **0.26 pp gap *is* the selection effect, made visible**, and is not
corrected because correcting it would mean choosing the deployed model on test. Every model that
early-stopped on validation drifts worse on test, expected because validation drove early stopping;
**Ridge is the lone exception at −0.47 pp**, being closed-form and never early-stopped, so it has no
optimism to give back. Plain boosters remain worse than
Ridge on test, confirming the §12.1 diagnosis was structural. Near-ties within ~0.1 pp on validation
do not reliably predict the test winner.

---

## S19 — §14.1 Repeat-property diagnostic (cells 53–55) · `central`

**The question: is the headline number measuring valuation, or memorisation?** The file is a price
history, so a dwelling sold three times contributes three rows; a chronological split cuts on **time**,
not **property**, so a flat sold 2010 (train) and 2016 (test) appears on both sides.

**Framing.** Not automatically cheating — forecasting a known building's next sale is a real business
task and the lagged features stay strictly historical — but the headline metric blends two different
problems, and **the unseen number is the one that generalises to new stock.**

**Result (cell 54).** `23.8% of test transactions are properties that also appear in training
(2,112 of 8,859). MdAPE gap between seen and unseen properties: -1.54 percentage points.`

| Test subset | Rows | MdAPE | MAE | R² | within_25pct |
|---|---:|---:|---:|---:|---:|
| Seen in training | 2,112 | 12.75 % | £118,212 | 0.808 | 79.97 % |
| Unseen property | 6,747 | 14.30 % | £137,644 | 0.791 | 75.49 % |

**Fix named:** a group-aware split keyed on `fullAddress` — improvement #1 in §18. Also called the
clearest single argument for why prior-sale features work: the model does better where it has history.

---

## S20 — §14.3 Choosing a target transform (cells 56–58) · `central`

**The open question from §12.1.** Does a *more granular* deflator do better? Intuition says yes.
Three candidates, all already trained: **regular** `log(price)`; **detrended market-wide**
`log(price / market_median_rolling_3m)`; **detrended borough-scaled**
`log(price / (lagged_borough_median_sqm × floorAreaSqM))`.

**Result (cell 57), `summarise_target_transform(RESULTS)`:**

| Backend | Target transform | Validation MdAPE | Test MdAPE | Test MAE |
|---|---|---:|---:|---:|
| XGBoost | regular | 14.33 % | 19.92 % | £157,856 |
| XGBoost | **market-wide** | **12.19 %** | 13.88 % | £133,597 |
| XGBoost | borough-scaled | 12.98 % | 14.32 % | £128,271 |
| CatBoost | regular | 13.20 % | 18.03 % | £142,472 |
| CatBoost | **market-wide** | **11.94 %** | 13.88 % | £133,012 |
| CatBoost | borough-scaled | 12.63 % | 16.00 % | £133,806 |

Both backends: market-wide wins on validation **and is also best on test**. The winner is chosen on
validation; the test column is printed so the reader can judge whether the choice generalised.

**Why the coarser deflator wins (cell 58) — the opposite of the hypothesis.**
`lagged_borough_median_sqm` is estimated from far fewer sales per month (one borough's transactions vs
the entire city's). Because the deflator is a **divisor**, a noisier deflator **injects that noise
directly into every training label it divides**, not merely into one more feature the model could
down-weight. And the coarser deflator costs nothing: `borough`, `floorAreaSqM` and
`lagged_borough_median_sqm` all remain ordinary input features, so the tree stays free to learn
"this borough commands a premium" — from *uncorrupted* labels.

**Stated general lesson.** *A detrending deflator should remove only what the model architecture
genuinely cannot learn on its own. Anything the model can already learn from a feature should stay a
feature, not get folded into the label.*

---

## S21 — §14.5 Feature-group ablation (cells 59–61) · `central`

**Framed as a scoping decision, not a model diagnosis.** Crime costs the most by far: it is why the
window stops at 2016, discarding **81 % of the record**. The rule adopted at the outset was to start
with the smaller window crime supports and widen only if crime proved not to matter.

**Method.** Retrain **the winning recipe** (XGBoost, detrended target, `capped`) once per feature
group, removing that group. Using the shipped recipe matters: ablating plain CatBoost on `log(price)`
would measure feature value on a model already handicapped by something else.

**Scored on validation, not test** — this study *decides* something. Absolute MdAPE is optimistic
because the models early-stop on validation; acceptable because every variant carries the identical
bias and the gate consumes only the **delta**.

**One group cannot be fully ablated.** The label is built from `market_median_rolling_3m`, so removing
"market lags" strips them from the *inputs* but not the *label*. The market-lag delta is therefore a
**lower bound**.

**Result (cell 60):**

| Variant | Features | MdAPE | MAE | MdAPE delta |
|---|---:|---:|---:|---:|
| Full | 28 | 12.192 % | £114,186 | 0.000 |
| No crime | 26 | 12.306 % | £114,611 | **+0.114** |
| No transport | 25 | 12.279 % | £113,689 | +0.087 |
| No macro | 27 | 12.139 % | £113,676 | **−0.054** |
| No market lags | 25 | 12.393 % | £115,248 | +0.201 |
| No prior sales | 24 | 13.119 % | £120,337 | **+0.927** |

Printed verdict: *Crime contributes +0.114 pp … Below the 0.15 pp gate: crime is not worth confining
the model to 2008-2016. The next iteration should drop crime and widen the window to the full
1995-2024 history (~418k rows, 5x current volume).*

**Reconciling with the EDA (cell 61)** — the notebook's own table:

| Group | §8 EDA showed | Ablation | Why they differ |
|---|---|---:|---|
| Transport | £900–950k within 500 m vs <£350k beyond 3 km; r = −0.30 | +0.09 pp | **Collinearity** — `borough`, `outcode`, lat/long and `distance_to_center_m` already encode "where" |
| Macro | rate collapse 5.5 %→0.5 % tracks the recovery | −0.05 pp | **Already in the target** — one value per month, a market-level trend the detrended target and market lags absorb; what remains is noise |
| Crime | confound stripped in §8.2 → r ≈ 0.00 | +0.11 pp | **The two agree** |
| Prior sales | 61.1 % of rows carry an earlier sale | +0.93 pp | **The two agree, and it is the biggest thing in the project** |

**A disclosure the notebook makes explicitly (cell 59).** *Both methodological choices change the
answer by enough to reverse the recommendation.* Scored on **test** and run on the **plain** target,
this same ablation reports crime at **+0.46 pp** — comfortably above the gate. On validation and on the
shipped recipe it collapses to near a rounding error. Both effects push the same way: the plain-target
model is so badly mis-levelled that *any* feature carrying market information looks valuable because
it partially compensates for the level error.

**Recommendations for the next data pull:** crime does not justify the window; **drop
`interest_rate`** (removal *improves* validation MdAPE); prior sales are the priority.

---

## S22 — §14.5 continued: crime resolution study (cells 62–65) · `central` (but see Q1)

**The distinction §8.2 opened.** The ablation removed *borough-grain, unnormalised, all-category*
crime. Before widening the window on that basis, the same question is asked of crime measured properly.

**Method.** The winning recipe refit with **six crime designs** over identical rows and an identical
target — only the crime columns move: borough vs LSOA grain, count vs rate, whole vs split by category.
**Five seeds** `(42, 43, 44, 45, 46)`, because a single GBT fit cannot separate a 0.1 pp effect from
run-to-run variation. Each gain **paired within its seed** before averaging, so seed variation cancels.

**Result (cell 63):**

| Crime features | Columns | MdAPE mean | MdAPE sd | Gain vs. no crime | Gain sd | Seeds won |
|---|---:|---:|---:|---:|---:|---:|
| No crime | 0 | 12.153 % | 0.129 | +0.000 pp | 0.000 | 0/5 |
| Borough count (status quo) | 2 | 12.136 % | 0.088 | +0.017 pp | 0.135 | 4/5 |
| LSOA total | 1 | 12.089 % | 0.038 | +0.064 pp | 0.164 | 3/5 |
| **LSOA by category** | 4 | 12.069 % | 0.143 | **+0.084 pp** | 0.187 | 3/5 |
| LSOA + density | 5 | 12.131 % | 0.089 | +0.022 pp | 0.133 | 2/5 |
| Borough + LSOA | 7 | 12.108 % | 0.097 | +0.045 pp | 0.200 | 4/5 |

**Two bars applied (cell 64).** Best design `LSOA by category`, +0.084 pp (sd 0.187, won 3/5 seeds).
**Seed noise floor 0.097 pp** (mean sd of one design across seeds). Gate 0.15 pp. Printed verdict:
*Crime does not clear the gate at its best resolution, as a count or a rate, whole or split by
category. The exploratory and modelling answers agree: the window can widen.*

**Stated significance (cell 65).** The gain is **below the noise it was measured through** — a gain
clearing the gate but not the noise floor would mean reading a decision off a number the experiment
cannot measure. *"This also settles a fairness question: crime was not dismissed on a technicality. It
was measured 147× more finely, normalised, and split by category, and still did not clear."*

---

## S23 — §14.6 What a property's own history is worth (cells 66–69) · `central` — **broken run**

**The question.** §8.3 established the repeat-sales panel; §9 built four prior-sale features; this is
**the study that put them in `FEATURES`, run before they were adopted**. Six candidate columns
measured, four carried. Same 0.15 pp gate and same paired-seed protocol as the crime study, "so the two
results are directly comparable". Seeds `(42, 43, 44)`.

**⚠️ Cell 67 raised `AttributeError: 'DataFrame' object has no attribute 'dtype'`** inside
`prior_sale_study` → `model.fit(X_train, y_train, eval_set=…)` (traceback points at
`src/lff/analysis.py`, lines ~233–284). One line printed before the failure:
`seed 42  No prior sale  0 cols  MdAPE 12.192%`. **Cell 68 has no output.** The table does not exist in
the notebook.

**What the notebook nevertheless states in prose (cells 69, 61, 80):**
- The group clears the gate **by roughly 6×, winning on every seed**: **+0.913 pp** (§14.6 prose);
  quoted as **+0.91 pp** in §18 and **+0.93 pp** in the §14.5 ablation and cell 0.
- Contrast with crime: +0.084 pp with a standard deviation larger than its mean.
- **Four columns adopted, two rejected.** `prev_sale_price`, `has_prev_sale`, `years_since_prev_sale`,
  `prev_sale_days_since_start` are in `FEATURES`. Carrying all six scored *worse* than four, so
  `log_prev_sale_price` and `n_prior_sales` earn nothing — "a tree splits on order, and the log of a
  column it already holds is the same ordering."
- **The elapsed-time pair doubles the value of the price alone:** prior price by itself ≈ **+0.45 pp**;
  adding *when* that sale happened takes it to **+0.91 pp**. Stated as the substantive finding:
  *a past price is only interpretable against how long ago it was paid.* £400k in 2009 and £400k in
  2015 say very different things.
- **The single largest modelling gain in the project** — larger than any architecture choice, second
  only to the target reframing in §12.1.
- *"The cost of getting here": these features were in the source file from the beginning; the pipeline
  read a price history as a transaction log for its entire first version.*

---

## S24 — §15 Conformal safety bound and the flip scanner (cells 70–74) · `central` — **no output**

**Method.** Multiplicative **split conformal prediction**. On the dedicated **calibration split**,
compute `r_i = y_i / ŷ_i` for every property and take the 10th percentile, `q_10`. The floor for a new
property is `ŷ × q_10`, so ~90 % should sit above it. A property is a **flip candidate** when its
transaction price falls below its own floor.

**Why ratios rather than differences.** Absolute residuals are heteroscedastic — errors widen sharply
as price rises. A £3 M house misses by far more pounds than a £200k flat while being no less accurate
in percentage terms, so a single absolute quantile would be far too loose at the bottom and far too
tight at the top. The ratio form scales the buffer with price, so one calibration serves both tiers.

**Why calibration is not the validation set.** Split conformal assumes the calibration residuals were
not used to fit the model; validation *was* — early stopping and architecture choice — so `q_10` there
would be optimistically tight.

**On exchangeability.** Classical conformal assumes calibration and test are exchangeable, which a
chronological split does not strictly guarantee — the market drifts. The empirical coverage check is
therefore **not a formality**; it is the actual evidence, reported honestly whether or not it lands.

**Code (cell 71).** `Q_SAFETY = calibrate_conformal(BEST, CALIB_EVAL, SPLITS, CONFIG.conformal_alpha)`
→ `scan = scan_for_flips(BEST, TEST_EVAL, SPLITS, Q_SAFETY)` → flips = `scan[scan["is_flip"]]` sorted
by margin; coverage = `(scan["actual_price"] >= scan["safe_lower_bound"]).mean() * 100`.
**Cell 71 has no stored output**, so `Q_SAFETY`, coverage, the flip count and the median margin are
**not recorded anywhere in the notebook.** Cell 73 (`plot_flip_margins`) likewise has **no figure**.

**The only §15 numbers recorded anywhere in the notebook** are in the live-listings appendix (cell 81):
**flip rate 13.39 % on 8,859 held-out test rows.**

**How to read it (cell 72).** Coverage is the number that validates the method; a shortfall of a point
or so is expected because the market drifted between calibration and test — reported rather than
corrected, because correcting against test would turn test into a tuning signal. **The flip rate is a
screening rate, not a hit rate.** Margin is the buffer in pounds, not expected profit.

**Figure description (cell 74).** Left: distribution of margins below the floor across flagged
properties (right-skewed — most just below, a few far below, where the screen is most interesting and
most likely picking up a short lease or a distressed sale). Right: actual vs predicted price for every
scanned property with the floor line drawn through it. **The floor is a single global ratio**, so it is
loose for easy properties and tight for hard ones — Mondrian/conditional conformal is the named fix.

---

## S25 — §16 Persisting the run (cells 75–76) · `secondary` — **no output**

`persist_run(BEST, Q_SAFETY, CONFIG, RESULTS, SPLITS)` writes to `artifacts/`:
`manifest.json` (selected model, feature list, target, conformal α and multiplier, config, both
leaderboards), `leaderboard.csv` (every model × split), `model.joblib` (fitted estimators, pinned
category dtypes, target encoder).

**Scope note.** The `predict` closures from §12 are not picklable by design, so what is persisted is
the underlying estimators plus everything needed to rebuild the closure — *the package is the
deployment unit, and the notebook is the narrative that produced it.* The remaining gap is a retraining
job that fails loudly when the §17 self-checks do.

---

## S26 — §17 Automated self-checks (cells 77–79) · `central` — **no output**

`run_self_checks(SPLITS, CONFIG, BEST, coverage, target, RAW, df_master)`. Seven invariants, and the
notebook states **each one guards a defect that was actually present in an earlier version**:

1. **Chronological integrity** — no training row dated after a validation row.
2. **No dead feature columns** — would have immediately caught the bug that left four categorical
   columns entirely NaN.
3. **Categorical levels pinned from training** — a code means the same thing at fit and predict time.
4. **Lagged market features never see the present** — a month's own median must not equal its own
   predictor.
5. **Prior sales strictly precede the row that reads them** — *asserted*, not merely reported, because
   a single violation is target leakage.
6. **Conformal coverage near nominal** — asserted on a **held-out slice of the calibration split**,
   never on test: the multiplier is refitted on the first 70 % of calibration and scored on the
   remaining 30 %, because checking coverage on the rows the multiplier was fitted on is an identity,
   not a test. Test coverage is printed for information and deliberately carries **no** assertion —
   making a run fail on a held-out metric turns that metric into a tuning signal.
7. **Re-runnability** — the raw station table still exists and is untouched, which an earlier version's
   variable clobbering broke.

The same probes run in `tests/` against a committed 500-row fixture in ~2 seconds.

**What a green run does not prove (cell 79).** Not that the model is good, that the features are right,
or that the protocol was followed *while the notebook was being written* — "that last one is what §18
exists to disclose."

---

## S27 — §18 Limitations and next steps (cell 80) · `central`

**What this model is not (six items).**
- **The scanner evaluates completed sales, not properties you can buy.** `TARGET` is `history_price`.
  A live scanner needs a listings feed and a calibration step for the asking-to-sold gap.
- **"Flip candidate" is a statistical claim, not a financial one** — says nothing about stamp duty,
  refurbishment, holding costs, fees, or *why* the property is cheap.
- **Conformal coverage is marginal, not conditional** — ~90 % overall does not hold inside Kensington
  or inside the top price decile.
- **The 2008–2016 window ends a decade ago**, and four shocks fall entirely outside it: the 2016 Brexit
  referendum, the 3 % stamp-duty surcharge on additional properties (same year, aimed squarely at
  flipping), the pandemic (which inverted the premium on being central), and the 2022 rate cycle.
- **Gain-based feature importance is not causal**, and the feature set is heavily collinear.
- **The evaluation universe is defined using the target** — the £1,500/m² floor and the £4 M cap both
  read `price`. Not a temporal leak, but not identifiable at prediction time either, so the reported
  MdAPE describes a population you could not select in production.

**Resolved since the first version (three).** Prior-sale features adopted (+0.91 pp, the largest
feature-side gain); crime tested at LSOA resolution and still failing the gate ("the finding is now
about crime rather than about resolution"); the pipeline lifted into `src/lff/` with a pytest suite and
`nbstripout` in a pre-commit hook.

**Ranked improvements (eight).** 1 — split by property, not only time (group-aware on `fullAddress`).
2 — **widen the window to 1995–2024**, ~60k → ~315k sales, "almost certainly worth more than every
remaining item on this list combined". 3 — walk-forward backtesting (one cut yields one number with no
error bar). 4 — make the margin an actual P&L. 5 — conditional (Mondrian) conformal. 6 — drop
`interest_rate`, revisit transport (travel *time* to Zone 1 rather than straight-line distance).
7 — features the data does not carry, **lease length above all**. 8 — interpretability that survives
collinearity (SHAP + permutation importance grouped over the location block).

---

## S28 — Appendix: checking against real, current listings (cell 81) · `unclear to me` (see Q4)

`scripts/live_flip_scan/` — a first, **deliberately uncalibrated** attempt at the live scanner §18 says
this dataset cannot build on its own. Scrapes current Rightmove listings (robots.txt checked at
runtime, rate-limited, responses cached), substitutes five public sources for features that only exist
in the 2008–2016 corpus (UK HPI for the market medians; `data.police.uk` for crime; EPC register for
floor area — unused this run, no API key; HM Land Registry Price Paid for `prev_sale_price`;
`lff.spatial` reused directly), retrains the selected model in-process and scores through the same
conformal scanner. Runs outside the notebook (~an hour), so the cell is a **static record of the last
run**, not re-executed.

**Result, 200 current London listings (2026-08-23):** flip rate **29.00 %** (n = 200) against
**13.39 %** on the held-out test set (n = 8,859).

**The notebook's own reading:** the live figure is *higher*, the opposite of what the asking-vs-sold gap
predicts. Splitting predicted/asking by borough points at why this probably is not real: Camden and
Kensington & Chelsea show predictions **1.7–2.5× asking**, more consistent with an artifact of the UK
HPI proxy or the 10–18 year extrapolation on `days_since_start` than genuine mispricing. **Treat
29.00 % as inconclusive, not as a finding about the 2026 market.**

---

## S29 — Appendix: related work (cell 82) · `secondary`

Six entries, each with a stated point of contact:
- **Rosen (1974)**, *Hedonic Prices and Implicit Markets* — the framing of §5–§9; the trees just drop
  the linear-in-attributes assumption.
- **Bailey, Muth & Nourse (1963)** / **Case & Shiller (1987)**, repeat sales — used in *both*
  directions: §12.1 divides out the market level to get a stationary target; §8.3/§14.6 feed the
  previous sale price back in as a feature.
- **Gibbons (2004)**, *The Costs of Urban Property Crime* — a hedonic study of London: criminal damage
  capitalises (≈1 % per tenth of a s.d. in Inner London), burglary does not. **Predicts what §8.2/§14.5
  find** — a real but small, category-dependent effect.
- **Lei et al. (2018)**, split conformal — §15 is split conformal with a **ratio** nonconformity score
  and **only the lower tail kept**, because a flip screen cares about the floor, not the ceiling.
- **Romano et al. (2019)**, conformalized quantile regression — the named next step for §15.
- **Zillow Prize** — the practitioner reference point; error rates explicitly **not** comparable
  (different market, no listing/interior data, every transaction scored rather than on-market only).

---

# Central / secondary split, as I read it

**Central (the deck must carry these):** S0 framing · S4 sources + the `saleEstimate_*` exclusion ·
S5 crime lags + rate curve · S6 spatial (projection, k-d tree, station filtering) · S7 master table
filters · S8–S9 EDA · S10 §8.2 crime confound · S11 §8.3 repeat-sales structure · S12 §9 features and
leakage discipline · S13 §10 split/variants/encoding · S14 §11 decision rules · S15–S16 §12/§12.1 the
ladder and the detrending fix · S17 §13 leaderboard · S18 §14 test · S19 §14.1 repeat diagnostic ·
S20 §14.3 transform choice · S21 §14.5 ablation · S22 crime resolution · S23 §14.6 prior sales ·
S24 §15 conformal · S26 §17 self-checks · S27 §18 limitations.

**Secondary (compressible to bullets or appendix):** S1 imports/versions · S2 config · S3 acquisition ·
S25 §16 persistence · S29 related work.

**Unclear to me:** S28 live-listings appendix (status in the story), and the whole
`prior_sale_study`-onward run state — see the questions.
