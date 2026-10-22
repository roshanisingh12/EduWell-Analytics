"""
EduWell Analytics - analysis service.

Runs the student_lifestyle_analysis pipeline on one dataset and precomputes
every payload the API serves, so GET requests are plain dictionary lookups.
Each analysis writes its CSVs, figures and report into its own work folder.
"""

import io
import logging
import os
import re
import shutil
import tempfile
import threading
import warnings
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats as sps

import student_lifestyle_analysis as sla

logger = logging.getLogger("eduwell.analysis")

sla.VERBOSE = False

NUM_COLS = sla.HOUR_COLS + ["GPA"]
CORR_COLS = sla.HOUR_COLS + ["Stress_Score", "GPA"]
STUDY, SLEEP, ACTIVITY = "Study_Hours_Per_Day", "Sleep_Hours_Per_Day", "Physical_Activity_Hours_Per_Day"

MIN_ROWS = 10
MIN_PER_LEVEL = 2
SCATTER_SAMPLE_SIZE = 400
HIST_BINS = 20
PREVIEW_ROWS = 8
FIGURE_NAMES = [
    "01_distributions.png", "02_stress_distribution.png", "03_stress_pie.png", "04_boxplots_by_stress.png",
    "05_group_means.png", "06_study_vs_gpa.png", "07a_sleep_vs_stress.png", "07b_activity_vs_stress.png",
    "08_target_correlations.png", "09_gpa_by_study_band.png", "10a_heatmap_pearson.png", "10b_heatmap_spearman.png",
]

# File name in the work folder -> download name
EXPORT_FILES = {
    "report.txt": "eduwell_analytics_report.txt",
    "cleaned_data.csv": "cleaned_student_lifestyle_data.csv",
    "descriptive_stats.csv": "descriptive_statistics.csv",
    "group_comparison.csv": "stress_group_comparison.csv",
    "pearson_corr.csv": "pearson_correlations.csv",
    "spearman_corr.csv": "spearman_correlations.csv",
}

# The pipeline keeps its output folder and report in module globals, and
# Matplotlib is not thread-safe, so only one analysis may run at a time.
_pipeline_lock = threading.Lock()


class DatasetError(Exception):
    """The dataset cannot be analysed. The message is safe to show to users."""

    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


class AnalysisBusyError(Exception):
    """Another analysis held the pipeline for longer than the wait limit."""


def jsonable(obj: Any) -> Any:
    """Recursively converts NumPy/Pandas values to JSON-safe Python types (NaN -> None)."""
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return jsonable(obj.tolist())
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return round(float(obj), 4) if np.isfinite(obj) else None
    if isinstance(obj, pd.Series):
        return jsonable(obj.to_dict())
    if isinstance(obj, pd.DataFrame):
        return jsonable(obj.to_dict(orient="records"))
    return obj


def label(col: str) -> str:
    return "Stress" if col == "Stress_Score" else sla.short(col)


# ----------------------------------------------------------------------
# Parsing and validation
# ----------------------------------------------------------------------
def parse_csv(content: bytes, max_rows: int) -> pd.DataFrame:
    """Parses uploaded CSV bytes and maps headers to the required schema (case-insensitive)."""
    if not content.strip():
        raise DatasetError("The uploaded file is empty.", status_code=400)
    df = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=encoding, nrows=max_rows + 1)
            break
        except UnicodeDecodeError:
            continue
        except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
            raise DatasetError(f"Unable to parse the CSV file: {exc}", status_code=400) from exc
    if len(df) > max_rows:
        raise DatasetError(f"The file has more than {max_rows:,} rows, which is the upload limit.", status_code=413)
    return normalize_columns(df)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    canonical = {c.lower(): c for c in sla.REQUIRED_COLS}
    rename = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in canonical:
            rename[col] = canonical[key]
    if len(set(rename.values())) < len(rename):
        raise DatasetError("The file has duplicate columns that differ only by case or spacing.", status_code=400)
    df = df.rename(columns=rename)
    missing = [c for c in sla.REQUIRED_COLS if c not in df.columns]
    if missing:
        raise DatasetError(f"Uploaded CSV is missing mandatory columns: {', '.join(missing)}", status_code=400)
    return df


def _raw_diagnostics(raw: pd.DataFrame) -> Dict[str, Any]:
    """Counts the rows each cleaning step will remove, mirroring sla.clean_data."""
    missing = {c: int(raw[c].isna().sum()) for c in sla.REQUIRED_COLS}
    dup_rows = int(raw.duplicated().sum())
    dup_ids = int(raw["Student_ID"].duplicated().sum())

    df = raw.drop_duplicates()
    nums = df[NUM_COLS].apply(pd.to_numeric, errors="coerce")
    non_numeric = int((nums.isna() & df[NUM_COLS].notna()).sum().sum())
    incomplete = nums.isna().any(axis=1) | df["Stress_Level"].isna()
    df, nums = df[~incomplete], nums[~incomplete]

    levels = df["Stress_Level"].astype(str).str.strip().str.title()
    bad_level = ~levels.isin(sla.STRESS_ORDER)
    nums = nums[~bad_level]

    bad_hours = ((nums[sla.HOUR_COLS] < 0) | (nums[sla.HOUR_COLS] > 24)).any(axis=1)
    bad_gpa = (nums["GPA"] < 0) | (nums["GPA"] > 4.0)
    return {
        "missing_values_per_column": missing,
        "missing_values_total": int(sum(missing.values())),
        "non_numeric_values": non_numeric,
        "duplicate_rows": dup_rows,
        "duplicate_student_ids": dup_ids,
        "dropped_incomplete_rows": int(incomplete.sum()),
        "dropped_invalid_stress_rows": int(bad_level.sum()),
        "unexpected_stress_labels": sorted(set(levels[bad_level]))[:10],
        "invalid_hours_rows": int(bad_hours.sum()),
        "invalid_gpa_rows": int(bad_gpa.sum()),
        "dropped_out_of_range_rows": int((bad_hours | bad_gpa).sum()),
        "raw_memory_bytes": int(raw.memory_usage(deep=True).sum()),
    }


def _check_analysable(df: pd.DataFrame) -> None:
    if len(df) < MIN_ROWS:
        raise DatasetError(
            f"Only {len(df)} valid row(s) remain after cleaning; at least {MIN_ROWS} are needed for the analysis."
        )
    counts = df["Stress_Level"].value_counts()
    thin = [lvl for lvl in sla.STRESS_ORDER if counts.get(lvl, 0) < MIN_PER_LEVEL]
    if thin:
        raise DatasetError(
            f"Each stress level (Low, Moderate, High) needs at least {MIN_PER_LEVEL} valid rows. "
            f"Too few rows for: {', '.join(thin)}."
        )
    constant = [label(c) for c in NUM_COLS if df[c].nunique() < 2]
    if constant:
        raise DatasetError(
            f"These columns have the same value in every row, so correlations cannot be computed: {', '.join(constant)}."
        )


# ----------------------------------------------------------------------
# Result container
# ----------------------------------------------------------------------
@dataclass
class AnalysisResult:
    work_dir: str
    summary: Dict[str, Any]
    dataset: Dict[str, Any]
    overview: Dict[str, Any]
    cleaning: Dict[str, Any]
    stats: Dict[str, Any]
    correlations: Dict[str, Any]
    insights: Dict[str, Any]
    plot_inputs: tuple = ()
    figures_ready: bool = False

    def path(self, name: str) -> str:
        return os.path.join(self.work_dir, name)

    def figure_path(self, name: str) -> Optional[str]:
        """Path of a rendered figure; call ensure_figures() first."""
        path = os.path.join(self.work_dir, "figures", name)
        return path if name in FIGURE_NAMES and os.path.isfile(path) else None

    def export_json(self) -> Dict[str, Any]:
        return {
            "dataset": self.summary,
            "overview": self.overview,
            "cleaning": self.cleaning,
            "stats": self.stats,
            "correlations": self.correlations,
            "insights": self.insights,
        }

    def export_zip(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, download in EXPORT_FILES.items():
                if os.path.isfile(self.path(name)):
                    zf.write(self.path(name), download)
            for fig in FIGURE_NAMES:
                if self.figure_path(fig):
                        zf.write(os.path.join(self.work_dir, "figures", fig), f"figures/{fig}")
        return buf.getvalue()

    def dispose(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)


# ----------------------------------------------------------------------
# Pipeline
# ----------------------------------------------------------------------
def run_analysis(raw: pd.DataFrame, filename: str, is_synthetic: bool, work_root: str,
                 wait_seconds: float = 60.0) -> AnalysisResult:
    """Validates, cleans and analyses `raw` (already schema-checked) into a new work folder."""
    raw = normalize_columns(raw)
    diagnostics = _raw_diagnostics(raw)
    os.makedirs(work_root, exist_ok=True)
    work_dir = tempfile.mkdtemp(prefix="analysis-", dir=work_root)
    try:
        if not _pipeline_lock.acquire(timeout=wait_seconds):
            raise AnalysisBusyError("The server is busy with other analyses. Please try again in a minute.")
        try:
            parts = _run_pipeline(raw, work_dir)
        finally:
            _pipeline_lock.release()
        return _build_result(work_dir, filename, is_synthetic, raw, diagnostics, *parts)
    except BaseException:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise


def _run_pipeline(raw: pd.DataFrame, work_dir: str):
    saved_dirs = sla.OUT_DIR, sla.FIG_DIR
    sla.OUT_DIR, sla.FIG_DIR = work_dir, os.path.join(work_dir, "figures")
    os.makedirs(sla.FIG_DIR, exist_ok=True)
    sla.report_lines.clear()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            df = sla.clean_data(raw)
            _check_analysable(df)
            df.to_csv(os.path.join(work_dir, "cleaned_data.csv"), index=False)
            stats, counts = sla.descriptive_stats(df)
            grp, eta = sla.group_comparison(df)
            pearson, spearman = sla.correlation_analysis(df)
            sla.generate_insights(df, counts, grp, eta, pearson, spearman)
        report = "\n".join(sla.report_lines)
        with open(os.path.join(work_dir, "report.txt"), "w", encoding="utf-8") as f:
            f.write(report)
        return df, stats, counts, grp, eta, pearson, spearman, report
    except DatasetError:
        raise
    except Exception as exc:
        logger.exception("Analysis pipeline failed")
        raise DatasetError(
            "The analysis could not be completed for this dataset. "
            "Check that hour and GPA columns are numeric and stress levels are Low, Moderate or High."
        ) from exc
    finally:
        sla.OUT_DIR, sla.FIG_DIR = saved_dirs
        sla.report_lines.clear()


def _build_result(work_dir, filename, is_synthetic, raw, diag, df, stats, counts, grp, eta,
                  pearson, spearman, report) -> AnalysisResult:
    n = len(df)
    summary = {
        "filename": filename,
        "is_synthetic": is_synthetic,
        "raw_rows": len(raw),
        "raw_columns": raw.shape[1],
        "cleaned_rows": n,
        "dropped_rows": len(raw) - n,
        "features_analyzed": len(NUM_COLS),
        "features_count": len(sla.REQUIRED_COLS),
        "analyzed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    outliers = _outliers(df)
    result = AnalysisResult(
        work_dir=work_dir,
        summary=jsonable(summary),
        dataset=jsonable(_dataset_payload(summary, df, diag)),
        overview=jsonable(_overview_payload(summary, df, counts, grp, pearson, spearman, diag)),
        cleaning=jsonable(_cleaning_payload(summary, df, counts, diag, outliers)),
        stats=jsonable(_stats_payload(summary, df, stats, counts, grp, eta)),
        correlations=jsonable(_correlations_payload(df, pearson, spearman)),
        insights=jsonable(_insights_payload(summary, report)),
        plot_inputs=(df, counts, grp, pearson, spearman),
    )
    return result


def ensure_figures(result: AnalysisResult, wait_seconds: float = 60.0) -> None:
    """Renders the Matplotlib figures on first use. They take ~10 s, so the main pipeline skips them."""
    if result.figures_ready:
        return
    if not _pipeline_lock.acquire(timeout=wait_seconds):
        raise AnalysisBusyError("The server is busy with other analyses. Please try again in a minute.")
    try:
        if result.figures_ready or not os.path.isdir(result.work_dir):
            return
        saved_dirs = sla.OUT_DIR, sla.FIG_DIR
        sla.OUT_DIR, sla.FIG_DIR = result.work_dir, os.path.join(result.work_dir, "figures")
        os.makedirs(sla.FIG_DIR, exist_ok=True)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                sla.make_all_plots(*result.plot_inputs)
        finally:
            sla.OUT_DIR, sla.FIG_DIR = saved_dirs
            sla.report_lines.clear()
        result.figures_ready = True
    finally:
        _pipeline_lock.release()


# ----------------------------------------------------------------------
# Payload builders
# ----------------------------------------------------------------------
def _by_stress(grp: pd.DataFrame, col: str) -> Dict[str, float]:
    return {lvl: grp.loc[lvl, col] for lvl in sla.STRESS_ORDER}


def _five_numbers(x: pd.Series) -> Dict[str, Any]:
    q1, med, q3 = x.quantile([0.25, 0.5, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    inside = x[(x >= lo) & (x <= hi)]
    return {
        "n": len(x), "min": x.min(), "q1": q1, "median": med, "q3": q3, "max": x.max(), "mean": x.mean(),
        "whisker_low": inside.min() if len(inside) else q1,
        "whisker_high": inside.max() if len(inside) else q3,
        "lower_bound": lo, "upper_bound": hi,
        "outlier_count": int(((x < lo) | (x > hi)).sum()),
    }


def _outliers(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    return {c: _five_numbers(df[c]) for c in NUM_COLS}


def _preview_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    head = df[sla.REQUIRED_COLS].head(PREVIEW_ROWS).copy()
    head["Stress_Level"] = head["Stress_Level"].astype(str)
    head["Student_ID"] = head["Student_ID"].astype(str)
    return head.to_dict(orient="records")


def _dataset_payload(summary, df, diag) -> Dict[str, Any]:
    present = df["Stress_Level"].value_counts().reindex(sla.STRESS_ORDER).fillna(0)
    issues = diag["dropped_incomplete_rows"] + diag["dropped_invalid_stress_rows"] + diag["dropped_out_of_range_rows"]
    return {
        **summary,
        "required_columns": sla.REQUIRED_COLS,
        "checks": [
            {"key": "schema", "label": "Schema headers", "ok": True,
             "value": f"{len(sla.REQUIRED_COLS)} / {len(sla.REQUIRED_COLS)} detected",
             "detail": "All mandatory columns present (matched case-insensitively)."},
            {"key": "rows", "label": "Row depth", "ok": summary["cleaned_rows"] >= MIN_ROWS,
             "value": f"{summary['cleaned_rows']:,} rows",
             "detail": f"{summary['cleaned_rows']:,} of {summary['raw_rows']:,} rows usable after cleaning."},
            {"key": "missing", "label": "Missing values", "ok": diag["missing_values_total"] == 0,
             "value": f"{diag['missing_values_total']:,} null values",
             "detail": f"{diag['dropped_incomplete_rows']:,} incomplete or non-numeric row(s) removed."},
            {"key": "ranges", "label": "Numeric ranges", "ok": diag["dropped_out_of_range_rows"] == 0,
             "value": f"{diag['dropped_out_of_range_rows']:,} out of range",
             "detail": "Daily hours must be 0–24 and GPA 0.00–4.00."},
            {"key": "stress", "label": "Stress tiers", "ok": diag["dropped_invalid_stress_rows"] == 0,
             "value": f"{int((present > 0).sum())} levels",
             "detail": f"{diag['dropped_invalid_stress_rows']:,} row(s) with unrecognised labels removed."},
        ],
        "issues_fixed": issues + diag["duplicate_rows"],
        "preview": {"columns": sla.REQUIRED_COLS, "rows": _preview_rows(df)},
        "mean_gpa": df["GPA"].mean(),
        "mean_sleep": df[SLEEP].mean(),
    }


def _overview_payload(summary, df, counts, grp, pearson, spearman, diag) -> Dict[str, Any]:
    n = len(df)
    stress_dist = {}
    for lvl in sla.STRESS_ORDER:
        cnt = int(counts.get(lvl, 0))
        stress_dist[lvl] = {"count": cnt, "percentage": round(cnt / n * 100, 1), "color": sla.STRESS_COLORS[lvl]}

    activity = {}
    for col in sla.HOUR_COLS:
        activity[col] = {
            "label": sla.short(col),
            "mean": df[col].mean(), "std": df[col].std(), "median": df[col].median(),
            "min": df[col].min(), "max": df[col].max(),
            "share_of_day_pct": df[col].mean() / 24 * 100,
        }

    hour_pairs = [(a, b, pearson.loc[a, b]) for i, a in enumerate(sla.HOUR_COLS) for b in sla.HOUR_COLS[i + 1:]]
    a, b, r_trade = min(hour_pairs, key=lambda p: p[2])
    hours_sum = df[sla.HOUR_COLS].sum(axis=1)
    sleep = df[SLEEP]

    def by_stress(col):
        r = spearman.loc[col, "Stress_Score"]
        return {"means": _by_stress(grp, col), "rho": r, "strength": sla.strength(r)}

    return {
        "dataset_name": summary["filename"],
        "is_synthetic": summary["is_synthetic"],
        "total_students": n,
        "raw_rows": summary["raw_rows"],
        "features_count": len(sla.REQUIRED_COLS),
        "missing_values_total": diag["missing_values_total"],
        "mean_gpa": df["GPA"].mean(),
        "std_gpa": df["GPA"].std(),
        "gpa": {"min": df["GPA"].min(), "q1": df["GPA"].quantile(0.25), "median": df["GPA"].median(),
                "q3": df["GPA"].quantile(0.75), "max": df["GPA"].max()},
        "sleep": {"mean": sleep.mean(), "min": sleep.min(), "max": sleep.max(),
                  "share_7_to_9_pct": ((sleep >= 7) & (sleep <= 9)).mean() * 100},
        "stress_distribution": stress_dist,
        "activity_averages": activity,
        "compositional_daily_sum": hours_sum.mean(),
        "is_compositional_24h": bool(np.allclose(hours_sum, 24.0, atol=0.05)),
        "highlights": {
            "study_by_stress": by_stress(STUDY),
            "sleep_by_stress": by_stress(SLEEP),
            "activity_by_stress": by_stress(ACTIVITY),
            "gpa_by_stress": by_stress("GPA"),
            "strongest_tradeoff": {"x": label(a), "y": label(b), "r": r_trade, "strength": sla.strength(r_trade)},
        },
    }


def _stage_status(count: int) -> str:
    return "PASSED" if count == 0 else "FIXED"


def _cleaning_payload(summary, df, counts, diag, outliers) -> Dict[str, Any]:
    n_raw, n = summary["raw_rows"], summary["cleaned_rows"]
    hours_sum = df[sla.HOUR_COLS].sum(axis=1)
    is_24h = bool(np.allclose(hours_sum, 24.0, atol=0.05))
    n_out = sum(o["outlier_count"] for o in outliers.values())
    dup_detail = f"Removed {diag['duplicate_rows']} identical row(s)."
    if diag["duplicate_student_ids"] > diag["duplicate_rows"]:
        dup_detail += (f" {diag['duplicate_student_ids'] - diag['duplicate_rows']} Student_ID value(s) repeat with "
                       "different data and were kept.")
    stages = [
        {
            "stage": 1, "key": "missing", "name": "Missing & Non-numeric Values",
            "status": _stage_status(diag["dropped_incomplete_rows"]),
            "details": (f"Scanned {n_raw:,} rows. {diag['missing_values_total']:,} empty cell(s) and "
                        f"{diag['non_numeric_values']:,} non-numeric value(s) found; "
                        f"{diag['dropped_incomplete_rows']:,} incomplete row(s) removed. No values were imputed."),
            "metrics": diag["missing_values_per_column"],
        },
        {
            "stage": 2, "key": "duplicates", "name": "Duplicate Removal",
            "status": "WARNING" if diag["duplicate_student_ids"] > diag["duplicate_rows"] else _stage_status(diag["duplicate_rows"]),
            "details": dup_detail,
            "metrics": {"duplicate_rows": diag["duplicate_rows"], "duplicate_student_ids": diag["duplicate_student_ids"]},
        },
        {
            "stage": 3, "key": "encoding", "name": "Stress Label Standardisation & Ordinal Encoding",
            "status": _stage_status(diag["dropped_invalid_stress_rows"]),
            "details": ("Labels trimmed and title-cased, then encoded Low=1, Moderate=2, High=3. "
                        f"{diag['dropped_invalid_stress_rows']:,} row(s) with other labels removed."),
            "unexpected_labels": diag["unexpected_stress_labels"],
            "encoding": [{"label": lvl, "code": sla.STRESS_MAP[lvl], "count": int(counts.get(lvl, 0)),
                          "percentage": counts.get(lvl, 0) / n * 100} for lvl in sla.STRESS_ORDER],
        },
        {
            "stage": 4, "key": "ranges", "name": "Range & Domain Validation",
            "status": _stage_status(diag["dropped_out_of_range_rows"]),
            "details": (f"Hours bounded [0, 24], GPA bounded [0.0, 4.0]. {diag['invalid_hours_rows']:,} row(s) with "
                        f"invalid hours and {diag['invalid_gpa_rows']:,} with invalid GPA removed."),
            "metrics": {"gpa_min": df["GPA"].min(), "gpa_max": df["GPA"].max(),
                        "hours_min": df[sla.HOUR_COLS].min().min(), "hours_max": df[sla.HOUR_COLS].max().max()},
        },
        {
            "stage": 5, "key": "composition", "name": "24-Hour Time Budget Check",
            "status": "VERIFIED" if is_24h else "VARIABLE",
            "is_strict_24h": is_24h,
            "daily_hours_summary": {"min": hours_sum.min(), "max": hours_sum.max(), "mean": hours_sum.mean()},
            "details": ("The five lifestyle hour columns sum to 24 h for every student (a closed compositional "
                        "system), so correlations between them are partly built into the data."
                        if is_24h else
                        "Daily lifestyle hours do not always sum to 24 h, so the hour columns are not strictly compositional."),
        },
        {
            "stage": 6, "key": "outliers", "name": "IQR Outlier Detection",
            "status": "COMPLETED",
            "details": f"{n_out:,} value(s) outside Tukey fences (1.5 × IQR) were flagged and kept in the analysis.",
            "outliers_by_variable": outliers,
        },
    ]
    return {
        "filename": summary["filename"],
        "is_synthetic": summary["is_synthetic"],
        "initial_rows": n_raw,
        "cleaned_rows": n,
        "dropped_rows": n_raw - n,
        "retention_rate_pct": round(n / n_raw * 100, 2) if n_raw else 0.0,
        "outliers_flagged": n_out,
        "stages": stages,
        "memory": {"raw_bytes": diag["raw_memory_bytes"], "cleaned_bytes": int(df.memory_usage(deep=True).sum())},
        "clean_summary": {**diag, "initial_rows": n_raw, "cleaned_rows": n, "dropped_rows": n_raw - n,
                          "is_compositional_24h": is_24h,
                          "daily_hours_summary": {"min": hours_sum.min(), "max": hours_sum.max(), "mean": hours_sum.mean()},
                          "outliers_iqr": outliers},
    }


def _stats_payload(summary, df, stats, counts, grp, eta) -> Dict[str, Any]:
    desc = stats.reset_index()
    desc["Label"] = desc["Variable"].apply(sla.short)
    desc["Q1"] = [df[c].quantile(0.25) for c in desc["Variable"]]
    desc["Q3"] = [df[c].quantile(0.75) for c in desc["Variable"]]
    desc["IQR"] = desc["Q3"] - desc["Q1"]

    groups = {lvl: df[df["Stress_Level"] == lvl] for lvl in sla.STRESS_ORDER}
    grp_std = df.groupby("Stress_Level", observed=True)[NUM_COLS].std()
    comparison = []
    for var in NUM_COLS:
        f_stat, p_val = sps.f_oneway(*[g[var] for g in groups.values()])
        low, high = grp.loc["Low", var], grp.loc["High", var]
        comparison.append({
            "Variable": var, "Label": sla.short(var),
            **{lvl: grp.loc[lvl, var] for lvl in sla.STRESS_ORDER},
            **{f"{lvl}_Std": grp_std.loc[lvl, var] for lvl in sla.STRESS_ORDER},
            "Eta_Squared": eta.get(var, 0.0),
            "F_Statistic": f_stat, "P_Value": p_val,
            "Shift_High_vs_Low": high - low,
            "Shift_Pct": (high - low) / low * 100 if low else None,
        })

    histograms = {}
    for var in NUM_COLS:
        counts_h, edges = np.histogram(df[var], bins=HIST_BINS)
        histograms[var] = {"label": sla.short(var), "counts": counts_h, "edges": edges,
                           "mean": df[var].mean(), "median": df[var].median(), "skewness": df[var].skew()}

    band = pd.cut(df[STUDY], bins=[0, 4, 6, 8, 10, np.inf], labels=["<4 h", "4–6 h", "6–8 h", "8–10 h", "≥10 h"],
                  right=False)
    bands = df.groupby(band, observed=True)["GPA"].agg(["mean", "std", "count"])

    return {
        "filename": summary["filename"],
        "n": len(df),
        "descriptive_statistics": desc.to_dict(orient="records"),
        "group_sizes": {lvl: int(counts.get(lvl, 0)) for lvl in sla.STRESS_ORDER},
        "group_comparison": comparison,
        "effect_sizes_eta_squared": [{"Variable": v, "Label": sla.short(v), "Eta_Squared": e} for v, e in eta.items()],
        "boxplots": {var: {lvl: _five_numbers(g[var]) for lvl, g in groups.items()} for var in NUM_COLS},
        "histograms": histograms,
        "gpa_by_study_band": [{"band": str(b), "mean": r["mean"], "std": r["std"], "count": int(r["count"])}
                              for b, r in bands.iterrows()],
    }


def _fisher_ci(r: float, n: int, se_scale: float = 1.0, extra_df: int = 0):
    if n - 3 - extra_df <= 0:
        return None, None
    z = np.arctanh(np.clip(r, -0.999999, 0.999999))
    se = np.sqrt(se_scale / (n - 3 - extra_df))
    return np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)


def _regression(df: pd.DataFrame, x: str, y: str) -> Dict[str, Any]:
    xv, yv = df[x].to_numpy(dtype=float), df[y].to_numpy(dtype=float)
    slope, intercept = np.polyfit(xv, yv, 1)
    resid = yv - (slope * xv + intercept)
    r = np.corrcoef(xv, yv)[0, 1]
    return {
        "x": x, "y": y, "x_label": label(x), "y_label": label(y),
        "slope": slope, "intercept": intercept, "r": r, "r_squared": r * r,
        "std_error_estimate": np.sqrt((resid ** 2).sum() / (len(xv) - 2)),
        "equation": f"y = {slope:.3f}x {'+' if intercept >= 0 else '−'} {abs(intercept):.2f}",
        "x_min": xv.min(), "x_max": xv.max(),
    }


def _correlations_payload(df, pearson, spearman) -> Dict[str, Any]:
    n = len(df)
    cols = list(pearson.columns)
    labels = [label(c) for c in cols]

    def matrix(m):
        return {"columns": cols, "labels": labels, "matrix": m.values, "dict": m.to_dict()}

    def ranked(target):
        rows = [{"variable": v, "label": label(v), "correlation": r, "strength": sla.strength(r)}
                for v, r in spearman[target].drop(target).items()]
        return sorted(rows, key=lambda row: abs(row["correlation"]), reverse=True)

    raw_r = pearson.loc["Stress_Score", "GPA"]
    partial_r = sla.partial_corr(df, "Stress_Score", "GPA", STUDY)
    partial_df = n - 3
    partial_t = partial_r * np.sqrt(partial_df / max(1e-12, 1 - partial_r ** 2))
    partial_p = 2 * sps.t.sf(abs(partial_t), partial_df)
    if abs(partial_r) < 0.1 <= abs(raw_r):
        interpretation = (f"After controlling for study hours, the stress–GPA correlation falls from {raw_r:+.2f} to "
                          f"{partial_r:+.2f}. Study hours appear to drive both, so the raw link should not be read "
                          "as stress affecting GPA.")
    elif abs(partial_r) < abs(raw_r) * 0.67:
        interpretation = (f"Controlling for study hours shrinks the stress–GPA correlation from {raw_r:+.2f} to "
                          f"{partial_r:+.2f}, so study hours explain part of the relationship.")
    else:
        interpretation = (f"The stress–GPA correlation stays similar after controlling for study hours "
                          f"({raw_r:+.2f} → {partial_r:+.2f}), so study hours do not explain it.")

    tests_spec = [
        (STUDY, "GPA", "pearson"),
        (SLEEP, "Stress_Score", "spearman"),
        (ACTIVITY, "Stress_Score", "spearman"),
        (STUDY, "Stress_Score", "spearman"),
        ("Stress_Score", "GPA", "spearman"),
    ]
    n_tests = len(tests_spec) + 1
    tests = []
    for x, y, method in tests_spec:
        if method == "pearson":
            r, p = sps.pearsonr(df[x], df[y])
            lo, hi = _fisher_ci(r, n)
        else:
            r, p = sps.spearmanr(df[x], df[y])
            lo, hi = _fisher_ci(r, n, se_scale=1.06)
        tests.append({"pair": f"{label(x)} × {label(y)}", "x": x, "y": y, "method": method,
                      "coefficient": r, "strength": sla.strength(r), "p_value": p,
                      "p_adjusted": min(1.0, p * n_tests), "ci_low": lo, "ci_high": hi})
    lo, hi = _fisher_ci(partial_r, n, extra_df=1)
    tests.append({"pair": "Stress × GPA (controlling for Study)", "x": "Stress_Score", "y": "GPA",
                  "method": "partial", "coefficient": partial_r, "strength": sla.strength(partial_r),
                  "p_value": partial_p, "p_adjusted": min(1.0, partial_p * n_tests), "ci_low": lo, "ci_high": hi})
    for t in tests:
        t["significant"] = bool(t["p_adjusted"] < 0.05)

    regressions = {f"{x}|{y}": _regression(df, x, y) for x in sla.HOUR_COLS for y in ("GPA", "Stress_Score")}
    regressions["study_vs_gpa"] = regressions[f"{STUDY}|GPA"]
    regressions["sleep_vs_stress"] = regressions[f"{SLEEP}|Stress_Score"]

    sample = df.sample(n=min(n, SCATTER_SAMPLE_SIZE), random_state=0)
    scatter_cols = sla.HOUR_COLS + ["GPA", "Stress_Score"]
    rows = [[*r[scatter_cols].tolist(), str(r["Stress_Level"]), str(r["Student_ID"])] for _, r in sample.iterrows()]

    return {
        "n": n,
        "variables": cols,
        "labels": labels,
        "pearson": matrix(pearson),
        "spearman": matrix(spearman),
        "partial_correlation": {
            "relationship": "Stress Score vs Cumulative GPA",
            "control_variable": STUDY,
            "raw_pearson_r": raw_r,
            "controlled_partial_r": partial_r,
            "p_value": partial_p,
            "interpretation": interpretation,
        },
        "ranked_stress_correlates": ranked("Stress_Score"),
        "ranked_gpa_correlates": ranked("GPA"),
        "significance_tests": tests,
        "multiple_comparison_correction": f"Bonferroni (×{n_tests})",
        "regressions": regressions,
        "scatter_sample": {"columns": scatter_cols + ["Stress_Level", "Student_ID"], "rows": rows,
                           "shown": len(rows), "total": n},
    }


def _insights_payload(summary, report: str) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    limitations: List[str] = []
    section = None
    for line in report.splitlines():
        text = line.strip()
        if text.startswith("STEP 6"):
            section = "findings"
            continue
        if text == "LIMITATIONS":
            section = "limitations"
            continue
        if not text or text.startswith("="):
            continue
        if section == "findings":
            m = re.match(r"(\d+)\.\s+(.*)", text)
            if m:
                findings.append({"number": int(m.group(1)), "text": m.group(2)})
            elif findings:
                findings[-1]["text"] += " " + text
        elif section == "limitations" and text.startswith("- "):
            limitations.append(text[2:])
    return {
        "filename": summary["filename"],
        "is_synthetic": summary["is_synthetic"],
        "analyzed_at": summary["analyzed_at"],
        "findings": findings,
        "limitations": limitations,
        "full_report_text": report,
        "figures": FIGURE_NAMES,
    }
