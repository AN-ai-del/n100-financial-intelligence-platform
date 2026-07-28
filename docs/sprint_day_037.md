# Sprint 6 — Day 37
# Cluster Profiling & Portfolio Analytics

## Objective

Extended the KMeans clustering pipeline by generating descriptive financial profiles for every cluster, assigning business-friendly archetype names, producing portfolio statistics, performing sector-relative outlier detection, and generating KPI correlation analysis.

---

# Features Implemented

- Cluster profiling engine
- Mean and median calculation for all clustering features
- Cluster archetype generation
- Representative company identification
- Cluster descriptions
- Company-level cluster mapping
- Pearson correlation matrix generation
- Correlation heatmap export
- Sector-relative Z-score outlier detection
- Portfolio descriptive statistics
- KPI usability audit
- Day 37 validation framework

---

# Cluster Profiles Generated

Each cluster now includes:

- Company count
- Sector count
- Average ROE
- Average Debt/Equity
- Average Revenue CAGR
- Average Free Cash Flow CAGR
- Average Operating Margin
- Representative companies
- Financial archetype
- Cluster description

---

# Financial Archetypes

Generated descriptive names for all five KMeans clusters:

- Emerging Growth
- Value Cyclicals
- High-Quality Compounders
- Leveraged or Turnaround
- Defensive Cash Generators

---

# Statistical Analysis

Calculated portfolio statistics for:

- Return on Equity
- Operating Profit Margin
- Net Profit Margin
- Debt to Equity
- Interest Coverage
- Asset Turnover
- Free Cash Flow
- Earnings Per Share
- Dividend Payout Ratio
- Composite Quality Score

Statistics include:

- P10
- P25
- Median
- P75
- P90
- Mean
- Standard Deviation

---

# Outlier Detection

Implemented sector-relative Z-score analysis.

Criteria:

- |Z-score| > 3

Generated a complete outlier report for downstream financial review.

---

# Correlation Analysis

Generated Pearson correlation matrix across ten financial KPIs.

Exported:

```
reports/correlation_heatmap.png
```

---

# Validation

## Companies

- Total Companies: 92
- Unique Companies: 92

## Clusters

- Total Clusters: 5
- Unique Cluster Names: 5

## Validation Checks

- Cluster reconciliation
- Missing values
- Missing cluster names
- Output generation
- Correlation matrix dimensions
- Portfolio statistics
- Outlier validation

Result:

PASS

---

# Outputs Generated

```
output/cluster_profiles.csv
```

```
output/company_cluster_profiles.csv
```

```
output/outlier_report.csv
```

```
output/portfolio_stats.csv
```

```
output/day37_validation_summary.csv
```

```
reports/correlation_heatmap.png
```

---

# Skills Demonstrated

- KMeans Cluster Interpretation
- Cluster Profiling
- Financial Analytics
- Descriptive Statistics
- Correlation Analysis
- Outlier Detection
- Z-score Analysis
- Feature Engineering
- Data Validation
- Portfolio Analytics
- Pandas
- NumPy
- Matplotlib
- Seaborn
- SQLite

---

# Result

Successfully transformed raw KMeans clusters into business-friendly financial archetypes with statistical profiling, correlation analysis, portfolio analytics, and automated validation for downstream financial intelligence applications.