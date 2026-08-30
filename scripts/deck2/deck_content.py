# -*- coding: utf-8 -*-
"""Slide content for presentation.pptx. Every number is copied from london_flip_finder.ipynb
outputs, or from the faithful re-run (scripts/deck2/rerun.log) for the cells whose stored
output the notebook lost at cell 67. Marked **bold** spans render as the slide's one
emphasised value."""

F = "figures/"

MAIN = [
# ---------------------------------------------------------------- 1
dict(layout="title",
     title="London Flip Finder",
     subtitle="Finding London homes that sold for less than they were worth — "
              "and putting a number on how much confidence that claim deserves",
     course="Applied Data Science 83901 · Bar-Ilan University · 2026",
     authors="[ student names — send me the three and I will set them ]",
     meta="59,946 transactions · 2008–2016 · four public sources · "
          "28 features · 14 models",
     notes="Open with the product, not the model: the deliverable is a screen that flags a "
           "sale as a flip candidate only when its price falls below a calibrated floor, not "
           "a point estimate of value. Deliberately hold the results back — the strip along "
           "the bottom states scope only, and no accuracy figure appears until slide 16. "
           "Say what the talk will do rather than what it found: value London sales from "
           "2008 to 2016, then put a floor under each estimate. The data is British and the "
           "vocabulary is defined in the notebook's second cell — offer to define borough, "
           "LSOA, tenure and outcode on demand rather than up front, and do not assume the "
           "room knows what leasehold means. Next slide states the work in five lines. "
           "Source: notebook cell 0."),
# ---------------------------------------------------------------- 2
dict(layout="bullets", kicker="OVERVIEW & MOTIVATION",
     title="A buyer sees the asking price but not the value — and cannot tell them apart",
     bullets=["Nobody values a home from floor area and a postcode",
              "A point estimate is not actionable; a buyer needs a floor",
              "Flag a sale only when its price falls below that floor",
              "'Looks cheap' becomes a quantified margin of safety"],
     notes="Set the business problem before any method, and assume the room did not see "
           "the proposal. A sale record on its own tells you very little: floor area, a "
           "few room counts, freehold or leasehold, property type, an energy rating, a "
           "postcode and a price. Nobody values a home from that alone — what a buyer "
           "actually brings to the question is context, and assembling that context is "
           "most of the work in this project. The motivation is the second half: even a "
           "good valuation is not something you can act on, because a point estimate "
           "carries no statement of how wrong it might be. What an investor needs is a "
           "floor — a value the property is very unlikely to be worth less than — so that "
           "a decision to spend money comes with a quantified margin of safety attached. "
           "That reframing is what turns this from a price-prediction exercise into a "
           "screen someone could actually use, and it is why section 15 exists at all. "
           "Next slide: what we actually built. Source: notebook cell 0."),
# ---------------------------------------------------------------- 3
dict(layout="bullets", kicker="WHAT WE DID",
     title="A sale record is thin, so the work was assembling context around it",
     bullets=["The record gives floor area, rooms, tenure, type, postcode",
              "We joined four public sources into one 59,946-row table",
              "Built 28 leakage-safe features, including each property's prior sale",
              "Trained 14 models on a chronological split",
              "Then wrapped each estimate in a price floor"],
     notes="This is the whole project in five lines, before any detail and before any "
           "result. Start from the first bullet: a sale record carries floor area, a few "
           "room counts, freehold or leasehold, property type, an energy rating and a "
           "postcode — nobody values a home from that alone. What a buyer actually brings "
           "is context, and assembling it is most of the engineering here: how far the home "
           "is from a station and how central that station is, which borough it sits in, "
           "what crime the neighbourhood recorded beforehand, what the market was doing in "
           "the run-up, what the central-bank rate was on completion day, and what the "
           "property itself last sold for. The fourth and fifth bullets are the modelling "
           "and the product: fourteen models trained on a time-ordered split, and then a "
           "floor placed under each estimate so a sale is flagged only when its price falls "
           "below it — that is the difference between 'this looks cheap' and a claim with a "
           "margin of safety attached. Deliberately no accuracy numbers yet; they start at "
           "slide 16 and are summarised at slide 27. Next slide is the map of how we get "
           "there. Source: notebook cells 0 to 2."),
# ---------------------------------------------------------------- 4
dict(layout="bullets", kicker="INITIAL QUESTIONS",
     title="Three questions we started with — and how two of them changed",
     bullets=["What is a property worth, given its context?",
              "Can we flag sales below a ~90 % floor?",
              "Does neighbourhood crime price into London property?",
              "Crime became: a verdict on crime, or on resolution?",
              "New: why do trees lose to a linear baseline?"],
     notes="The rubric asks what we set out to answer and how it evolved, and this project "
           "has an unusually clear answer on both counts. The first two questions never "
           "changed: what is this property worth, and can we put a floor under that "
           "estimate which holds at a stated rate. The third is where the project moved. "
           "Crime started as a feature we assumed would matter — and it is the reason the "
           "modelling window stops in 2016, because the crime file ends there, which costs "
           "81 % of the available sale records. When crime measured as worth almost "
           "nothing, the question sharpened rather than closing: was that a verdict on "
           "crime, or on the fact that 4,835 LSOAs had been aggregated into 33 boroughs? "
           "Sections 8.2 and 14.5 exist to answer that fairly. Two questions arrived "
           "mid-project that we did not start with. First, why do gradient-boosted trees "
           "lose to a linear baseline on tabular data, which is backwards — that becomes "
           "section 12.1 and the largest result in the project. Second, once we noticed "
           "the source file is a price history rather than a transaction log, what is a "
           "property's own past sale worth as a feature — section 14.6. The Final Analysis "
           "slide returns and answers all of these explicitly. Source: notebook cells 0, "
           "25, 31 and 42."),
# ---------------------------------------------------------------- 5
dict(layout="bullets", kicker="RELATED WORK",
     title="Where each idea comes from — no ingredient here is new on its own",
     bullets=["Rosen 1974, hedonic prices — the framing of §5–§9",
              "Bailey, Muth & Nourse 1963, repeat sales",
              "Gibbons 2004, London crime — predicts our small effect",
              "Lei et al. 2018, split conformal — lower tail only",
              "Romano et al. 2019, conformalized quantile regression"],
     notes="What is specific to this project is the combination: a hedonic model of London "
           "stock in 2008 to 2016, given the property's own sale history, wrapped in a "
           "one-sided calibrated floor so the output is a screen a buyer can act on rather "
           "than a point estimate. Rosen prices a differentiated good as a bundle of "
           "measured attributes each carrying an implicit price, which is exactly what the "
           "feature set is; the tree models just drop the linear-in-attributes assumption. "
           "The repeat-sales idea is used in opposite directions in the same project: "
           "section 12.1 divides out the market level to get a stationary target, and "
           "sections 8.3 and 14.6 feed the previous sale price back in as a feature. "
           "Gibbons is the closest prior work — a hedonic study of London specifically, "
           "finding that criminal damage capitalises into prices at roughly 1 % per tenth "
           "of a standard deviation in Inner London while burglary does not — so it "
           "predicts what we find, a real but small and category-dependent effect, and is "
           "worth citing as the reason the crime block earns so little once location is "
           "already in the model. Lei et al. is the reference treatment of split conformal "
           "prediction, which section 15 adapts with a ratio nonconformity score, keeping "
           "only the lower tail. The Zillow Prize is the practitioner reference point, in "
           "the backup slides; its error rates are explicitly not comparable — different "
           "market, no listing data, every transaction scored. Source: notebook cell 82."),
# ---------------------------------------------------------------- 6
dict(layout="diagram",
     kicker="ROADMAP",
     title="Seven phases, and one rule that governs every design decision",
     notes="This is the map for the next twenty minutes; point at it again when the talk "
           "changes phase. Setup and Data build one modelling table from four raw sources; "
           "Exploration asks what actually moves price; Features and Split decide what the "
           "model may see; Models and Decision train, rank and score; Assurance is what is "
           "asserted and what is still wrong. The rule along the bottom is the one line that "
           "nearly every later decision follows from — the shifted rolling medians, the "
           "chronological split, the strictly-prior sale lookup and the separate calibration "
           "slice are all consequences of it. Note that the phase numbering is the notebook's "
           "own, so any slide can be traced straight back to a section. Source: notebook "
           "cell 2, the phase table."),
# ---------------------------------------------------------------- 7
dict(layout="table", kicker="§4 · THE SOURCES",
     title="Four sources, four different grains — and one column that is refused",
     table=dict(headers=["Source", "Grain", "Rows"],
                rows=[["Land Registry price history", "one sale event", "418,201"],
                      ["Met Police crime", "LSOA × category × month", "13,490,604"],
                      ["Bank of England base rate", "one rate change", "246"],
                      ["TfL stations (Feb 2022 snapshot)", "one station", "471"],
                      ["GLA boundaries", "one borough polygon", "33"]],
                widths=[4.6, 4.2, 2.4]),
     bullets=["saleEstimate_* is never read — a rival model's output leaks the target",
              "Crime is read twice: borough grain to model, LSOA grain to test"],
     notes="Start with the shapes, because the grains are what make the merge non-trivial: "
           "nothing here is one row per property. The price history is one row per sale "
           "event, so a flat sold three times contributes three rows — that fact drives "
           "section 8.3, the repeat-property diagnostic and the strongest feature block in "
           "the model. Crime arrives at LSOA by category by month, 13.5 million rows, which "
           "has to be aggregated before it can join anything. The base rate is 246 rows "
           "total, a sparse list of change dates that has to be expanded. Stations and "
           "borough boundaries are geometry, with no key in common with a sale at all — "
           "they can only be joined spatially. The refused column matters: the source file "
           "ships saleEstimate_* and rentEstimate_*, another company's valuation model "
           "output for the same property, and using it to predict price would be leakage "
           "dressed up as a feature, so load_raw never reads those columns. Crime is "
           "deliberately read twice, at borough grain for the pipeline and at its native "
           "LSOA grain for section 8.2, which asks whether the borough aggregation threw "
           "the signal away. Next slide: what each source has to become before it can join. "
           "Source: notebook cells 9 and 10."),
# ---------------------------------------------------------------- 8
dict(layout="figure_below", kicker="§5 · CLEANING", figure=F+"new_cleaning_funnel.png",
     title="Each source is reshaped before it is allowed to join",
     bullets=["Crime: summed to borough-months, then rolling(12, closed='left')",
              "Rates: 246 changes expanded to 3,288 daily rows",
              "**Forward-fill only** — an earlier .bfill() leaked rates backwards"],
     notes="Three independent pure transforms, each taking one raw frame and returning a "
           "tidy one, with no cross-source joining yet. Houses is restricted to the window "
           "and gains total_rooms; rows with neither floor area nor room count are dropped, "
           "taking 82,122 in-window rows to 79,815. Crime is grouped to borough-months and "
           "gains a trailing twelve-month sum computed with closed='left', which excludes "
           "the current month so the window is strictly historical — 3,564 borough-months "
           "across 33 boroughs. The rate curve is the one to dwell on, because it carries a "
           "real bug that was found and fixed. The 246 change dates are expanded onto a "
           "daily calendar so every sale can match the rate in force on the day it "
           "completed. An earlier version called .bfill() to fill the leading gap, which "
           "propagated the first in-window rate backwards over every preceding day — "
           "stamping a rate onto dates before it had been announced. Forward-fill alone "
           "cannot look ahead. The fix seeds row zero from the last change at or before the "
           "window opens and then forward-fills only; where no prior rate exists the "
           "leading days stay NaN and each model imputes from training data rather than "
           "from the future. That is the shape of nearly every decision in this project. "
           "Source: notebook cells 11 and 12."),
# ---------------------------------------------------------------- 9
dict(layout="joins", kicker="§6–§9 · THE MERGE",
     title="Six joins onto one spine — three of them deliberately lagged",
     joins=[("Underground + rail stations", "cKDTree, k=1  →  distance + fare zone", False),
            ("Borough and LSOA polygons", "gpd.sjoin, predicate='within'", False),
            ("Bank of England base rate", "exact key on date  (daily, forward-filled)", False),
            ("Met Police crime", "key on (month − 1, borough)", True),
            ("Borough £/m² level", "key on (month + 1, borough)", True),
            ("The property's own prior sale", "merge_asof, backward, no exact match", True)],
     bullets=["No shared key: three join on geometry, three on time",
              "Every time join is offset off the row's own month"],
     notes="This is the map of the merge, and the slide to come back to. The price history "
           "is the spine: every join adds columns to it and none of them adds rows. Read "
           "the middle column as the actual join key. The first three are unlagged because "
           "they are static — a station's location and a borough's boundary do not change "
           "within the window, and the base rate is matched to the exact completion date "
           "from an already-expanded daily calendar. The bottom three are lagged on "
           "purpose, and that is the whole leakage story in one place: crime joins on the "
           "month before the sale, the borough price level is stamped onto the following "
           "month, and the prior sale is an as-of merge that refuses an exact date match. "
           "Point out that no two sources share a key with the houses frame — stations and "
           "boundaries have no identifier in common with a sale at all, which is why three "
           "of the six are spatial joins rather than key joins. The next three slides take "
           "the k-d tree, the point-in-polygon join and the lagged keys in turn. Source: "
           "notebook cells 13 to 16, and cells 32 to 33 for the prior-sale merge."),
# ---------------------------------------------------------------- 10
dict(layout="code", kicker="§6 · SPATIAL JOIN 1",
     title="Nearest station by k-d tree, with the fare zone carried along free",
     code=["tree = cKDTree(np.c_[stations.geometry.x, stations.geometry.y])",
           "dist, idx = tree.query(np.c_[houses.geometry.x, houses.geometry.y], k=1)",
           "houses['distance_to_underground_m'] = dist",
           "houses['station_zone'] = stations['station_zone'].to_numpy()[idx]"],
     bullets=["EPSG:27700 first — degrees distort distance east–west",
              "The tree splits points on alternating axes; each query is O(log n)",
              "Avoids **32 M** comparisons: 80,000 properties × 400 stations",
              "query returns the neighbour's index, so its fare zone rides along"],
     notes="Two spatial joins in the pipeline, and this is the first. Everything is "
           "reprojected to the British National Grid before a single distance is computed, "
           "because at London's latitude a degree of longitude covers only about 62 % of "
           "the ground a degree of latitude does — measuring in degrees quietly squashes "
           "geography along the east-west axis. BNG is metric, so a distance of 1000 means "
           "a thousand metres in any direction. On the algorithm: a k-d tree recursively "
           "partitions the points, splitting on one coordinate axis at each level of depth, "
           "so a nearest-neighbour query descends to the leaf containing the query point "
           "and then only has to back up into sibling branches that could still hold "
           "something closer than the best found so far. That turns a linear scan of every "
           "station into a logarithmic descent. Brute-forcing 80,000 properties against 400 "
           "stations is 32 million distance calculations for no benefit. The fourth bullet "
           "is the part worth stealing: query returns both the distance and the index of "
           "the winning station, so attaching that station's fare zone costs one array "
           "lookup rather than a second join. The same function runs twice, once against "
           "the 270 Underground stations and once against all 399 heavy-rail stations, "
           "which is where the two distance features come from. A CRS mismatch raises "
           "rather than silently producing degrees. Source: notebook cells 13 and 14."),
# ---------------------------------------------------------------- 11
dict(layout="code", kicker="§6 · SPATIAL JOIN 2",
     title="Point-in-polygon puts every sale inside a borough and an LSOA",
     code=["gpd.sjoin(houses, boroughs[['NAME', 'geometry']],",
           "          how='left', predicate='within')"],
     bullets=["The same operation twice: 33 borough polygons, then 4,835 LSOAs",
              "predicate='within' tests containment, not proximity",
              "Boundary-line coordinates can match two polygons — the first is kept",
              "Sales outside the GLA boundary are dropped, never imputed"],
     notes="The second spatial join, and a different question from the first: not how far "
           "to the nearest thing, but which region contains this point. A point-in-polygon "
           "join tests each point against candidate polygons — in practice a bounding-box "
           "index narrows the candidates first, then containment is tested exactly. "
           "predicate='within' is doing real work in that line: the alternative predicates "
           "would match on intersection or proximity, which for a point on a boundary is a "
           "different answer. The same function runs twice against very different polygon "
           "counts, 33 boroughs for the model and 4,835 LSOAs for section 8.2 — that "
           "147-fold difference in resolution is the whole subject of the crime argument "
           "later. Two edge cases are handled rather than ignored. A property whose "
           "coordinates fall exactly on a boundary line can match two polygons and appear "
           "twice; the duplicate is detected and the first match kept, with a printed "
           "count. And sales that fall outside the GLA boundary entirely match nothing, and "
           "are dropped rather than imputed, because guessing a borough would put a "
           "fabricated location into a feature the model leans on heavily. Borough is then "
           "uppercased and stripped so it joins cleanly against the crime table's own "
           "borough strings. Source: notebook cells 13 to 16."),
# ---------------------------------------------------------------- 12
dict(layout="code", kicker="§7 · TIME JOINS",
     title="Three joins carry a deliberate offset so no row sees its own month",
     code=["crime_key = month_year - pd.DateOffset(months=1)",
           "df.merge(crime, left_on=['_crime_key', 'borough'],",
           "         right_on=['date', 'borough'], how='left')"],
     bullets=["Crime joins on (month − 1, borough), never the current month",
              "The borough £/m² level is stamped onto the following month",
              "Rates join on the exact date, from the forward-filled calendar",
              "Crime stays **NaN** through 2008 until 12 months accumulate"],
     notes="The three time joins, and the offset is the point of all of them. Crime is "
           "joined on a composite key of borough and a month key that has had one month "
           "subtracted from it, so a sale in June reads May's crime and can never read its "
           "own month. The LSOA-grain crime join uses the identical offset, so the two "
           "grains stay directly comparable when section 8.2 puts them head to head. The "
           "borough price level runs the same idea from the other side: the median price "
           "per square metre is computed per borough-month and then the period is "
           "incremented by one before the join, so each month's level is stamped onto the "
           "following month. Rates are the exception that proves the rule — they join on "
           "the exact completion date, which is safe only because the daily calendar they "
           "come from was built with a forward-fill that cannot look ahead. The last bullet "
           "is a deliberate non-decision: early-2008 rows have no twelve-month crime window "
           "behind them and stay NaN. Median-filling here would inject a statistic computed "
           "over the whole period, including the future, into the earliest rows; instead "
           "each model imputes on its own, the boosted trees natively and Ridge through a "
           "SimpleImputer fitted on the training split alone. Every join is a left join, so "
           "the row count never changes. Source: notebook cells 15 and 16."),
# ---------------------------------------------------------------- 13
dict(layout="figure_below", kicker="§8 · EDA", figure=F+"c18_price_clip.png",
     title="Price is right-skewed, which is why every model trains in log space",
     bullets=["Peak £250k–£300k, long tail; a few £20 M sales flatten the axis",
              "Charts clip at the 95th percentile — models see everything",
              "**Log space** makes the loss proportional at £200k and £2 M"],
     notes="The first of two exploratory slides, and it exists to justify a modelling "
           "decision rather than to describe the market. Two panels of the same price "
           "column: the full distribution on the left, clipped to the 95th percentile on "
           "the right, 59,946 properties becoming 56,966 in the clipped view. The x axis "
           "is price in pounds, the y axis a count of properties. On the left the entire "
           "market collapses into a single spike against the axis, because a handful of "
           "multi-million-pound sales stretch the range to £60 million; clipped, the same "
           "data resolves into a proper right-skewed distribution with a visible peak and "
           "shoulder. The shape underneath is identical — only legibility changes, which "
           "is why every other exploratory chart uses the clipped view, and why the "
           "comparison is shown rather than asserted. The modelling consequence is the "
           "third bullet: a squared-pound loss on the raw scale is dominated by the "
           "expensive tail, where one £3 M house outweighs thirty £100k flats, so every "
           "model trains on log1p(price) and inverts with expm1. Anticipated question: "
           "does clipping bias the model? No — it is a display choice in the plotting "
           "functions only. Source: notebook cells 17 to 21."),
# ---------------------------------------------------------------- 14
dict(layout="figure_below", kicker="§8.1 · EDA", figure=F+"c23a_tube_premium.png",
     title="Location dominates — and the location features are heavily collinear",
     bullets=["£960k within 250–500 m of a station, under £350k beyond 3 km",
              "Borough spans **5×** in median £/m²: £11,000 K&C to £2,300 Bexley",
              "floorAreaSqM and total_rooms correlate at r = 0.85"],
     notes="The second exploratory slide, and the one that sets up section 14.5. The x "
           "axis is distance to the nearest station in bands, the y axis mean price; the "
           "gradient is steep and monotone after the first band — note that the very "
           "closest band, 0 to 250 m, is not the most expensive, plausibly a shorter walk "
           "traded against living right next to the station itself. The borough figure is "
           "the centre-to-edge gradient of the city in one number: Kensington and Chelsea "
           "over £11,000 per square metre against Bexley at about £2,300. On the "
           "statistical methods considered: this section uses Pearson correlation over the "
           "numeric block, group medians for the categorical splits, quartile banding for "
           "crime, and in section 8.2 within-group de-meaning and a differenced panel, "
           "which are the two standard ways of stripping a confound without fitting a "
           "model. The third bullet is the flag to plant: floor area and total rooms "
           "correlate at 0.85, and borough, outcode, latitude, longitude and "
           "distance-to-centre all encode where, so expect the ablation to find that "
           "removing whole feature groups costs almost nothing. Everything here is a "
           "marginal association — a different question from whether a feature adds "
           "anything the others do not already carry. Backup slides hold the correlation "
           "matrix, the borough ranking, the log-log scatter and the rate panels. Source: "
           "notebook cells 22 to 24."),
# ---------------------------------------------------------------- 15
dict(layout="figure_below", kicker="§8.2 · EDA", figure=F+"c28_within_borough.png",
     title="Higher-crime neighbourhoods cost more, because both track the centre",
     bullets=["Borough grain sums 4,835 LSOAs into 33 — a 147× aggregation loss",
              "Re-measured at LSOA grain, as a rate, split by category",
              "Across boroughs r = +0.30, **within borough r = +0.00**"],
     notes="Both panels plot log median price per square metre against log crime density, one "
           "point per LSOA. On the left, raw across all boroughs, the fitted line slopes up "
           "at r = +0.30 — read naively, more crime means more money. On the right both "
           "variables are de-meaned within their own borough, and the relationship is gone: "
           "r = +0.00, a flat line through a formless cloud. The entire apparent association "
           "was which borough a property sits in. Explain why the re-measurement was "
           "necessary before the verdict: the pipeline sums 4,835 LSOA codes into 33 "
           "boroughs, a 147-fold loss that averages Hampstead together with Kilburn a mile "
           "away, and crime_volume is a raw count so a more populous borough scores high "
           "automatically — an LSOA count is already close to a per-capita rate because every "
           "LSOA holds roughly 1,500 residents. A second, independent check differences over "
           "time, asking whether LSOAs where crime fell saw faster price growth: r = −0.01 "
           "over 863 LSOAs. The choropleths that set this up, and the differenced scatter, "
           "are appendix slides. This is only the exploratory answer — slide 22 puts the same "
           "question to the fitted model. Source: notebook cells 25 to 30."),
# ---------------------------------------------------------------- 16
dict(layout="figure_below", kicker="§8.3 & §9 · THE FILE'S OWN HISTORY",
     figure=F+"new_repeat_share.png",
     title="The file is a price history, not a transaction list",
     bullets=["Median 6.9 years earlier (p10 2.2, p90 13.8)",
              "Four features: prev_sale_price, has_prev_sale, years_since, days_since",
              "merge_asof backward, by fullAddress, allow_exact_matches=False"],
     notes="This is the structural fact none of the charts surface, and it turns out to "
           "matter more than any of them. Removing the 24.5 % of rows that are exact "
           "duplicates leaves 314,895 distinct sales, and 66 % of addresses record two or "
           "more. Every other feature asks what is a property like this worth; a prior sale "
           "asks a much easier question — what was this exact property worth last time, and "
           "how far has the market moved since — with quality, layout, street and lease held "
           "fixed between the two observations. That is the logic of the repeat-sales index "
           "literature, Bailey Muth and Nourse 1963. History is read from the whole 1995 to "
           "2024 file rather than the modelling window, because a 2009 sale's previous sale "
           "is usually pre-2008 and clipping first would discard most of the signal. Strictly "
           "before is load-bearing and three things could break it: the 102,527 duplicate "
           "rows are removed first or an as-of merge can return the very row it is meant to "
           "predict, 779 same-day price conflicts are collapsed to their median, and "
           "assert_no_lookahead runs as a hard check here and again in the section 17 "
           "self-checks. The columns are 38.9 % missing by construction, which is informative "
           "missingness rather than a defect — has_prev_sale lets the model treat never sold "
           "before as its own case. Slide 23 measures what all this is worth. Source: "
           "notebook cells 31 to 34."),
# ---------------------------------------------------------------- 17
dict(layout="bullets", kicker="§9 · FEATURES",
     title="Every feature answers one question: would the buyer have known this?",
     bullets=["Rolling market medians: .shift(1) then roll, dropping this month",
              "lagged_borough_median_sqm stamped onto the following month",
              "Crime lags: prior month, plus 12-month sum, closed='left'",
              "Rates forward-filled daily — the rate on completion day",
              "avg_room_size ±∞ → **NaN, left NaN**; imputing here leaks"],
     notes="This is where most of the leakage risk in a property model lives, so every "
           "feature is built to answer one question. The shift-then-roll ordering is the "
           "important detail on the first bullet: the shift drops the current month before "
           "the rolling window opens, so a month's own median never informs its own "
           "prediction. The borough median per square metre is computed for a month and "
           "stamped onto the following one, for the same reason. Crime gets two lags and "
           "never contemporaneous data — the month immediately before the sale as a "
           "short-term safety signal, and a trailing twelve-month sum computed with "
           "closed='left' so the current month is excluded, as a stable reputation signal. "
           "The last bullet is the subtlest and worth dwelling on: total_rooms can be zero, "
           "so floor area divided by rooms yields plus or minus infinity, and those are "
           "converted to NaN and deliberately left as NaN. Filling them with the column "
           "median here would leak, because this function runs on the whole table before the "
           "split, so the median would be computed over validation, calibration and test rows "
           "and baked into a training feature. Small, but real. Imputation is deferred to "
           "each model, inside a pipeline fitted on the training split alone; gradient-boosted "
           "trees handle NaN natively. Also built here: days_since_start and a sine-cosine "
           "encoding of calendar month so December and January end up adjacent. Source: "
           "notebook cells 11, 12 and 32 to 34."),
# ---------------------------------------------------------------- 18
dict(layout="table", kicker="§10 · PARTITION",
     title="Split by time, and give calibration a slice of its own",
     table=dict(headers=["Split", "Rows", "Date range"],
                rows=[["train", "35,967", "2008-01-01 → 2014-04-17"],
                      ["val", "8,991", "2014-04-17 → 2015-04-30"],
                      ["calib", "5,994", "2015-04-30 → 2015-12-17"],
                      ["test", "8,994", "2015-12-17 → 2016-12-31"]],
                widths=[2.4, 2.0, 4.6]),
     bullets=["Cut 60/15/10/15 by date, never at random",
              "Evaluation universe fixed at ≤£4M: **8,840/5,916/8,859** rows",
              "Only training varies: raw 35,967, capped 35,693, cleaned 35,075"],
     notes="The split is by time, not at random, because a random split would let the model "
           "learn from June 2016 to predict January 2016 — a situation that never occurs in "
           "production. Sorting by date and cutting sixty, fifteen, ten, fifteen reproduces "
           "the real task: train on the past, forecast the future. Calibration gets its own "
           "slice because one validation set cannot serve early stopping, model selection and "
           "conformal calibration at once without the 90 % guarantee being partly calibrated "
           "on data the model was already tuned against — that is circular. The evaluation "
           "universe is fixed for every model: validation, calibration and test rows under "
           "the £4 M cap, so leaderboard differences reflect the model and its training data "
           "and never a shifting denominator. Only the training data varies across the three "
           "variants — and IsolationForest, which flags 618 anomalies at a 2 % target rate, "
           "is fitted on the training slice and filters only that, because dropping flagged "
           "rows everywhere would be marking your own exam after removing the difficult "
           "questions. Dropped to the appendix: the encoding, where categorical levels are "
           "pinned from training and coercing those four columns with pd.to_numeric would "
           "silently blank all of them. Anticipated question: why validation before "
           "calibration in time? It was tested both ways and kept because it gives smaller "
           "validation-to-test drift for the tree models — and section 18 discloses that this "
           "comparison was itself made by scoring on test. Source: notebook cells 35 to 38."),
# ---------------------------------------------------------------- 19
dict(layout="bullets", kicker="§11 · DECISION RULES",
     title="The metric and the gates are fixed before any model runs",
     bullets=["Headline metric MdAPE — robust to the tail dominating MAE",
              "Model selection: lowest validation MdAPE, never test",
              "Feature-group gate ABLATION_GATE_PP = **0.15 pp**",
              "Seed-noise floor: a gain must exceed 2× mean sd",
              "Coverage target 90 %; every model trained in log space"],
     notes="Nothing is trained yet. This section fixes the three things that must be settled "
           "before any model runs, because deciding them afterwards is how a project talks "
           "itself into a result: what each model optimises, what everything is scored on, "
           "and what rule decides the winner. MdAPE is the median of absolute percentage "
           "errors; MAE is reported in pounds and is intuitive but is dominated by the "
           "expensive tail, where a 10 % miss on a £3 M house contributes thirty times more "
           "than the same miss on a £100k flat even though both are equally wrong in the only "
           "sense the buyer cares about. One regression_metrics implementation is used "
           "everywhere — near-identical variants defined across several cells are how a "
           "leaderboard silently mixes two spellings of one metric. The 0.15 pp gate is "
           "defined in the config cell rather than at its point of use, because two separate "
           "studies consume it and both must apply the same bar. The seed-noise floor is the "
           "second bar and it does real work on slide 22. The standing protocol: decisions "
           "read validation, test is read only to report — and section 18 records the two "
           "points where that was not followed. Source: notebook cell 39."),
# ---------------------------------------------------------------- 20
dict(layout="table", kicker="§11–§12 · WHAT WAS TRAINED",
     title="Fourteen models, five families — and what each one optimises",
     table=dict(headers=["Model", "Trained on", "Objective"],
                rows=[["Ridge (baseline)", "log1p(price)", "squared error, alpha=1.0"],
                      ["XGBoost (plain)", "log1p(price)", "reg:squarederror"],
                      ["CatBoost (plain)", "log1p(price)", "MAE"],
                      ["XGBoost detrended", "log(price / market level)", "reg:absoluteerror"],
                      ["CatBoost detrended", "log(price / market level)", "MAE"]],
                widths=[3.3, 3.5, 3.6]),
     bullets=["Each family trained on raw, capped and cleaned variants",
              "Plus luxury-routing MoE and 3-seed ensembles, on both targets",
              "**No neural network**: ~60k tabular rows, no text, images or sequence"],
     notes="This is the full roster before any result is shown. It is a ladder, not fourteen "
           "guesses: each rung exists because the rung below it failed in a specific, "
           "diagnosable way. Ridge is the baseline — closed-form and hard to overfit, and a "
           "baseline should not need tuning to be fair; it doubles as a sanity check, because "
           "if a gradient-boosted ensemble cannot beat a straight-line model on tabular data "
           "of this shape then the problem is the setup, not the architecture. XGBoost and "
           "CatBoost on log price are the standard answer for tabular hedonic data, CatBoost "
           "specifically for native categorical handling of property type, tenure, borough "
           "and outcode. Rows four and five are the detrended target that slide 15 explains — "
           "mention it forward, do not explain it yet. Note the objective column carefully: "
           "XGBoost moves to absolute error because squared error in log space fits the "
           "conditional mean while the reported metric is a median, and CatBoost is left on "
           "MAE unchanged, which isolates whether the deflator or the objective is doing the "
           "work. The neural-network omission is deliberate and worth stating: sixty thousand "
           "rows of tabular data with no free text, images or sequence structure is where "
           "gradient-boosted trees win. Every trainer returns the same ModelBundle.predict "
           "signature, which is what lets the leaderboard, the test evaluation and the "
           "conformal calibration all run through one code path. Source: notebook cells 39, "
           "41 and 43."),
# ---------------------------------------------------------------- 21
dict(layout="table", kicker="§12.1 · THE FAILURE",
     title="A tree's leaf is a constant, so it cannot follow a rising market",
     table=dict(headers=["Model (validation)", "Mean residual", "Median residual",
                         "Under-predicted"],
                rows=[["XGBoost (capped)", "£74,679", "£38,198", "70.4 %"],
                      ["XGBoost detrended-market", "£24,331", "£8,626", "54.8 %"],
                      ["Ridge (baseline)", "£51,754", "£36,073", "65.6 %"]],
                widths=[4.0, 2.5, 2.5, 2.4]),
     bullets=["On test the plain boosters score 19.57–20.25 % against Ridge's 16.62 %",
              "Beyond the training range every row lands in the same boundary leaf",
              "Predicted signature: a large **positive** mean residual, not noise"],
     notes="Start with the anomaly: gradient-boosted trees are normally the stronger choice "
           "on tabular data of this shape, so a plain Ridge regression beating them reads as "
           "a symptom, not a verdict on the architecture. The mechanism is structural. A "
           "tree's prediction is a constant per leaf, so once a trending feature such as "
           "days_since_start or market_median_rolling_3m exceeds anything seen in training, "
           "every such row lands in the same boundary leaf and the model flat-lines at the "
           "last price level it learned. It cannot extrapolate a rising market. That "
           "mechanism makes a testable prediction — a large, one-directional positive mean "
           "residual, where residual is actual minus predicted — and the table measures "
           "exactly that, on validation only. Plain XGBoost under-predicts by a mean of "
           "£74,679 and under-predicts 70.4 % of rows. Be precise about what the table also "
           "shows: Ridge under-predicts too, by £51,754, because the market rose faster than "
           "any linear projection of its training window. So the accurate claim is not trees "
           "cannot extrapolate and Ridge can — it is that a non-stationary target biases every "
           "model here and punishes the trees hardest. What separates them is the size of the "
           "level error, not its presence. Crucially this is all measured on validation, so "
           "the fix on the next slide never required the test set. Source: notebook cells 42, "
           "44, 45 and 46."),
# ---------------------------------------------------------------- 22
dict(layout="code", kicker="§12.1 · THE FIX",
     title="Predict the ratio to the market, and the trees only interpolate",
     code=["# market_median_rolling_3m is the leakage-safe §9 column",
           "y = log(price / market_level)",
           "model.fit(X_train, y)",
           "price_hat = exp(model.predict(X)) * market_level"],
     bullets=["The ratio is near-stationary while the market itself trends",
              "Mean residual £74,679 → **£24,331**; XGBoost objective → reg:absoluteerror",
              "Two deflators enter the pool — slide 20 decides on validation"],
     notes="The fix does not make the trees better at extrapolating; it removes the need to "
           "extrapolate at all. Instead of predicting price, predict the ratio of price to "
           "the lagged whole-market median — a column that already exists from section 9 and "
           "is leakage-safe by construction. How much is this property worth relative to "
           "where the market already is, is close to stationary across time even while the "
           "market itself trends, so a tree only has to interpolate within the range of "
           "ratios it saw in training. The market level is multiplied back onto the "
           "prediction at inference. A second change rides along for XGBoost only, the move "
           "to absolute error, for the reasons on slide 12; CatBoost already trained with "
           "MAE, so leaving it alone isolates which of the two changes is doing the work. "
           "Emphasise that two deflator candidates enter the pool rather than one — the "
           "market-wide median and a borough-and-size-scaled alternative — and both are "
           "registered in train_all like every other model, so whichever wins validation "
           "becomes BEST and flows through the whole downstream. Slide 20 reports that "
           "head-to-head. Anticipated question: is dividing by a market median leakage? No — "
           "the median is shifted by one month before the rolling window opens, so it "
           "contains no information from the month being predicted. Source: notebook cells "
           "42 to 46."),
# ---------------------------------------------------------------- 23
dict(layout="figure_below", kicker="§13 · VALIDATION", figure=F+"c48_leaderboard.png",
     title="Every detrended model outranks every plain one",
     bullets=["Top: CatBoost detrended-market (cleaned) at **11.94 %** validation MdAPE",
              "Ridge 17.09 %; the detrended family sweeps positions one to six",
              "Luxury-routing MoE 12.49 % loses to its own 3-seed control, 12.12 %",
              "Built from the results registry, so the table cannot disagree"],
     notes="Fourteen models ranked by validation MdAPE on the left, mean absolute error on "
           "the right, both lower-is-better, every model scored on the same 8,840 validation "
           "rows. The single largest effect in the whole leaderboard is the block structure: "
           "every model trained on log price over market level outranks every model trained "
           "on log price, which confirms section 12.1 diagnosed the right problem. Point out "
           "that the two panels do not agree on ordering — they answer different questions, "
           "typical percentage miss versus average pound miss, the latter dominated by "
           "expensive properties. Selection uses MdAPE as fixed on slide 12; MAE is reported "
           "so the disagreement is visible rather than hidden. The table is generated from "
           "the results registry, where every row was appended by evaluate() at training "
           "time, so the leaderboard cannot disagree with what the models actually scored — a "
           "hand-assembled table typed into a DataFrame literal carries no such guarantee. "
           "Whichever model tops this table becomes BEST, and nothing has read the test split "
           "yet. The full fourteen-row table with R2 and within-25 % is an appendix slide. "
           "Source: notebook cells 47 to 49."),
# ---------------------------------------------------------------- 24
dict(layout="table", kicker="§14 · HELD-OUT TEST",
     title="Test costs every model 1.3–5.7 pp — and the winner is not the test winner",
     table=dict(headers=["Model", "Val MdAPE", "Test MdAPE", "Drift"],
                rows=[["3-seed average detrended (XGB)", "12.12 %", "13.62 %", "+1.50 pp"],
                      ["CatBoost detrended-market  ← selected", "11.94 %", "13.88 %",
                       "+1.94 pp"],
                      ["XGBoost detrended-market (capped)", "12.19 %", "13.88 %", "+1.68 pp"],
                      ["Ridge (baseline)", "17.09 %", "16.62 %", "−0.47 pp"],
                      ["XGBoost (cleaned)", "14.60 %", "20.25 %", "+5.66 pp"]],
                widths=[5.0, 2.1, 2.1, 2.1]),
     bullets=["The **0.26 pp** gap to the test winner is the selection effect",
              "Not corrected — revising here makes test a selection signal",
              "Plain boosters fall behind Ridge on test, confirming §12.1"],
     notes="The procedure is: pick the winner by validation MdAPE, then score on test; the "
           "gap between the two is the honest measure of how much validation performance was "
           "selection effect. Validation picked CatBoost detrended-market at 11.94 %, and it "
           "scores 13.88 % on test. The best test score belongs to the 3-seed average "
           "detrended at 13.62 %. That 0.26 pp gap is the selection effect made visible, and "
           "it is deliberately not corrected, because correcting it would mean choosing the "
           "deployed model on test — the one thing holding test out was meant to prevent. "
           "Every model drifts worse on test, which is expected because validation drove "
           "early stopping and its scores are optimistic by construction; the drift column is "
           "the size of that optimism. The last row is the confirmation of section 12.1: "
           "plain boosted trees land at 19.57 to 20.25 % against Ridge's 16.62 %, so the "
           "diagnosis was structural rather than a validation-set artefact. One number worth "
           "having ready: Ridge's test R2 is minus 180.118 against 0.539 on validation — a "
           "few catastrophic extrapolations on expensive properties, which is exactly why "
           "R2 is reported and never decided on. Near-ties at the top should not be "
           "over-read: where two models sit within 0.1 pp on validation, that gap does not "
           "reliably predict which wins on test. Full fourteen-row table in the appendix. "
           "Source: notebook cells 50 to 52."),
# ---------------------------------------------------------------- 25
dict(layout="table", kicker="§14.1 · DIAGNOSTIC",
     title="Is the headline number measuring valuation, or memorisation?",
     table=dict(headers=["Test subset", "Rows", "MdAPE", "MAE", "within 25 %"],
                rows=[["Seen in training", "2,112", "12.75 %", "£118,212", "79.97 %"],
                      ["Unseen property", "6,747", "14.30 %", "£137,644", "75.49 %"]],
                widths=[3.4, 1.7, 1.9, 2.3, 2.0]),
     bullets=["The split cuts on time, not property — **23.8 %** were seen",
              "Read the unseen number as generalisation to new stock",
              "Fix: a group-aware split keyed on fullAddress"],
     notes="The source file is a price history, one row per sale event, so a dwelling that "
           "changed hands three times between 2008 and 2016 contributes three rows. A "
           "chronological split cuts on time, not on property, which means a flat sold in "
           "2010 into training and again in 2016 into test appears on both sides of the wall "
           "— 2,112 of the 8,859 test rows. That is not automatically cheating: forecasting a "
           "known building's next sale price is a real business task and the lagged features "
           "remain strictly historical. But it does mean the headline test metric blends two "
           "different problems — re-valuing a property the model has already seen, and "
           "valuing one it never has — and the second number is the one that generalises to "
           "new stock. The gap is 1.54 percentage points, which is modest; if it were large "
           "the headline metric would be measuring memorisation as much as valuation. This "
           "matters more now than before section 9, because prior-sale features make the "
           "model explicitly better on exactly the repeat properties this diagnostic "
           "isolates — which is also the clearest single argument for why they work. The fix "
           "is improvement number one in section 18. Source: notebook cells 53 to 55."),
# ---------------------------------------------------------------- 26
dict(layout="table", kicker="§14.3 · TARGET TRANSFORM",
     title="The coarser deflator wins — a noisy divisor corrupts every label",
     table=dict(headers=["Target transform", "XGB val", "XGB test", "CatB val", "CatB test"],
                rows=[["regular  log(price)", "14.33 %", "19.92 %", "13.20 %", "18.03 %"],
                      ["detrended market-wide", "12.19 %", "13.88 %", "11.94 %", "13.88 %"],
                      ["detrended borough-scaled", "12.98 %", "14.32 %", "12.63 %", "16.00 %"]],
                widths=[4.2, 1.9, 1.9, 1.9, 1.9]),
     bullets=["Market-wide wins on validation for **both backends**, and on test",
              "The borough deflator uses far fewer sales per month",
              "As a divisor its noise enters the label directly"],
     notes="The open question from section 12.1: once a market-wide deflator fixes the "
           "extrapolation problem, does a more granular one do better — deflating by borough "
           "and property size rather than the whole market? The intuition says yes, a "
           "deflator built from genuinely comparable properties should carry more signal. The "
           "data says the opposite, for both backends, and by a wide margin for CatBoost on "
           "test. The explanation is on the last two bullets and it is the best "
           "transferable lesson in the project. The borough deflator, lagged_borough_median_sqm "
           "times floor area, is estimated from one borough's transactions in a three-month "
           "window rather than the entire city's thousands of sales. Because the deflator is "
           "a divisor, a noisier deflator injects that noise directly into every training "
           "label it divides, not merely into one more feature the model could choose to "
           "down-weight. And the coarser deflator costs nothing in borough- or size-specific "
           "signal, because borough, floorAreaSqM and the borough median all remain ordinary "
           "input features — the tree stays free to learn that a borough commands a premium, "
           "from uncorrupted labels. The general lesson: a detrending deflator should remove "
           "only what the architecture genuinely cannot learn on its own; anything the model "
           "can already learn from a feature should stay a feature, not get folded into the "
           "label. The winner was chosen on validation; the test columns are shown so you can "
           "judge whether the choice generalised, not so it could make the choice. Source: "
           "notebook cells 56 to 58."),
# ---------------------------------------------------------------- 27
dict(layout="figure_below", kicker="§14.5 · ABLATION", figure=F+"c60_ablation.png",
     title="Only the property's own history clears the gate",
     bullets=["Prior sales **+0.93 pp**; market lags +0.20, crime +0.11, transport +0.09",
              "Removing interest_rate improves the model — it is already in the target",
              "Ablates the shipped recipe on validation, because this decides something"],
     notes="The x axis is the cost in validation MdAPE percentage points of removing each "
           "feature group; a longer bar means the group was carrying more weight. The method "
           "matters: this retrains the winning recipe — XGBoost on the detrended target, "
           "capped variant — once per group, because ablating a plain-target model would "
           "measure feature value on a model already handicapped by something else. It is "
           "scored on validation, not test, because this study decides something, and "
           "although early stopping makes the absolute MdAPE optimistic, every variant "
           "carries the identical bias and the gate consumes only the delta. Prior sales at "
           "+0.93 pp is six times the next-largest group and the only one comfortably clear "
           "of the 0.15 pp gate. Now reconcile with the exploratory analysis, because three "
           "of the four external drivers slides 7 and 8 presented as important measure as "
           "worth roughly nothing here — that is not a contradiction, the two analyses answer "
           "different questions. Transport had a steep bivariate gradient but borough, "
           "outcode, latitude, longitude and distance-to-centre already encode where, so it "
           "is largely redundant given them. The base rate is one value per month shared by "
           "every row, which is exactly the market-level time trend the detrended target and "
           "the market lags already absorb, so what remains is noise and removing it helps. "
           "One caveat: market lags cannot be fully ablated, because the deflator keeps them "
           "in the label, so +0.20 pp is a lower bound. Source: notebook cells 59 to 61."),
# ---------------------------------------------------------------- 28
dict(layout="table", kicker="§14.5 · CRIME VERDICT",
     title="Crime fails at its best resolution too, so the window can widen",
     table=dict(headers=["Crime design", "Cols", "MdAPE mean", "Gain", "Seeds won"],
                rows=[["No crime", "0", "12.153 %", "+0.000 pp", "0 / 5"],
                      ["Borough count (status quo)", "2", "12.136 %", "+0.017 pp", "4 / 5"],
                      ["LSOA by category (best)", "4", "12.069 %", "+0.084 pp", "3 / 5"]],
                widths=[4.0, 1.2, 2.2, 2.0, 1.6]),
     bullets=["Six designs × five seeds, each gain paired within its seed",
              "Best gain **+0.084 pp**, under both the gate and the noise",
              "So drop crime and widen to 1995–2024 — roughly 5× data"],
     notes="This is the scoping decision the whole dataset size depends on. The crime file "
           "only covers 2008 to 2016, and that single constraint is why the modelling window "
           "stops there: 59,946 in-window sales against 314,895 distinct sales in the full "
           "history, so 81 % of the record is discarded to accommodate one feature block. The "
           "ablation on the previous slide removed borough-grain, unnormalised, all-category "
           "crime, so before acting on that verdict the same question is asked of crime "
           "measured properly — six designs over identical rows and an identical target, with "
           "only the crime columns moving. Two details make it a test rather than a "
           "formality: five seeds, because a single gradient-boosted fit cannot separate a "
           "0.1 pp effect from run-to-run variation, and each gain paired within its seed "
           "before averaging so seed-level variation cancels. The best design is LSOA grain "
           "split by category at +0.084 pp — better than borough grain, still below the gate, "
           "and more importantly below the noise it was measured through: the seed noise "
           "floor is 0.097 pp and this design's own gain standard deviation is 0.187 with "
           "only three of five seeds won. Both bars matter; a gain clearing the gate but not "
           "the noise floor would mean reading a decision off a number the experiment cannot "
           "resolve. Say the fairness point out loud: crime was not dismissed on a "
           "technicality. It was measured 147 times more finely, normalised, and split by "
           "category, and still did not clear. All six designs are in the appendix. Source: "
           "notebook cells 62 to 65."),
# ---------------------------------------------------------------- 29
dict(layout="table", kicker="§14.6 · PRIOR SALES",
     title="A past price is only interpretable against how long ago it was paid",
     table=dict(headers=["Prior-sale design", "Gain vs. none", "Seeds won"],
                rows=[["Prior price only", "+0.453 pp", "3 / 3"],
                      ["Prior price + elapsed time", "+0.913 pp", "3 / 3"],
                      ["Full six-column candidate set", "+0.894 pp", "3 / 3"]],
                widths=[5.2, 3.0, 2.6]),
     bullets=["**+0.913 pp** — roughly 6× the gate, and winning on every seed",
              "Adding when the sale happened doubles the value of the price alone",
              "log_prev_sale_price and n_prior_sales earn nothing and are dropped"],
     notes="Same protocol as the crime study — same 0.15 pp gate, seeds paired within run — "
           "so the two verdicts are directly comparable, and the contrast is stark: crime's "
           "best design scored +0.084 pp with a standard deviation larger than its mean, "
           "while this scores +0.913 pp with all seeds agreeing. The substantive finding is "
           "the middle row. Prior price by itself is worth about +0.45 pp; adding when that "
           "sale happened — years_since_prev_sale and prev_sale_days_since_start — takes it "
           "to +0.91. A past price is only interpretable against how long ago it was paid: "
           "£400k in 2009 and £400k in 2015 say very different things about what a property "
           "is worth today. The third row is the rejection: carrying all six candidate "
           "columns scores worse than carrying four, so log_prev_sale_price and n_prior_sales "
           "earn nothing — a tree splits on order, and the log of a column it already holds "
           "is the same ordering. This is the single largest modelling gain in the project, "
           "larger than any architecture choice and second only to the target reframing. "
           "Worth saying: these features were sitting in the source file from the beginning, "
           "and the pipeline read a price history as a transaction log for its entire first "
           "version — the largest wins often come from re-reading the data you already have. "
           "Caveat to disclose if asked: this cell errored in the notebook's last saved run, "
           "so the table is from a faithful re-execution that reproduces every other number "
           "in the notebook exactly. Source: notebook cells 66 to 69."),
# ---------------------------------------------------------------- 30
dict(layout="code", kicker="§15 · CONFORMAL",
     title="A point estimate is not actionable — the product is a floor",
     code=["r = actual / predicted            # on the calibration split only",
           "q_10 = quantile(r, 0.10)          # -> **0.7674**",
           "floor = predicted * q_10          # flag when price < floor"],
     bullets=["Ratios not differences: errors widen sharply with price",
              "Calibrated on its own slice — validation drove early stopping",
              "Lower tail only: a screen needs a floor, not a ceiling"],
     notes="A predicted price is not enough to justify spending money; what an investor needs "
           "is a floor, a value the property is very unlikely to be worth less than. "
           "Multiplicative split conformal prediction supplies one. On the dedicated "
           "calibration split of 5,916 properties, compute the ratio of actual to predicted "
           "price for every property, take the tenth percentile, and the floor for a new "
           "property is its prediction times that multiplier — here 0.7674, so the floor sits "
           "at about 77 % of the prediction. Why ratios rather than differences: absolute "
           "residuals in this market are heteroscedastic and errors widen sharply as price "
           "rises, so a £3 M house misses by far more pounds than a £200k flat while being no "
           "less accurate in percentage terms; a single absolute quantile would be far too "
           "loose at the bottom of the market and far too tight at the top, whereas the ratio "
           "form scales the buffer with the price so one calibration serves both tiers. Why "
           "calibration is not the validation set: split conformal assumes the calibration "
           "residuals were not used to fit the model, and validation was — for early stopping "
           "and architecture choice — so a model's iteration count is implicitly tuned to "
           "minimise error on exactly those rows and q_10 there would be optimistically "
           "tight. Only the lower tail is kept because a flip screen cares about the floor, "
           "not the ceiling, which is where this departs from the textbook two-sided "
           "interval. Source: notebook cells 70 to 72."),
# ---------------------------------------------------------------- 31
dict(layout="figure_below", kicker="§15 · THE SCAN", figure=F+"c73_flip_margins.png",
     title="The floor holds at 86.61 % on data it was never fitted on",
     bullets=["Target 90 %, empirical **86.61 %** on test — reported, not corrected",
              "1,186 of 8,859 flagged (13.39 %); median margin £66,124",
              "A flip rate is a screening rate, not a hit rate"],
     notes="Left panel: the distribution of margins below the floor across flagged "
           "properties, x axis pounds, y axis a count — right-skewed, so most flagged "
           "properties sit just below the floor and a few sit far below. That far tail is "
           "where the screen is most interesting and also where it is most likely picking up "
           "something the data does not record: a short lease, a structural problem, a "
           "distressed sale. Right panel: actual price against predicted value for all 8,859 "
           "scanned properties on log-log axes, with the calibrated floor drawn through it as "
           "a dashed line at 0.77 times the prediction; the orange points below the line are "
           "the candidates. The line is not a decision boundary the model learned — it is the "
           "conformal bound applied uniformly. Coverage is the number that validates the "
           "method: 86.61 % against a 90 % target, a 3.39 point shortfall. That is expected "
           "rather than alarming, because the market drifted between the calibration window "
           "and the test window, which is precisely the departure from exchangeability a "
           "chronological split cannot rule out. It is reported rather than corrected, "
           "because correcting it against test would turn test into a tuning signal. The "
           "self-checks assert coverage instead on a held-out slice of calibration, where it "
           "lands at 88.39 %. Be firm on the last bullet: a flagged property sold below a "
           "calibrated valuation floor, and that says nothing about why. Source: notebook "
           "cells 71 to 74."),
# ---------------------------------------------------------------- 32
dict(layout="table", kicker="RESULTS",
     title="13.88 % typical error — and the reframed target is what got there",
     table=dict(headers=["Result", "Figure"],
                rows=[["Selected model (chosen on validation)",
                       "CatBoost detrended-market — 13.88 % test"],
                      ["Ridge baseline", "16.62 % test"],
                      ["Plain gradient-boosted trees", "19.57–20.25 % test"],
                      ["Strongest feature group", "prior sale, +0.93 pp"],
                      ["Weakest feature group", "crime, +0.11 pp — below the gate"]],
                widths=[5.0, 6.4]),
     bullets=["The result is the target reframing, not the architecture",
              "Floor at ×0.7674 covers **86.61 %** against a 90 % target",
              "1,186 of 8,859 test sales fall below their own floor"],
     notes="This is the recap: everything the pipeline found, in one place, after the "
           "argument that earned it. Read the table top down. The selected model was chosen "
           "on validation MdAPE alone and scores 13.88 % on a test split nothing before "
           "section 14 had read. Ridge, the linear baseline, scores 16.62 %. The plain "
           "gradient-boosted trees land at 19.57 to 20.25 %, worse than the linear baseline "
           "— which is the anomaly the whole middle of the talk exists to explain. The "
           "bottom two rows are the scoping verdicts: a property's own prior sale is worth "
           "+0.93 pp and is the strongest block in the model, while crime is worth +0.11 pp "
           "and fails the 0.15 pp gate it had to clear to justify confining the window to "
           "2008-2016. The first bullet is the sentence to land: no architecture change "
           "moved the number as much as reframing the target from price to price relative "
           "to the market level. The last two bullets are the product: a floor at 0.7674 "
           "times the prediction, covering 86.61 % of held-out sales against a 90 % target, "
           "flagging 1,186 of 8,859. Next slide qualifies all of it. Source: notebook cell "
           "0, with the figures from cells 51, 60, 63 and 71."),
# ---------------------------------------------------------------- FINAL ANALYSIS
dict(layout="figure_below", kicker="FINAL ANALYSIS", figure=F+"new_coverage.png",
     title="Answering the three questions we opened with",
     bullets=["Value: 13.88 % typical error; 75.5 % of unseen within 25 %",
              "Crime: no — at LSOA grain, as a rate, split by category",
              "Learned: the file's own history beat any model choice"],
     notes="Close the loop the Initial Questions slide opened, in the same order. Question "
           "one, what is a property worth: the selected model reaches 13.88 % median "
           "absolute percentage error on a test split nothing before section 14 had read, "
           "and — the number that matters for generalisation — 75.5 % of properties the "
           "model had never seen before land within 25 % of their actual price. Question "
           "two, can we put a floor under that: yes, and it is checked rather than "
           "assumed. Empirical coverage is 86.61 % on test against a 90 % target, and "
           "88.39 % on a held-out slice of the calibration split that the multiplier was "
           "not fitted on. The shortfall on test is market drift between the calibration "
           "and test windows, reported rather than corrected because correcting against "
           "test would turn test into a tuning signal. Question three, does crime price "
           "in: no — and we can say that fairly, because it was re-measured 147 times more "
           "finely, normalised into a rate and split by category, and still failed both "
           "the 0.15 pp gate and the seed-noise floor. How we justify these answers: every "
           "decision was made on validation with the rule fixed in advance, test was read "
           "only to report, and the design studies were run under multiple seeds with "
           "gains paired within seed. The last bullet is the thing worth remembering — the "
           "largest single gain in the project came from re-reading data we already had, "
           "not from adding a model on top. Next slide is what this still is not. Source: "
           "notebook cells 51, 54, 63, 67, 71 and 80."),
# ---------------------------------------------------------------- 33
dict(layout="bullets", kicker="§18 · LIMITS AND NEXT",
     title="What this is not, and the two changes worth making first",
     bullets=["It scores completed sales, not listings anyone can buy",
              "Coverage is marginal, not conditional; not per borough",
              "The evaluation universe is defined using the target",
              "Next: split by property, keyed on fullAddress",
              "Next: drop crime, widen to 1995–2024 — **~5× data**"],
     notes="Close on the honest limits rather than the headline. The target is what a "
           "property actually sold for, so a sale below its floor in 2016 validates the "
           "valuation model but is not something anyone can act on; a live scanner needs a "
           "listings feed and a calibration step for the asking-to-sold gap, which is a "
           "different distribution. The flip flag is a statistical claim, not a financial "
           "one: it says nothing about stamp duty, refurbishment, financing, fees, or why the "
           "property is cheap — and properties are usually cheap for a reason the data does "
           "not record, a lease with few years left above all. Coverage being marginal means "
           "roughly 90 % of properties sit above the floor overall, which does not guarantee "
           "90 % inside any particular borough or price decile; Mondrian conformal is the "
           "named fix. The third bullet is the sharpest self-criticism in the project: both "
           "the £1,500 per square metre floor and the £4 M cap read price, so the reported "
           "MdAPE describes a population you could not actually select in production, where "
           "price is the unknown. Also worth mentioning: the window ends a decade ago and "
           "four shocks fall outside it — the Brexit referendum, the 3 % stamp-duty surcharge "
           "aimed squarely at this kind of purchase, the pandemic, and the 2022 rate cycle. "
           "The two next steps are ranked in the notebook; widening the window is described "
           "as almost certainly worth more than every other item combined. Backup slides "
           "cover the remaining six improvements, the live Rightmove scan, and the related "
           "work. Source: notebook cell 80."),
]

APPENDIX = [
dict(layout="figure_full", kicker="APPENDIX", figure=F+"c20_property_chars.png",
     title="A1 · Property characteristics and price, all four panels",
     notes="The full section 8 figure: price distribution clipped at the 95th percentile, "
           "price by total rooms, median price by property type, and the correlation matrix. "
           "Median price rises from about £320k at two rooms to roughly £950k at eight, but "
           "the boxes widen and overlap heavily at the top end — room count alone does not "
           "pin down price for larger properties. Detached properties top the median-price "
           "ranking at roughly double the cheapest terraced categories. In the correlation "
           "matrix, floorAreaSqM leads the positives at r = 0.57 and bathrooms at 0.52, while "
           "distance_to_center_m at −0.36 and distance_to_underground_m at −0.30 lead the "
           "negatives. The 0.85 between floorAreaSqM and total_rooms is the collinearity that "
           "slide 21 cashes in. Source: notebook cell 20."),
dict(layout="figure_full", kicker="APPENDIX", figure=F+"c26_lsoa_maps.png",
     title="A2 · The confound, mapped: price and crime at LSOA grain",
     notes="Two choropleths of Greater London at LSOA grain, price per square metre on the "
           "left in blue and recorded crime density on the right in orange, one hue each so "
           "the panels cannot be misread as sharing a scale. 2,562 of the 2,863 Greater "
           "London LSOAs record at least five sales in the window and are used here. Both "
           "maps run darkest in the middle: central London is simultaneously the most "
           "expensive and the most crime-recording part of the city, so the raw association "
           "comes out positive and naively more crime looks like more money. This is the "
           "confound the within-borough de-meaning on slide 8 removes. Source: notebook "
           "cells 26 and 27."),
dict(layout="figure_full", kicker="APPENDIX", figure=F+"c29_crime_change.png",
     title="A3 · The differenced view: crime change against price growth",
     notes="A second, independent route to the same verdict. The x axis is the percentage "
           "change in monthly crime for an LSOA between 2008-2010 and 2014-2016; the y axis "
           "is that LSOA's growth in median price per square metre over the same period; "
           "colour encodes the crime change again. Differencing removes every fixed feature "
           "of a place at once — architecture, parks, distance to the centre, reputation — "
           "and asks a sharper question: did the LSOAs where crime fell see faster price "
           "growth than the ones where it rose? The fitted line is flat, r = −0.01 over 863 "
           "LSOAs. Whatever the raw scatter measures, it is not crime. Source: notebook "
           "cells 29 and 30."),
dict(layout="figure_full", kicker="APPENDIX", figure=F+"c23b_crime_and_market_0.png",
     title="A4 · The chart that started §8.2: price by crime band",
     notes="Median price climbs from the Low band through to Severe, topping out over £470k "
           "against roughly £390k in Low. Read naively this says more crime means higher "
           "prices, which is backwards from what buyers report caring about. The bands are "
           "quartiles of the trailing twelve-month borough crime volume, so the confound is "
           "baked in: central boroughs are both the most expensive and the most "
           "crime-recording. This is the chart that motivated the whole of section 8.2. "
           "Source: notebook cell 23."),
dict(layout="figure_full", kicker="APPENDIX", figure=F+"c23b_crime_and_market_1.png",
     title="A5 · Housing market and the cost of borrowing, 2008–2016",
     notes="Two stacked panels sharing one x axis: median London transaction price on top, "
           "Bank of England base rate below. The base rate collapses from 5.5 % to 0.5 % "
           "across 2008-2009 while price dips and then climbs steadily for years afterward. "
           "The design decision is deliberate and worth defending: stacked panels rather than "
           "one chart with twin y-axes, because a dual-axis chart lets whoever draws it "
           "decide where the two lines appear to cross by choosing the scales, manufacturing "
           "a visual correlation that may not exist. Note the irony for slide 21 — this is "
           "the most visually compelling external driver in the exploratory analysis, and "
           "removing interest_rate from the model improves it. Source: notebook cells 22 "
           "and 23."),
dict(layout="figure_full", kicker="APPENDIX", figure=F+"c23d_borough_sqm.png",
     title="A6 · Median price per square metre, all 28 boroughs in the table",
     notes="The full borough ranking behind the five-times figure quoted on slide 7. "
           "Kensington and Chelsea sits at just under £12,000 per square metre; Bexley, on the "
           "outer south-eastern edge, at about £2,300. Westminster, the City of London and "
           "Camden follow at the top, and Croydon, Newham and Bexley anchor the bottom. The "
           "ordering is essentially a map of distance from the centre, which is the point: "
           "borough, outcode, latitude, longitude and distance-to-centre are all measuring "
           "the same underlying thing. That is why the ablation on slide 21 finds transport "
           "worth only +0.09 pp despite its steep bivariate gradient — the location "
           "information is already in the model several times over. Source: notebook "
           "cell 23."),
dict(layout="figure_full", kicker="APPENDIX", figure=F+"c23c_price_vs_area.png",
     title="A7 · Price against floor area on log-log axes",
     notes="Price tracks floor area closely on a log-log scale, which is the single "
           "strongest physical relationship in the data at r = 0.57 on the raw correlation. "
           "The spread widens at the top end, where finish and location start to matter as "
           "much as square metreage. The vertical striping at low areas is rounding in the "
           "recorded floor-area values. This is the hedonic core of the model: the tree "
           "models drop the linear-in-attributes assumption but they are estimating the same "
           "implicit prices Rosen 1974 describes. Source: notebook cell 23."),
dict(layout="table", kicker="APPENDIX",
     title="A8 · Full validation leaderboard, all 14 models",
     table=dict(headers=["Model", "MdAPE", "MAE", "R²", "within 25 %"],
                rows=[["CatBoost detrended-market (cleaned)", "11.94 %", "£115,177", "0.824", "80.8 %"],
                      ["3-seed average detrended (XGB)", "12.12 %", "£114,888", "0.834", "80.3 %"],
                      ["XGBoost detrended-market (capped)", "12.19 %", "£114,186", "0.834", "80.5 %"],
                      ["MoE – luxury routing detrended (XGB)", "12.49 %", "£120,442", "0.817", "79.0 %"],
                      ["CatBoost detrended-borough (cleaned)", "12.63 %", "£118,386", "0.819", "80.8 %"],
                      ["XGBoost detrended-borough (capped)", "12.98 %", "£118,293", "0.830", "79.2 %"],
                      ["CatBoost (cleaned)", "13.20 %", "£123,849", "0.800", "79.3 %"],
                      ["3-seed average (CatBoost)", "13.26 %", "£122,881", "0.807", "79.4 %"],
                      ["XGBoost (raw)", "13.88 %", "£126,418", "0.787", "78.4 %"],
                      ["MoE – luxury routing (XGB)", "14.05 %", "£137,102", "0.751", "77.1 %"],
                      ["3-seed average (XGB)", "14.23 %", "£134,327", "0.763", "77.7 %"],
                      ["XGBoost (capped)", "14.33 %", "£126,492", "0.813", "77.9 %"],
                      ["XGBoost (cleaned)", "14.60 %", "£137,929", "0.750", "76.6 %"],
                      ["Ridge (baseline)", "17.09 %", "£163,715", "0.539", "68.7 %"]],
                widths=[5.0, 1.7, 2.0, 1.4, 1.8]),
     dense=True,
     notes="The complete section 13 table, every model scored on the same 8,840 validation "
           "rows. Note the block structure: positions one to six are all detrended models "
           "and positions seven to fourteen are all plain-target ones, with no interleaving. "
           "Note also that MdAPE and MAE disagree on ordering in places — the 3-seed average "
           "detrended has a better MAE than the model above it, and XGBoost capped has a "
           "better MAE than several models that beat it on MdAPE. Selection uses MdAPE as "
           "fixed in section 11. Source: notebook cell 48."),
dict(layout="table", kicker="APPENDIX",
     title="A9 · Full test comparison, all 14 models with drift",
     table=dict(headers=["Model", "Val MdAPE", "Test MdAPE", "Drift"],
                rows=[["3-seed average detrended (XGB)", "12.12 %", "13.62 %", "+1.50 pp"],
                      ["XGBoost detrended-market (capped)", "12.19 %", "13.88 %", "+1.68 pp"],
                      ["CatBoost detrended-market (cleaned)", "11.94 %", "13.88 %", "+1.94 pp"],
                      ["MoE – luxury routing detrended (XGB)", "12.49 %", "14.31 %", "+1.83 pp"],
                      ["XGBoost detrended-borough (capped)", "12.98 %", "14.32 %", "+1.34 pp"],
                      ["CatBoost detrended-borough (cleaned)", "12.63 %", "16.00 %", "+3.37 pp"],
                      ["Ridge (baseline)", "17.09 %", "16.62 %", "−0.47 pp"],
                      ["CatBoost (cleaned)", "13.20 %", "18.03 %", "+4.83 pp"],
                      ["3-seed average (CatBoost)", "13.26 %", "18.47 %", "+5.21 pp"],
                      ["MoE – luxury routing (XGB)", "14.05 %", "18.99 %", "+4.94 pp"],
                      ["XGBoost (raw)", "13.88 %", "19.57 %", "+5.69 pp"],
                      ["3-seed average (XGB)", "14.23 %", "19.75 %", "+5.52 pp"],
                      ["XGBoost (capped)", "14.33 %", "19.92 %", "+5.59 pp"],
                      ["XGBoost (cleaned)", "14.60 %", "20.25 %", "+5.66 pp"]],
                widths=[5.4, 2.2, 2.2, 2.1]),
     dense=True,
     notes="Sorted by test MdAPE. The detrended family occupies the top six places on test "
           "just as it did on validation. The drift column is test minus validation and is "
           "the size of the optimism validation carried; note that it is 1.3 to 1.9 points "
           "for the detrended models but 4.8 to 5.7 points for the plain-target ones, which "
           "is itself evidence that the plain models were fitting a level that did not hold "
           "forward. Ridge is the only model whose test score improves on validation, at "
           "−0.47 pp. Source: notebook cell 51."),
dict(layout="table", kicker="APPENDIX",
     title="A10 · All six crime designs, five seeds each",
     table=dict(headers=["Crime design", "MdAPE mean", "sd", "Gain", "Seeds won"],
                rows=[["No crime  (0 cols)", "12.153 %", "0.129", "+0.000 pp", "0 / 5"],
                      ["Borough count, status quo  (2)", "12.136 %", "0.088", "+0.017 pp", "4 / 5"],
                      ["LSOA total  (1)", "12.089 %", "0.038", "+0.064 pp", "3 / 5"],
                      ["LSOA by category  (4)", "12.069 %", "0.143", "+0.084 pp", "3 / 5"],
                      ["LSOA + density  (5)", "12.131 %", "0.089", "+0.022 pp", "2 / 5"],
                      ["Borough + LSOA  (7)", "12.108 %", "0.097", "+0.045 pp", "4 / 5"]],
                widths=[4.2, 2.2, 1.4, 2.0, 1.7]),
     dense=True,
     notes="Every design refit under five seeds, with each gain differenced against the "
           "no-crime baseline within its own seed before averaging. The best gain, LSOA by "
           "category at +0.084 pp, is below the 0.15 pp gate. The seed noise floor — the mean "
           "of the sd column, 0.097 pp — is the second bar, and the best design's own gain "
           "standard deviation is 0.187, larger than the gain itself. No design wins more "
           "than four of five seeds. The experiment cannot resolve an effect this size, which "
           "is the honest conclusion rather than a null result dressed up as one. Source: "
           "notebook cells 63 and 64."),
dict(layout="bullets", kicker="APPENDIX",
     title="A11 · Encoding: two representations, both fitted on training only",
     bullets=["Native category dtype for XGBoost: propertyType, tenure, borough, outcode",
              "Level set pinned from training, so codes stay stable",
              "CatBoost gets raw strings via cat_features",
              "Smoothed target encoding for routers, pulling rare levels in",
              "pd.to_numeric(errors='coerce') would blank all four — self-check #2"],
     notes="Two representations, both fitted on training data only. The outcode is the first "
           "half of a UK postcode, so it is a mid-grained location label sitting between "
           "borough and street. Pinning the level set from the training split is what makes a "
           "category code mean the same thing at fit time and predict time; without it a "
           "category present only in validation shifts every code above it. Smoothing in the "
           "target encoder pulls low-frequency categories toward the global mean, so a "
           "borough with three sales does not get a confident price estimate. The last bullet "
           "records a bug that actually happened: coercing those four columns to numeric with "
           "errors='coerce' turns all of them entirely NaN and leaves the CatBoost models and "
           "every router training on dead columns — which is why self-check number two exists "
           "and asserts that no feature column is all-NaN. Source: notebook cell 35."),
dict(layout="bullets", kicker="APPENDIX",
     title="A12 · The remaining ranked improvements, 3 to 8",
     bullets=["Walk-forward backtesting: one cut gives no error bar",
              "Make the margin a P&L: stamp duty, refurbishment, fees",
              "Mondrian conformal: multipliers per borough and price decile",
              "Drop interest_rate; revisit transport as travel time",
              "Lease length above all; then SHAP over location"],
     notes="Improvements three through eight from section 18, after the group-aware split and "
           "widening the window. Walk-forward or rolling-origin evaluation would give a "
           "distribution of MdAPE rather than a single number, and reveal whether performance "
           "depends on which slice of the cycle you happened to test on. Turning the margin "
           "into a profit-and-loss means adding the costs a buyer actually pays, including "
           "the 3 % stamp-duty surcharge that applies to exactly this kind of "
           "second-property purchase, after which the scanner can rank by return rather than "
           "by pounds. Mondrian conformal calibrates separate multipliers per segment so "
           "coverage holds within the boroughs an investor actually shops in, not just "
           "on average. Lease length is the most consequential missing column: a leasehold "
           "flat with 70 years left is worth materially less than an otherwise identical one "
           "with 950, and extending a short lease costs tens of thousands — so this single "
           "absent feature is a plausible part of what the scanner currently mistakes for "
           "underpricing. Source: notebook cell 80."),
dict(layout="bullets", kicker="APPENDIX",
     title="A13 · Pointed at today's market: 29.00 % flagged, and why that is an artifact",
     bullets=["scripts/live_flip_scan scrapes Rightmove, substituting public sources",
              "200 listings flagged at 29.00 % against 13.39 % on test",
              "Higher, not lower — the opposite of asking-versus-sold",
              "Camden and K&C show predictions 1.7–2.5× asking",
              "Inconclusive: an HPI-proxy or extrapolation artifact"],
     notes="This ran outside the notebook — scraping plus a full retrain takes the better "
           "part of an hour — so the notebook cell is a static record of the last run rather "
           "than something re-executed top to bottom. It substitutes UK HPI for the market "
           "medians, data.police.uk for crime as a point-radius rather than a borough sum, "
           "the EPC register for floor area, and HM Land Registry Price Paid Data for the "
           "prior-sale block matched on postcode and street, then scores the live listings "
           "through the same conformal scanner as section 15. The result is worth showing "
           "precisely because it does not validate anything: the live flip rate is higher "
           "than the test rate, which is the opposite of what the asking-versus-sold gap "
           "alone would predict, since an asking price above the eventual sold price should "
           "make fewer listings look underpriced. Splitting the predicted-over-asking ratio "
           "by borough points at why: predictions 1.7 to 2.5 times asking in a handful of "
           "central boroughs are far more consistent with an artifact of the HPI market-level "
           "proxy, or with a ten-to-eighteen-year extrapolation on days_since_start, than "
           "with genuine mispricing. Treat 29.00 % as inconclusive, not as a finding about "
           "the 2026 market. Source: notebook cell 81."),
dict(layout="bullets", kicker="APPENDIX",
     title="A15 · Seven assertions, each guarding a defect that was actually present",
     bullets=["No training row postdates a validation row; no dead columns",
              "Categorical levels pinned; lagged features exclude the present",
              "Prior sales strictly precede — asserted, one violation is leakage",
              "Coverage on a calibration holdout: **88.39 %**, 1,775 rows",
              "Persisted: manifest.json, leaderboard.csv, model.joblib"],
     notes="A notebook with no assertions is a notebook that fails silently, and each of "
           "these checks encodes an invariant that a real earlier bug violated. The dead-column "
           "check exists because coercing the four categorical columns with pd.to_numeric and "
           "errors='coerce' once turned all of them entirely NaN, leaving the CatBoost models "
           "and every router training on dead columns. The re-runnability check exists because "
           "an EDA cell that rebound a variable name once clobbered the raw station table for "
           "every cell below it. The conformal check is the most carefully constructed: the "
           "multiplier is refitted on the first 70 % of calibration and scored on the "
           "remaining 30 %, because checking coverage on the same rows the multiplier was "
           "fitted on is an identity, not a test — and test-set coverage is printed alongside "
           "but deliberately carries no assertion, because making a run fail on a held-out "
           "metric turns that metric into a tuning signal. All ten checks pass on the current "
           "run. The same probes run in the pytest suite against a committed 500-row fixture "
           "in about two seconds. On persistence: the predict closures are not picklable by "
           "design, so what is saved is the estimators plus everything needed to rebuild the "
           "closure — the package is the deployment unit and the notebook is the narrative "
           "that produced it. What a green run does not prove: that the model is good, that "
           "the features are right, or that the protocol was followed while the notebook was "
           "being written. That last one is the next slide. Source: notebook cells 75 to 79."),
]
