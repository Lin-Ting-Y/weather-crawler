# -*- coding: utf-8 -*-
"""
50_Startups 特徵選擇範例（CRISP-DM 流程）
請先確定安裝：pandas numpy scikit-learn matplotlib seaborn
pip install pandas numpy scikit-learn matplotlib seaborn
"""

import pandas as pd
import numpy as np
from urllib.request import urlopen
from io import StringIO

# Modeling & preprocessing
from sklearn.model_selection import cross_val_score, KFold
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LinearRegression, LassoCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import SequentialFeatureSelector, RFE
from sklearn.metrics import mean_squared_error, make_scorer

# Plotting
import matplotlib.pyplot as plt
import seaborn as sns
sns.set(style="whitegrid")

RANDOM_STATE = 42

# 1. CRISP-DM: Data understanding & load
url = "https://gist.githubusercontent.com/GaneshSparkz/b5662effbdae8746f7f7d8ed70c42b2d/raw/faf8b1a0d58e251f48a647d3881e7a960c3f0925/50_Startups.csv"
# read directly from URL (pandas can do this)
df = pd.read_csv(url)

# quick look
print("資料 shape:", df.shape)
print(df.head())

# 2. Data preprocessing (資料準備)
# target
target = "Profit"

# features
num_features = ["R&D Spend", "Administration", "Marketing Spend"]
cat_features = ["State"]

# If there are stray spaces in column names, strip them:
df.columns = [c.strip() for c in df.columns]

X = df[num_features + cat_features]
y = df[target].values

# Preprocessing pipeline: OneHot for state + StandardScaler for numeric
preproc = ColumnTransformer(transformers=[
    ("num", StandardScaler(), num_features),
    ("cat", OneHotEncoder(sparse=False, drop='first'), cat_features)  # drop first to avoid collinearity
])

# helper: evaluate pipeline with given estimator
cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
rmse_scorer = make_scorer(lambda y_true, y_pred: mean_squared_error(y_true, y_pred, squared=False), greater_is_better=False)
# note: make_scorer expects greater_is_better; we'll compute RMSE manually with cross_val_score using neg MSE for clarity below

def cv_rmse(pipe, X, y):
    # return mean RMSE across folds
    neg_mse = cross_val_score(pipe, X, y, scoring="neg_mean_squared_error", cv=cv)
    rmse = np.sqrt(-neg_mse)
    return rmse.mean(), rmse.std()

# 3. Baseline: Linear Regression with all features
pipe_baseline = Pipeline([
    ("pre", preproc),
    ("reg", LinearRegression())
])
baseline_mean_rmse, baseline_std = cv_rmse(pipe_baseline, X, y)
print(f"Baseline LinearRegression RMSE: {baseline_mean_rmse:.2f} ± {baseline_std:.2f}")

# Fit baseline to get coefficients (for plotting)
pipe_baseline.fit(X, y)
# get feature names after preprocessing
onehot = pipe_baseline.named_steps["pre"].named_transformers_["cat"]
cat_names = onehot.get_feature_names_out(cat_features).tolist()
feature_names = num_features + cat_names
coefs = pipe_baseline.named_steps["reg"].coef_
coef_df = pd.DataFrame({"feature": feature_names, "coef": coefs})
coef_df["abs_coef"] = coef_df["coef"].abs()
coef_df = coef_df.sort_values("abs_coef", ascending=False)
print("\nBaseline coefficients:")
print(coef_df)

# 4. LassoCV (L1 selection)
pipe_lasso = Pipeline([
    ("pre", preproc),
    ("lasso", LassoCV(cv=5, random_state=RANDOM_STATE, max_iter=5000))
])
lasso_mean_rmse, lasso_std = cv_rmse(pipe_lasso, X, y)
print(f"\nLassoCV RMSE: {lasso_mean_rmse:.2f} ± {lasso_std:.2f}")

pipe_lasso.fit(X, y)
lasso_coef = pipe_lasso.named_steps["lasso"].coef_
lasso_df = pd.DataFrame({"feature": feature_names, "coef": lasso_coef})
lasso_df["selected"] = lasso_df["coef"].abs() > 1e-6
print("\nLasso selected features:")
print(lasso_df.sort_values("coef", key=lambda s: s.abs(), ascending=False))

# 5. Random Forest feature importance
pipe_rf = Pipeline([
    ("pre", preproc),
    ("rf", RandomForestRegressor(n_estimators=200, random_state=RANDOM_STATE))
])
rf_mean_rmse, rf_std = cv_rmse(pipe_rf, X, y)
print(f"\nRandomForest RMSE: {rf_mean_rmse:.2f} ± {rf_std:.2f}")

pipe_rf.fit(X, y)
rf_imp = pipe_rf.named_steps["rf"].feature_importances_
rf_df = pd.DataFrame({"feature": feature_names, "importance": rf_imp})
rf_df = rf_df.sort_values("importance", ascending=False)
print("\nRandomForest importances:")
print(rf_df)

# For RandomForest-based selection, pick top-k (k = 3 as example)
k = 3
rf_topk = rf_df.head(k)["feature"].tolist()

# 6. Forward Selection (SequentialFeatureSelector) — 前向選擇
# We'll use a simple linear regressor as the estimator for selection
est = LinearRegression()
# sequential selector expects numeric matrix; we'll run selection after preprocessing - so we build a small helper
X_pre = preproc.fit_transform(X)  # numpy array
# feature names already in feature_names
sfs_forward = SequentialFeatureSelector(est, n_features_to_select=3, direction="forward", cv=5)
sfs_forward.fit(X_pre, y)
mask_forward = sfs_forward.get_support()
selected_forward = [f for f, m in zip(feature_names, mask_forward) if m]
print("\nForward-selected features (n=3):", selected_forward)

# Evaluate performance of model trained only on forward-selected features
from sklearn.linear_model import Ridge
# create pipeline that selects columns by mask in preprocessed array
def evaluate_on_mask(mask, estimator=LinearRegression()):
    # build pipeline that uses preproc then a custom selector by index
    from sklearn.base import TransformerMixin, BaseEstimator
    class ColumnSelector(TransformerMixin, BaseEstimator):
        def __init__(self, mask):
            self.mask = np.array(mask)
        def fit(self, X, y=None):
            return self
        def transform(self, X):
            return X[:, self.mask]
    pipe = Pipeline([
        ("pre", preproc),
        ("select", ColumnSelector(mask)),
        ("reg", estimator)
    ])
    return cv_rmse(pipe, X, y)

forward_mean_rmse, forward_std = evaluate_on_mask(mask_forward, LinearRegression())
print(f"Forward-selection LinearRegression RMSE: {forward_mean_rmse:.2f} ± {forward_std:.2f}")

# 7. Elimination (RFE) - recursive elimination with LinearRegression
# RFE acts on numeric arrays, so we use X_pre and feature_names
rfe = RFE(estimator=LinearRegression(), n_features_to_select=3)
rfe.fit(X_pre, y)
mask_rfe = rfe.get_support()
selected_rfe = [f for f, m in zip(feature_names, mask_rfe) if m]
print("\nRFE-selected features (n=3):", selected_rfe)

rfe_mean_rmse, rfe_std = evaluate_on_mask(mask_rfe, LinearRegression())
print(f"RFE LinearRegression RMSE: {rfe_mean_rmse:.2f} ± {rfe_std:.2f}")

# 8. Collect results and plot
results = pd.DataFrame([
    {"method": "Baseline (all)", "mean_rmse": baseline_mean_rmse, "std_rmse": baseline_std},
    {"method": "LassoCV", "mean_rmse": lasso_mean_rmse, "std_rmse": lasso_std},
    {"method": "RandomForest", "mean_rmse": rf_mean_rmse, "std_rmse": rf_std},
    {"method": "ForwardSelect (3)", "mean_rmse": forward_mean_rmse, "std_rmse": forward_std},
    {"method": "RFE (3)", "mean_rmse": rfe_mean_rmse, "std_rmse": rfe_std},
])

print("\nSummary results:")
print(results)

# Plot 1: RMSE comparison
plt.figure(figsize=(8,5))
sns.barplot(x="method", y="mean_rmse", data=results, palette="muted", yerr=results["std_rmse"])
plt.ylabel("CV RMSE")
plt.title("Method comparison (lower is better)")
plt.xticks(rotation=30)
plt.tight_layout()
plt.show()

# Plot 2: Feature coefficients/importances side-by-side
# Merge baseline coefs, lasso coefs, rf importances
plot_df = pd.DataFrame({"feature": feature_names})
plot_df = plot_df.merge(coef_df[["feature", "coef"]], on="feature", how="left")
plot_df = plot_df.merge(lasso_df[["feature", "coef"]].rename(columns={"coef":"lasso_coef"}), on="feature", how="left")
plot_df = plot_df.merge(rf_df[["feature", "importance"]], on="feature", how="left")
# Fill NaN with 0
plot_df = plot_df.fillna(0)

# plot grouped bars
x = np.arange(len(plot_df))
width = 0.25
plt.figure(figsize=(10,5))
plt.bar(x - width, plot_df["coef"].abs(), width=width, label="Linear coef (abs)")
plt.bar(x, plot_df["lasso_coef"].abs(), width=width, label="Lasso coef (abs)")
plt.bar(x + width, plot_df["importance"], width=width, label="RF importance")
plt.xticks(x, plot_df["feature"], rotation=30)
plt.ylabel("magnitude")
plt.title("Feature magnitude: Linear vs Lasso vs RF")
plt.legend()
plt.tight_layout()
plt.show()

# Print selected features summary
print("\nSelected features by method:")
print("Lasso selected:", lasso_df[lasso_df['selected']]['feature'].tolist())
print("RF top-{}:".format(k), rf_topk)
print("Forward (3):", selected_forward)
print("RFE (3):", selected_rfe)
