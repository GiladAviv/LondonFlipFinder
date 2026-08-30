# Your gradient boosting isn't broken — your target is

### A linear baseline beat XGBoost and CatBoost on 60,000 London property sales. The fix wasn't a better model.

---

Halfway through building a valuation model for London property, I hit a result that
should not happen.

On tabular data — 60,000 rows, 28 features, a mix of numeric and categorical — gradient-boosted
trees are supposed to win. That is the whole reason they are the default. Instead, on the
held-out test set, my plain XGBoost and CatBoost models scored **19.57 % to 20.25 %** median
absolute percentage error, while a Ridge regression with `alpha=1.0` and no tuning at all scored
**16.62 %**.

Worse, they had looked fine right up until that moment:

| Model | Validation MdAPE | Test MdAPE | Drift |
|---|---:|---:|---:|
| XGBoost (raw) | 13.88 % | 19.57 % | **+5.69 pp** |
| XGBoost (capped) | 14.33 % | 19.92 % | **+5.59 pp** |
| CatBoost (cleaned) | 13.20 % | 18.03 % | **+4.83 pp** |
| Ridge (baseline) | 17.09 % | 16.62 % | −0.47 pp |

Every tree model beat Ridge on validation. Every tree model then lost to it on test, dropping
five to six percentage points, while the linear model actually got *better*.

That asymmetry is the tell. A model that overfits degrades on new data — but it does not
degrade *five times more than the linear model sitting next to it*. Something structural was
wrong, and it wasn't the architecture.

---

## The setup, briefly

The project: given a London property's physical, spatial, temporal and macroeconomic context,
what is it worth — and can we flag sales priced below a floor we can actually defend?

The data is 59,946 transactions between 2008 and 2016, assembled from four public sources: a
Land-Registry-derived price history, Metropolitan Police crime by neighbourhood and month, the
Bank of England base rate, and Transport for London station geodata. One rule governed every
design decision: **only use what a buyer standing at the transaction date could have known.**

That rule is why the split is chronological — 60 / 15 / 10 / 15 into train, validation,
calibration and test — rather than random. Training on June 2016 to predict January 2016 is a
situation that never occurs in production, so it shouldn't occur in evaluation either.

It is also, as it turns out, why the trees failed.

---

## The diagnosis: a leaf is a constant

Here is the mechanism.

A decision tree's prediction is a **constant per leaf**. It has no slope, no coefficient, no
capacity to extrapolate. Once a value of a trending feature — `days_since_start`, or a rolling
market median — exceeds anything the tree saw in training, every such row falls into the same
boundary leaf, and the model flat-lines at the last price level it learned.

London prices rose substantially across 2008–2016. My training split ends in April 2014. The
test split runs from December 2015 to December 2016. The trees were being asked to predict a
market level they had never seen, using a mechanism that structurally cannot project one.

Ridge suffers less, because it multiplies by a coefficient instead of splitting on a threshold
— so it at least projects the trend forward, even if imperfectly.

That diagnosis makes a **falsifiable prediction**: if this is right, the plain trees should
under-predict with a large, one-directional *positive* mean residual — a level error, not
symmetric noise. So I measured it, on validation only:

| Model (validation) | Mean residual | Median residual | Under-predicted |
|---|---:|---:|---:|
| XGBoost (capped) | £74,679 | £38,198 | 70.4 % |
| Ridge (baseline) | £51,754 | £36,073 | 65.6 % |

There it is. Plain XGBoost under-predicts by a mean of £74,679 and gets 70 % of rows too low.
That is not noise; that is a systematic level error.

Note the second row, though, because it complicates the tidy story: **Ridge under-predicts
too**, by £51,754. The market rose faster than any linear projection of the training window
could follow. What separates the models is the *size* of the level error, not its presence.

So the accurate claim is not "trees can't extrapolate and linear models can." It is: **a
non-stationary target biases every model here, and punishes trees hardest.**

Which means the fix should target the shared cause, not the architecture.

---

## The fix: stop predicting price

If the problem is that the target moves, then don't predict the target. Predict its **ratio to
where the market already is**:

```python
# market_median_rolling_3m: the market-wide monthly median, shifted one month
# and then rolled -- so a month's own median never informs its own prediction
y = log(price / market_level)

model.fit(X_train, y)
price_hat = exp(model.predict(X)) * market_level
```

"How much is this property worth *relative to the current market*" is close to stationary even
while the market itself trends. A tree only has to interpolate within a range of ratios it has
already seen. At inference, the market level is multiplied back on.

The deflator is a feature I already had, built to be leakage-safe: the market-wide median is
`.shift(1)`-ed *before* the rolling window opens, so no month can see itself.

Two lines of conceptual change. Here is what it bought:

| Model | Validation | Test |
|---|---:|---:|
| XGBoost, plain | 14.33 % | 19.92 % |
| XGBoost, detrended | 12.19 % | **13.88 %** |
| CatBoost, plain | 13.20 % | 18.03 % |
| CatBoost, detrended | 11.94 % | **13.88 %** |

Six points of test MdAPE on XGBoost. Four on CatBoost. And the residual bias collapsed from
£74,679 to **£24,331**.

*[FIGURE: c48_leaderboard.png — validation leaderboard, all 14 models]*

On the full leaderboard the effect is a clean block structure: every model trained on
`log(price / market level)` outranks every model trained on `log(price)`, with no interleaving.
No architecture change in the project came close — not CatBoost's native categorical handling,
not a mixture-of-experts with a luxury router, not seed averaging.

**The target was the bottleneck. Not the model.**

---

## The lesson that generalises: don't fold features into your labels

Having established that a deflator helps, the obvious next move is a *better* deflator. Instead
of dividing by one market-wide median shared by every property that month, why not divide by
something local — the median price per square metre in that specific borough, times the
property's floor area? Comparable properties, personalised per row. It should carry more signal.

It doesn't. I tested it, and the coarser deflator won for both backends:

| Target transform | XGB val | XGB test | CatBoost val | CatBoost test |
|---|---:|---:|---:|---:|
| `log(price)` | 14.33 % | 19.92 % | 13.20 % | 18.03 % |
| detrended, market-wide | **12.19 %** | **13.88 %** | **11.94 %** | **13.88 %** |
| detrended, borough-scaled | 12.98 % | 14.32 % | 12.63 % | 16.00 % |

The reason is worth internalising, because it applies well beyond property data.

The borough median is estimated from *one borough's* transactions in a three-month window. The
market-wide median is estimated from the entire city's. The borough figure is noisier — and
because the deflator is a **divisor**, that noise goes directly into every training label it
divides. It doesn't become one more slightly-noisy feature the model can learn to down-weight.
It corrupts the ground truth.

Meanwhile the coarse deflator costs nothing, because `borough`, `floorAreaSqM` and the borough
median all remain ordinary input features. The tree is still free to learn "this borough
commands a premium" — from *uncorrupted* labels.

> **A detrending deflator should remove only what the architecture genuinely cannot learn on
> its own.** Anything the model could already learn from a feature should stay a feature, not
> get folded into the label.

---

## A negative result, done properly

The second finding is one I expected to go the other way.

Crime was in this project from the start, and it was expensive: the Met Police file only covers
2008–2016, and **that single constraint is why the entire modelling window stops there** —
59,946 in-window sales against 314,895 in the full history. Eighty-one percent of the available
record, discarded to accommodate one feature block.

The exploratory signal looked promising, then immediately suspicious. Across London,
neighbourhood crime correlates *positively* with price (r = +0.30) — more crime, more money,
which is backwards from what buyers say they care about.

*[FIGURE: c28_within_borough.png — raw vs within-borough scatter]*

It's a confound, and a big one. Central London is simultaneously the most expensive and the
most crime-recording part of the city, so a raw correlation largely measures centrality. Subtract
each borough's own mean from both variables and the relationship vanishes: **r = +0.00**. Ask a
different question entirely — did neighbourhoods where crime *fell* see faster price growth? —
and you get r = −0.01 across 863 areas.

But a feature can carry no marginal correlation and still earn its place by interacting inside a
model. So I put the same question to the fitted model, with the bar fixed in advance at 0.15
percentage points of validation MdAPE.

*[FIGURE: c60_ablation.png — cost of removing each feature group]*

Crime came in at **+0.11 pp**. Below the bar.

The tempting move is to stop there. But the ablation had removed *borough-grain, unnormalised,
all-category* crime — and the raw file is at neighbourhood grain, 4,835 areas summed into 33
boroughs. That's a 147× loss of resolution. "Crime doesn't matter" and "crime measured 147× too
coarsely doesn't matter" are different claims, and I'd only tested the second.

So I refit six crime designs — borough vs neighbourhood grain, count vs rate, whole vs split by
category — each under five random seeds, with each gain paired within its own seed:

| Crime design | MdAPE mean | Gain | Seeds won |
|---|---:|---:|---:|
| No crime | 12.153 % | — | 0 / 5 |
| Borough count (status quo) | 12.136 % | +0.017 pp | 4 / 5 |
| **LSOA by category (best)** | 12.069 % | **+0.084 pp** | 3 / 5 |

The best design still fails the gate. More importantly, it fails a second bar: the **seed noise
floor** — the mean standard deviation of one design across seeds — is 0.097 pp, and this
design's own gain has a standard deviation of 0.187. The effect is smaller than the noise it was
measured through. This experiment cannot resolve it at all.

Verdict: crime does not earn the window. Measured 147× more finely, normalised, and split by
category, it still didn't clear. The next iteration drops it and widens to 1995–2024 — roughly
five times the data.

That's a null result I'm confident in, precisely because the gate and the noise floor were
fixed *before* the numbers came in.

---

## The strongest feature was in the file the whole time

The third finding is the most humbling.

The source file is a price **history**, not a transaction list — 418,201 rows covering 137,760
unique addresses, of which 66 % sold more than once. Within the modelling window, **61.1 % of
sales have an earlier sale of the same property**, typically about seven years prior.

The first version of this pipeline used none of it. It read a price history as a transaction log.

Every other feature asks *what is a property like this worth?* A prior sale asks a different and
far easier question: *what was this exact property worth last time, and how far has the market
moved since?* Quality, layout, street and lease are all held fixed between the two observations
— the logic behind the repeat-sales index literature going back to Bailey, Muth and Nourse
(1963).

Measured on the same gate and protocol as crime:

| Prior-sale design | Gain vs. none | Seeds won |
|---|---:|---:|
| Prior price only | +0.453 pp | 3 / 3 |
| **Prior price + elapsed time** | **+0.913 pp** | 3 / 3 |
| All six candidate columns | +0.894 pp | 3 / 3 |

Six times the gate, winning on every seed — against crime's +0.084 pp with a standard deviation
larger than its mean.

And note the middle row. The prior *price* alone is worth +0.45 pp. Adding *when* that sale
happened doubles it. **A past price is only interpretable against how long ago it was paid**:
£400k in 2009 and £400k in 2015 say very different things about what a property is worth now.

Row three is a useful negative: carrying all six candidate columns scored *worse* than carrying
four. `log_prev_sale_price` earned nothing, because a tree splits on order and the log of a
column it already holds is the same ordering.

The largest gain in the entire project came from re-reading data I already had.

---

## Making it actionable: a floor, not an estimate

A point estimate is not something you can spend money on. It carries no statement of how wrong
it might be.

So the last step wraps the prediction in a **one-sided conformal floor**. On a calibration split
that nothing else touches, compute the ratio of actual to predicted price for every property,
take the 10th percentile, and use it as a multiplier:

```python
r     = actual / predicted        # calibration split only
q_10  = quantile(r, 0.10)         # -> 0.7674
floor = predicted * q_10          # flag when price < floor
```

Ratios rather than differences, because errors in this market are heteroscedastic — a £3 M house
misses by far more pounds than a £200k flat while being no less accurate in percentage terms. A
single absolute quantile would be far too loose at the bottom and far too tight at the top.

Only the lower tail is kept. A screen for underpriced property cares about the floor, not the
ceiling.

*[FIGURE: c73_flip_margins.png — margin distribution and the floor line]*

On the held-out test set the floor covers **86.61 %** of sales against its 90 % target, flagging
1,186 of 8,859 properties with a median margin of £66,124 below their floor.

I'm reporting that shortfall rather than correcting it. Conformal prediction assumes calibration
and test data are exchangeable, and a chronological split does not guarantee that — the market
drifted between the two windows. Correcting the multiplier against the test set would turn test
into a tuning signal, which is the one thing holding it out was meant to prevent. On a held-out
slice of the *calibration* split, where exchangeability does hold, coverage is 88.39 %.

---

## What this still isn't

The scanner evaluates completed sales, not listings anyone can buy. A "flip candidate" is a
statistical claim, not a financial one — it says nothing about stamp duty, refurbishment, or
*why* a property is cheap, and properties are usually cheap for a reason the data doesn't
record. Lease length, above all: a leasehold flat with 70 years left is worth materially less
than an identical one with 950, and that column simply isn't in the dataset.

Coverage is marginal, not conditional — roughly 90 % overall doesn't guarantee 90 % inside any
one borough. And 23.8 % of test rows are properties that also appear in training, because the
split cuts on time, not on property; on genuinely unseen stock the error is 14.30 % rather than
12.75 %.

---

## The takeaway

If your gradient-boosted trees are losing to a linear baseline on tabular data, don't reach for
a bigger model. Check whether your target is stationary over the split you're evaluating on.
Trees interpolate; they cannot extrapolate a trend. If the thing you're predicting drifts, give
them something that doesn't.

And before you add another model, re-read the data you already have.

---

*Code and the full notebook: [github.com/…](https://github.com) · All figures are original,
generated from the analysis described.*

---
---

# HOW TO PUBLISH THIS ON MEDIUM
*(delete this whole section before publishing — it is notes to you, not part of the post)*

## 1. Medium does not support tables

This is the main gotcha. The six tables above are already rendered as images in
`figures/blog/`. Upload them at the marked points and delete the markdown table.

| Where in the post | Image |
|---|---|
| The opening val/test/drift table | `figures/blog/table1.png` |
| Signed-residual diagnostic | `figures/blog/table2.png` |
| "Here is what it bought" | `figures/blog/table3.png` |
| Target-transform comparison | `figures/blog/table4.png` |
| Crime designs | `figures/blog/table5.png` |
| Prior-sale designs | `figures/blog/table6.png` |

## 2. The four analysis figures

Upload at the `*[FIGURE: ...]*` markers, then delete the marker line:

- `figures/c48_leaderboard.png` — validation leaderboard
- `figures/c28_within_borough.png` — the crime confound
- `figures/c60_ablation.png` — feature-group ablation
- `figures/c73_flip_margins.png` — the conformal floor

Give each one a caption in Medium (click the image, type below it). Captions matter for
accessibility and Medium surfaces them in previews.

## 3. Pasting

Medium does **not** convert pasted markdown. Two options:

- **Paste plain, then format.** Headings: type `## ` at the start of a line and Medium converts
  it live. Bold: select and Ctrl/Cmd-B. Code blocks: type ``` on a new line and press Enter.
- **Import instead.** Push this file to GitHub Pages or any public URL, then use Medium's
  *Import a story* (medium.com/p/import) and paste the URL. Formatting survives better, and
  Medium marks the original as canonical so you do not compete with yourself on search.

## 4. Before you hit publish

- Replace the GitHub link at the foot with your actual repo URL.
- Add your byline and a one-line bio.
- Tags (max 5): `machine-learning`, `data-science`, `gradient-boosting`,
  `conformal-prediction`, `real-estate`.
- Subtitle: Medium uses the first line after the title as the preview — the italic line is
  already written for that.
- **Check the Kaggle dataset licence.** The rest of the sources are UK Open Government Licence
  and fine to describe and cite; confirm `kaggle_london_house_price_data.csv` permits what you
  are doing before you publish, and credit every source.

## 5. Then submit to Towards Data Science

TDS is independent of Medium now. Submit through their contributor form
(`contributor.insightmediagroup.io`); they aim to respond within a week, and they accept work
previously published on a personal blog — so publishing on Medium first does not disqualify you.
You will need a real name, photo and bio on your profile, and their rules require that the data
and code permit commercial use.
