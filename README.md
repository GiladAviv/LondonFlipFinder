# 🇬🇧 London Flip Finder: Advanced Real Estate Valuation Model

## 📌 Overview
This project aims to identify highly profitable real estate investment opportunities (Flips) in the London housing market. By building a robust machine learning valuation model (using **XGBoost**), the system calculates the true fair market value of properties based on their physical characteristics, spatial data, macro-economic indicators, and neighborhood safety metrics. 

Properties where the actual market asking price (or API estimate) is significantly lower than our model's predicted value are flagged as potential "Flips".

---

## 🏗️ Complex Data Fusion Architecture
One of the core strengths of this project is the integration of multiple, disparate data sources into a single unified dataset using advanced joins:

1. **Spatial Join:**
   * **The Challenge:** The raw property dataset lacked accurate municipal borough identifiers, which are crucial for merging neighborhood-level statistics (like crime).
   * **The Solution:** We downloaded official London Borough Shapefiles (polygons) from Kaggle. Using the exact `latitude` and `longitude` of each property, we performed a point-in-polygon Spatial Join (`gpd.sjoin(predicate='within')`) to precisely map every property to its official borough.

2. **Temporal Join with 1-Month Lag:**
   * **The Challenge:** Merging monthly crime data with real estate transaction dates without introducing Data Leakage (i.e., using future data to predict the present).
   * **The Solution:** We engineered a `crime_lag_month` feature. If a property was sold in May 2012, the model merges the total crime volume from *April 2012*. Additionally, a rolling 12-month crime volume feature was merged using this exact lag to capture the neighborhood's stable safety profile.

3. **Exact-Date Macro Join:**
   * Daily Bank of England (BoE) interest rates were merged using an exact `date` match to reflect the precise cost of borrowing on the day the transaction was closed.

---

## 🧹 Data Cleaning & Imputation Strategy
Handling missing values in real estate data requires a methodical approach to avoid signal distortion:

* **Macro & Environmental Imputation (Median):** Missing values in the merged crime datasets (e.g., `crime_volume_prev_12m`) were imputed using the **Median** of the dataset. This ensures that properties sold in fringe dates or edge-case locations do not crash the model, while avoiding the skewness that a mean imputation might cause due to highly anomalous neighborhoods.
* **Strict Feature Engineering (`total_rooms`):** Instead of forcefully filling missing bedroom or living room counts with `0` (which distorts the model by grouping missing data with actual studio apartments), we used strict addition (`bedrooms + livingRooms`). If either value was `NaN`, the sum remained `NaN`.
* **Algorithmic Imputation (XGBoost Sparsity-Aware Split):** For continuous physical features like exact distance to the Tube or missing `total_rooms`, we intentionally left the values as `NaN`. XGBoost natively handles missing data by learning the optimal default split direction, preventing the introduction of synthetic bias.
* **Information Threshold Filtering:** Rows lacking the absolute minimum critical physical data (specifically, missing *both* `floorAreaSqM` and `total_rooms`) were dropped (`dropna(how='all')`), as they act as "black boxes" that add noise rather than predictive power.

---

## 📊 Data Dictionary (Key Features)

### 🎯 Target Variable
* `price`: The actual historical transaction price of the property (in £).

### 📍 Spatial & Location Features
* `borough`: The official London municipal borough (Extracted via Spatial Join).
* `distance_to_nearest_tube_m`: The exact distance in meters to the closest London Underground station (Calculated using Scipy's `cKDTree`).
* `latitude` / `longitude`: Exact geographical coordinates.
* `outcode`: The first half of the UK postcode, representing the general district.

### 🏠 Physical Property Features
* `floorAreaSqM`: The internal built area of the property in square meters.
* `total_rooms`: Engineered feature summing `bedrooms` and `livingRooms`.
* `propertyType`: The architectural type of the property (e.g., Flat, Terraced House, Detached).
* `tenure`: The legal ownership type (Freehold vs. Leasehold).

### 🌍 Environmental & Macro-Economic Features
* `crime_volume_prev_12m`: The total reported crime events in the property's borough during the 12 full months strictly preceding the sale month.
* `interest_rate`: The official Bank of England interest rate on the exact day of the transaction.

### 🤖 API Market Estimates (For Flip Identification)
* `saleEstimate_currentPrice`: The current estimated market value provided by the external Real Estate API (Used as the baseline to compare against our model's valuation).
* `rentEstimate_currentPrice`: Estimated monthly rental income (Useful for Yield/ROI calculations).

---

## 🚀 Next Steps
1. **Model Training:** Training an XGBoost regressor with Conformal Prediction to output price ranges with a 90% confidence interval.
2. **Flip Identification:** Running the current API listings through the model to extract properties where: `Predicted Value > (API Estimate + Renovation Margin)`.
