# 🏙️ London Flip Finder

# Overview

**London Flip Finder** is an end-to-end machine learning project for predicting residential property prices across London using spatial, temporal, economic, and property-specific information.

The project integrates multiple public datasets with advanced feature engineering to build a robust property valuation model. Several machine learning approaches—including linear regression, gradient boosting, and Mixture of Experts (MoE)—were developed and compared to investigate how specialized models can improve prediction accuracy across different segments of the housing market.

The notebook follows a complete real-world data science workflow, from raw data collection and preprocessing to model evaluation and interpretation.

---

# Project Objectives

This project aims to answer several practical questions:

- How accurately can London residential property prices be predicted?
- How much do geographic and spatial features improve model performance?
- Can specialized machine learning models outperform traditional regression models?
- Does separating different market segments improve predictive accuracy?
- Which factors contribute most to property prices?

---

# Data Sources

The model combines multiple publicly available datasets:

- London Land Registry property transactions
- Transport for London (TfL) Underground stations
- London Borough boundary shapefiles
- UK postcode geographic data
- Crime statistics
- Bank of England interest rates

These datasets are spatially joined to create a rich property-level machine learning dataset.

---

# Feature Engineering

Extensive feature engineering was performed across multiple domains.

## Property Features

- Floor area
- Bedrooms
- Bathrooms
- Living rooms
- Property type

## Spatial Features

- Distance to nearest Underground station
- Borough assignment
- Geographic coordinates
- Neighborhood characteristics

## Crime Features

- Previous-month crime counts
- Rolling 12-month crime totals

## Economic Features

- Bank of England base interest rate
- Historical housing market trends

## Temporal Features

- Transaction year
- Cyclical month encoding
- Lagged rolling median property prices

All temporal features were carefully engineered to prevent data leakage.

---

# Exploratory Data Analysis

The notebook includes extensive exploratory analysis covering:

- Property price distributions
- Price per square meter
- Property type comparisons
- Borough-level price differences
- Floor area versus price
- Distance-to-Tube premium
- Crime impact analysis
- Interest rate effects
- Correlation analysis

These analyses guided the feature engineering process and model selection.

---

# Machine Learning Pipeline

```
Raw Data
      │
      ▼
Data Cleaning
      │
      ▼
Spatial Data Integration
      │
      ▼
Feature Engineering
      │
      ▼
Exploratory Data Analysis
      │
      ▼
Chronological Train / Validation / Test Split
      │
      ▼
Baseline Ridge Regression
      │
      ▼
XGBoost
      │
      ▼
XGBoost - MOE
      │
      ▼
CatBoost
      │
      ▼
CatBoost - MOE
      │
      ▼
Conformal Pradiction
```

---

# Machine Learning Models

Several predictive models were implemented and compared throughout the project.

## Ridge Regression

A linear baseline model used to establish benchmark performance.

## XGBoost

The primary gradient boosting model featuring:

- Log-transformed target values
- Early stopping
- Native categorical feature handling
- Chronological validation strategy

## CatBoost

CatBoost was evaluated as an alternative gradient boosting algorithm with native categorical encoding capabilities, providing a strong benchmark against XGBoost.

## Mixture of Experts (MoE)

To further improve prediction accuracy, a **Mixture of Experts (MoE)** architecture was implemented.

Instead of relying on a single global model, specialized expert models were trained for different market segments, allowing each expert to focus on a subset of the housing market. The gating strategy routes each property to the most appropriate expert, improving predictive performance on heterogeneous data.

---

# Data Cleaning

Several preprocessing strategies were evaluated, including:

- Missing value handling
- Geographic validation
- Temporal alignment
- Luxury property filtering
- Feature normalization
- Leakage prevention through lagged variables

Filtering extreme luxury properties (> £4M) was also investigated to improve overall model robustness.

---

# Model Evaluation

Models were evaluated using multiple performance metrics:

- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)
- Mean Absolute Percentage Error (MAPE)
- R² Score

Additional diagnostics include:

- Residual analysis
- Prediction error visualization
- Feature importance analysis
- Model comparison

---

# Technologies

- Python
- Pandas
- NumPy
- GeoPandas
- Shapely
- SciPy (cKDTree)
- Scikit-Learn
- XGBoost
- CatBoost
- Matplotlib
- Seaborn

---

# Running the Project

The notebook is fully configured to run in **Google Colab**.

## Dataset

Due to GitHub's file size limitations, the datasets are **not stored directly inside the repository**.

Instead, they are available in the repository's **Releases** section.

## Setup

1. Download the latest dataset package from **GitHub Releases**.
2. Extract the downloaded archive.
3. Upload the dataset folder to your **Google Drive**.
4. Open `london_flip_finder.ipynb` in Google Colab.
5. Mount your Google Drive.
6. Update the dataset path if necessary.
7. Run the notebook from top to bottom.

> **Note:** The notebook expects all datasets to be stored in Google Drive. Running the notebook without downloading the dataset package from the **Releases** section will result in missing file errors.

---

# Repository Structure

```
London-Flip-Finder/

│── london_flip_finder.ipynb
│── README.md
│
└── Releases/
    └── Dataset Package
```

---

# Future Improvements

Potential future extensions include:

- LightGBM benchmarking
- Graph Neural Networks
- Live property listing integration
- Automated model retraining pipeline

---

# Key Highlights

- End-to-end machine learning workflow
- Multi-source spatial data integration
- Advanced geospatial feature engineering
- Leakage-free temporal features
- Efficient nearest-station computation using cKDTree
- Chronological train/validation/test splitting
- Ridge Regression baseline
- XGBoost implementation
- CatBoost implementation
- Mixture of Experts (MoE) architecture
- Feature importance analysis
- Conformal Pradiction implementation
- Professional Google Colab workflow
---

---

⭐ If you found this project interesting, consider giving the repository a **Star**!
