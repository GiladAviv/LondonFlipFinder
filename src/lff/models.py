"""Trainers, deflators and the mixture-of-experts slate. Section 12."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
import xgboost as xgb
from catboost import CatBoostRegressor
from scipy.optimize import minimize
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from .config import Config
from .features.registry import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from .metrics import ModelBundle, ResultsRegistry, evaluate
from .split import Splits


def _as_string_frame(X: pd.DataFrame) -> pd.DataFrame:
    """Categorical columns as plain strings -- module level so the pipeline stays picklable."""
    return X.astype(str)


def _catboost_frame(X: pd.DataFrame) -> pd.DataFrame:
    """CatBoost wants raw strings in cat_features, never numeric codes."""
    out = X.copy()
    for col in CATEGORICAL_FEATURES:
        out[col] = out[col].astype(str).fillna("MISSING")
    return out


def train_ridge(train_df: pd.DataFrame, splits: Splits, cfg: Config, variant: str) -> ModelBundle:
    """Regularised linear baseline: median-imputed + scaled numerics, one-hot categoricals."""
    numeric_tf = Pipeline([("impute", SimpleImputer(strategy="median")),
                           ("scale", StandardScaler())])
    categorical_tf = Pipeline([
        ("to_str", FunctionTransformer(_as_string_frame, feature_names_out="one-to-one")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    pipeline = Pipeline([
        ("prep", ColumnTransformer([("num", numeric_tf, NUMERIC_FEATURES),
                                    ("cat", categorical_tf, CATEGORICAL_FEATURES)])),
        ("model", TransformedTargetRegressor(regressor=Ridge(alpha=1.0),
                                             func=np.log1p, inverse_func=np.expm1)),
    ])
    pipeline.fit(splits.features(train_df), splits.target(train_df))
    return ModelBundle("Ridge (baseline)", variant, lambda X: pipeline.predict(X),
                       {"pipeline": pipeline})


def train_xgboost(train_df: pd.DataFrame, val_df: pd.DataFrame, splits: Splits,
                  cfg: Config, variant: str) -> ModelBundle:
    """Gradient-boosted trees with native categorical support and early stopping."""
    model = xgb.XGBRegressor(
        n_estimators=cfg.n_estimators, max_depth=8, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8, enable_categorical=True, tree_method="hist",
        early_stopping_rounds=50, random_state=cfg.seed, n_jobs=-1,
    )
    model.fit(
        splits.features(train_df), np.log1p(splits.target(train_df)),
        eval_set=[(splits.features(val_df), np.log1p(splits.target(val_df)))], verbose=False,
    )
    return ModelBundle(f"XGBoost ({variant})", variant,
                       lambda X: np.expm1(model.predict(X)), {"model": model})


def train_catboost(train_df: pd.DataFrame, val_df: pd.DataFrame, splits: Splits,
                   cfg: Config, variant: str) -> ModelBundle:
    """CatBoost with genuine categorical features -- the original passed it four all-NaN columns."""
    model = CatBoostRegressor(
        iterations=cfg.catboost_iterations, learning_rate=0.05, depth=8, l2_leaf_reg=3,
        loss_function="MAE", eval_metric="MAE", random_seed=cfg.seed, verbose=False,
    )
    model.fit(
        _catboost_frame(splits.features(train_df)), np.log1p(splits.target(train_df)),
        eval_set=(_catboost_frame(splits.features(val_df)), np.log1p(splits.target(val_df))),
        cat_features=CATEGORICAL_FEATURES, use_best_model=True, early_stopping_rounds=50,
    )
    return ModelBundle(f"CatBoost ({variant})", variant,
                       lambda X: np.expm1(model.predict(_catboost_frame(X))), {"model": model})


def fit_market_deflator(train_df: pd.DataFrame) -> float:
    """Training-only fallback for the handful of rows too early to have a 3-month rolling window."""
    return float(train_df["market_median_rolling_3m"].median())


def market_level(X: pd.DataFrame, deflator: float) -> np.ndarray:
    """Lagged whole-market median price -- a calendar-time deflator, the same number for
    every property sold in a given month regardless of its size or location."""
    level = X["market_median_rolling_3m"].fillna(X["market_median_rolling_12m"])
    return level.fillna(deflator).to_numpy()


def fit_borough_deflator(train_df: pd.DataFrame) -> tuple[float, float]:
    """Training-only fallbacks: the market-wide level (missing borough data) and the median
    floor area (missing floorAreaSqM)."""
    return (
        float(train_df["market_median_rolling_3m"].median()),
        float(train_df["floorAreaSqM"].median()),
    )


def borough_level(X: pd.DataFrame, deflator: tuple[float, float]) -> np.ndarray:
    """Lagged borough L/sqm x this property's own floor area -- a size- and location-scaled
    deflator, personalised per row rather than one number per month. Falls back to the
    market-wide level (fit_market_deflator's constant) wherever borough or area data is
    missing, rather than bucketing on a coarse category like bedroom count: bucketing by
    bedrooms x borough x property type would leave many 3-month cells with only a handful of
    sales, and a noisy deflator injects noise directly into every label it is divided into.
    """
    market_fallback, area_fallback = deflator
    area = X["floorAreaSqM"].fillna(area_fallback)
    level = X["lagged_borough_median_sqm"] * area
    market_wide = X["market_median_rolling_3m"].fillna(X["market_median_rolling_12m"])
    market_wide = market_wide.fillna(market_fallback)
    return level.fillna(market_wide).to_numpy()


# Two deflator strategies, compared head-to-head in the leaderboard rather than assumed.
DEFLATORS = {
    "market": (fit_market_deflator, market_level),
    "borough": (fit_borough_deflator, borough_level),
}


def detrend(y: pd.Series, level: np.ndarray) -> np.ndarray:
    """log(price / level): a ratio a tree can interpolate instead of extrapolating price."""
    return np.log(y.to_numpy(dtype=float) / level)


def retrend(y_log_ratio: np.ndarray, level: np.ndarray) -> np.ndarray:
    """Invert detrend() -- multiply the predicted ratio back onto the deflator level."""
    return np.exp(y_log_ratio) * level


def train_xgboost_detrended(train_df: pd.DataFrame, val_df: pd.DataFrame, splits: Splits,
                            cfg: Config, variant: str,
                            deflator_kind: str = "market") -> ModelBundle:
    """XGBoost on a detrended, stationary target with an MAE objective aligned to MdAPE."""
    fit_deflator, level_fn = DEFLATORS[deflator_kind]
    deflator = fit_deflator(train_df)
    X_train, X_val = splits.features(train_df), splits.features(val_df)
    y_train = detrend(splits.target(train_df), level_fn(X_train, deflator))
    y_val = detrend(splits.target(val_df), level_fn(X_val, deflator))

    model = xgb.XGBRegressor(
        n_estimators=cfg.n_estimators, max_depth=8, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8, enable_categorical=True, tree_method="hist",
        objective="reg:absoluteerror", early_stopping_rounds=50, random_state=cfg.seed, n_jobs=-1,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    def predict(X: pd.DataFrame) -> np.ndarray:
        return retrend(model.predict(X), level_fn(X, deflator))

    return ModelBundle(f"XGBoost detrended-{deflator_kind} ({variant})", variant, predict,
                       {"model": model})


def train_catboost_detrended(train_df: pd.DataFrame, val_df: pd.DataFrame, splits: Splits,
                             cfg: Config, variant: str,
                            deflator_kind: str = "market") -> ModelBundle:
    """CatBoost on the same detrended target -- isolates detrending's effect from the loss's,
    since CatBoost already trains with an MAE loss."""
    fit_deflator, level_fn = DEFLATORS[deflator_kind]
    deflator = fit_deflator(train_df)
    X_train, X_val = splits.features(train_df), splits.features(val_df)
    y_train = detrend(splits.target(train_df), level_fn(X_train, deflator))
    y_val = detrend(splits.target(val_df), level_fn(X_val, deflator))

    model = CatBoostRegressor(
        iterations=cfg.catboost_iterations, learning_rate=0.05, depth=8, l2_leaf_reg=3,
        loss_function="MAE", eval_metric="MAE", random_seed=cfg.seed, verbose=False,
    )
    model.fit(
        _catboost_frame(X_train), y_train, eval_set=(_catboost_frame(X_val), y_val),
        cat_features=CATEGORICAL_FEATURES, use_best_model=True, early_stopping_rounds=50,
    )

    def predict(X: pd.DataFrame) -> np.ndarray:
        return retrend(model.predict(_catboost_frame(X)), level_fn(X, deflator))

    return ModelBundle(f"CatBoost detrended-{deflator_kind} ({variant})", variant, predict,
                       {"model": model})


def _make_expert(backend: str, seed: int, cfg: Config, target_transform: str = "log"):
    if backend == "xgboost":
        # Match the winning single model's recipe when experts train on a detrended target,
        # so "does routing help" is the only variable, not "does routing help AND get a
        # better-aligned loss for free".
        objective = ("reg:absoluteerror" if target_transform == "detrend-market"
                     else "reg:squarederror")
        return xgb.XGBRegressor(
            n_estimators=cfg.n_expert_estimators, max_depth=7, learning_rate=0.03,
            subsample=0.7, colsample_bytree=0.8, enable_categorical=True, tree_method="hist",
            objective=objective, random_state=seed, n_jobs=-1,
        )
    return CatBoostRegressor(
        iterations=cfg.n_expert_estimators, depth=7, learning_rate=0.05, loss_function="MAE",
        bootstrap_type="Bernoulli", subsample=0.7, random_seed=seed, verbose=False,
    )


def _fit_expert(model, backend: str, X: pd.DataFrame, y_log: np.ndarray):
    if backend == "catboost":
        model.fit(_catboost_frame(X), y_log, cat_features=CATEGORICAL_FEATURES)
    else:
        model.fit(X, y_log)
    return model


def _predict_log(model, backend: str, X: pd.DataFrame) -> np.ndarray:
    return model.predict(_catboost_frame(X) if backend == "catboost" else X)


def _router_transform(splits: Splits, imputer: SimpleImputer, X: pd.DataFrame) -> np.ndarray:
    """Routers need dense numerics: target-encode the categoricals, then impute."""
    return imputer.transform(splits.encoder.transform(X))


def train_moe_luxury(train_df: pd.DataFrame, splits: Splits, cfg: Config,
                     variant: str, target_transform: str = "log") -> ModelBundle:
    """Router separates standard from luxury stock; one expert each, blended by probability.

    `target_transform="detrend-market"` trains both experts on section 12.1's fix (the winning
    single model's recipe) instead of plain log1p(price), so this MoE competes fairly against
    the best single model rather than against a version of itself handicapped by the extrapolation
    bug the single model no longer has.
    """
    X_train, y_train = splits.features(train_df), splits.target(train_df)
    is_luxury = (y_train >= cfg.luxury_threshold).astype(int)
    deflator = fit_market_deflator(train_df) if target_transform == "detrend-market" else None

    def to_target(y: pd.Series, X: pd.DataFrame) -> np.ndarray:
        if target_transform == "detrend-market":
            return detrend(y, market_level(X, deflator))
        return np.log1p(y.to_numpy(dtype=float))

    def to_price(pred: np.ndarray, X: pd.DataFrame) -> np.ndarray:
        if target_transform == "detrend-market":
            return retrend(pred, market_level(X, deflator))
        return np.expm1(pred)

    # Carve a calibration slice off the END of training. Temperature must be fitted on data
    # the router did not see, and using the validation set would contaminate model selection.
    cut = int(len(train_df) * 0.85)
    fit_idx, calib_idx = np.arange(cut), np.arange(cut, len(train_df))

    imputer = SimpleImputer(strategy="median").fit(splits.encoder.transform(X_train))
    router = RandomForestClassifier(
        n_estimators=100, max_depth=10, random_state=cfg.seed, n_jobs=-1
    ).fit(_router_transform(splits, imputer, X_train.iloc[fit_idx]), is_luxury.iloc[fit_idx])

    probs = router.predict_proba(
        _router_transform(splits, imputer, X_train.iloc[calib_idx])
    )[:, 1]
    probs = np.clip(probs, 1e-7, 1 - 1e-7)
    logits = np.log(probs / (1 - probs))
    y_calib = is_luxury.iloc[calib_idx]

    if y_calib.nunique() < 2:            # calibration slice has only one class
        temperature = 1.0
    else:
        temperature = float(
            minimize(
                lambda t: log_loss(y_calib, 1 / (1 + np.exp(-logits / t[0]))),
                x0=[1.0], bounds=[(0.1, 10.0)], method="L-BFGS-B",
            ).x[0]
        )

    X_std, y_std = X_train[is_luxury == 0], y_train[is_luxury == 0]
    X_lux, y_lux = X_train[is_luxury == 1], y_train[is_luxury == 1]
    standard = _fit_expert(_make_expert("xgboost", cfg.seed, cfg, target_transform), "xgboost",
                           X_std, to_target(y_std, X_std))
    luxury = _fit_expert(_make_expert("xgboost", cfg.seed + 1, cfg, target_transform), "xgboost",
                         X_lux, to_target(y_lux, X_lux))

    def predict(X: pd.DataFrame) -> np.ndarray:
        p = np.clip(router.predict_proba(_router_transform(splits, imputer, X))[:, 1],
                    1e-7, 1 - 1e-7)
        p_lux = 1 / (1 + np.exp(-(np.log(p / (1 - p)) / temperature)))
        return (to_price(_predict_log(standard, "xgboost", X), X) * (1 - p_lux)
                + to_price(_predict_log(luxury, "xgboost", X), X) * p_lux)

    suffix = " detrended" if target_transform == "detrend-market" else ""
    print(f"   luxury router: temperature {temperature:.3f}, "
          f"{is_luxury.sum():,} luxury / {(1 - is_luxury).sum():,} standard training rows")
    return ModelBundle(f"MoE - luxury routing{suffix} (XGB)", variant, predict,
                       {"router": router, "standard": standard, "luxury": luxury,
                        "temperature": temperature, "imputer": imputer})


def train_moe_error_driven(train_df: pd.DataFrame, splits: Splits, cfg: Config, variant: str,
                           backend: str = "xgboost", target_transform: str = "log"
                           ) -> tuple[ModelBundle, ModelBundle]:
    """Three seed-diverse experts + a router that learns which one wins per property.

    Returns the MoE *and* a plain average of the identical three experts -- the control that
    tells you whether the routing added anything beyond ordinary ensembling. With
    `target_transform="detrend-market"`, all three experts train on section 12.1's fix, so this
    checks whether routing/averaging adds anything on top of the best single model, not on top
    of a handicapped one.
    """
    X_train, y_train = splits.features(train_df), splits.target(train_df)
    deflator = fit_market_deflator(train_df) if target_transform == "detrend-market" else None

    if target_transform == "detrend-market":
        y_log = detrend(y_train, market_level(X_train, deflator))
    else:
        y_log = np.log1p(y_train.to_numpy(dtype=float))

    def to_price(pred: np.ndarray, X: pd.DataFrame) -> np.ndarray:
        if target_transform == "detrend-market":
            return retrend(pred, market_level(X, deflator))
        return np.expm1(pred)

    experts = [
        _fit_expert(_make_expert(backend, seed, cfg, target_transform), backend, X_train, y_log)
        for seed in (10, 20, 30)
    ]
    train_preds = np.column_stack([_predict_log(e, backend, X_train) for e in experts])
    best_expert = np.argmin(np.abs(y_log[:, None] - train_preds), axis=1)

    imputer = SimpleImputer(strategy="median").fit(splits.encoder.transform(X_train))
    router = RandomForestClassifier(
        n_estimators=150, max_depth=12, class_weight="balanced",
        random_state=cfg.seed, n_jobs=-1,
    ).fit(_router_transform(splits, imputer, X_train), best_expert)

    def predict_moe(X: pd.DataFrame) -> np.ndarray:
        weights = router.predict_proba(_router_transform(splits, imputer, X))
        preds = np.column_stack([to_price(_predict_log(e, backend, X), X) for e in experts])
        return (preds * weights).sum(axis=1)

    def predict_mean(X: pd.DataFrame) -> np.ndarray:
        preds = np.column_stack([to_price(_predict_log(e, backend, X), X) for e in experts])
        return preds.mean(axis=1)

    label = "XGB" if backend == "xgboost" else "CatBoost"
    suffix = " detrended" if target_transform == "detrend-market" else ""
    counts = np.bincount(best_expert, minlength=3)
    print(f"   {label} expert wins on training data: "
          + ", ".join(f"E{i} {c:,}" for i, c in enumerate(counts)))

    return (
        ModelBundle(f"MoE - error routing{suffix} ({label})", variant, predict_moe,
                    {"experts": experts, "router": router, "imputer": imputer,
                     "backend": backend}),
        ModelBundle(f"3-seed average{suffix} ({label})", variant, predict_mean,
                    {"experts": experts, "backend": backend}),
    )


def train_all(splits: Splits, variants: dict[str, pd.DataFrame], cfg: Config,
              val_eval: pd.DataFrame, results: ResultsRegistry) -> dict[str, ModelBundle]:
    """Train the full slate. Early stopping watches the evaluation universe."""
    bundles: dict[str, ModelBundle] = {}
    started = time.time()

    def register(bundle: ModelBundle) -> None:
        bundles[bundle.name] = bundle
        evaluate(bundle, val_eval, "val", results, splits)

    print("--- Baseline ---")
    register(train_ridge(variants["capped"], splits, cfg, "capped"))

    print("\n--- Single gradient-boosted models ---")
    for variant in ("raw", "capped", "cleaned"):
        register(train_xgboost(variants[variant], val_eval, splits, cfg, variant))
    register(train_catboost(variants["cleaned"], val_eval, splits, cfg, "cleaned"))

    print("\n--- Detrended gradient-boosted models (section 12.1) ---")
    for kind in ("market", "borough"):
        register(train_xgboost_detrended(variants["capped"], val_eval, splits, cfg, "capped", kind))
        register(train_catboost_detrended(variants["cleaned"], val_eval, splits, cfg,
                                          "cleaned", kind))

    print("\n--- Mixture of Experts ---")
    register(train_moe_luxury(variants["cleaned"], splits, cfg, "cleaned"))
    for backend in ("xgboost", "catboost"):
        moe, mean = train_moe_error_driven(variants["cleaned"], splits, cfg, "cleaned", backend)
        register(moe)
        register(mean)

    print("\n--- Mixture of Experts on the best recipe (detrended, section 12.1) ---")
    # Same variant as the winning single model (capped), so this isolates one question: does
    # routing or averaging add anything on top of the best model, not on top of a handicapped one.
    register(train_moe_luxury(variants["capped"], splits, cfg, "capped", "detrend-market"))
    moe_d, mean_d = train_moe_error_driven(variants["capped"], splits, cfg, "capped",
                                           "xgboost", "detrend-market")
    register(moe_d)
    register(mean_d)

    print(f"\nTrained {len(bundles)} models in {time.time() - started:.0f}s")
    return bundles
