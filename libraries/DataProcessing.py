"""
Module for statistical analysis and data processing of cell survival studies.

This module provides methods for loading and normalizing cell survival data,
performing statistical significance analysis, and organizing results for
downstream visualization or comparison. The statistical analysis incorporates
ANOVA using survival data across various treatments and cell lines.

"""

import csv
from dataclasses import dataclass
import pathlib

import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import ols


class DataProcessingError(ValueError):
    """Raised when the summary files do not contain usable statistics data."""

@dataclass
class AnovaResult:
    """Makes it less of a pain to access elements of the ANOVA results later in the script."""
    comparison: str
    p_value: float
    table: pd.DataFrame


def significance(df, cell_list):
    comparison_results = []
    control_cell_line = cell_list[0]

    for cell_line in cell_list[1:]:
        # Select the two cell lines being compared.
        filtered_df = df.loc[
            df["Cell_Line"].isin([control_cell_line, cell_line])
        ].copy()

        model = ols(
            "Survival ~ C(Cell_Line) * C(Treatment)", data=filtered_df
        ).fit()
        anova_table = sm.stats.anova_lm(model, typ=2)

        # Interaction p-value that we care about is at row 3, column 4.
        interaction_p_value = float(anova_table.iat[2, 3])
        comparison_results.append(
            AnovaResult(
                comparison=f"{control_cell_line} vs {cell_line}",
                p_value=interaction_p_value,
                table=anova_table,
            )
        )

    return comparison_results


def _read_metadata(summary_file):
    """Read the cell-line metadata written above the summary table."""
    cell_line = ""
    treatment_name = ""
    is_control = False

    with open(summary_file, newline="", encoding="utf-8-sig") as handle:
        for line in csv.reader(handle, delimiter="\t"):
            if not line:
                continue

            if line[0] in ("# CTRL Sample=", "# CTRL_Sample"):
                is_control = line[1].strip().lower() in ("yes", "y", "true", "1")
            elif line[0] == "# Cell Line=":
                cell_line = line[1].strip()
            elif line[0] == "# Treatment=":
                treatment_name = line[1].strip()

    if not cell_line:
        raise DataProcessingError(
            f"{pathlib.Path(summary_file).name} does not contain a cell-line name."
        )
    return cell_line, treatment_name, is_control


def _significance_symbol(p_value):
    if p_value < 0.0001:
        return "****"
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return "ns"


def data_processing(input_path=None, output_path=None):

    selected_path = output_path or input_path
    if not selected_path:
        raise DataProcessingError("An output directory is required.")
    analysis_path = pathlib.Path(selected_path)
    summary_files = sorted(analysis_path.glob("Summary_*.txt"))
    if not summary_files:
        raise DataProcessingError(
            f"No Summary_*.txt files were found in {analysis_path}."
        )

    data_frames = []
    cell_line_names = []
    treatment_names = []
    control_cell_lines = []

    # No more dictionaries, doing pandas here now
    for summary_file in summary_files:
        cell_line, treatment_name, is_control = _read_metadata(summary_file)
        summary_data = pd.read_csv(summary_file, sep="\t", comment="#")

        # The Jython writer pads fields for a readable plain-text table. Remove that display-only whitespace after pandas splits the real tab columns.
        # No need for this anymore since writing the summary file in readable format didn't really work.
        # summary_data.columns = summary_data.columns.str.strip()
        # for column in summary_data.select_dtypes(include="object").columns:
        #     summary_data[column] = summary_data[column].str.strip()

        required_columns = {"ImageName", "Group", "Colonies"}
        missing_columns = required_columns - set(summary_data.columns)
        if missing_columns:
            raise DataProcessingError(
                f"{summary_file.name} is missing: {', '.join(sorted(missing_columns))}."
            )

        # Older summary files do not have seeded-cell information.
        if "SeededCells" not in summary_data.columns:
            summary_data["SeededCells"] = pd.NA

        # Convert the numeric inputs before combining the summary files.
        summary_data["Group"] = pd.to_numeric(summary_data["Group"], errors="coerce")
        summary_data["Colonies"] = pd.to_numeric(
            summary_data["Colonies"], errors="coerce"
        )
        summary_data["SeededCells"] = pd.to_numeric(
            summary_data["SeededCells"], errors="coerce"
        )
        if summary_data[["Group", "Colonies"]].isna().any().any():
            raise DataProcessingError(
                f"{summary_file.name} contains a nonnumeric group or colony count."
            )

        # Add the metadata as columns so all later grouping uses pandas.
        summary_data["Cell_Line"] = cell_line
        summary_data["Treatment_Name"] = treatment_name
        summary_data["Control_Cell_Line"] = is_control
        summary_data["Source_File"] = summary_file.name
        data_frames.append(summary_data)
        cell_line_names.append(cell_line)
        treatment_names.append(treatment_name)
        if is_control:
            control_cell_lines.append(cell_line)

    if len(set(cell_line_names)) != len(cell_line_names):
        raise DataProcessingError("Each summary file must have a unique cell-line name.")
    if len(control_cell_lines) > 1:
        raise DataProcessingError("Only one cell line may be marked as the control.")
    if len(set(treatment_names)) > 1:
        raise DataProcessingError("All summary files must use the same treatment name.")

    # Put the marked control first so comparison labels are easy to read.
    if control_cell_lines:
        control_name = control_cell_lines[0]
        cell_line_names.remove(control_name)
        cell_line_names.insert(0, control_name)

    # Combine all image rows into one tidy DataFrame.
    raw_data = pd.concat(data_frames, ignore_index=True)

    # Use colonies per seeded cell when seeded-cell counts were supplied.
    seeded_cells_used = raw_data["SeededCells"].notna().any()
    if seeded_cells_used:
        if raw_data["SeededCells"].isna().any() or (raw_data["SeededCells"] <= 0).any():
            raise DataProcessingError(
                "Seeded-cell counts must be provided for every image and be greater than 0."
            )
        raw_data["Colony_Rate"] = raw_data["Colonies"] / raw_data["SeededCells"]
    else:
        # This preserves the original calculation for older data.
        raw_data["Colony_Rate"] = raw_data["Colonies"]

    # Calculate the dose-0 mean separately for every cell line.
    control_means = (
        raw_data.loc[raw_data["Group"] == 0]
        .groupby("Cell_Line", as_index=False)["Colony_Rate"]
        .mean()
        .rename(columns={"Colony_Rate": "Control_Average"})
    )
    missing_controls = set(cell_line_names) - set(control_means["Cell_Line"])
    if missing_controls:
        raise DataProcessingError(
            "A dose-0 group is required for: " + ", ".join(sorted(missing_controls))
        )
    if (control_means["Control_Average"] == 0).any():
        raise DataProcessingError("Dose-0 mean colony values must be greater than 0.")

    # Merge the control mean onto each observation and calculate survival.
    raw_data = raw_data.merge(control_means, on="Cell_Line", how="left")
    raw_data["Survival"] = (
        raw_data["Colony_Rate"] / raw_data["Control_Average"] * 100
    ).round(1)

    # Keep the original column names used by the ANOVA formula.
    anova_data = raw_data.rename(columns={"Group": "Treatment"})[
        ["Treatment", "Cell_Line", "Survival"]
    ]

    # Run the same all-pairs comparison loop used by the original script.
    anova_results = []
    for index in range(len(cell_line_names) - 1):
        anova_results.extend(significance(anova_data, cell_line_names[index:]))

    # Summarize mean survival and SEM at each dose for the report and plot.
    dose_summary = (
        raw_data.groupby(["Cell_Line", "Group"], as_index=False)
        .agg(
            Replicates=("Survival", "size"),
            Seeded_Cells=("SeededCells", "first"),
            Mean_Colonies=("Colonies", "mean"),
            Mean_Colony_Rate=("Colony_Rate", "mean"),
            Mean_Survival=("Survival", "mean"),
            SEM_Survival=("Survival", "sem"),
        )
        .sort_values(["Cell_Line", "Group"])
    )

    # Write a readable report containing the summary and each full ANOVA table.
    report_path = analysis_path / "statistics_summary.txt"
    with open(report_path, "w", encoding="utf-8") as report:
        report.write("countPHICS2 Statistics Summary\n")
        report.write("================================\n")
        report.write(f"Treatment:\t{treatment_names[0] or 'Treatment'}\n")
        report.write(f"Cell lines:\t{', '.join(cell_line_names)}\n")
        report.write(
            f"Control cell line:\t{control_cell_lines[0] if control_cell_lines else 'None'}\n"
        )
        report.write(
            f"Seeded-cell correction:\t{'Used' if seeded_cells_used else 'Not used'}\n\n"
        )

        report.write("DOSE SUMMARY\n")
        report.write("------------\n")
        dose_summary.to_csv(report, sep="\t", index=False, float_format="%.4g")
        report.write("\nANOVA COMPARISONS\n")
        report.write("-----------------\n")

        for result in anova_results:
            report.write(
                f"{result.comparison}\tInteraction p-value={result.p_value:.6g}"
                f"\t{_significance_symbol(result.p_value)}\n"
            )
            result.table.to_csv(report, sep="\t", float_format="%.6g")
            report.write("\n")

    # Convert the summaries into the column names expected by FIJIGrapher.
    curve_data = dose_summary.rename(
        columns={
            "Cell_Line": "CellLine",
            "Group": "Treatment",
            "Mean_Survival": "MeanSurvivalPercent",
            "SEM_Survival": "SEMSurvivalPercent",
        }
    )
    
    # Draw and save one kill curve with a different color for each cell line.
    from libraries.grapher import FIJIGrapher
    import matplotlib.pyplot as plt

    plots_path = analysis_path / "plots"
    plots_path.mkdir(exist_ok=True)
    grapher = FIJIGrapher()
    grapher.set_data(curve_data)
    grapher.kill_curve(
        x="Treatment",
        y="MeanSurvivalPercent",
        hue="CellLine",
        yerr="SEMSurvivalPercent",
        control_cell_line=control_cell_lines[0] if control_cell_lines else None,
        treatment_label=treatment_names[0] or "Treatment",
        title="Cell survival kill curve",
    )
    
    # Save both png and svg for now, might make optional later
    grapher.save_current_plot(plots_path / "kill_curve.png")
    grapher.save_current_plot(plots_path / "kill_curve.svg", svg=True)
    plt.close()

    return (
        f"Saved {report_path.name} and plots for {len(cell_line_names)} cell lines.\n"
        f"Treatment: {treatment_names[0] or 'Treatment'} -- Cell lines: {', '.join(cell_line_names)} -- Control line: {control_cell_lines[0] if control_cell_lines else 'None'}\n"
        f"Results saved in {report_path}\n"
        f"ANOVA p-values:\n"
        + "\n".join(
            f"{result.comparison}: p={result.p_value:.6g}" for result in anova_results)
    )

if __name__ == "__main__":
    data_processing()
