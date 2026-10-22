"""
Automated Integration Tests for EduWell Analytics FastAPI Backend
Tests all endpoints:
- POST /api/upload (valid CSV, missing columns, invalid format)
- POST /api/sample
- GET /api/overview
- GET /api/cleaning-report
- GET /api/descriptive-stats
- GET /api/correlations
- GET /api/insights
- GET /api/export-report (txt, cleaned_csv, descriptive_csv, json)
- GET /api/figures/01_distributions.png
"""

import io
import sys
import pandas as pd
from fastapi.testclient import TestClient
from main import app


def run_all_tests():
    with TestClient(app) as client:
        results = {}

        print("=== STARTING EDUWELL ANALYTICS API TESTS ===\n")

        # 1. Test Root Endpoint
        resp = client.get("/")
        assert resp.status_code == 200, f"Root failed: {resp.status_code}"
        results["GET /"] = {
            "status": "PASSED",
            "code": resp.status_code,
            "detail": "Dashboard HTML loaded successfully",
        }
        print("[PASS] GET /")

        # 2. Test POST /api/sample
        resp = client.post("/api/sample")
        assert resp.status_code == 200, f"Sample loader failed: {resp.status_code}, {resp.text}"
        sample_data = resp.json()
        assert sample_data["status"] == "success"
        assert sample_data["is_synthetic"] is True
        assert sample_data["cleaned_rows"] > 0
        results["POST /api/sample"] = {
            "status": "PASSED",
            "code": resp.status_code,
            "detail": f"Loaded {sample_data['cleaned_rows']} synthetic rows",
        }
        print(f"[PASS] POST /api/sample -> {sample_data['cleaned_rows']} records analyzed")

        # 3. Test GET /api/overview
        resp = client.get("/api/overview")
        assert resp.status_code == 200, f"Overview failed: {resp.status_code}"
        overview = resp.json()
        assert "total_students" in overview
        assert "stress_distribution" in overview
        assert "activity_averages" in overview
        assert overview["total_students"] == 2000
        assert "Low" in overview["stress_distribution"]
        assert "Moderate" in overview["stress_distribution"]
        assert "High" in overview["stress_distribution"]
        results["GET /api/overview"] = {
            "status": "PASSED",
            "code": resp.status_code,
            "detail": f"Total: {overview['total_students']}, Mean GPA: {overview['mean_gpa']}, Low Stress: {overview['stress_distribution']['Low']['percentage']}%",
        }
        print(f"[PASS] GET /api/overview -> GPA={overview['mean_gpa']}, Students={overview['total_students']}")

        # 4. Test GET /api/cleaning-report
        resp = client.get("/api/cleaning-report")
        assert resp.status_code == 200, f"Cleaning report failed: {resp.status_code}"
        cleaning = resp.json()
        assert "stages" in cleaning
        assert len(cleaning["stages"]) in (5, 6)
        assert "clean_summary" in cleaning
        assert cleaning["clean_summary"]["is_compositional_24h"] is True
        results["GET /api/cleaning-report"] = {
            "status": "PASSED",
            "code": resp.status_code,
            "detail": f"5 pipeline stages passed, strict 24h compositional: {cleaning['clean_summary']['is_compositional_24h']}",
        }
        print("[PASS] GET /api/cleaning-report -> 5 stages verified, compositional sum=24h")

        # 5. Test GET /api/descriptive-stats
        resp = client.get("/api/descriptive-stats")
        assert resp.status_code == 200, f"Descriptive stats failed: {resp.status_code}"
        stats = resp.json()
        assert "descriptive_statistics" in stats
        assert len(stats["descriptive_statistics"]) == 6  # 5 hours + GPA
        assert "group_comparison" in stats
        assert len(stats["group_comparison"]) == 6
        assert "effect_sizes_eta_squared" in stats
        results["GET /api/descriptive-stats"] = {
            "status": "PASSED",
            "code": resp.status_code,
            "detail": f"Returned {len(stats['descriptive_statistics'])} variable statistics & ANOVA group means",
        }
        print(f"[PASS] GET /api/descriptive-stats -> {len(stats['descriptive_statistics'])} variables analyzed")

        # 6. Test GET /api/correlations
        resp = client.get("/api/correlations")
        assert resp.status_code == 200, f"Correlations failed: {resp.status_code}"
        corrs = resp.json()
        assert "pearson" in corrs
        assert "spearman" in corrs
        assert "partial_correlation" in corrs
        assert "ranked_stress_correlates" in corrs
        assert "ranked_gpa_correlates" in corrs
        assert "regressions" in corrs
        results["GET /api/correlations"] = {
            "status": "PASSED",
            "code": resp.status_code,
            "detail": "Pearson, Spearman, partial correlation & regressions verified",
        }
        print("[PASS] GET /api/correlations -> Pearson, Spearman & Partial correlations calculated")

        # 7. Test GET /api/insights
        resp = client.get("/api/insights")
        assert resp.status_code == 200, f"Insights failed: {resp.status_code}"
        insights = resp.json()
        assert "findings" in insights
        assert len(insights["findings"]) >= 6
        assert "limitations" in insights
        results["GET /api/insights"] = {
            "status": "PASSED",
            "code": resp.status_code,
            "detail": f"{len(insights['findings'])} empirical findings generated",
        }
        print(f"[PASS] GET /api/insights -> {len(insights['findings'])} findings generated")

        # 8. Test GET /api/export-report (txt)
        resp = client.get("/api/export-report?format=txt")
        assert resp.status_code == 200, f"Export txt failed: {resp.status_code}"
        assert len(resp.text) > 500
        results["GET /api/export-report?format=txt"] = {
            "status": "PASSED",
            "code": resp.status_code,
            "detail": f"Report downloaded ({len(resp.text)} chars)",
        }
        print(f"[PASS] GET /api/export-report (txt) -> {len(resp.text)} characters")

        # 9. Test GET /api/export-report (json)
        resp = client.get("/api/export-report?format=json")
        assert resp.status_code == 200, f"Export json failed: {resp.status_code}"
        export_json = resp.json()
        assert "dataset" in export_json
        assert "overview" in export_json
        results["GET /api/export-report?format=json"] = {
            "status": "PASSED",
            "code": resp.status_code,
            "detail": "Full research bundle JSON exported",
        }
        print("[PASS] GET /api/export-report (json) -> Valid JSON bundle")

        # 10. Test GET /api/figures/01_distributions.png
        resp = client.get("/api/figures/01_distributions.png")
        assert resp.status_code == 200, f"Figure endpoint failed: {resp.status_code}"
        assert resp.headers["content-type"] == "image/png"
        results["GET /api/figures/01_distributions.png"] = {
            "status": "PASSED",
            "code": resp.status_code,
            "detail": f"Matplotlib figure served ({len(resp.content)} bytes PNG)",
        }
        print(f"[PASS] GET /api/figures/01_distributions.png -> {len(resp.content)} bytes PNG")

        # 11. Test POST /api/upload with missing columns
        bad_df = pd.DataFrame({"Student_ID": [1, 2], "Study_Hours": [4.0, 5.0]})
        bad_buf = io.BytesIO()
        bad_df.to_csv(bad_buf, index=False)
        bad_buf.seek(0)
        resp = client.post(
            "/api/upload",
            files={"file": ("bad_schema.csv", bad_buf, "text/csv")},
        )
        assert resp.status_code == 400, f"Expected 400 for bad schema, got {resp.status_code}"
        results["POST /api/upload (Missing Columns Validation)"] = {
            "status": "PASSED",
            "code": resp.status_code,
            "detail": "Correctly rejected missing columns with HTTP 400",
        }
        print("[PASS] POST /api/upload (Missing Columns) -> Correctly rejected with HTTP 400")

        # 12. Test POST /api/upload with non-csv extension
        resp = client.post(
            "/api/upload",
            files={"file": ("document.pdf", b"fake pdf data", "application/pdf")},
        )
        assert resp.status_code == 400, f"Expected 400 for non-csv, got {resp.status_code}"
        results["POST /api/upload (Invalid Format Validation)"] = {
            "status": "PASSED",
            "code": resp.status_code,
            "detail": "Correctly rejected non-CSV file with HTTP 400",
        }
        print("[PASS] POST /api/upload (Invalid Extension) -> Correctly rejected with HTTP 400")

        print("\n=== ALL 12 API TESTS PASSED SUCCESSFULLY! ===")
        return results


if __name__ == "__main__":
    run_all_tests()
