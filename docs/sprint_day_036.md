# Sprint 6 — Day 36
# Company Clustering using K-Means

## Objective

Implemented an unsupervised machine learning pipeline to automatically group Nifty 100 companies based on their financial characteristics.

This module creates reusable company clusters that will later power portfolio segmentation, peer comparisons, recommendation engines, and intelligent financial analytics.

---

# Features Implemented

- Built company feature engineering pipeline for clustering.
- Combined financial ratios, growth metrics, profitability and leverage.
- Added automatic data-quality validation before clustering.
- Added financial ratio sanity checks.
- Repaired invalid ROE values using trusted company master data.
- Reconstructed incorrect Operating Profit Margin values using Profit & Loss statements.
- Deferred unrealistic Free Cash Flow CAGR values to sector-median imputation.
- Implemented hierarchical missing-value imputation.
  - Broad-sector median
  - Portfolio median fallback
- Standardized features using StandardScaler.
- Implemented KMeans clustering.
- Generated Elbow Curve for cluster selection.
- Calculated company distance from assigned cluster centroid.
- Exported clustering outputs for downstream analytics.

---

# Data Quality Improvements

Several raw financial ratios contained unrealistic values caused by inconsistencies in source tables.

Examples include:

- BEL ROE > 4700%
- HAL ROE > 3800%
- INDIGO ROE > 890%
- Multiple Operating Margin values above 1000%
- Extremely high Free Cash Flow CAGR values

The clustering pipeline now automatically detects these anomalies and repairs them using:

- Company master metrics
- Profit & Loss reconstruction
- Sector-median imputation
- Portfolio-median fallback

This prevents outliers from dominating KMeans.

---

# Machine Learning Pipeline

Financial Data
↓

Data Validation
↓

Automatic Repairs
↓

Feature Engineering
↓

Missing Value Imputation
↓

Feature Scaling

(StandardScaler)
↓

KMeans Clustering

(k = 5)
↓

Cluster Labels

↓

Distance From Centroid

↓

CSV Export

---

# Outputs Generated

## Cluster Labels

```
output/cluster_labels.csv
```

Contains:

- Company
- Assigned Cluster
- Cluster Name
- Distance From Centroid

---

## Feature Audit

```
output/clustering_features.csv
```

Contains all engineered features used by KMeans.

---

## Repair Audit

```
output/clustering_data_repairs.csv
```

Contains every automatic repair performed during preprocessing.

---

## Elbow Plot

```
reports/elbow_plot.png
```

Used to validate the chosen number of clusters.

---

# Validation Results

## Companies

- Official Companies: 92
- Companies Clustered: 92
- Unique Companies: 92

---

## Data Quality

- Missing Cluster IDs: 0
- Missing Distances: 0
- Missing Feature Values: 0

---

## Cluster Distribution

| Cluster | Companies |
|----------|----------:|
| Cluster 0 | 43 |
| Cluster 1 | 9 |
| Cluster 2 | 6 |
| Cluster 3 | 13 |
| Cluster 4 | 21 |

---

## Validation Status

PASS

---

# Skills Demonstrated

- Unsupervised Machine Learning
- KMeans Clustering
- Feature Engineering
- Financial Analytics
- Data Cleaning
- Missing Value Imputation
- Outlier Detection
- StandardScaler
- Cluster Analysis
- Data Validation
- Financial Data Engineering
- Python
- Pandas
- NumPy
- Scikit-learn
- SQLite

---

# Files Added

```
src/analytics/clustering.py
```

```
output/cluster_labels.csv
```

```
output/clustering_features.csv
```

```
output/clustering_data_repairs.csv
```

```
reports/elbow_plot.png
```

```
docs/sprint_day_036.md
```

---

# Result

Successfully built a production-ready clustering pipeline that automatically validates, repairs, engineers, scales, and clusters all official Nifty 100 companies into meaningful financial peer groups for downstream analytics.

---