# London Flip Finder

**Valuation and mispricing detection for the London residential property market, 2008–2016.**

The project predicts what a London property is worth from its physical, spatial, temporal and
macroeconomic context — and, for the 61 % of sales that have one, from **what the property itself
last sold for** — then applies **conformal prediction** to derive a statistically calibrated price
floor. A sale priced below that floor is flagged as a **flip candidate**, with a quantified margin
of safety rather than a hunch.

The pipeline lives in [`src/lff/`](src/lff/); [`london_flip_finder.ipynb`](london_flip_finder.ipynb)
is the narrative layer that drives it and carries the analysis.

A closer look at the central finding — why gradient-boosted trees lost to a linear
baseline, and what fixed it — is written up on Medium:
[*I Beat XGBoost With Linear Regression (By Accident)*](https://medium.com/@giladaviv987/i-beat-xgboost-with-linear-regression-by-accident-37fed729835e).

**What the finished pipeline found**, over 59,946 in-window transactions scored on a held-out test
split that nothing before §14 reads:

| Result | Figure |
|---|---|
| Selected model (chosen on validation MdAPE) | `CatBoost detrended-market (cleaned)` — **13.88 %** test MdAPE |
| Ridge baseline | 16.62 % test |
| Plain gradient-boosted trees | 18–20 % test — **worse than the linear baseline**, until §12.1 reframes the target |
| Strongest feature group | a property's **own prior sale**: +0.91 pp of validation MdAPE |
| The group that decides the data window | **crime**, at +0.11 pp — below the 0.15 pp bar it had to clear to justify confining the model to 2008–2016 |
| Safety bound | a multiplicative conformal floor at a 90 % target, with empirical coverage reported rather than assumed |

The headline result is not an architecture. It is that **the target had to be reframed**:
predicting a property's price *relative to the market level*, rather than its price outright, is
what lets gradient-boosted trees beat a linear baseline at all.

<details>
<summary><b>Reading this without London knowledge</b> — British property and transport terms, defined once</summary>

The data is British, and the vocabulary is load-bearing rather than decorative: `tenure`,
`borough` and `outcode` are model features, stamp duty is a cost line in the profit calculation
below, and the difference between London's rail networks is why the station file gets filtered
at all.

| Term | What it means |
|---|---|
| **Borough** | One of London's 33 local-government districts, each holding roughly 150,000–400,000 people. The coarsest geography used here. |
| **LSOA** | *Lower Layer Super Output Area*, the UK census's small-area unit: about 1,500 residents each. 4,835 cover London — roughly 147 per borough, which is the resolution argument in §8.2. |
| **Postcode**, **outcode** | A UK postal code looks like `SW1A 1AA`. The **outcode** is its first half (`SW1A`), covering a few thousand addresses — finer than a borough, coarser than a street. |
| **Freehold** vs **leasehold** (`tenure`) | Freehold: you own building and land outright. Leasehold: you own the right to occupy for a fixed term, often 99–999 years at the start, and value falls as that term runs down. Most London flats are leasehold — which is why "a short lease" appears below as a reason a property is genuinely cheap rather than mispriced. |
| **Flat** | An apartment. |
| **Terraced**, **semi-detached**, **detached** | A row house joined on both sides, a house joined on one side, a free-standing house. |
| **Underground**, **Overground**, **DLR**, **Elizabeth Line**, **Tramlink** | London's rail networks: the subway; the suburban rail network; an automated light-rail line serving the eastern docklands; a fast east–west line opened in 2022; and street-running trams in one southern suburb. **TfL** (Transport for London) runs all of them. |
| **Fare zone** | London transport is priced in concentric rings, Zone 1 at the centre out to Zone 6 — a serviceable shorthand for how central an address is. |
| **Land Registry** | The government body recording every property sale in England and Wales; the price history derives from it. |
| **Bank of England base rate** | The UK central bank's policy rate — what mortgages are priced off. |
| **Met Police** | The Metropolitan Police, the force covering Greater London. The crime data is theirs. |
| **Stamp duty** | A tax the **buyer** pays on a purchase, charged in bands, with an extra 3 % since 2016 on any property that is not your main home — a substantial cost for a flipper. |
| **Units** | Prices in pounds sterling (£); floor areas in square metres (1 sqm ≈ 10.8 sq ft). |

</details>

## Related work

None of the ingredients here are new on their own — hedonic valuation, repeat-sales history, and
distribution-free prediction intervals each have a literature. What is specific to this project is
the combination: a hedonic model of London stock in 2008–2016, given the property's own sale
history, wrapped in a *one-sided* calibrated floor so the output is a screen a buyer can act on
rather than a point estimate.

| Work | What it is | Where it touches this project |
|---|---|---|
| Rosen (1974), [*Hedonic Prices and Implicit Markets*](https://www.journals.uchicago.edu/doi/10.1086/260169), JPE 82(1):34–55 | The theory that prices a differentiated good as a bundle of measured attributes, each carrying an implicit price. | The framing of §5–§9. Every feature — floor area, tenure, distance to a station, borough — is an attribute whose implicit price the model is estimating; the tree models just drop the linear-in-attributes assumption. |
| Bailey, Muth & Nourse (1963), [*A Regression Method for Real Estate Price Index Construction*](https://www.semanticscholar.org/paper/A-Regression-Method-for-Real-Estate-Price-Index-Bailey-Muth/8384788b906b9cbde02c20fede181f7163fc29eb), JASA 58:933–942; extended by [Case & Shiller (1987)](https://www.nber.org/system/files/working_papers/w2506/w2506.pdf) | Repeat sales: use properties sold more than once to separate market movement from property quality, since the property is held fixed between the two sales. | Both halves of that idea are used here, in opposite directions. §12.1 divides out the market level to get a stationary target; §14.6 goes the other way and feeds the *previous sale price* back in as a feature — the strongest feature block in the project (+0.91 pp of validation MdAPE, on every seed). §14.1 also reports errors on repeat properties separately. |
| Gibbons (2004), [*The Costs of Urban Property Crime*](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-0297.2004.00254.x), Economic Journal 114(499):F441–F463 | A hedonic study of London specifically: criminal damage capitalises into prices (≈1% per tenth of a standard deviation in Inner London), burglary does not. | The closest prior work to §8.2 and §14.5, and it predicts what we find — a real but small effect that is category-dependent. Worth reading as the reason the crime block earns so little once location is already in the model, rather than as a contradiction of it: §8.2 re-measures crime at LSOA grain, normalised and split by category, and it still does not clear the gate. |
| Lei, G'Sell, Rinaldo, Tibshirani & Wasserman (2018), [*Distribution-Free Predictive Inference for Regression*](https://arxiv.org/abs/1604.04173), JASA 113(523):1094–1111 | The reference treatment of split conformal prediction: finite-sample marginal coverage on top of any regressor, with no distributional assumptions. | §15 is split conformal with a *ratio* nonconformity score (actual/predicted) and only the lower tail kept, because a flip screen cares about the floor and not the ceiling. |
| Romano, Patterson & Candès (2019), [*Conformalized Quantile Regression*](https://papers.nips.cc/paper/8613-conformalized-quantile-regression), NeurIPS 32:3538–3548 | Conformal intervals that adapt their width to the input, rather than one global correction. | The obvious next step for §15. The multiplier q here is a single constant across the whole market, so coverage holds on average but the floor is loose for easy properties and tight for hard ones. [MAPIE](https://github.com/scikit-learn-contrib/MAPIE) is the usual scikit-learn implementation of both this and the split method above. |
| [Zillow Prize](https://www.zillow.com/z/info/zillow-prize/) (Kaggle, 2017–2019) | The largest public competition on automated valuation: 3,800+ teams predicting the Zestimate's log error; the winners improved on the benchmark by ~13%, and Zillow reports the national median error falling from ~4.5% to under 4%. | The practitioner reference point for §12–§14 — gradient-boosted ensembles over property, location and time features are what won there too. The error rates are *not* comparable to the 13.88% MdAPE here: a different market, no listing or interior data, and every transaction scored rather than on-market homes only. |

---

## Layout

```
src/lff/                  the pipeline, one module per stage
  config.py               paths, tunables, seeding                     (§2)
  ingest.py               dataset download and raw reads               (§3-4)
  clean.py                per-source cleaning                          (§5)
  spatial.py              projection, k-d tree and polygon joins       (§6)
  external.py             ONS sources fetched and cached at build time (§8.2)
  crime.py                crime at native LSOA grain                   (§8.2)
  master.py               the joined master table                      (§7)
  features/               temporal, market, prior-sale, the registry   (§9)
  split.py                chronological split, encoding, variants      (§10)
  metrics.py              one metric implementation, one registry      (§11)
  models.py               trainers, deflators, mixture-of-experts      (§12)
  analysis.py             diagnostics and design studies               (§12.1, §14)
  conformal.py            conformal bound and flip scanner             (§15)
  plots.py, maps.py       every figure; the choropleths need geometry
  notebook.py             display theme and the two warning filters    (§1)
  persist.py              run artifacts and self-checks                (§16-17)
tests/                    45 pytest checks over a committed 500-row fixture
scripts/live_flip_scan/   the out-of-notebook scan against live listings
london_flip_finder.ipynb  narrative, EDA, results
artifacts/                written by a run: model, manifest, leaderboard
data/external/            ONS boundaries, cached with URL and fetch date
```

Section numbers refer to the notebook, which reads top to bottom as the argument; the modules
hold the machinery it calls.

---

## Quickstart

```bash
git clone https://github.com/GiladAviv/LondonFlipFinder.git
cd LondonFlipFinder

python3 -m venv venv
./venv/bin/pip install -U pip setuptools wheel
./venv/bin/pip install -r requirements.txt
./venv/bin/pip install -e .
./venv/bin/python -m ipykernel install --user \
    --name london-flip-finder --display-name "London Flip Finder"

./venv/bin/jupyter lab london_flip_finder.ipynb
```

Then run the notebook top to bottom. **No manual data setup is required** — section 3 downloads
the 220 MB dataset archive from [Releases](https://github.com/GiladAviv/LondonFlipFinder/releases/tag/v1.0.0)
and extracts it to `data/` (1.8 GB on disk) on first run, and skips the download on every run
after that.

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

### Tests

```bash
./venv/bin/python -m pytest tests/ -q
```

45 checks, about two seconds, against a committed 500-row fixture. The suite covers the leakage
probes that section 17 runs at the end of a full pipeline run — that a lagged market feature
cannot move when its own month is shocked tenfold, that the Bank Rate curve never back-fills a
rate onto dates before it was announced, that the target encoder falls back to the global mean
for categories absent from training — plus the prior-sale invariants that matter most (an as-of
merge never returns the row it is predicting, addresses never borrow each other's history,
history is read from the whole file rather than the modelling window), the LSOA crime joins, and
unit coverage of zone parsing, the crime window, the metrics and the conformal bound.

### Configuration

| Variable | Effect |
|---|---|
| `LFF_DATA_DIR` | Point at an existing dataset directory instead of `./data` |
| `LFF_FAST_MODE=1` | Shrink every model's iteration budget for a fast smoke run |

Everything else — price caps, split ratios, the luxury threshold, the conformal α, the random
seed — lives in the single frozen `Config` object in section 2.

---

## The pipeline

```
GitHub Release ──► data/ ──► load ──► clean ──► spatial join ──► master table
                                                                      │
                              ┌───────────────────────────────────────┘
                              ▼
      temporal + market + prior-sale features (all strictly lagged)
                              │
                              ▼
     chronological split ── 60% train / 15% val / 10% calib / 15% test
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
| Land-Registry-derived price history | one row per sale event | target price, physical attributes, **and the property's own prior sale** |
| Met Police crime by LSOA | LSOA × category × month | neighbourhood safety, at borough grain for the model and LSOA grain for §8.2 |
| Bank of England base rate | one row per rate change | cost of borrowing |
| TfL station geodata (Feb 2022 snapshot) | one row per station | transport connectivity |
| GLA borough boundaries | polygon per borough | administrative context |
| ONS LSOA boundaries (2011 vintage) | polygon per LSOA | the 147× finer geography §8.2 measures crime on |

Everything except the ONS boundaries comes from the one release archive and is reproduced byte for
byte. The boundaries are fetched live and cached under `data/external/` with the URL and retrieval
date recorded in a sidecar JSON, so a source that moves or changes shape shows up in a diff.

**The price history is a repeat-sales panel, and the first version of this pipeline read it as a
transaction log.** 418,201 rows cover 137,760 addresses; 102,527 of them (24.5 %) are exact
(address, date, price) duplicates and a further 779 address-date pairs carry conflicting prices.
Once those are removed and collapsed, **314,895 distinct sales** remain and **66.0 % of addresses
sold more than once** — which is where the prior-sale features in §9 come from, and why they turn
out to be the strongest block in the model (§14.6).

**Deliberately excluded.** The source file carries `saleEstimate_*` and `rentEstimate_*` columns —
a third party's model output for the same property. Using them to predict price would be target
leakage.

**The station file is a problem the pipeline corrects, not ignores.** It is a February 2022
network snapshot applied to 2008–2016 transactions. Used raw, 41 of its 471 stations are Elizabeth
Line stops that did not open until May 2022 — crediting a 2009 sale with a rail link that arrived
thirteen years later — and another 39 are Tramlink stops, street-running trams in one southern
suburb with no Underground service at all. Both are filtered out by positive selection on the
Underground/Overground/DLR flags, which correctly keeps the 6 stations that had been Underground
stops for decades and merely *gained* Elizabeth Line service on top; Paddington, a major central
interchange, is one of them. What survives the filter: **270 Underground and 399 heavy-rail
stations, with 72 stops excluded** as post-window or non-rail.
*Residual caveat:* some Overground/DLR extensions also post-date parts of the window; fixing that
fully needs per-station opening dates, which this dataset does not carry.

## Features

28 features (23 numeric, 5 categorical) are built to answer one question: *would a buyer standing
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
| Prior sale | `prev_sale_price`, `years_since_prev_sale`, `prev_sale_days_since_start`, `has_prev_sale` |

The prior-sale block reads the property's own history, matched on address with a strict `<` bound
so a sale can never see itself: history is taken from the **whole 1995–2024 file**, not the
modelling window, because a 2009 sale's previous sale is usually pre-2008. 61.1 % of in-window
rows (36,609 of 59,946) carry a match, typically 6.9 years earlier. Two further columns the module
can build — `log_prev_sale_price` and `n_prior_sales` — are deliberately not carried; §14.6 shows
they earn nothing, since a tree splits on order and the log of a column it already holds is the
same ordering.

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
| **CatBoost detrended-market** ← *selected on validation* | cleaned | **11.94 %** | **13.88 %** | +1.94 pp | £133,012 | 0.794 |
| 3-seed average detrended (XGB) *(best on test)* | capped | 12.12 % | 13.62 % | +1.50 pp | £131,587 | 0.803 |
| XGBoost detrended-market | capped | 12.19 % | 13.88 % | +1.68 pp | £133,597 | 0.794 |
| MoE — luxury routing detrended (XGB) | capped | 12.49 % | 14.31 % | +1.83 pp | £135,590 | 0.798 |
| CatBoost detrended-borough | cleaned | 12.63 % | 16.00 % | +3.37 pp | £133,806 | 0.803 |
| XGBoost detrended-borough | capped | 12.98 % | 14.32 % | +1.34 pp | £128,271 | 0.813 |
| CatBoost | cleaned | 13.20 % | 18.03 % | +4.83 pp | £142,472 | 0.792 |
| 3-seed average (CatBoost) | cleaned | 13.26 % | 18.47 % | +5.21 pp | £142,693 | 0.796 |
| XGBoost | raw | 13.88 % | 19.57 % | +5.69 pp | £154,835 | 0.752 |
| MoE — luxury routing (XGB) | cleaned | 14.05 % | 18.99 % | +4.94 pp | £159,358 | 0.724 |
| 3-seed average (XGB) | cleaned | 14.23 % | 19.75 % | +5.52 pp | £162,207 | 0.706 |
| XGBoost | capped | 14.33 % | 19.92 % | +5.59 pp | £157,856 | 0.750 |
| XGBoost | cleaned | 14.60 % | 20.25 % | +5.66 pp | £165,254 | 0.704 |
| Ridge (baseline) | capped | 17.09 % | 16.62 % | −0.47 pp | £247,612 | −180.1 |

**The detrended block sweeps the top six rows**, and the drift column is the whole story of
section 12.1: every plain-target tree drifts +4.8 to +5.7 pp between validation and test, while
the detrended models sit between +1.3 and +1.9 pp — the one exception being CatBoost
detrended-borough at +3.4, which is the deflator question §14.3 takes up. What drift remains is a
residual cost of the split geometry, not the extrapolation failure the detrending fixed.

The selected model is chosen on validation MdAPE alone. On test it lands 0.001 pp from `XGBoost
detrended-market` — 13.877 % against 13.876 %, a dead heat — and 0.25 pp behind `3-seed average
detrended (XGB)`. That gap is reported rather than corrected for: overriding the selection with a
test-set result would defeat the point of holding test out in the first place.

**Ridge's test row is worth reading twice.** Its median error is respectable — 16.62 %, better
than every plain-target tree — while its MAE is £247,612 and its R² is −180. Test RMSE is £7.4 M
against that £247 k MAE, which is the signature of a handful of catastrophic linear
extrapolations dragging every squared-error statistic with them. The median does not move. That is
precisely the property the *Why MdAPE is the headline metric* note below argues for, showing up
unprompted in the baseline.

**Conformal bound.** Calibrated on a dedicated calibration split at α = 0.10 (5,916 rows, never
touched by early stopping or model selection), the safety multiplier is **q₁₀ = 0.7674** — the
floor sits at 76.7 % of the predicted value. Empirical coverage on the held-out test set is
**86.61 %** against a 90 % target, a **−3.39 pp** shortfall. That is reported, not corrected:
correcting it against test would turn the test set into a tuning signal, and the shortfall is
itself informative — a chronological split does not satisfy conformal prediction's exchangeability
assumption, the market moved between the calibration window (May–Dec 2015) and the test window
(Dec 2015–Dec 2016), and this is what that costs. The §17 self-check therefore asserts coverage on
a *held-out slice of the calibration split* instead — **88.39 %** on 1,775 rows the multiplier was
not fitted on — where exchangeability is much closer to holding. The scanner flags **1,186 of
8,859** test properties (**13.39 %**) as priced below their floor, at a median margin of
**£66,124**.

### Feature-group ablation: what is each block of features worth?

The crime file caps the whole project at 2008–2016, discarding **81 %** of the available record —
59,946 in-window sales out of 314,895 distinct sales. §14.5 prices that trade, and every other
block along with it, by retraining the winning detrended XGBoost recipe with each feature group
removed in turn. The full model scores **12.19 %** validation MdAPE:

| Group removed | Validation MdAPE | Δ vs. full | Verdict |
|---|---:|---:|---|
| Prior sales | 13.12 % | **+0.93 pp** | Dominant — over four times the next group, and the only one comfortably clear of the gate |
| Market lags | 12.39 % | +0.20 pp | Clears the gate, and is a lower bound: the deflator keeps them in the label |
| Crime | 12.31 % | +0.11 pp | **Below the 0.15 pp gate** |
| Transport (distance + zone) | 12.28 % | +0.09 pp | Below the gate |
| Macro (`interest_rate`) | 12.14 % | **−0.05 pp** | Removing it *improves* the model |

**Verdict on crime: +0.11 pp, below the 0.15 pp bar, so the 81 % sacrifice is not earned.** The
recommended next step is to drop crime and widen the window to the full 1995–2024 history — or, if
the signal is wanted, to source post-2016 LSOA crime data so the window can widen without losing
it. `interest_rate` fails for a different reason: it is one value per month shared by every row, a
market-level time trend, which is exactly what the detrended target and the market lags already
absorb. What is left is noise, and removing it helps.

**Three of §8's four headline drivers measure as worth roughly nothing here, and that is not a
contradiction.** §8 asked *does price vary with this?* — a marginal association. The ablation asks
*does this add anything the other features do not already carry?* — a conditional contribution.
Transport shows a steep bivariate gradient (£900–950k within 500 m of a station against under
£350k beyond 3 km) and still scores +0.09 pp, because `borough`, `outcode`, latitude, longitude
and `distance_to_center_m` already encode "where". A feature can be strong on the first question
and worth nothing on the second.

*(Scored on validation, which is also the early-stopping set, so the absolute level is optimistic.
All six variants share that bias identically and the gate consumes only the delta.)*

**An earlier version of this ablation reached the opposite verdict, and the reversal is the
point.** It scored on the **test set** and ran on the **plain, non-detrended target** — the recipe
§12.1 shows is broken — and reported crime at +0.46 pp, above the bar. Both were defects: a
decision must not read test, and measuring feature value on a model with a known level error
credits any feature that partially compensates for it. Scored on validation and on the recipe
actually shipped, most of that apparent value disappeared. The market-lag group fell the same way,
from +2.19 pp to +0.20 pp, because detrending moves the market signal into the *target* — those
columns are no longer carrying it as inputs.

#### Is that a verdict on crime, or on the resolution it was measured at?

The ablation above removed *borough-grain, unnormalised, all-category* crime, and three things
about that measurement stack against it: 4,835 LSOAs summed down to 33 boroughs is a **147×**
resolution loss, exactly the within-borough variation a crime-price relationship would live in; a
raw count scores a populous borough high automatically; and burglary summed with drug offences
assumes a buyer prices them identically. Before the window is widened on the strength of one
number, §8.2 re-asks the question with all three fixed — six crime designs over identical rows and
an identical target, each refit under **five seeds**, with gains paired *within* seed so seed
variation cancels rather than accumulates:

| Crime design | Columns | Mean val MdAPE | Gain vs. no crime | Gain sd | Seeds won |
|---|---:|---:|---:|---:|---:|
| No crime | 0 | 12.153 % | — | — | 0/5 |
| Borough count (status quo) | 2 | 12.136 % | +0.017 pp | 0.135 | 4/5 |
| LSOA total | 1 | 12.089 % | +0.064 pp | 0.164 | 3/5 |
| **LSOA by category** | 4 | 12.069 % | **+0.084 pp** | 0.187 | 3/5 |
| LSOA + density | 5 | 12.131 % | +0.022 pp | 0.133 | 2/5 |
| Borough + LSOA | 7 | 12.108 % | +0.045 pp | 0.200 | 4/5 |

The best design is LSOA grain split by category, at **+0.084 pp** — better than borough grain, and
still below the 0.15 pp gate. More importantly it is **below the noise it was measured through**:
the seed noise floor (the mean standard deviation of one design across seeds) is 0.097 pp, the
best design's own gain sd is 0.187, and it wins only 3 of 5 seeds. The effect is not resolvable by
this experiment at all, and keeping 2008–2016 — discarding 81 % of the sale records — on a
difference that size would be reading a decision off a number the study cannot measure.

**Crime does not earn the window, at its best available resolution, as a count or a rate, whole or
split by category.** The exploratory route agrees by an independent path: the raw across-borough
correlation of r = +0.30 between crime and price falls to **r = +0.00 within** borough, and
differencing over time gives **r = −0.01** across 863 LSOAs. Whatever the raw scatter measures, it
is not crime — and crime was not dismissed on a technicality.

#### What a property's own history is worth

The same protocol, same gate, applied to the prior-sale block (§14.6) — this is the study that put
those four columns in `FEATURES`, run before they were adopted:

| Prior-sale design | Columns | Mean val MdAPE | Gain vs. none | Gain sd | Seeds won |
|---|---:|---:|---:|---:|---:|
| No prior sale | 0 | 13.049 % | — | — | 0/3 |
| Prior price only | 2 | 12.596 % | +0.453 pp | 0.065 | 3/3 |
| **Prior price + elapsed time** | 4 | 12.136 % | **+0.913 pp** | 0.116 | 3/3 |
| Full candidate group | 6 | 12.155 % | +0.894 pp | 0.126 | 3/3 |

**The group clears the gate by roughly 6× and wins on every seed** — the opposite profile to
crime, which cleared neither the gate nor its own noise floor. Two things are worth pulling out.
First, **the elapsed-time pair doubles the value of the price alone**: prior price by itself is
worth +0.45 pp, and adding *when* that sale happened takes it to +0.91 pp. A past price is only
interpretable against how long ago it was paid — £400k in 2009 and £400k in 2015 say very
different things about what a property is worth now. Second, carrying all six candidate columns
scored *worse* than carrying four, so `log_prev_sale_price` and `n_prior_sales` were rejected: a
tree splits on order, and the log of a column it already holds is the same ordering.

This is the largest feature-side gain in the project, and it came from columns that were sitting
in the source file from the beginning. The pipeline read a price *history* as a list of
independent transactions for its entire first two versions.

### Why the trees couldn't beat Ridge — and the fix

Plain XGBoost and CatBoost beat the Ridge baseline comfortably on validation and then lose to it
on test, by 1.4 to 3.6 points of MdAPE — on tabular data of exactly the shape gradient boosting
should win on. The gap opens *between* the two splits, which is the tell: it is a symptom of the
target, not a verdict on the architecture.

**The real cause: a tree's prediction is a leaf constant, so it cannot extrapolate a rising
market.** Once a value of a trending feature (`days_since_start`, `market_median_rolling_3m`)
exceeds anything seen in training, every such row falls into the same boundary leaf and the model
flat-lines at the last price level it learned. Ridge multiplies by a coefficient instead of
splitting, so it at least projects the trend forward — that asymmetry is what produces the gap.
Measured on the **validation** set (section 12.1), plain XGBoost under-predicts by a mean residual
of **+£74,679** against Ridge's **+£51,754**, and it under-predicts on **70.4 %** of rows against
Ridge's 65.6 % — a one-directional level error, not noise.

Note what that Ridge figure implies, because it sharpens the claim: Ridge is *also* biased by the
same mechanism, just less. The market rose faster than any linear projection of the training
window. So the honest statement is not "trees cannot extrapolate and Ridge can" but "a
non-stationary target biases every model here, and punishes the trees hardest."

**The fix removes the need to extrapolate at all.** Instead of predicting `price`, the detrended
models (section 12.1) predict the *ratio* of price to a lagged market level:

$$y = \log\!\left(\frac{\text{price}}{\text{market level}}\right)$$

"How much is this property worth relative to where the market already is" stays close to
stationary even while the market trends upward, so the tree only has to interpolate within a
range of ratios it has already seen — never extrapolate past it. The predicted ratio is multiplied
back onto the market level at inference time. XGBoost also gets an explicit
`objective="reg:absoluteerror"`, aligning its loss with MdAPE (a median of relative errors)
instead of the unset default of squared error on `log(price)`.

The result: validation mean-residual bias fell from **+£74,679 to +£24,331** — less than half
Ridge's — the share of under-predicted rows fell from 70.4 % to **54.8 %**, near the 50 % an
unbiased model would show, and test-set drift for XGBoost collapsed from **+5.59 pp to +1.68 pp**,
using the *identical* four-way split as before. That last point is the clean argument that split
geometry is not the primary cause: detrending changes nothing about which rows are in which split,
yet it closes most of the gap. The residual +1.3–1.9 pp of drift on the detrended models is what
the split-ordering cost documented below actually looks like — real, but a secondary effect riding
on top of the much larger extrapolation problem.

### Which deflator? A three-way comparison, not an assumption

The detrending fix itself has two candidate forms, and a natural next question: does a
*finer-grained* deflator do even better than a market-wide one? Three options were trained and
scored head to head for both backends (section 14.3):

Validation MdAPE decides; test is shown so the choice can be checked rather than trusted:

| Backend | | Regular | Market-wide | Borough-scaled |
|---|---|---:|---:|---:|
| XGBoost | validation | 14.33 % | **12.19 %** | 12.98 % |
| XGBoost | test | 19.92 % | **13.88 %** | 14.32 % |
| CatBoost | validation | 13.20 % | **11.94 %** | 12.63 % |
| CatBoost | test | 18.03 % | **13.88 %** | 16.00 % |

*Market-wide* = `log(price / market_median_rolling_3m)`, one deflator per calendar month, shared
by every property. *Borough-scaled* = `log(price / (lagged_borough_median_sqm × floorAreaSqM))`,
personalised to each property's own size and borough — the hypothesis being that finer granularity
should capture more signal.

**That hypothesis was wrong.** The coarser, market-wide deflator wins for both backends, on both
validation and test, and by a wide margin for CatBoost. `lagged_borough_median_sqm` is estimated
from far fewer sales per month than the whole-market median — one borough's transactions in a
3-month window, against the entire city's — and because the deflator is a *divisor*, that extra
noise gets baked directly into every training label it divides into. The whole-market median,
estimated from thousands of sales, does not have that problem. Crucially, using the coarser
deflator costs nothing in borough- or size-specific signal: `borough`, `floorAreaSqM` and
`lagged_borough_median_sqm` are still ordinary input features, so the tree remains free to learn
those effects directly, from *uncorrupted* labels. The general lesson: a deflator should remove
only what the model architecture cannot learn on its own (the market-wide time trend); anything
the model can already learn from a feature should stay a feature, not get folded into the label.
**Market-wide is the deflator the selected model uses.** One caveat on the borough-scaled column:
on test MAE, `XGBoost detrended-borough` is actually the best model in the project (£128,271). The
choice is made on MdAPE, on validation, where it loses — but a reader optimising for pounds rather
than percentage error should know the two metrics disagree here.

### Repeat-property diagnostic

**23.8 %** of test transactions (2,112 of 8,859) are properties that also appear in training — a
consequence of splitting a price *history* by time rather than by property. Scored against the
selected model, `CatBoost detrended-market (cleaned)`:

| Test subset | Rows | MdAPE | MAE | R² | Within 25 % |
|---|---:|---:|---:|---:|---:|
| Seen in training | 2,112 | 12.75 % | £118,212 | 0.808 | 80.0 % |
| Unseen property | 6,747 | 14.30 % | £137,644 | 0.791 | 75.5 % |

Previously-seen properties are predicted **1.54 pp better** than genuinely unseen stock — a real
memorisation effect, and one that has recurred with the same sign (though different magnitude)
across every model change in this project. That is mild evidence it is a stable property of the
data (repeat sales genuinely are easier to value) rather than noise tied to any one model. It also
now has a mechanism rather than only a correlation: the prior-sale features of §14.6 act precisely
on this subset, and they are the largest feature-side gain in the project. Even the *harder*,
unseen-property subset — the number that generalises to new stock — sits at 14.30 % MdAPE, better
than every non-detrended model's *blended* headline figure. A group-aware split (improvement 1
below) would remove the remaining ambiguity, and it matters more now than it did before those
features existed.

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
lands on target. It does not: test coverage comes in at 86.61 % against the 90 % nominal, and that
gap is the price of a market that moved between the calibration and test windows. Section 17
asserts on a held-out slice of the calibration split (88.39 %) and only *reports* the test figure,
because gating a pipeline on a held-out metric turns the test set into a tuning signal the first
time a run fails.

---

## What changed from the previous version

The previous notebook was a Colab research scratchpad. The rewrite fixed ten defects, several of
which materially changed the reported results.

| # | Defect | Consequence | Fix |
|---|---|---|---|
| 1 | `pd.to_numeric(category_of_strings, errors='coerce')` on `propertyType`, `tenure`, `borough`, `outcode` | Those four columns became **entirely NaN**; every CatBoost model and the MoE router trained on four dead features | CatBoost uses native `cat_features`; the router uses train-fitted target encoding |
| 2 | The conformal cell called `expert_0`/`router_clf` directly, but a later cell had rebound them to a different backend trained on a different feature space | The "90 % guarantee" was computed from a model nobody intended to deploy, on mismatched features | Uniform `ModelBundle.predict()`; calibration and scoring share one code path |
| 3 | `IsolationForest` fitted on all data, anomalies dropped from validation and test too | Hard cases deleted from the exam — scores inflated | Fitted on the training slice, filters training only |
| 4 | Every reported metric came from the validation set | Model selection and reporting on the same data — circular | Select on validation, score once on the untouched test set |
| 5 | Two incompatible encodings (target-encoded numerics vs raw `category`) compared as equals in one table | Leaderboard compared models *and* feature spaces simultaneously | One encoding path, one evaluation universe |
| 6 | `df_tube` rebound inside an EDA cell, destroying the raw station table | Notebook could not be re-run top to bottom | Plot functions use locals; nothing rebinds global state |
| 7 | `distance_to_center` computed as Euclidean distance in **degrees** | Distorted geography along the east–west axis | Computed in BNG metres |
| 8 | Crime gaps filled with a median computed over the whole period | A statistic including the future injected into early rows | Left as NaN; each model imputes from training data |
| 9 | Empty cell; `target_encode()` defined but never called; one cell fully redundant with the next | Dead code | Removed |
| 10 | Chart labels said "<£5M" where the cap was £4 M; three near-identical metric functions with inconsistent key spellings (`MdAPE` vs `MDAPE`); leaderboard assembled from hand-typed literals | Silent mislabelling | Labels derive from config; one metric function; leaderboard generated from a results registry |

Two additions worth calling out:

* **A 3-seed average baseline.** Fitting the same recipe three times, differing only by random
  seed, and averaging the predictions costs nothing conceptually — it is the plain-ensembling
  comparison point an MoE design has to beat. Without it, an MoE that beats a single model has
  proved only that ensembling works, not that its architecture does.
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
| 1 | The station file is a Feb 2022 snapshot; 41 Elizabeth Line stations (that line opened May 2022) and 39 Tramlink stops (suburban street trams, no Underground service) fed the one distance feature used for every 2008–2016 transaction | Positive selection on Underground/Overground/DLR flags; split into `distance_to_underground_m` and `distance_to_transit_m` |
| 2 | `Zone`, present for all 471 stations, had zero references in the pipeline | Nearest station's fare zone attached as `station_zone`, free from the existing `cKDTree` query |
| 3 | The conformal calibration set was the same validation set used for early stopping and model selection — calibrating on data the model was implicitly tuned against | New dedicated calibration split (60/15/10/15 train/val/calib/test); §17 gained an ordering assertion |
| 4 | `bathrooms` was loaded and only plotted; `currentEnergyRating` was not even loaded; `crime_volume` was engineered, merged, and never added to `FEATURES` | All four wired into the feature list |

Also new: **§14.5**, a feature-group ablation that quantifies whether crime is worth the 81 % of
the record it costs (see *Results* above) — the previous iteration only asserted this as a future
improvement; it is now measured.

The honest cost of fix #3: shrinking training data by 10 percentage points and moving validation
further from test raised the *plain* tree models' test MdAPE by several points, and — at the time
— was the leading explanation for why Ridge had overtaken them. A later iteration (see *Why the
trees couldn't beat Ridge — and the fix*, in Results) found the split-ordering cost was real but
secondary: the primary cause was a non-stationary target the trees could not extrapolate, and
fixing that closed the gap using the identical split. Both findings are kept in this document
because both are true and both were disclosed as they were found, not because the second
supersedes the first's honesty — it corrects its causal attribution.

### Phase B — the pipeline left the notebook, and the data got read properly

Three changes since Phase A, in the order they landed:

| # | Change | What it bought |
|---|---|---|
| 1 | **The pipeline moved into `src/lff/`**, one module per stage, each a pure function; the notebook became the narrative that drives it | Any cell can be re-run without corrupting another's state, and a 45-check `pytest` suite runs the leakage probes in ~2 s against a committed 500-row fixture instead of only at the end of a full run |
| 2 | **Crime re-measured at native LSOA grain** — 4,835 areas instead of 33 boroughs, as a density as well as a count, split into three category series (§8.2) | The verdict on crime is now a verdict on *crime*, not on a 147× aggregation. It still does not clear the gate |
| 3 | **The file was finally read as the repeat-sales panel it is** — four prior-sale features, matched on address with a strict `<` bound (§9, §14.6) | +0.91 pp of validation MdAPE, the largest feature-side gain in the project, from columns that were sitting in the source file the whole time |

Change 3 is the one worth dwelling on. Nothing was added to the dataset: the pipeline had been
reading a price *history* as if it were a list of independent transactions for its entire first
two versions. The largest win available came from re-reading data already in hand, not from
another model on top.

---

## Limitations

* **The scanner evaluates completed sales, not properties you can buy.** `TARGET` is
  `history_price` — what a property *actually sold for*. A transaction that sold below its floor
  in 2016 validates the valuation model; it is not a listing anyone can act on today. A live
  scanner needs an asking-price feed and a calibration step for the asking→sold gap, which this
  dataset does not contain. `scripts/live_flip_scan/` is a first, deliberately uncalibrated
  attempt — see [Checking against real listings](#checking-against-real-listings) below.
* **A flip flag is a statistical claim, not a financial one.** It says nothing about stamp duty
  (the UK's banded purchase tax, paid by the buyer),
  refurbishment, holding costs, or *why* the property is cheap — and properties are usually cheap
  for a reason the data does not record — few years left on the lease, structural problems, a
  seller who needs out quickly.
* **Conformal coverage is marginal, not conditional** — ~90 % overall, not guaranteed within any
  given borough or price decile.
* **The 2008–2016 window ends a decade ago**, and §14.5 prices crime — the only reason the window
  stops there — at +0.11 pp, with §8.2 unable to rescue it even at LSOA grain, so the window *can*
  be widened by dropping crime, and probably should be. The 2016 Brexit referendum (which hit
  London prices hardest in the UK), the 3 % stamp-duty surcharge on additional properties
  introduced the same year and aimed squarely at flipping, the pandemic, and the 2022 rate cycle
  that took the base rate from near zero to over 5 % all fall outside the current window
  regardless.
* **The evaluation universe is defined using the target.** Two filters decide which rows are
  eligible to be scored, and both read `price`: the £1,500/sqm floor (applied before the split, to
  all four slices) and the £4 M cap. Both are defensible as a definition of "the standard market
  this product serves", and neither is a temporal leak — but neither is identifiable at prediction
  time either, so the reported MdAPE describes a population you could not actually select in
  production, where price is the unknown.
* **Gain-based importance is not causal**, and this feature set is heavily collinear — latitude,
  longitude, borough, outcode and distance-to-centre all encode "where".
* **The four-way split has a real, secondary accuracy cost for models that use early stopping**,
  documented in *Why the trees couldn't beat Ridge — and the fix* above — smaller than the
  non-stationary-target problem that section also diagnoses and fixes, but not zero.
* **The borough-scaled deflator was a reasonable idea that measurably did not work** (section
  14.3) — worth knowing before reaching for finer-grained detrending elsewhere in this pipeline
  (e.g. per-property-type) without testing it the same way.

## Checking against real listings

`scripts/live_flip_scan/` scrapes current Rightmove listings (robots.txt checked at runtime,
rate-limited, every response cached), substitutes five public data sources for the features that
only exist inside this project's own 2008–2016 corpus, retrains the selected model in-process, and
scores the live listings through the same conformal scanner as section 15:

| Live-data proxy | Real feature it stands in for |
|---|---|
| UK HPI (`landregistry.data.gov.uk`) | `market_median_rolling_3m/12m`, `lagged_borough_median_sqm` |
| `data.police.uk` | `crime_volume`, `crime_volume_prev_12m` (point-radius, not borough-sum; the 12-month figure is the latest month annualised, not a real trailing sum) |
| EPC register | `floorAreaSqM`, `currentEnergyRating` fallback (unused in the run below — no API key configured) |
| HM Land Registry Price Paid Data | `prev_sale_price` and the rest of the prior-sale block, matched on postcode + street |
| `lff.spatial`, reused directly | borough, distance to nearest station/centre |

```bash
python scripts/run_live_flip_scan.py --stage all
```

**Result, 200 current London listings (2026-08-23).** 13.39 % of the held-out test set (completed
sales) was flagged as a flip candidate, against 29.00 % of the live listings (asking prices) —
the opposite direction the asking-vs-sold gap alone would predict, since an asking price sitting
above the eventual sold price should make *fewer* listings look underpriced, not more. Splitting
the predicted/asking ratio by borough points at why this is probably not a real signal: a handful
of boroughs (Camden, Kensington & Chelsea) show predictions 1.7–2.5× the asking price, more
consistent with an artifact of the UK HPI market-level proxy or the 10–18 year extrapolation on
`days_since_start` than genuine mispricing. Treat 29.00 % as inconclusive, not as a finding about
the 2026 market — the script prints the full proxy-vs-real breakdown with every run.

## Where to take it next

1. **Split by property, not only by time** — group-aware splitting keyed on `fullAddress`,
   reported alongside the chronological number. This matters more now that prior-sale features
   exist, since they act precisely on repeat properties; §14.1 quantifies the overlap at 23.8 % of
   test rows.
2. **Widen the window to the full 1995–2024 history** — ~315k distinct sales, roughly 5× the
   current 59,946. Crime is the only reason the window stops at 2016, and it prices at +0.11 pp of
   validation MdAPE (§14.5), or +0.084 pp at its best LSOA-grain design (§8.2) — below both the
   0.15 pp gate and the study's own 0.097 pp seed-noise floor. Dropping it is almost certainly
   worth more than everything else on this list combined. If the signal is still wanted,
   `data.police.uk` publishes post-2016 monthly LSOA extracts that would let the window widen
   without losing it.
3. **Walk-forward backtesting** — one 60/15/10/15 cut yields one number with no error bar.
   Rolling-origin evaluation (expanding window, refit each year) gives a distribution of MdAPE and
   reveals whether the detrended models' lead depends on which slice of the cycle got tested.
4. **Turn the margin into a P&L** — stamp duty bands (including the 3 % additional-property
   surcharge, which applies to exactly this kind of purchase), refurbishment, financing, agent and
   legal fees; then rank candidates by return rather than by pounds.
5. **Conditional (Mondrian) conformal prediction** — per-borough and per-decile multipliers so
   coverage holds within the segments an investor actually shops in.
6. **Drop `interest_rate`, and revisit the remaining thin groups.** §14.5 measures its removal as
   an *improvement* (−0.05 pp). Transport at +0.09 pp is similarly marginal given how much else
   encodes location — though travel *time* to Zone 1, rather than straight-line distance, might
   not be.
7. **Lease length** drives much of flat valuation and is absent entirely from the source data. A
   leasehold flat with 70 years left is worth materially less than an otherwise identical one with
   950, so this one missing column is a plausible part of what the scanner currently mistakes for
   underpricing.
8. **SHAP plus location-grouped permutation importance**, so "where" is credited once rather than
   split five ways.
9. **Direct quantile regression** (`objective='reg:quantileerror'`) as an alternative to a single
   global conformal multiplier that applies one ratio to every property.
10. **Operational hardening** — *partly done*: the pipeline is a package with a pytest suite over a
    committed fixture, and `nbstripout` runs in pre-commit. Still outstanding: a retraining job
    that fails loudly when the section 17 self-checks do.
11. **Try reordering the four-way split** to train → calibration → validation → test. A minor
    optimisation rather than the main fix — *Why the trees couldn't beat Ridge* shows detrending
    closed most of the gap on the *current* split order — but the residual drift on the detrended
    models suggests a little further gain is on the table.

## License

MIT.
