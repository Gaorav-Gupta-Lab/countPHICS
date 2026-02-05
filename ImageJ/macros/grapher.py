from pathlib import Path
from dataclasses import dataclass
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ----------------------------
# Metadata container
# ----------------------------
@dataclass
class FijiRunMetadata:
    macro_version: str
    runtime_seconds: float
    raw_header: str


# ----------------------------
# Main grapher
# ----------------------------
class FIJIGrapher:
    """
    Lightweight analysis + visualization layer for FIJI summary outputs.

    Expected file format:
    line 1  -> metadata (macro version, runtime, etc.)
    line 2  -> empty
    line 3+ -> TSV header + data
    """

    def __init__(self, style="whitegrid", dpi=120):
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

            self.data = pd.read_csv(
                filepath,
                sep="\t",
                header=0,
                skiprows=2
            )

            print(
                f"Loaded {len(self.data)} rows from {filepath.name}"
            )

        except Exception as e:
            print(f"Failed to load data: {e}")

    def _parse_metadata(self, header_line: str) -> FijiRunMetadata:
        """
        Parse macro metadata from the first line.

        Example header:
        MacroVersion=1.2.3; RuntimeSeconds=184.5
        """
        parts = {}
        for token in header_line.split(";"):
            if "=" in token:
                k, v = token.split("=", 1)
                parts[k.strip()] = v.strip()

        return FijiRunMetadata(
            macro_version=parts.get("MacroVersion", "unknown"),
            runtime_seconds=float(parts.get("RuntimeSeconds", np.nan)),
            raw_header=header_line
        )
    
    def load_area_distribution_file(self, filepath: str | Path, skiprows=0):
        filepath = Path(filepath)

        if not filepath.exists():
            print(f"File not found: {filepath}")
            return

        try:
            data = pd.read_csv(
                filepath,
                sep="\t",
                header=0,
                skiprows=skiprows
            )

            print(
                f"Loaded {len(data)} rows from {filepath.name}"
            )

            return data

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

    def save_current_plot(self, outpath: str | Path):
        outpath = Path(outpath)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(outpath)
        print(f"Saved plot → {outpath}")

    # ----------------------------
    # Plots
    # ----------------------------
    def histogram(
        self,
        x: str,
        bins: int = 30,
        kde: bool = True,
        title: str | None = None,
    ):
        self.assert_columns(x)

        self._new_figure()
        sns.histplot(data=self.data, x=x, bins=bins, kde=kde)

        plt.xlabel(x)
        plt.ylabel("Count")
        plt.title(title or f"Distribution of {x}")

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
        sns.violinplot(data=self.data, x=x, y=y, inner="quartile")

        plt.xlabel(x or "")
        plt.ylabel(y)
        plt.title(title or f"{y} distribution")

        self._annotate_metadata()

    # ----------------------------
    # Metadata annotation
    # ----------------------------
    def _annotate_metadata(self):
        """
        Adds macro version + runtime to the plot footer.
        """
        if not self.metadata:
            return

        footer = f"Macro {self.metadata.macro_version} | Runtime {self.metadata.runtime_seconds:.1f}s"
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
