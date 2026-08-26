# London Flip Finder

**Valuation and mispricing detection for the London residential property market, 2008–2016.**

The project predicts what a London property is worth from its physical, spatial, temporal and
macroeconomic context, then applies **conformal prediction** to derive a statistically calibrated
price floor. A listing priced below that floor is flagged as a **flip candidate** — with a
quantified margin of safety rather than a hunch.

The pipeline lives in [`src/lff/`](src/lff/); [`london_flip_finder.ipynb`](london_flip_finder.ipynb)
is the narrative layer that drives it and carries the analysis.

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
| Bailey, Muth & Nourse (1963), [*A Regression Method for Real Estate Price Index Construction*](https://www.semanticscholar.org/paper/A-Regression-Method-for-Real-Estate-Price-Index-Bailey-Muth/8384788b906b9cbde02c20fede181f7163fc29eb), JASA 58:933–942; extended by [Case & Shiller (1987)](https://www.nber.org/system/files/working_papers/w2506/w2506.pdf) | Repeat sales: use properties sold more than once to separate market movement from property quality, since the property is held fixed between the two sales. | Both halves of that idea are used here, in opposite directions. §12.1 divides out the market level to get a stationary target; §14.6 goes the other way and feeds the *previous sale price* back in as a feature — the single strongest signal in the data (+0.9 pp MdAPE). §14.1 also reports errors on repeat properties separately. |
| Gibbons (2004), [*The Costs of Urban Property Crime*](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-0297.2004.00254.x), Economic Journal 114(499):F441–F463 | A hedonic study of London specifically: criminal damage capitalises into prices (≈1% per tenth of a standard deviation in Inner London), burglary does not. | The closest prior work to §8.2 and §14.5, and it predicts what we find — a real but small effect that is category-dependent. Worth reading as the reason the crime block earns so little once location is already in the model, rather than as a contradiction of it. |
| Lei, G'Sell, Rinaldo, Tibshirani & Wasserman (2018), [*Distribution-Free Predictive Inference for Regression*](https://arxiv.org/abs/1604.04173), JASA 113(523):1094–1111 | The reference treatment of split conformal prediction: finite-sample marginal coverage on top of any regressor, with no distributional assumptions. | §15 is split conformal with a *ratio* nonconformity score (actual/predicted) and only the lower tail kept, because a flip screen cares about the floor and not the ceiling. |
| Romano, Patterson & Candès (2019), [*Conformalized Quantile Regression*](https://papers.nips.cc/paper/8613-conformalized-quantile-regression), NeurIPS 32:3538–3548 | Conformal intervals that adapt their width to the input, rather than one global correction. | The obvious next step for §15. The multiplier q here is a single constant across the whole market, so coverage holds on average but the floor is loose for easy properties and tight for hard ones. [MAPIE](https://github.com/scikit-learn-contrib/MAPIE) is the usual scikit-learn implementation of both this and the split method above. |
| [Zillow Prize](https://www.zillow.com/z/info/zillow-prize/) (Kaggle, 2017–2019) | The largest public competition on automated valuation: 3,800+ teams predicting the Zestimate's log error; the winners improved on the benchmark by ~13%, and Zillow reports the national median error falling from ~4.5% to under 4%. | The practitioner reference point for §12–§14 — gradient-boosted ensembles over property, location and time features are what won there too. The error rates are *not* comparable to the 13.30% MdAPE here: a different market, no listing or interior data, and every transaction scored rather than on-market homes only. |

---

## Layout

```
src/lff/                  the pipeline, one module per stage
  config.py               paths, tunables, seeding                    (§2)
  ingest.py               dataset download and raw reads              (§3-4)
  clean.py                per-source cleaning                         (§5)
  spatial.py              projection, k-d tree and polygon joins      (§6)
  master.py               the joined master table                     (§7)
  features/               temporal, market, and the feature registry  (§9)
  split.py                chronological split, encoding, variants     (§10)
  metrics.py              one metric implementation, one registry     (§11)
  models.py               trainers, deflators, mixture-of-experts     (§12)
  analysis.py             diagnostics and design studies              (§12.1, §14)
  conformal.py            conformal bound and flip scanner            (§15)
  plots.py                every figure
  persist.py              run artifacts and self-checks               (§16-17)
tests/                    pytest suite over a committed 500-row fixture
london_flip_finder.ipynb  narrative, EDA, results
artifacts/                written by a run: model, manifest, leaderboard
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

Runs in about two seconds against a committed 500-row fixture. The suite covers the leakage
probes that section 17 runs at the end of a full pipeline run — that a lagged market feature
cannot move when its own month is shocked tenfold, that the Bank Rate curve never back-fills a
rate onto dates before it was announced, that the target encoder falls back to the global mean
for categories absent from training — plus unit coverage of zone parsing, the crime window,
the metrics and the conformal bound.

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
             temporal + market features (all strictly lagged)
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
| Land-Registry-derived price history | one row per sale event | target price, physical attributes |
| Met Police crime by LSOA | LSOA × category × month | neighbourhood safety |
| Bank of England base rate | one row per rate change | cost of borrowing |
| TfL station geodata (Feb 2022 snapshot) | one row per station | transport connectivity |
| GLA borough boundaries | polygon per borough | administrative context |

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
interchange, is one of them.
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
| **3-seed average detrended (XGB)** ← *selected on validation* | capped | **13.06 %** | **13.30 %** | +0.24 pp | £132,005 | 0.794 |
| XGBoost detrended-market *(best single model)* | capped | 13.12 % | 13.48 % | +0.36 pp | £132,608 | 0.790 |
| CatBoost detrended-market | cleaned | 13.40 % | 14.43 % | +1.03 pp | £137,437 | 0.776 |
| MoE — luxury routing detrended (XGB) | capped | 13.54 % | 14.11 % | +0.57 pp | £139,260 | 0.786 |
| XGBoost detrended-borough | capped | 13.98 % | 15.21 % | +1.23 pp | £135,392 | 0.796 |
| CatBoost detrended-borough | cleaned | 14.09 % | 18.03 % | +3.94 pp | £147,661 | 0.777 |
| CatBoost | cleaned | 14.79 % | 21.39 % | +6.60 pp | £162,248 | 0.747 |
| 3-seed average (CatBoost) | cleaned | 14.97 % | 21.86 % | +6.89 pp | £162,481 | 0.755 |
| 3-seed average (XGB) | cleaned | 15.12 % | 21.46 % | +6.34 pp | £172,972 | 0.690 |
| XGBoost | raw | 15.30 % | 22.49 % | +7.19 pp | £173,485 | 0.689 |
| XGBoost | capped | 15.45 % | 22.62 % | +7.17 pp | £173,433 | 0.720 |
| MoE — luxury routing (XGB) | cleaned | 15.46 % | 21.36 % | +5.90 pp | £175,174 | 0.684 |
| XGBoost | cleaned | 15.55 % | 22.47 % | +6.92 pp | £178,700 | 0.674 |
| Ridge (baseline) | capped | 17.43 % | 16.72 % | −0.71 pp | £168,702 | 0.280 |

The top six rows are new: four single detrended models (section 12.1, see *Why the trees
couldn't beat Ridge — and the fix* below) plus two Mixture-of-Experts variants retrained on that
same fixed target. Every row below Ridge is unchanged from before detrending existed: the plain
trees and the plain-target MoE variants still show the same +6.4–7.2 pp drift they always did,
which turns out to be diagnostic rather than incidental. The model at the top of this table is
what the pipeline actually selects and deploys — chosen on validation MdAPE alone, as always. Its
0.07 pp test-set disadvantage against the single-model runner-up is real but small, and is reported
rather than corrected for: overriding the selection with a test-set result would defeat the point
of holding test out in the first place.

**Conformal bound.** Calibrated on a dedicated calibration split at α = 0.10 (never touched by
early stopping or model selection), the safety multiplier is **q₁₀ = 0.7484** — the floor sits at
74.8 % of the predicted value, tighter than the previous iteration's 0.8823 because the underlying
model's predictions are now far more accurate and need a smaller safety margin. Empirical coverage
on the held-out test set is **88.96 %** against a 90 % target (−1.04 pp), and the §17 self-check
verifies coverage on a *held-out slice of the calibration split* (90.25 %) rather than asserting on
test. The scanner flags **978 of 8,859** test properties (11.04 %) as priced below their floor, at
a median margin of **£76,166**.

### Feature-group ablation: is crime worth the data it costs?

The crime file caps the whole project at 2008–2016, discarding 80 % of the available 418k-row
price history. Section 14.5 measures what that trade actually buys by retraining the winning
detrended XGBoost recipe with each feature group removed:

| Removed | Validation MdAPE | Δ vs. full |
|---|---:|---:|
| Macro (`interest_rate`) | 13.05 % | −0.07 pp |
| *(full model)* | 13.12 % | — |
| Crime | 13.13 % | **+0.01 pp** |
| Market lags | 13.29 % | +0.17 pp |
| Transport (distance + zone) | 13.37 % | +0.25 pp |

**Verdict: crime falls far below the 0.15 pp bar (+0.01 pp), so the 80 % data sacrifice is not
justified.** The recommended next step is to drop crime and widen the window to the full 1995–2024
history — roughly 5× the current volume — or, if the signal is wanted, to source post-2016 LSOA
crime data so the window can widen without losing it. Removing `interest_rate` actually *improves*
validation MdAPE slightly, so the macro group is not earning its place either.

**This verdict reversed, and the reversal is the point.** An earlier version of this ablation
scored on the **test set** and ran on the **plain, non-detrended target** — the recipe §12.1 shows
is broken — and reported crime at +0.46 pp, above the bar. Both were defects: a decision must not
read test, and measuring feature value on a model with a known level error credits any feature that
partially compensates for it. Scored on validation and on the recipe actually shipped, most of that
apparent value disappears. The market-lag group falls the same way, from +2.19 pp to +0.17 pp,
because detrending moves the market signal into the *target* — so those columns are no longer
carrying it as inputs. That figure is a lower bound for the same reason: the deflator still uses
`market_median_rolling_3m`, so the group cannot be fully ablated.

*(Scored on validation, which is also the early-stopping set, so the absolute level is optimistic.
All six variants share that bias identically and the gate consumes only the delta.)*

### Why the trees couldn't beat Ridge — and the fix

Plain XGBoost and CatBoost lose to the Ridge baseline by five points of MdAPE or more — on
tabular data of exactly the shape gradient boosting should win on. That is a symptom, not a
verdict on the architecture.

**The real cause: a tree's prediction is a leaf constant, so it cannot extrapolate a rising
market.** Once a value of a trending feature (`days_since_start`, `market_median_rolling_3m`)
exceeds anything seen in training, every such row falls into the same boundary leaf and the model
flat-lines at the last price level it learned. Ridge multiplies by a coefficient instead of
splitting, so it at least projects the trend forward — that asymmetry is what produces the gap.
Measured on the **validation** set (section 12.1), plain XGBoost under-predicts by a mean residual
of **+£78,782** against Ridge's **+£52,225** — a one-directional level error, not noise.

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

The result: validation mean-residual bias fell from **+£78,782 to +£20,873** — less than half
Ridge's — and test-set drift for XGBoost collapsed from **+7.17 pp to +0.36 pp**, using the
*identical* four-way split as before. That last point is the clean argument that split geometry
is not the primary cause: detrending changes nothing about which rows are in which split, yet it
closes almost all of the gap. The split-ordering cost documented below is real, but it is a
secondary effect riding on top of the much larger extrapolation problem, not the main story.

### Which deflator? A three-way comparison, not an assumption

The detrending fix itself has two candidate forms, and a natural next question: does a
*finer-grained* deflator do even better than a market-wide one? Three options were trained and
scored head to head for both backends (section 14.3):

Validation MdAPE decides; test is shown so the choice can be checked rather than trusted:

| Backend | | Regular | Market-wide | Borough-scaled |
|---|---|---:|---:|---:|
| XGBoost | validation | 15.45 % | **13.12 %** | 13.98 % |
| XGBoost | test | 22.62 % | **13.48 %** | 15.21 % |
| CatBoost | validation | 14.79 % | **13.40 %** | 14.09 % |
| CatBoost | test | 21.39 % | **14.43 %** | 18.03 % |

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
**Market-wide is the deflator used by `XGBoost detrended-market (capped)`** — the best-scoring
single model, and the runner-up to the model section 14 actually selects (see below).

### Repeat-property diagnostic

**23.8 %** of test transactions (2,112 of 8,859) are properties that also appear in training — a
consequence of splitting a price *history* by time rather than by property. Recomputed against the
selected model, `3-seed average detrended (XGB)`:

| Test subset | Rows | MdAPE | MAE | R² | Within 25 % |
|---|---:|---:|---:|---:|---:|
| Seen in training | 2,112 | 11.70 % | £110,430 | 0.811 | 83.8 % |
| Unseen property | 6,747 | 13.96 % | £138,759 | 0.790 | 75.3 % |

Previously-seen properties are predicted **2.26 pp better** than genuinely unseen stock — a real
memorisation effect, and one that has recurred with the same sign (though different magnitude)
across every model change in this project, unlike the single-iteration flip seen earlier. That is
mild evidence it is a stable property of the data (repeat sales genuinely are easier to value)
rather than noise tied to any one model. Even the *harder*, unseen-property subset — the number
that generalises to new stock — sits at 13.96 % MdAPE, comfortably better than every non-detrended
model's *blended* headline figure. A group-aware split (improvement 1 below) would remove the
remaining ambiguity.

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

Also new: **§14.5**, a feature-group ablation that quantifies whether crime is worth the 80 % of
the dataset it costs (see *Results* above) — the previous iteration only asserted this as a future
improvement; it is now measured.

The honest cost of fix #3: shrinking training data by 10 percentage points and moving validation
further from test raised the *plain* tree models' test MdAPE by several points, and — at the time
— was the leading explanation for why Ridge had overtaken them. A later iteration (see *Why the
trees couldn't beat Ridge — and the fix*, in Results) found the split-ordering cost was real but
secondary: the primary cause was a non-stationary target the trees could not extrapolate, and
fixing that closed the gap using the identical split. Both findings are kept in this document
because both are true and both were disclosed as they were found, not because the second
supersedes the first's honesty — it corrects its causal attribution.

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
  dataset does not contain. `scripts/live_flip_scan/` is a first, deliberately uncalibrated
  attempt — see [Checking against real listings](#checking-against-real-listings) below.
* **A flip flag is a statistical claim, not a financial one.** It says nothing about stamp duty
  (the UK's banded purchase tax, paid by the buyer),
  refurbishment, holding costs, or *why* the property is cheap — and properties are usually cheap
  for a reason the data does not record — few years left on the lease, structural problems, a
  seller who needs out quickly.
* **Conformal coverage is marginal, not conditional** — ~90 % overall, not guaranteed within any
  given borough or price decile.
* **The 2008–2016 window ends a decade ago**, and the corrected §14.5 ablation shows crime is
  worth only +0.01 pp — so the window *can* be widened by dropping crime, and probably should be.
  the 2016 Brexit referendum (which hit London prices hardest in the UK), the 3 % stamp-duty
  surcharge on additional properties introduced the same year and aimed squarely at flipping, the
  pandemic, and the 2022 rate cycle that took the base rate from near zero to over 5 % all fall
  outside the
  current window regardless.
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
| EPC register | `floorAreaSqM`, `currentEnergyRating` fallback |
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

1. **Split by property, not only by time** — group-aware splitting keyed on address, reported
   alongside the chronological number.
2. **Widen the window to the full 1995–2024 history** (~418k rows, 5× current volume). The
   corrected §14.5 ablation prices crime at +0.01 pp of validation MdAPE, so the feature no longer
   justifies the 80 % of the data its coverage costs. Dropping it is now the cheapest large win
   available. If the signal is still wanted, `data.police.uk` publishes post-2016 monthly LSOA
   extracts that would let the window widen without losing it — but that is optional rather than
   prerequisite. `interest_rate` is also a candidate for removal: ablating it *improved*
   validation MdAPE by 0.07 pp.
3. **Try reordering the four-way split** to train → calibration → validation → test. Now a minor
   optimisation rather than the main fix — *Why the trees couldn't beat Ridge* shows detrending
   closed most of the gap on the *current* split order — but the residual +0.30–0.80 pp drift on
   the detrended models suggests a small further gain is still on the table.
4. **Walk-forward backtesting** — rolling-origin evaluation gives a distribution of MdAPE instead
   of a single number with no error bar, and would settle whether the detrended models' lead over
   Ridge is stable across market regimes or specific to this test window.
5. **Turn the margin into a P&L** — stamp duty bands (including the 3 % additional-property
   surcharge, which applies to exactly this kind of purchase), refurbishment,
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
