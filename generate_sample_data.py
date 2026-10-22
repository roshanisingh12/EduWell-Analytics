"""
Synthetic Dataset Generator for EduWell Analytics
Generates a realistic, synthetic 2,000-student lifestyle and wellness dataset
adhering to the required schema, 24-hour daily budget constraint, and statistical relationships.

Clearly labeled: SYNTHETIC DATASET (Educational & Research Demonstration Only).
"""

import numpy as np
import pandas as pd


def generate_synthetic_data(num_students=2000, random_seed=42):
    rng = np.random.default_rng(random_seed)

    # Dirichlet base proportions for 5 activities:
    # [Study, Extracurricular, Sleep, Social, Physical Activity]
    # Approximate mean hours: Study ~ 7.2, Extra ~ 2.0, Sleep ~ 7.3, Social ~ 3.5, Physical ~ 4.0 -> sum = 24.0
    alpha = [7.2, 2.0, 7.4, 3.6, 3.8]
    proportions = rng.dirichlet(alpha, size=num_students)

    hours = proportions * 24.0
    # Round to 2 decimal places and balance the last column to ensure strict 24.00 sum
    hours_rounded = np.round(hours, 2)
    diff = 24.00 - hours_rounded[:, :4].sum(axis=1)
    hours_rounded[:, 4] = np.round(diff, 2)

    study = hours_rounded[:, 0]
    extra = hours_rounded[:, 1]
    sleep = hours_rounded[:, 2]
    social = hours_rounded[:, 3]
    physical = hours_rounded[:, 4]

    # GPA: positively correlated with study hours, with random variation, bounded in [2.0, 4.0]
    gpa_raw = 1.95 + 0.185 * study + rng.normal(0, 0.25, num_students)
    gpa = np.clip(np.round(gpa_raw, 2), 2.00, 4.00)

    # Stress index: increased by high study, reduced by adequate sleep and physical activity
    stress_latent = (
        0.42 * study
        - 0.40 * sleep
        - 0.28 * physical
        - 0.15 * social
        + rng.normal(0, 0.8, num_students)
    )

    q_low, q_high = np.quantile(stress_latent, [0.25, 0.65])
    stress_level = np.where(
        stress_latent <= q_low,
        "Low",
        np.where(stress_latent <= q_high, "Moderate", "High"),
    )

    student_ids = [f"STU_{i+1:04d}" for i in range(num_students)]

    df = pd.DataFrame({
        "Student_ID": student_ids,
        "Study_Hours_Per_Day": study,
        "Extracurricular_Hours_Per_Day": extra,
        "Sleep_Hours_Per_Day": sleep,
        "Social_Hours_Per_Day": social,
        "Physical_Activity_Hours_Per_Day": physical,
        "GPA": gpa,
        "Stress_Level": stress_level,
    })

    return df


if __name__ == "__main__":
    df = generate_synthetic_data()
    output_path = "student_lifestyle_dataset.csv"
    df.to_csv(output_path, index=False)
    print(f"Generated synthetic dataset with {len(df)} rows saved to {output_path}")
