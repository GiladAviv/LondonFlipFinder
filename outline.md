# Stage 3 — slide budget and outline

**Deck:** 26 slides main + appendix. **Content time 23.0 min + ~2 min questions = 25 min.**
(26 is inside the stated 24–26 tolerance; going to 25 would mean cutting a stage, so I used the
tolerance instead.)

Decisions already taken from your answers: crime = **2 slides** (S8 EDA confound, S21 modelling
verdict) · Mixture of Experts = **1 dedicated slide** (S17) · live Rightmove scan = **appendix**.

---

## Part 1 — Budget by section

| # | Section of `pipeline.md` | Slides | Min | Obvious or judgment call? |
|---|---|---:|---:|---|
| — | Title | 1 | 0.5 | obvious |
| — | Pipeline map | 1 | 0.5 | obvious (required) |
| S0 | Framing: the problem and the one rule | 1 | 0.75 | obvious |
| S4+S5+S7 | Sources → cleaning → master table | 1 | 0.75 | **judgment (J1)** — three notebook sections on one slide |
| S6 | Spatial engineering | 1 | 0.75 | obvious |
| S8 | EDA: price distribution | 1 | 0.75 | obvious |
| S9 | EDA: §8.1 external drivers | 1 | 0.75 | obvious |
| S10 | §8.2 crime confound | 1 | 1.25 | your call — 2 crime slides total |
| S11+S12b | §8.3 repeat-sales panel + the four prior-sale features | 1 | 1.0 | **judgment (J2)** — discovery + construction merged |
| S12a | §9 temporal & market features, leakage discipline | 1 | 0.75 | obvious |
| S13 | §10 split + eval universe + training variants | 1 | 1.0 | **judgment (J3)** — encoding pushed to appendix |
| S14 | §11 metrics and the four decision rules | 1 | 0.75 | obvious |
| S15 | §12 the ladder, and where it broke | 1 | 0.75 | obvious |
| S16 | §12.1 detrending — mechanism, fix, residual evidence | **2** | 2.25 | obvious (the notebook's stated headline) |
| S17 | §13 validation leaderboard | 1 | 1.25 | obvious |
| S18 | §14 held-out test and drift | 1 | 1.25 | obvious |
| S15b | Mixture of Experts vs the 3-seed control | 1 | 0.75 | your call |
| S19 | §14.1 repeat-property diagnostic | 1 | 0.75 | obvious |
| S20 | §14.3 which deflator | 1 | 1.0 | obvious |
| S21 | §14.5 feature-group ablation | 1 | 1.25 | obvious |
| S22 | §14.5 crime resolution verdict | 1 | 0.75 | your call — crime slide 2 |
| S23 | §14.6 what a property's own history is worth | 1 | 1.0 | obvious |
| S24 | §15 conformal method | 1 | 0.75 | obvious |
| S24 | §15 coverage and the flip scan | 1 | 1.25 | obvious |
| S25+S26 | §16 artifacts + §17 self-checks | 1 | 0.75 | **judgment (J4)** — merged |
| S27 | §18 limitations + ranked next steps | 1 | 0.75 | **judgment (J5)** — 6 limitations + 8 improvements on one slide, rest to appendix |
| | **Main deck** | **26** | **23.0** | |
| S28, S29, misc | Appendix | 14 | — | see Part 3 |

**Nothing is cut.** Every stage in `pipeline.md` is on a main slide or an appendix slide.

---

## Part 2 — Slide-by-slide outline

Format: **title (the claim)** · core idea · bullets · figure/table · cells · minutes.

---

**1 · London Flip Finder — finding London homes that sold below their worth** — 0.5 min
Title slide. Subtitle carries the finished result: 59,946 sales, 13.88 % test MdAPE, a 90 %-target
conformal floor. *Cells 0.*

**2 · Seven phases, one rule: only what a buyer knew on the transaction date** — 0.5 min
*Core idea:* a map of the whole pipeline so every later slide has a home.
Diagram: Sources → Clean → Spatial → Master table → EDA → Features → Split → Models → Test →
Conformal floor, with the §-numbers on it. *Cells 2 (the phase table).*

**3 · A sale record is not a valuation — the work is assembling the context** — 0.75 min
*Core idea:* what the raw record carries, what has to be added, and the single governing rule.
- Record gives: floor area, rooms, tenure, type, energy rating, postcode, price
- Added context: station distance + fare zone, borough, crime, market level, base rate
- Prior sale of the same property — recorded for **61 %** of sales
- Governing rule: use only what a buyer knew at the transaction date
- Output is a **floor**, not an estimate: flag only when price < floor
*Cells 0–2.*

**4 · Four sources become one 59,946-row table — and one column is refused** — 0.75 min
*Core idea:* the join, the filters, and the leakage column that is never read.
- 418,201 sale rows · 13.5 M crime rows · 246 BoE rates · 471 stations
- `saleEstimate_*` never read — a third party's model output is target leakage
- `price_per_sqm >= 1500` drops £1 transfers, parking spaces, lease extensions
- Dedup on date+geometry+size+price; chronological sort before any rolling window
- Result: **59,946 × 37**, cached to Parquet
*Cells 9–16.*

**5 · Distance needs metres, so everything is reprojected before it is measured** — 0.75 min
*Core idea:* three spatial decisions, each fixing a specific distortion.
- EPSG:27700 first — a degree of longitude covers 62 % of a degree of latitude here
- `cKDTree` for nearest station: O(log n), and the index returns the fare zone free
- Feb-2022 station file filtered: 33 Elizabeth-only + 39 tram stops excluded
- Filter on network flags, not the label — Paddington kept, it was Underground since 1863
- Two distances kept: `distance_to_underground_m` and `distance_to_transit_m`
*Cells 13–14.*

**6 · Price is right-skewed, which is why every model trains in log space** — 0.75 min
*Core idea:* the distribution shape drives the loss-function decision in §11.
Figure: `c18_price_clip` — full distribution vs clipped to the 95th percentile.
- Peak £250k–£300k with a long tail; a few £20 M sales flatten every axis
- Charts clip at p95 (59,946 → 56,966) — **display only, models see untruncated data**
- Log space makes the loss proportional: a 10 % miss costs the same at £200k and £2 M
*Cells 17–21.*

**7 · Location is the dominant driver — and the location features are collinear** — 0.75 min
*Core idea:* the strongest marginal signals, plus the collinearity that §14.5 later cashes in.
Figure: `c23a_tube_premium` — mean price by distance band to the nearest station.
- £960k within 250–500 m of a station, under £350k beyond 3 km
- Borough spans **5×** in median £/m²: £11,000 K&C → £2,300 Bexley
- `floorAreaSqM` r = 0.57, `distance_to_center_m` r = −0.36
- `floorAreaSqM` ↔ `total_rooms` **r = 0.85** — several drivers measure size
- These are marginal associations; §14.5 asks the conditional question
*Cells 22–24.*

**8 · Higher-crime neighbourhoods cost more — because both track the centre** — 1.25 min
*Core idea:* the raw crime–price association is centrality, and it survives neither correction.
Figure: `c28_within_borough` — raw scatter (r = +0.30) beside the within-borough scatter (r = +0.00).
- Borough grain sums 4,835 LSOAs into 33 — a **147×** aggregation loss
- Re-measured at LSOA grain, as a rate, split by category
- Across boroughs r = +0.30 → within borough **r = +0.00**
- Differenced 2008–10 → 2014–16: r = −0.01 across 863 LSOAs
- This is the exploratory answer; §14.5 asks the fitted model
*Cells 25–30.*

**9 · The file is a price history, not a transaction log — 61.1 % of sales have a prior sale** — 1.0 min
*Core idea:* the dataset's own structure yields the strongest feature block in the project.
- 418,201 rows → **314,895** distinct sales across 137,760 addresses
- 66.0 % of addresses sold more than once; in-window **61.1 %** carry an earlier sale
- Median 6.9 years earlier (p10 2.2, p90 13.8)
- Four features: `prev_sale_price`, `has_prev_sale`, `years_since_prev_sale`,
  `prev_sale_days_since_start`
- As-of merge with a strict `<` bound; `assert_no_lookahead` is a hard check
*Cells 31–34.*

**10 · Every feature is built to answer: would the buyer have known this?** — 0.75 min
*Core idea:* the leakage discipline, stated as concrete construction rules.
- `market_median_rolling_3m/12m`: `.shift(1)` **then** roll — the shift drops the current month
- `lagged_borough_median_sqm` stamped onto the *following* month
- Crime lags: prior month, plus a 12-month sum with `closed='left'`
- BoE rates forward-filled onto a daily calendar — the rate in force on completion day
- `avg_room_size` ±∞ → NaN and **left NaN**; imputing here would leak across the split
*Cells 11–12, 32–34.*

**11 · Split by time, and give calibration its own slice** — 1.0 min
*Core idea:* the partition, the fixed evaluation universe, and the three training variants.
Table (4×3): train 35,967 (2008-01-01→2014-04-17) · val 8,991 · calib 5,994 · test 8,994.
- 60 / 15 / 10 / 15 chronological — a random split predicts January from June
- Calibration is separate so the 90 % bound is not calibrated on tuned data
- Evaluation universe **fixed** at price ≤ £4 M: 8,840 val / 5,916 calib / 8,859 test
- Only *training* data varies: raw 35,967 · capped 35,693 · cleaned 35,075
- `IsolationForest` flags 618 anomalies — **training only**, val and test untouched
*Cells 35–38.*

**12 · The metric and the gates are fixed before any model runs** — 0.75 min
*Core idea:* what decides, settled in advance so no result chooses its own bar.
- Headline metric **MdAPE** — robust to the tail MAE is dominated by
- Model selection: lowest **validation** MdAPE, never test
- Feature-group gate `ABLATION_GATE_PP` = **0.15 pp**
- Seed-noise floor: a gain must exceed 2 × mean sd across seeds
- Coverage target 90 %; all models trained in log space
*Cell 39.*

**13 · A ladder, not fourteen guesses — and rung 3 fails** — 0.75 min
*Core idea:* each model exists because the one below it failed in a diagnosable way.
- Ridge, `alpha=1.0`, closed-form — the baseline that should not need tuning
- XGBoost + CatBoost on `log1p(price)`, the standard tabular answer
- **On test the plain boosters score 19.57–20.25 % against Ridge's 16.62 %**
- No neural network: ~60k rows, no text, no images, no sequence structure
- Every trainer returns one `ModelBundle.predict` — one code path for all downstream
*Cells 41, 43, 51.*

**14 · A tree's leaf is a constant, so it cannot follow a rising market** — 1.25 min
*Core idea:* the failure has a mechanism, and the mechanism makes a testable prediction.
Table (3×4): signed-residual diagnostic on validation.
- Once `days_since_start` exceeds training, every row lands in the same boundary leaf
- Prediction: a large **positive** mean residual, not symmetric noise
- Plain XGBoost under-predicts validation by a mean of **£74,679** (70.4 % of rows)
- Ridge also under-predicts (£51,754) — the difference is size, not presence
- Measured on validation, so the fix never needed the test set
*Cells 42, 44–46.*

**15 · Predict the ratio to the market, and the trees only have to interpolate** — 1.0 min
*Core idea:* the fix, stated as the target change, plus what it bought.
Code (3 lines): `y = log(price / market_median_rolling_3m)`; predict; multiply back.
- The ratio is near-stationary while the market itself trends
- Detrending moves the mean residual £74,679 → **£24,331**
- XGBoost objective → `reg:absoluteerror`; CatBoost stays MAE, isolating the deflator
- Two deflator candidates enter the pool — §14.3 decides on validation
*Cells 42–46.*

**16 · Every detrended model outranks every plain one** — 1.25 min
*Core idea:* the reframed target is the largest single effect in the leaderboard.
Figure: `c48_leaderboard` (MdAPE panel).
- Top: `CatBoost detrended-market (cleaned)` **11.94 %** validation MdAPE
- Ridge baseline 17.09 %; the detrended family sweeps positions 1–6
- Built from the results registry, so the table cannot disagree with the models
- Same evaluation rows for every model — differences are the model, not the denominator
*Cells 47–49.*

**17 · Test costs every model 1.3–5.7 pp, and the winner is not the test winner** — 1.25 min
*Core idea:* the selection effect, measured rather than assumed away.
Table (6×4): selected + best + Ridge + worst rows, val / test / drift. Full 14 rows in appendix.
- Selected on validation: `CatBoost detrended-market (cleaned)` → **13.88 %** test
- Best on test is `3-seed average detrended (XGB)` at 13.62 % — a 0.26 pp selection effect
- Not corrected: revising here would make test a selection signal
- Plain boosters fall behind Ridge on test, confirming the §12.1 diagnosis
- Ridge test R² −180.118 against 0.539 on validation
*Cells 50–52.*

**18 · Segmenting the market did not beat modelling it whole** — 0.75 min
*Core idea:* the MoE is judged against a plain-ensembling control, not against a single model.
- Luxury router soft-weights two experts: temperature 0.763, 3,541 luxury / 32,152 standard
- 3-seed average exists as the control the MoE has to beat
- On the detrended recipe: MoE 12.49 % vs 3-seed average **12.12 %** vs single XGB 12.19 %
- Both were also trained on the detrended recipe, so neither is judged on a handicapped target
- Verdict: the ensembling control wins; routing adds nothing here
*Cells 41, 43, 48, 51.*

**19 · 23.8 % of test rows are properties the model has already seen** — 0.75 min
*Core idea:* the headline metric blends valuation with re-valuation.
Table (2×5): seen vs unseen — rows, MdAPE, MAE, R², within_25pct.
- The split cuts on time, not on property; a flat sold 2010 and 2016 sits on both sides
- Seen 12.75 % MdAPE (2,112 rows) vs unseen **14.30 %** (6,747 rows)
- Read the unseen number as generalisation to new stock
- Fix named: a group-aware split keyed on `fullAddress` (§18 #1)
*Cells 53–55.*

**20 · The coarser deflator wins — a noisy divisor corrupts every label it divides** — 1.0 min
*Core idea:* the intuition predicted the opposite, and why it was wrong.
Table (6×4): backend × transform × validation MdAPE × test MdAPE.
- Market-wide **11.94 %** vs borough-scaled 12.63 % vs regular 13.20 % (CatBoost, validation)
- Market-wide wins for both backends on validation, and also on test
- `lagged_borough_median_sqm` is estimated from one borough's sales, not the city's
- As a divisor its noise enters the label directly, not just one more feature
- borough, floorArea and the borough median stay inputs — nothing is lost
*Cells 56–58.*

**21 · Only the property's own history clears the gate** — 1.25 min
*Core idea:* the conditional contribution of each block, against a bar fixed in §11.
Figure: `c60_ablation` — MdAPE delta per removed group.
- Prior sales **+0.93 pp**; market lags +0.20; crime +0.11; transport +0.09; macro −0.05
- Ablating the shipped recipe, on validation, because this study decides something
- Transport's steep EDA gradient collapses: borough and outcode already encode "where"
- Removing `interest_rate` *improves* the model — it is already in the target
- Market lags are a lower bound: the deflator keeps them in the label
*Cells 59–61.*

**22 · Crime fails at its best resolution too, so the window can widen** — 0.75 min
*Core idea:* the scoping decision that 81 % of the record depends on.
- Six crime designs × five seeds, gains paired within seed
- Best design `LSOA by category`: **+0.084 pp**, sd 0.187, 3/5 seeds
- Seed-noise floor 0.097 pp — the gain is below the noise it was measured through
- Crime was measured 147× more finely, normalised and split by category, and still failed
- Next iteration drops crime and widens 2008–2016 → 1995–2024, ~5× the data
*Cells 62–65.*

**23 · A past price is only interpretable against how long ago it was paid** — 1.0 min
*Core idea:* the largest feature-side gain, and which columns actually earned it.
Table (4×3): design × mean validation MdAPE × paired gain.
- Full group **+0.913 pp**, winning every seed — ~6× the gate
- Prior price alone +0.453 pp; adding *when* it sold doubles it to +0.91
- Four of six candidates adopted; `log_prev_sale_price` and `n_prior_sales` earn nothing
- A tree splits on order, so the log of a column it holds is the same ordering
- These columns were in the source file from the start
*Cells 66–69.*

**24 · A point estimate is not actionable — the product is a floor** — 0.75 min
*Core idea:* multiplicative split conformal, and why each choice was made.
Code (4 lines): `r = y / ŷ` on calibration; `q_10`; floor = `ŷ × q_10`; flag if price < floor.
- Ratios not differences: residuals are heteroscedastic, so one absolute quantile misfits both tiers
- Calibrated on the dedicated slice — validation drove early stopping
- Only the lower tail is kept; a flip screen cares about the floor, not the ceiling
- Exchangeability is not guaranteed by a chronological split, so coverage is measured
*Cells 70–72.*

**25 · The floor holds on data it was never fitted on** — 1.25 min
*Core idea:* the empirical coverage check, and what a flagged property does and does not mean.
Figure: `c73_flip_margins`. **Numbers from the re-run** — the notebook cell has no stored output.
- Target 90 %, empirical coverage on held-out test *(from re-run)*
- Flip candidates *(from re-run)*; the appendix records 13.39 % on 8,859 test rows
- A flip rate is a screening rate, not a hit rate
- Margin is a buffer in pounds, not profit — stamp duty and refurbishment are not in it
*Cells 71–74.*

**26 · Seven assertions, each guarding a defect that was actually present** — 0.75 min
*Core idea:* what is persisted and what is asserted, plus the honest limits.
- Chronological integrity · no dead columns · pinned categorical levels · lagged features
- Prior sales strictly precede — asserted, because one violation is leakage
- Coverage asserted on a held-out slice of *calibration*; test coverage printed, never asserted
- Persisted: `manifest.json`, `leaderboard.csv`, `model.joblib`
- Top limits: window ends 2016 · coverage is marginal, not conditional · eval universe uses the target
- Next: group-aware split · widen to 1995–2024 (~5× data) · Mondrian conformal · lease length
*Cells 75–80.*

---

## Part 3 — Appendix (backup slides, referenced from the notes)

A1 property-characteristics 4-panel (c20) · A2 correlation matrix, enlarged · A3 borough £/m², all 28
(c23d) · A4 price vs floor area log-log (c23c) · A5 price by crime band boxplot (c23b_0) · A6 market
vs base rate, stacked panels (c23b_1) · A7 LSOA price and crime choropleths (c26) · A8 differenced
crime view (c29) · A9 full validation leaderboard, 14 rows · A10 full test comparison, 14 rows ·
A11 crime resolution study, all 6 designs · A12 encoding: native categoricals vs smoothed target
encoding · A13 live Rightmove scan, 29.00 % vs 13.39 % and why it is inconclusive (cell 81) ·
A14 related work, six entries (cell 82).

---

## Judgment calls I need you to confirm

**J1 — Sources + cleaning + master table on one slide (slide 4).** §4, §5 and §7 are three notebook
sections. Alternative: two slides, splitting the sources/exclusion from the filters/joins.
*My recommendation: one slide.* The crime lags and rate curve from §5 are covered properly on
slide 10, where they belong with the rest of the leakage discipline.

**J2 — §8.3 and the prior-sale features on one slide (slide 9).** Alternative: two slides — the
discovery, then the construction. *My recommendation: one slide.* The discovery is one fact, and
§14.6 (slide 23) is where the payoff is argued.

**J3 — Encoding to the appendix (A12).** Native `category` dtype for XGBoost, pinned levels, raw
strings for CatBoost, smoothed target encoding for the routers, and the `pd.to_numeric` warning.
*My recommendation: appendix*, because the split and the variants are the decisions and the encoding
is the mechanics — but the `to_numeric` bug is a good story if you want it on slide 11.

**J4 — §16 persistence merged into the self-checks slide (26).** *Recommendation: yes.* Three
artifact files is a bullet, not a slide.

**J5 — §18 compressed to two bullets on slide 26.** Six limitations and eight ranked improvements
do not fit. *My recommendation:* keep the three limitations that qualify the headline number and
the two top improvements; the rest go to the speaker notes. Alternative: give §18 its own slide
and drop to 27 slides.

**J6 — Which crime figure goes on slide 8.** `c28_within_borough` (the two scatters, r = +0.30 →
+0.00 — the quantified result) or `c26_lsoa_maps` (the two choropleths — visually stronger, and the
notebook's own setup for the confound). *My recommendation: c28*, with the maps in the appendix,
because the slide's claim is the correction and c28 is the correction.
