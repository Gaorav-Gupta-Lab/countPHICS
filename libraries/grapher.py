"""
Lightweight analysis and visualization system for handling FIJI summary outputs.

The main purpose of this module is to provide an interface for loading,
parsing, inspecting, and visualizing FIJI-generated TSV summary files.
This is achieved through a set of convenience methods organized around
plotting common statistical visualizations such as histograms, boxplots,
and scatterplots. It also handles metadata extraction from summary files.

Classes and Methods:
- FijiRunMetadata: A container for macro version and runtime information.
- FIJIGrapher: Implements file loading, metadata parsing, data inspection, and visualization.

The module relies on pandas for data handling and seaborn/matplotlib for visualization.

@ Author: Paolo Guerra
@ The University of North Carolina at Chapel Hill
@ Date: February 2026
@ Version: 1.0.0
"""

from pathlib import Path
from dataclasses import dataclass
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import weibull_min, kstest

# ----------------------------
# Metadata container
# ----------------------------
@dataclass
class FijiRunMetadata:
    macro_version: str
    run_datetime: float
    raw_header: str


# ----------------------------
# Main grapher
# ----------------------------
class FIJIGrapher:
    """
    Lightweight analysis + visualization layer for FIJI summary outputs.

    Expected file format:
    line 1 -> metadata (macro version, runtime, etc.)
    line 2 -> empty
    line 3+ -> TSV header and data
    """

    def __init__(self, style="whitegrid", dpi=300):
        self.style = style
        self.dpi = dpi
        sns.set_style(self.style)

        self.data: pd.DataFrame | None = None
        self.metadata: FijiRunMetadata | None = None

    # ----------------------------
    # IO
    # ----------------------------

    def set_data(self, data: pd.DataFrame):
        self.data = data

    def load_summary_file(self, filepath: str | Path):
        filepath = Path(filepath)

        if not filepath.exists():
            print(f"File not found: {filepath}")
            return

        try:
            with open(filepath, "r") as f:
                header_line = f.readline().strip()
                _ = f.readline()  # empty spacer line

            self.metadata = self._parse_metadata(header_line)

            # print(f"Parsed metadata: {self.metadata}")

            self.data = pd.read_csv(
                filepath,
                sep="\t",
                header=0,
                comment="#",
                skip_blank_lines=True
            )

            # Summary columns are padded for plain-text readability. Tabs still
            # delimit the fields, so remove only the display padding after load.
            self.data.columns = self.data.columns.str.strip()
            for column in self.data.select_dtypes(include="object").columns:
                self.data[column] = self.data[column].str.strip()

            # print(
            #     f"Loaded {len(self.data)} rows from {filepath.name}"
            # )

        except Exception as e:
            print(f"Failed to load data: {e}")

    @staticmethod
    def _parse_metadata(header_line: str) -> FijiRunMetadata:
        """
        Parse macro metadata from the first line.
        """
        parts = {}
        # for token in header_line.split(" "):
            # if "=" in token:
            #     k, v = token.split("=", 1)
            #     parts[k.strip()] = v.strip()
        split_header = header_line.split(" ")
        parts["macro_version"] = split_header[2]
        parts["run_datetime"] = split_header[4] + " " + split_header[5]

        return FijiRunMetadata(
            macro_version=parts.get("macro_version", "version_unknown"),
            run_datetime=parts.get("run_datetime", "date_unkown"),
            raw_header=header_line
        )
    
    def load_area_distribution_file(self, filepath: str | Path, skiprows=0):
        filepath = Path(filepath)

        if not filepath.exists():
            print(f"File not found: {filepath}")
            return

        try:
            self.data = pd.read_csv(
                filepath,
                sep="\t",
                header=0,
                comment="#",
                skiprows=skiprows
            )

            # print(
            #     f"Loaded {len(self.data)} rows from {filepath.name}"
            # )

            return self.data

        except Exception as e:
            print(f"Failed to load area distribution data: {e}")
            return None

    # ----------------------------
    # Sanity checks
    # ----------------------------
    def require_data(self):
        if self.data is None:
            raise RuntimeError("No data loaded. Call load_summary_file first.")

    def assert_columns(self, *cols):
        self.require_data()
        missing = set(cols) - set(self.data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    # ----------------------------
    # Quick inspection helpers
    # ----------------------------
    def describe(self) -> pd.DataFrame:
        self.require_data()
        return self.data.describe(include="all")

    def preview(self, n=5) -> pd.DataFrame:
        self.require_data()
        return self.data.head(n)

    # ----------------------------
    # Plotting primitives
    # ----------------------------
    def _new_figure(self, figsize=(8, 5)):
        plt.figure(figsize=figsize, dpi=self.dpi)

    @staticmethod
    def save_current_plot(outpath: str | Path, svg=False):
        outpath = Path(outpath)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        if svg:
            plt.savefig(outpath, format="svg", bbox_inches="tight")
        else:
            plt.savefig(outpath, bbox_inches="tight")

    # ----------------------------
    # Plots
    # ----------------------------
    def histogram(
        self,
        x: str,
        bins: int = 30,
        xmin: float | None = None,
        xmax: float | None = None,
        kde: bool = False,
        title: str | None = None,
    ):

        self.assert_columns(x)

        # ---- Prepare data ----
        data = self.data[x].dropna()
        data = data[data > 0]  # Weibull requires positive values

        self._new_figure()

        # ---- Histogram (normalized) ----
        sns.histplot(
            data=data,
            bins=bins,
            stat="density",     # CRITICAL
            kde=kde,
            edgecolor="black",
            alpha=0.6,
        )

        if len(data) > 0:
            # ---- Weibull fit (MLE) ----
            shape, loc, scale = weibull_min.fit(data, floc=0)

            # ---- PDF for plotting ----
            x_fit = np.linspace(data.min(), data.max(), 500)
            y_fit = weibull_min.pdf(x_fit, shape, loc=loc, scale=scale)

            plt.plot(
                x_fit,
                y_fit,
                "r-",
                linewidth=2.5,
                label=f"Weibull fit (k={shape:.2f}, λ={scale:.2f})"
            )

            # ---- Goodness of fit (KS test) ----
            D, p = kstest(data, "weibull_min", args=(shape, loc, scale))

            plt.text(
                0.95,
                0.95,
                f"KS p = {p:.3g}",
                transform=plt.gca().transAxes,
                ha="right",
                va="top"
            )
        else:
            plt.text(
                0.95,
                0.95,
                "No positive data available for fit",
                transform=plt.gca().transAxes,
                ha="right",
                va="top"
            )

        plt.xlim(xmin, xmax)
        plt.xlabel(x)
        plt.ylabel("Density")
        plt.title(title or f"Distribution of {x}")
        ax = plt.gca()
        handles, labels = ax.get_legend_handles_labels()
        if labels:
            plt.legend()

        self._annotate_metadata()


    def boxplot(
        self,
        x: str | None,
        y: str,
        title: str | None = None,
    ):
        self.assert_columns(y)
        if x:
            self.assert_columns(x)

        self._new_figure()
        sns.boxplot(data=self.data, x=x, y=y)
        sns.stripplot(
            data=self.data,
            x=x,
            y=y,
            color="black",
            alpha=0.6,
            size=8,
            jitter=True,
            # dodge=True
        )

        plt.xlabel(x or "")
        plt.ylabel(y)
        plt.title(title or f"{y} distribution")

        self._annotate_metadata()

    def scatter(
        self,
        x: str,
        y: str,
        hue: str | None = None,
        title: str | None = None,
    ):
        self.assert_columns(x, y)
        if hue:
            self.assert_columns(hue)

        self._new_figure()
        sns.scatterplot(data=self.data, x=x, y=y, hue=hue)

        plt.xlabel(x)
        plt.ylabel(y)
        plt.title(title or f"{y} vs {x}")

        self._annotate_metadata()

    def violin(
        self,
        x: str | None,
        y: str,
        title: str | None = None,
    ):
        self.assert_columns(y)
        if x:
            self.assert_columns(x)

        self._new_figure()
        
        sns.violinplot(
            data=self.data,
            x=x,
            y=y,
            inner="quartile",
            bw_adjust=0.2,
            inner_kws=dict(color="black"),
            zorder=1,
        )
        # sns.stripplot(
        #     data=self.data,
        #     x=x,
        #     y=y,
        #     alpha=0.5,
        #     color="black",
        #     size=2,
        #     jitter=True,
        #     zorder=2,
        # )
        median_values = self.data.groupby(x)[y].median() if x else [self.data[y].median()]
        for i, median in enumerate(median_values):
            plt.plot(
                [i - 0.1, i + 0.1],
                [median, median],
                color="red",
                linewidth=3,
                zorder=10,
            )
        plt.xlabel(x or "")
        plt.ylabel(y)
        plt.title(title or f"{y} distribution")

        self._annotate_metadata()

    def kill_curve(
        self,
        x: str,
        y: str,
        hue: str,
        yerr: str,
        control_cell_line: str | None = None,
        treatment_label: str = "Treatment",
        title: str | None = None,
    ):
        """Plot mean cell survival with SEM at each treatment dose."""
        self.assert_columns(x, y, hue, yerr)

        cell_lines = sorted(self.data[hue].dropna().unique(), key=str.casefold)
        if control_cell_line in cell_lines:
            cell_lines.remove(control_cell_line)
            cell_lines.insert(0, control_cell_line)

        self._new_figure(figsize=(8, 5))
        curve_ax = plt.gca()
        palette = sns.color_palette("colorblind", n_colors=max(len(cell_lines), 1))

        for index, cell_line in enumerate(cell_lines):
            series = self.data.loc[self.data[hue].eq(cell_line)].sort_values(x)
            is_control = cell_line == control_cell_line
            legend_label = f"{cell_line} (control)" if is_control else str(cell_line)
            errors = series[yerr].fillna(0)
            curve_ax.errorbar(
                series[x],
                series[y],
                yerr=errors,
                label=legend_label,
                color=palette[index],
                marker="o",
                markersize=8 if is_control else 6,
                linewidth=3 if is_control else 2,
                capsize=4,
            )

        # curve_ax.axhline(
        #     100,
        #     color="#666666",
        #     linestyle="--",
        #     linewidth=1,
        #     alpha=0.7,
        #     label="100% survival",
        # )

        curve_ax.set_xlabel(treatment_label)
        curve_ax.set_ylabel("Survival (%)")
        curve_ax.set_title(title or "Cell survival kill curve")
        # curve_ax.set_ylim(bottom=0.00)
        curve_ax.set_xlim(left=0)
        curve_ax.set_yticks(np.arange(0, 101, 10))
        curve_ax.set_yticklabels([f"{i}%" for i in np.arange(0, 101, 10)])
        curve_ax.set_yscale("log")
        curve_ax.minorticks_on()
        curve_ax.tick_params(axis="y", which="minor", length=3, width=0.8, color="gray")
        curve_ax.grid(False)
        curve_ax.legend(frameon=True)

    # ----------------------------
    # Metadata annotation
    # ----------------------------
    def _annotate_metadata(self):
        """
        Adds macro version + runtime to the plot footer.
        """
        if not self.metadata:
            return

        footer = f"Macro {self.metadata.macro_version} | {self.metadata.run_datetime}"
        plt.figtext(
            0.99, 0.01,
            footer,
            ha="right",
            va="bottom",
            fontsize=8,
            alpha=0.6
        )

    # ----------------------------
    # Batch convenience
    # ----------------------------
    def auto_overview(self, numeric_only=True):
        """
        Generate a fast exploratory overview for all numeric columns.
        """
        self.require_data()

        cols = self.data.select_dtypes(
            include=np.number if numeric_only else None
        ).columns

        for col in cols:
            self.histogram(col)
            plt.show()
