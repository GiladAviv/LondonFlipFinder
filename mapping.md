# Slide → notebook cell map

`presentation.pptx` — **34 main slides + 14 appendix slides**. Cell indices
are 0-based positions in `london_flip_finder.ipynb` (same numbering as `pipeline.md`); § numbers
are the notebook's own section headings. Generated from `scripts/deck2/deck_content.py`, so it
cannot drift from the deck.

## Bar-Ilan ADS 83901 rubric coverage

| Required presentation element | Slides |
|---|---|
| Overview and Motivation | 2, 3 |
| Related Work | 5 (+ Zillow Prize in A13) |
| Initial Questions, and how they evolved | 4 (answered on 33) |
| Data — source, cleanup, storage | 7–12 |
| Exploratory Data Analysis | 13–15 (+ A1–A7) |
| Basic ML model + performance + error analysis | 20, 21 |
| Improved ML model + analysis | 22, 23, 24, 26 |
| Final Analysis | 32, 33, 34 |
| 15–25 min, Hebrew or English | English, **~28 min — over the stated cap** |

**The one open non-compliance is length.** At ~28 minutes the talk exceeds the rubric's
25-minute ceiling (Q&A excluded). To land inside it, cut roughly four slides: the fastest
candidates are 11 (point-in-polygon) and 12 (lagged joins) merged into 9, 26 (deflator choice)
folded into 23, and 25 (repeat-property diagnostic) moved to the appendix.

## Main deck

| # | Slide | § | Cells | Artifact |
|---|---|---|---|---|
| 1 | London Flip Finder | — | 0 | — |
| 2 | A buyer sees the asking price but not the value — and cannot tell them apart | §0 | 0 | — |
| 3 | A sale record is thin, so the work was assembling context around it | §0 | 0–2 | — |
| 4 | Three questions we started with — and how two of them changed | §0, §8.2, §12.1 | 0, 25, 31, 42 | — |
| 5 | Where each idea comes from — no ingredient here is new on its own | Appendix | 82 | — |
| 6 | Seven phases, and one rule that governs every design decision | — | 2 | diagram |
| 7 | Four sources, four different grains — and one column that is refused | §4 | 9–10 | table |
| 8 | Each source is reshaped before it is allowed to join | §5 | 11–12 | — |
| 9 | Six joins onto one spine — three of them deliberately lagged | §6–§9 | 13–16, 32–33 | diagram |
| 10 | Nearest station by k-d tree, with the fare zone carried along free | §6 | 13–14 | code |
| 11 | Point-in-polygon puts every sale inside a borough and an LSOA | §6 | 13–16 | code |
| 12 | Three joins carry a deliberate offset so no row sees its own month | §7 | 15–16 | code |
| 13 | Price is right-skewed, which is why every model trains in log space | §8 | 17–21 | figure |
| 14 | Location dominates — and the location features are heavily collinear | §8.1 | 22–24 | figure |
| 15 | Higher-crime neighbourhoods cost more, because both track the centre | §8.2 | 25–30 | figure |
| 16 | The file is a price history, not a transaction list | §8.3, §9 | 31–34 | — |
| 17 | Every feature answers one question: would the buyer have known this? | §9 | 11–12, 32–34 | — |
| 18 | Split by time, and give calibration a slice of its own | §10 | 35–38 | table |
| 19 | The metric and the gates are fixed before any model runs | §11 | 39 | — |
| 20 | Fourteen models, five families — and what each one optimises | §11–§12 | 39, 41, 43 | table |
| 21 | A tree's leaf is a constant, so it cannot follow a rising market | §12.1 | 42, 44–46 | table |
| 22 | Predict the ratio to the market, and the trees only interpolate | §12.1 | 42–46 | code |
| 23 | Every detrended model outranks every plain one | §13 | 47–49 | figure |
| 24 | Test costs every model 1.3–5.7 pp — and the winner is not the test winner | §14 | 50–52 | table |
| 25 | Is the headline number measuring valuation, or memorisation? | §14.1 | 53–55 | table |
| 26 | The coarser deflator wins — a noisy divisor corrupts every label | §14.3 | 56–58 | table |
| 27 | Only the property's own history clears the gate | §14.5 | 59–61 | figure |
| 28 | Crime fails at its best resolution too, so the window can widen | §14.5 | 62–65 | table |
| 29 | A past price is only interpretable against how long ago it was paid | §14.6 | 66–69 | table |
| 30 | A point estimate is not actionable — the product is a floor | §15 | 70–72 | code |
| 31 | The floor holds at 86.61 % on data it was never fitted on | §15 | 71–74 | figure |
| 32 | 13.88 % typical error — and the reframed target is what got there | §0, §13–§15 | 0, 51, 60, 63, 71 | table |
| 33 | Answering the three questions we opened with | §14–§18 | 51, 54, 63, 67, 71, 80 | — |
| 34 | What this is not, and the two changes worth making first | §18 | 80 | — |

## Appendix

| # | Slide | § | Cells | Artifact |
|---|---|---|---|---|
| 35 | A1 · Property characteristics and price, all four panels | §8 | 20–21 | figure |
| 36 | A2 · The confound, mapped: price and crime at LSOA grain | §8.2 | 26–27 | figure |
| 37 | A3 · The differenced view: crime change against price growth | §8.2 | 29–30 | figure |
| 38 | A4 · The chart that started §8.2: price by crime band | §8.1 | 23–24 | figure |
| 39 | A5 · Housing market and the cost of borrowing, 2008–2016 | §8.1 | 22–24 | figure |
| 40 | A6 · Median price per square metre, all 28 boroughs in the table | §8.1 | 23–24 | figure |
| 41 | A7 · Price against floor area on log-log axes | §8.1 | 23–24 | figure |
| 42 | A8 · Full validation leaderboard, all 14 models | §13 | 48 | table |
| 43 | A9 · Full test comparison, all 14 models with drift | §14 | 51 | table |
| 44 | A10 · All six crime designs, five seeds each | §14.5 | 63–65 | table |
| 45 | A11 · Encoding: two representations, both fitted on training only | §10 | 35 | — |
| 46 | A12 · The remaining ranked improvements, 3 to 8 | §18 | 80 | — |
| 47 | A13 · Pointed at today's market: 29.00 % flagged, and why that is an artifact | Appendix | 81 | — |
| 48 | A15 · Seven assertions, each guarding a defect that was actually present | §16–§17 | 75–79 | — |

## Cells with no slide

| Cells | Why |
|---|---|
| 3–8 | §1–§3 imports, `Config`, dataset download. Versions, `fast_mode`, split fractions and `ABLATION_GATE_PP` are quoted on slides 18–19 and in notes; the bootstrap carries no result. |
| 40 | `RESULTS = ResultsRegistry()` — covered by slide 23's "built from the results registry". |
| 76 | `persist_run(...)` — covered on appendix slide A15. |

## Where the merge detail comes from

Slides 7–12 describe the join machinery. The notebook's §1 module map, §6 and §7 name every
mechanism (`cKDTree`, EPSG:27700, "point-in-polygon joins", the as-of merge with a strict `<`
bound). The exact call signatures — `predicate="within"`, `allow_exact_matches=False`, the
`pd.DateOffset(months=1)` crime key, the `.bfill()` bug in `build_rate_curve`, the
`np.searchsorted` prior-sale count — come from the modules the notebook points to:
`src/lff/spatial.py`, `master.py`, `clean.py`, `features/`. One exception: the line on slide 10
explaining *how* a k-d tree partitions space is standard algorithm background, not a claim from
this project.

## Numbers recovered by re-running the notebook

The notebook's saved outputs stop at cell 67, which raised `AttributeError` in
`prior_sale_study`; cells 68, 71, 73, 76 and 78 have no stored output. `scripts/deck2/rerun.py`
re-executes the notebook's own calls and reproduces **every** number the notebook did record,
digit for digit.

| Slide | Value | Source cell |
|---|---|---|
| 29 | +0.453 / +0.913 / +0.894 pp, 3/3 seeds | 67 |
| 30 | `q_10 = 0.7674`, calibrated on 5,916 rows | 71 |
| 31 | coverage 86.61 %, 1,186 of 8,859 (13.39 %), median margin £66,124 | 71 |
| 31 | `c73_flip_margins` figure | 73 |
| A15 | calibration-holdout coverage 88.39 % on 1,775 rows; all checks pass | 78 |

Cross-check: the notebook's live-scan appendix (cell 81) independently records the test-set flip
rate as **13.39 % on 8,859** — identical to the re-run.

## Result-free opening

Slides 1–4 quote scope and questions only. The first accuracy **value** appears on slide 21; the
findings are recapped on slide 32 and tied back to the opening questions on slide 33.
