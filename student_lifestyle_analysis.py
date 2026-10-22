"""
Scientific Analysis of Student Lifestyle and Mental Wellness Using Python
=========================================================================
Libraries: NumPy, Pandas, Matplotlib only.

Pipeline:
    Dataset -> Data Cleaning -> Statistical Analysis -> Correlation Analysis
            -> Visualization -> Insights

Usage:
    python student_lifestyle_analysis.py
    python student_lifestyle_analysis.py path/to/student_lifestyle_dataset.csv

Outputs (in ./output/):
    figures/*.png, cleaned_data.csv, descriptive_stats.csv,
    group_comparison.csv, pearson_corr.csv, spearman_corr.csv, report.txt

Note: this analysis finds statistical relationships only. It does not
diagnose any mental-health condition.
"""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # save figures without needing a display
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
DEFAULT_PATH = "student_lifestyle_dataset.csv"
OUT_DIR = "output"
FIG_DIR = os.path.join(OUT_DIR, "figures")

HOUR_COLS = [
    "Study_Hours_Per_Day",
    "Extracurricular_Hours_Per_Day",
    "Sleep_Hours_Per_Day",
    "Social_Hours_Per_Day",
    "Physical_Activity_Hours_Per_Day",
]
REQUIRED_COLS = ["Student_ID"] + HOUR_COLS + ["GPA", "Stress_Level"]
STRESS_ORDER = ["Low", "Moderate", "High"]
STRESS_MAP = {"Low": 1, "Moderate": 2, "High": 3}
STRESS_COLORS = {"Low": "#4caf50", "Moderate": "#ffb300", "High": "#e53935"}

plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.25})

report_lines = []
VERBOSE = True  # False collects the report without printing it (used by the web API)


def log(text=""):
    """Print and store a line for the final report."""
    if VERBOSE:
        print(text)
    report_lines.append(str(text))


def short(col):
    """Readable axis label: Sleep_Hours_Per_Day -> Sleep"""
    return col.replace("_Hours_Per_Day", "").replace("_", " ")


# ----------------------------------------------------------------------
# 1. Load + validate
# ----------------------------------------------------------------------
def load_data(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found: {path}")
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    return df


# ----------------------------------------------------------------------
# 2. Cleaning + preprocessing
# ----------------------------------------------------------------------
def clean_data(df):
    log("=" * 70)
    log("STEP 1: DATA OVERVIEW AND CLEANING")
    log("=" * 70)
    log(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
    log("\nData types:")
    log(df.dtypes.to_string())

    # Missing values and duplicates
    log("\nMissing values per column:")
    log(df.isna().sum().to_string())
    log(f"\nDuplicate rows: {df.duplicated().sum()}")
    log(f"Duplicate Student_IDs: {df['Student_ID'].duplicated().sum()}")

    df = df.drop_duplicates().copy()
    num_cols = HOUR_COLS + ["GPA"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    before = len(df)
    df = df.dropna(subset=num_cols + ["Stress_Level"])
    log(f"Rows dropped for missing/invalid values: {before - len(df)}")

    # Standardise stress labels, then validate them
    df["Stress_Level"] = df["Stress_Level"].astype(str).str.strip().str.title()
    bad_labels = set(df["Stress_Level"]) - set(STRESS_ORDER)
    if bad_labels:
        log(f"WARNING: unexpected Stress_Level labels removed: {bad_labels}")
        df = df[df["Stress_Level"].isin(STRESS_ORDER)]

    # Range validation (hours in [0, 24], GPA in [0, 4])
    invalid_hours = ((df[HOUR_COLS] < 0) | (df[HOUR_COLS] > 24)).any(axis=1)
    invalid_gpa = (df["GPA"] < 0) | (df["GPA"] > 4.0)
    log(f"Rows with hours outside 0-24: {invalid_hours.sum()}")
    log(f"Rows with GPA outside 0-4: {invalid_gpa.sum()}")
    df = df[~invalid_hours & ~invalid_gpa]

    # Does the daily time budget add up to 24 hours?
    total = df[HOUR_COLS].sum(axis=1)
    log(f"\nTotal daily hours per student: min={total.min():.2f}, "
        f"max={total.max():.2f}, mean={total.mean():.2f}")
    if np.allclose(total, 24.0, atol=0.05):
        log("NOTE: the five hour columns add up to 24 for every student. "
            "The data is compositional: spending more time on one activity "
            "mathematically forces less on others. Correlations BETWEEN the "
            "lifestyle variables partly reflect this constraint, not "
            "behaviour.")

    # Outlier detection with the IQR rule (reported, not removed)
    log("\nOutlier check (IQR rule, outliers kept in the analysis):")
    for col in num_cols:
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_out = int(((df[col] < lo) | (df[col] > hi)).sum())
        log(f"  {col:<34} bounds=[{lo:6.2f}, {hi:6.2f}]  outliers={n_out}")

    # Ordinal encoding of the categorical stress variable
    df["Stress_Score"] = df["Stress_Level"].map(STRESS_MAP)
    df["Stress_Level"] = pd.Categorical(df["Stress_Level"],
                                        categories=STRESS_ORDER, ordered=True)
    df = df.reset_index(drop=True)
    log(f"\nCleaned dataset: {len(df)} rows")
    log("Stress_Level encoded as ordinal: Low=1, Moderate=2, High=3")
    return df


# ----------------------------------------------------------------------
# 3. Statistical analysis
# ----------------------------------------------------------------------
def descriptive_stats(df):
    log("\n" + "=" * 70)
    log("STEP 2: DESCRIPTIVE STATISTICS")
    log("=" * 70)
    cols = HOUR_COLS + ["GPA"]
    rows = []
    for c in cols:
        x = df[c].to_numpy(dtype=float)
        rows.append({
            "Variable": c,
            "Mean": np.mean(x),
            "Median": np.median(x),
            "Variance": np.var(x, ddof=1),
            "Std_Dev": np.std(x, ddof=1),
            "Min": np.min(x),
            "Max": np.max(x),
            "Skewness": float(pd.Series(x).skew()),
        })
    stats = pd.DataFrame(rows).set_index("Variable").round(3)
    log(stats.to_string())
    stats.to_csv(os.path.join(OUT_DIR, "descriptive_stats.csv"))

    log("\nStress level distribution:")
    counts = df["Stress_Level"].value_counts().reindex(STRESS_ORDER)
    pct = (counts / counts.sum() * 100).round(1)
    log(pd.DataFrame({"Count": counts, "Percent": pct}).to_string())
    return stats, counts


def group_comparison(df):
    log("\n" + "=" * 70)
    log("STEP 3: LIFESTYLE PATTERNS BY STRESS LEVEL (group means)")
    log("=" * 70)
    cols = HOUR_COLS + ["GPA"]
    grp = df.groupby("Stress_Level", observed=True)[cols].mean().round(3)
    log(grp.to_string())
    grp.to_csv(os.path.join(OUT_DIR, "group_comparison.csv"))

    log("\nGroup standard deviations:")
    log(df.groupby("Stress_Level", observed=True)[cols].std().round(3).to_string())

    # Effect size: how much of each variable's variance is explained by
    # stress group (eta-squared, computed with NumPy/Pandas only)
    log("\nEta-squared (share of variance explained by stress group):")
    eta = {}
    for c in cols:
        grand = df[c].mean()
        ss_between = sum(len(g) * (g[c].mean() - grand) ** 2
                         for _, g in df.groupby("Stress_Level", observed=True))
        ss_total = ((df[c] - grand) ** 2).sum()
        eta[c] = ss_between / ss_total
    eta = pd.Series(eta).round(3).sort_values(ascending=False)
    log(eta.to_string())
    return grp, eta


# ----------------------------------------------------------------------
# 4. Correlation analysis
# ----------------------------------------------------------------------
def correlation_analysis(df):
    log("\n" + "=" * 70)
    log("STEP 4: CORRELATION ANALYSIS")
    log("=" * 70)
    cols = HOUR_COLS + ["Stress_Score", "GPA"]
    pearson = df[cols].corr(method="pearson").round(3)
    # Spearman = Pearson on ranks (implemented without SciPy)
    spearman = df[cols].rank().corr(method="pearson").round(3)

    log("Pearson correlation matrix:")
    log(pearson.to_string())
    log("\nSpearman (rank) correlation matrix - better suited to the "
        "ordinal stress variable:")
    log(spearman.to_string())
    pearson.to_csv(os.path.join(OUT_DIR, "pearson_corr.csv"))
    spearman.to_csv(os.path.join(OUT_DIR, "spearman_corr.csv"))

    log("\nCorrelations with Stress_Score and GPA (Spearman, sorted):")
    for target in ["Stress_Score", "GPA"]:
        s = spearman[target].drop(target).sort_values(key=np.abs, ascending=False)
        log(f"\n  vs {target}:")
        for k, v in s.items():
            log(f"    {short(k):<20} {v:+.3f}  ({strength(v)})")
    log("\nControlling for study hours (partial correlation):")
    pc = partial_corr(df, "Stress_Score", "GPA", "Study_Hours_Per_Day")
    log(f"  Stress vs GPA, raw Pearson r = {pearson.loc['Stress_Score', 'GPA']:+.3f}"
        f"  ->  after controlling for study hours r = {pc:+.3f}")
    return pearson, spearman


def partial_corr(df, x, y, control):
    """Correlation between x and y after removing the linear effect of
    `control` from both (residual method, NumPy only)."""
    c = df[control].to_numpy(dtype=float)
    def resid(v):
        v = df[v].to_numpy(dtype=float)
        b, a = np.polyfit(c, v, 1)
        return v - (b * c + a)
    return float(np.corrcoef(resid(x), resid(y))[0, 1])


def strength(r):
    a = abs(r)
    if a < 0.1:
        label = "negligible"
    elif a < 0.3:
        label = "weak"
    elif a < 0.5:
        label = "moderate"
    elif a < 0.7:
        label = "strong"
    else:
        label = "very strong"
    return label


# ----------------------------------------------------------------------
# 5. Visualization
# ----------------------------------------------------------------------
def save_fig(name):
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, name), bbox_inches="tight")
    plt.close()


def plot_distributions(df):
    cols = HOUR_COLS + ["GPA"]
    fig, axes = plt.subplots(2, 3, figsize=(14, 7))
    for ax, c in zip(axes.ravel(), cols):
        ax.hist(df[c], bins=25, color="#3f6fb5", edgecolor="white")
        ax.axvline(df[c].mean(), color="#e53935", ls="--", lw=1.5,
                   label=f"mean = {df[c].mean():.2f}")
        ax.axvline(df[c].median(), color="#2e7d32", ls=":", lw=1.5,
                   label=f"median = {df[c].median():.2f}")
        ax.set_title(short(c) if c != "GPA" else "GPA")
        ax.set_xlabel("Hours per day" if c != "GPA" else "GPA")
        ax.set_ylabel("Students")
        ax.legend(fontsize=8)
    fig.suptitle("Distribution of Lifestyle Variables and GPA", fontsize=14)
    save_fig("01_distributions.png")


def plot_stress_distribution(counts):
    fig, ax = plt.subplots(figsize=(6, 4.5))
    colors = [STRESS_COLORS[k] for k in counts.index]
    bars = ax.bar(counts.index.astype(str), counts.values, color=colors)
    total = counts.sum()
    for b, v in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width() / 2, v + total * 0.01,
                f"{v}\n({v / total * 100:.1f}%)", ha="center", fontsize=9)
    ax.set_ylim(0, counts.max() * 1.18)
    ax.set_title("Students by Stress Level")
    ax.set_ylabel("Number of students")
    ax.grid(axis="x", visible=False)
    save_fig("02_stress_distribution.png")

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.pie(counts.values, labels=counts.index.astype(str), colors=colors,
           autopct="%1.1f%%", startangle=90, wedgeprops={"edgecolor": "white"})
    ax.set_title("Stress Level Share")
    save_fig("03_stress_pie.png")


def plot_boxplots_by_stress(df):
    cols = HOUR_COLS + ["GPA"]
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, c in zip(axes.ravel(), cols):
        data = [df.loc[df["Stress_Level"] == s, c] for s in STRESS_ORDER]
        bp = ax.boxplot(data, patch_artist=True, tick_labels=STRESS_ORDER,
                        medianprops={"color": "black"})
        for patch, s in zip(bp["boxes"], STRESS_ORDER):
            patch.set_facecolor(STRESS_COLORS[s])
            patch.set_alpha(0.75)
        ax.set_title(f"{short(c)} by Stress Level")
        ax.set_ylabel("Hours per day" if c != "GPA" else "GPA")
    fig.suptitle("Lifestyle Factors and GPA Across Stress Levels", fontsize=14)
    save_fig("04_boxplots_by_stress.png")


def plot_group_means(grp):
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(HOUR_COLS))
    w = 0.26
    for i, s in enumerate(STRESS_ORDER):
        ax.bar(x + (i - 1) * w, grp.loc[s, HOUR_COLS].values, w,
               label=s, color=STRESS_COLORS[s])
    ax.set_xticks(x)
    ax.set_xticklabels([short(c) for c in HOUR_COLS])
    ax.set_ylabel("Mean hours per day")
    ax.set_title("Average Daily Hours by Stress Level")
    ax.legend(title="Stress level")
    ax.grid(axis="x", visible=False)
    save_fig("05_group_means.png")


def scatter_with_trend(df, xcol, ycol, fname, jitter_y=False):
    x = df[xcol].to_numpy(dtype=float)
    y = df[ycol].to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(7, 5))
    yp = y + np.random.default_rng(0).normal(0, 0.06, len(y)) if jitter_y else y
    colors = df["Stress_Level"].astype(str).map(STRESS_COLORS)
    ax.scatter(x, yp, c=colors, alpha=0.4, s=14)
    slope, intercept = np.polyfit(x, y, 1)
    r = np.corrcoef(x, y)[0, 1]
    xs = np.linspace(x.min(), x.max(), 100)
    ax.plot(xs, slope * xs + intercept, color="black", lw=2,
            label=f"trend: y = {slope:.3f}x + {intercept:.2f}   (r = {r:.2f})")
    ax.set_xlabel(f"{short(xcol)} (hours per day)")
    ax.set_ylabel(short(ycol) if ycol == "GPA" else "Stress score (1=Low, 3=High)")
    ax.set_title(f"{short(xcol)} vs {short(ycol)}")
    handles = [plt.Line2D([], [], marker="o", ls="", color=STRESS_COLORS[s],
                          label=s) for s in STRESS_ORDER]
    leg1 = ax.legend(handles=handles, title="Stress", loc="lower right",
                     fontsize=8)
    ax.add_artist(leg1)
    ax.legend(loc="upper left", fontsize=8)
    save_fig(fname)


def plot_heatmap(corr, title, fname):
    labels = [short(c) if c != "Stress_Score" else "Stress" for c in corr.columns]
    fig, ax = plt.subplots(figsize=(8.5, 7))
    im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    for i in range(len(labels)):
        for j in range(len(labels)):
            v = corr.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=9,
                    color="white" if abs(v) > 0.6 else "black")
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Correlation")
    ax.set_title(title)
    save_fig(fname)


def plot_target_correlations(spearman):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, target, name in zip(axes, ["Stress_Score", "GPA"],
                                ["Stress", "GPA"]):
        s = spearman[target].drop(target).sort_values()
        colors = ["#e53935" if v < 0 else "#1e88e5" for v in s.values]
        ax.barh([short(k) if k != "Stress_Score" else "Stress" for k in s.index],
                s.values, color=colors)
        ax.axvline(0, color="black", lw=0.8)
        ax.set_xlim(-1, 1)
        ax.set_title(f"Spearman correlation with {name}")
        ax.set_xlabel("Correlation coefficient")
        for i, v in enumerate(s.values):
            ax.text(v + (0.02 if v >= 0 else -0.02), i, f"{v:+.2f}",
                    va="center", ha="left" if v >= 0 else "right", fontsize=9)
    save_fig("08_target_correlations.png")


def plot_gpa_by_study_band(df):
    bins = [0, 4, 6, 8, 10.01]
    labels = ["<4 h", "4-6 h", "6-8 h", "8-10 h"]
    band = pd.cut(df["Study_Hours_Per_Day"], bins=bins, labels=labels,
                  right=False)
    g = df.groupby(band, observed=True)["GPA"].agg(["mean", "std", "count"])
    fig, ax = plt.subplots(figsize=(7, 4.8))
    ax.bar(g.index.astype(str), g["mean"], yerr=g["std"], capsize=5,
           color="#3f6fb5", alpha=0.85)
    for i, (m, n) in enumerate(zip(g["mean"], g["count"])):
        ax.text(i, 0.1, f"n={n}", ha="center", color="white", fontsize=9)
    ax.set_xlabel("Study hours per day")
    ax.set_ylabel("Mean GPA (error bars = 1 SD)")
    ax.set_title("GPA by Study-Hours Band")
    ax.grid(axis="x", visible=False)
    save_fig("09_gpa_by_study_band.png")
    return g


def make_all_plots(df, counts, grp, pearson, spearman):
    log("\n" + "=" * 70)
    log("STEP 5: VISUALIZATION")
    log("=" * 70)
    plot_distributions(df)
    plot_stress_distribution(counts)
    plot_boxplots_by_stress(df)
    plot_group_means(grp)
    scatter_with_trend(df, "Study_Hours_Per_Day", "GPA", "06_study_vs_gpa.png")
    scatter_with_trend(df, "Sleep_Hours_Per_Day", "Stress_Score",
                       "07a_sleep_vs_stress.png", jitter_y=True)
    scatter_with_trend(df, "Physical_Activity_Hours_Per_Day", "Stress_Score",
                       "07b_activity_vs_stress.png", jitter_y=True)
    plot_heatmap(pearson, "Pearson Correlation Heatmap", "10a_heatmap_pearson.png")
    plot_heatmap(spearman, "Spearman Correlation Heatmap",
                 "10b_heatmap_spearman.png")
    plot_target_correlations(spearman)
    plot_gpa_by_study_band(df)
    log(f"Figures saved in: {FIG_DIR}/")


# ----------------------------------------------------------------------
# 6. Insights (generated from the computed numbers)
# ----------------------------------------------------------------------
def generate_insights(df, counts, grp, eta, pearson, spearman):
    log("\n" + "=" * 70)
    log("STEP 6: KEY INSIGHTS")
    log("=" * 70)
    n = len(df)

    top = counts.idxmax()
    log(f"1. Stress distribution: {top} stress is the most common "
        f"({counts[top]} students, {counts[top] / n * 100:.1f}%). "
        f"Low: {counts['Low'] / n * 100:.1f}%, "
        f"Moderate: {counts['Moderate'] / n * 100:.1f}%, "
        f"High: {counts['High'] / n * 100:.1f}%.")

    r = pearson.loc["Study_Hours_Per_Day", "GPA"]
    slope = np.polyfit(df["Study_Hours_Per_Day"], df["GPA"], 1)[0]
    log(f"2. Study hours vs GPA: r = {r:+.2f} ({strength(r)}). Each extra "
        f"study hour per day is associated with about {slope:+.3f} GPA points.")

    r = spearman.loc["Sleep_Hours_Per_Day", "Stress_Score"]
    log(f"3. Sleep vs stress: Spearman rho = {r:+.2f} ({strength(r)}). "
        f"Mean sleep: Low = {grp.loc['Low', 'Sleep_Hours_Per_Day']:.2f} h, "
        f"Moderate = {grp.loc['Moderate', 'Sleep_Hours_Per_Day']:.2f} h, "
        f"High = {grp.loc['High', 'Sleep_Hours_Per_Day']:.2f} h.")

    r = spearman.loc["Physical_Activity_Hours_Per_Day", "Stress_Score"]
    log(f"4. Physical activity vs stress: Spearman rho = {r:+.2f} "
        f"({strength(r)}). Mean activity: "
        f"Low = {grp.loc['Low', 'Physical_Activity_Hours_Per_Day']:.2f} h, "
        f"High = {grp.loc['High', 'Physical_Activity_Hours_Per_Day']:.2f} h.")

    r = spearman.loc["Stress_Score", "GPA"]
    log(f"5. Stress vs GPA: Spearman rho = {r:+.2f} ({strength(r)}). "
        f"Mean GPA: Low = {grp.loc['Low', 'GPA']:.2f}, "
        f"Moderate = {grp.loc['Moderate', 'GPA']:.2f}, "
        f"High = {grp.loc['High', 'GPA']:.2f}.")

    pc = partial_corr(df, "Stress_Score", "GPA", "Study_Hours_Per_Day")
    log(f"   Controlling for study hours, the stress-GPA correlation becomes "
        f"{pc:+.2f}. Study hours appear to drive both variables, so the raw "
        f"stress-GPA link should not be read as 'stress raises GPA'.")

    s = spearman["Stress_Score"].drop("Stress_Score").drop("GPA")
    best = s.abs().idxmax()
    log(f"6. Strongest lifestyle correlate of stress: {short(best)} "
        f"(rho = {s[best]:+.2f}). Strongest by variance explained "
        f"(eta-squared): {short(eta.index[0])} ({eta.iloc[0]:.2f}).")

    g = spearman["GPA"].drop(["GPA", "Stress_Score"])
    best = g.abs().idxmax()
    log(f"7. Strongest lifestyle correlate of GPA: {short(best)} "
        f"(rho = {g[best]:+.2f}).")

    log("\nLIMITATIONS")
    log("- Correlation does not imply causation: this is observational data, "
        "so a relationship cannot show that one factor causes another.")
    log("- The five hour variables sum to 24, so they are not independent. "
        "Correlations between them are partly built into the data.")
    log("- Stress is a 3-level category, so a lot of detail is lost; "
        "Spearman is used for it instead of Pearson.")
    log("- The dataset appears to be clean and possibly synthetic, so real "
        "student populations may show weaker or different patterns.")
    log("- Findings describe statistical relationships in this dataset only. "
        "They are not a diagnosis of any mental-health condition.")


# ----------------------------------------------------------------------
# Main pipeline
# ----------------------------------------------------------------------
def run_pipeline(path=DEFAULT_PATH):
    os.makedirs(FIG_DIR, exist_ok=True)
    report_lines.clear()
    raw = load_data(path)
    df = clean_data(raw)
    df.to_csv(os.path.join(OUT_DIR, "cleaned_data.csv"), index=False)

    stats, counts = descriptive_stats(df)
    grp, eta = group_comparison(df)
    pearson, spearman = correlation_analysis(df)
    make_all_plots(df, counts, grp, pearson, spearman)
    generate_insights(df, counts, grp, eta, pearson, spearman)

    with open(os.path.join(OUT_DIR, "report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\nDone. All outputs are in the '{OUT_DIR}/' folder.")
    return df


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    run_pipeline(csv_path)
