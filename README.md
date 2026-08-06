# countPHICS2 - Colony Counter Interface

A Python-based graphical interface for automated cell colony counting and analysis using FIJI/ImageJ. This tool provides a user-friendly GUI for processing images of colonies with advanced image analysis, statistical visualization, and batch processing capabilities.<br>
**Originally developed by Beata Brzozowska and published DOI: 10.1007/s00411-018-00772-z.**

## Overview

Count and Plot HIstograms of Colony Size 2 (countPHICS2) is designed to automate the tedious process of counting colonies. It combines the power of FIJI/ImageJ's image processing capabilities with Python's data analysis and visualization tools through an intuitive desktop interactive interface.

### Key Features

- **User-friendly GUI** - Clean, modern interface built with PySide6
- **Automated colony detection** - Advanced image processing with customizable parameters
- **Batch processing** - Process multiple colony images automatically
- **Statistical analysis** - Weibull fitting, KS tests, survival normalization, and pairwise ANOVA
- **Data visualization** - Automatic generation of histograms, boxplots, and distribution plots
- **Comprehensive reporting** - Detailed summary files with metadata and parameters

## Requirements

### Software Dependencies

- **Python 3.12+** - With the following packages:
  - PySide6 (Qt6 bindings)
  - pandas
  - numpy
  - matplotlib
  - seaborn
  - scipy
  - natsort
  - statsmodels
  - tifffile

### Installation
#### Manual Download and Setup
1. **FIJI/ImageJ Installation**
    - The project comes prepackaged with an installation of ImageJ, so no prior installation is necessary. 

2. **Install Python dependencies (if not using executable)**
   ```bash
   pip install PySide6 pandas numpy matplotlib seaborn scipy natsort statsmodels tifffile
   ```

3. **Clone or download this repository**
   ```bash
   git clone <repository-url>
   cd countPHICS2
   ```
## Project Structure

```
countPHICS2/
├── countPHICS.bat         # Windows launcher
├── main_window.py         # Main GUI application
├── ImageJ/
│   ├── ImageJ-win64.exe   # Bundled Windows FIJI/ImageJ executable
│   └── macros/
│       └── macro_moj.py   # FIJI/ImageJ macro (Jython)
├── libraries/
│   ├── grapher.py         # Data visualization and analysis
│   └── layout.qss         # Qt stylesheet
├── assets/
│   └── countphics2.ico    # Application icon
└── README.md              # This file
```

## Usage
### Starting the Application

Double click batch file in downloaded directory or run terminal command:

```bash
python main_window.py
```

### Workflow

1. **Select input directory**
   - Select directory images 300-1200 dpi with high contrast for best analysis
        - Described in further detail in <a href=https://pubmed.ncbi.nlm.nih.gov/30673853>original countPHICS paper</a>
        - Example image:<br>
            <img src=examples/example.png alt="drawing" width="300"/>
   - Click "Browse Input" to select a folder containing your `.tif`, `.tiff`, `.png`, `.jpeg` or `.jpg` images
   - Images should be RGB.

2. **Choose output location** (optional)
   - Click "Browse Output" to specify where results should be saved
   - If left blank, results will be saved in a `countPHICS_output` folder within the input directory

3. **Configure analysis settings**

   **General Settings:**
   - **Use same ROI for all images** - Define region of interest once, apply to all images
   - **Split Image** - Crop supported composite TIFF scans into separate dish images
   - **Generate plots after processing** - Automatically create visualization plots

   **Group Assignment:**
   - Enter each treatment dose and its number of image replicates.
   - **Seeded cells** is optional. Leave the entire column blank to use the
     original colony-count normalization. If seeded-cell counts are used, enter
     a value for every treatment row.

   **Advanced Settings** :
   - **Rolling Ball Radius** - Background subtraction parameter
   - **Min Colony Size** - Minimum area to count as colony
   - **Max Colony Size** - Maximum area to count as colony
   - **Min Circularity** - Shape filter (0.0 = any shape, 1.0 = perfect circle)
   - **Sigma** - Gaussian blur strength before detection
   - **ROI Thickness** - Line thickness when selecting plate ROI

4. **Launch processing**
   - Click "▶ LAUNCH FIJI" to start analysis
   - Monitor progress in the console window
   - FIJI will open and process images automatically

5. **Review results**
   - Results are saved in the user defined output directory with the following structure:
     ```
     countPHICS_output/
     ├── Summary_<cell-line>.txt        # Cell-line-specific results table
     ├── statistics_summary.txt         # ANOVA report and dose summary
     ├── plots/                         # Visualization plots
     │   ├── all_colony_counts_boxplot.png
     │   ├── all_colony_sizes_violinplot.png
     │   ├── kill_curve.png
     │   └── *_area_hist.png
     ├── size_distribution_files/       # Per-image colony sizes
     │   └── *_size_distribution.txt
     └── image_outputs/                 # Annotated images
         └── *_counted.jpg
     ```

## Output Files

### `Summary_<cell-line>.txt`

The summary filename is derived from the **Cell line** field in the GUI. For
example, entering `TP53KO` produces `Summary_TP53KO.txt`. The plotting workflow
loads this same cell-line-specific file after FIJI finishes.

Summary columns are padded so they line up in monospaced text editors, while
real tab characters remain between fields. The file can therefore still be
copied into Excel or opened as a tab-delimited table without losing columns.

Tab-separated values file containing:
- **Metadata** - Macro version, run timestamp, parameters
- **Per-image results**:
  - Image name
  - Group (assigned in the group-definition dialog)
  - Number of colonies
  - Optional number of seeded cells
  - Min/max counted colony size
  - Median colony size
  - Geometric mean colony size

Example:
```
# countPHICS2 v2.3.0 run: 2026-02-11 11:30:22

# Parameters: 
# AutoThreshold= False
# SameROI=True
# Image ROI=Roi[Oval, x, y, width, height, pos]
# RollingBall=62
# MinColony=150
# MaxColony=10000
# Circularity=0.75
# Sigma=3.0
# MinThresh=0.0
# MaxThresh=240.0

ImageName\tGroup\tColonies\tSeededCells\tMinCountedSize\tMaxCountedSize\tMedianSize\tGeomMeanSize
sampleWT_01.tif\t0\t145\t500\t152\t8234\t1024\t987.42
sampleWT_02.tif\t0\t138\t500\t156\t7891\t1012\t953.18
sampleKO_01.tif\t5\t89\t1000\t150\t5621\t894\t915.23
sampleKO_02.tif\t5\t94\t1000\t153\t5963\t942\t907.42
```

### Size Distribution Files

Individual `.txt` files for each image containing:
- Colony count header
- Each colony with its respective area per line (in pixels²)

Example:
```
Number of colonies: 110
Colony Area
328.0
678.0
175.0
160.0
...
```

### Image Outputs

Individual `.jpg` files for each image containing:
- Thresholded image of colonies.
- Counted colonies surrounded by green outline.

<img src=examples/example_counted.jpg alt="drawing" width="350"/>


### Output Plots
The `grapher.py` module provides powerful analysis capabilities using `matplotlib` and `seaborn`:

- Boxplot summarizing colony counts among replicates in each assigned group.

- Violin plot summarizing colony size distributions in each assigned group.

- Individual histograms for each image summarizing size ditribution:

<img src=examples/example_size_distribution_area_hist.png alt="plot" height="300">

### Kill Curve and Statistical Report

After processing two or more cell lines into the same `countPHICS_output`
folder, click **RUN STATS**. Each cell line must have a unique name and a
treatment group `0` with a nonzero mean colony value. Zero or one cell line may
be marked as the control.

The analysis normalizes every image to the mean treatment-0 colony count for
its own cell line. When seeded-cell counts are supplied, it first divides each
colony count by its seeded-cell count and normalizes those colony rates instead.
It then runs a type-II ANOVA for every pair of cell lines using
`Survival ~ C(Cell_Line) * C(Treatment)`.

The analysis produces:

- `statistics_summary.txt`, a readable tab-separated report containing the
  dose-level survival summary, pairwise interaction p-values, significance
  labels, and the complete ANOVA table for every comparison.
- `plots/kill_curve.png`, showing each cell line in a different color with
  mean survival and SEM error bars at each treatment dose.

Significance labels use `ns` for p ≥ 0.05, followed by `*`, `**`, `***`, and
`****` for p < 0.05, 0.01, 0.001, and 0.0001 respectively. A comparison that
cannot be estimated is retained in the report and shown as `NA` on the plot.


### Available Plot Types

- **histogram()** - Distribution with Weibull fit and KS test
- **boxplot()** - Group comparisons with overlaid strip plots
- **scatter()** - Correlation analysis
- **violin()** - Distribution shape visualization
- **kill_curve()** - Mean survival with SEM for each cell line and dose

### Statistical Features

- **Weibull distribution fitting** - Maximum likelihood estimation for colony size distributions
- **Kolmogorov-Smirnov test** - Goodness-of-fit assessment with p-value
- **Descriptive statistics** - Mean, median, quartiles, std deviation
- **Metadata annotation** - Plots include macro version and runtime information

## Image Processing Pipeline

The FIJI macro (`macro_moj.py`) performs the following steps:

1. **Channel selection** - Automatically selects RGB channel with highest contrast
2. **Gaussian blur** - Noise reduction (sigma parameter)
3. **Background subtraction** - Rolling ball algorithm
4. **ROI definition** - Region selection on initial image
5. **Thresholding** - Set thresholding based on initial image
6. **Particle analysis** - Size and circularity filtering
7. **Result compilation** - Colony counting and area measurements

## Troubleshooting

### General
- For general troubleshooting, output images and summary files provide a quick way to diagnose errors.
- If errors persist please refer below for common errors and how to solve them.

### FIJI Path Issues
- **Problem**: Application can't find FIJI
- **Solution**: Manually set the FIJI path in the code or parameter file
- On Windows, check: `C:\Program Files\Fiji.app\` or `C:\Users\<username>\Fiji.app\`
- On macOS, check: `/Applications/Fiji.app/`

### No Colonies Detected
- **Problem**: All images show 0 colonies
- **Solutions**:
  - Decrease minimum colony size
  - Increase sigma value for more blur
  - Check that images are RGB format

### Too Many False Positives
- **Problem**: Background noise being counted
- **Solutions**:
  - Increase minimum colony size
  - Increase minimum circularity
  - Adjust rolling ball radius
  - Refine ROI to exclude edges

### Memory Errors with Large Batches
- **Problem**: FIJI crashes or freezes
- **Solutions**:
  - Process images in smaller batches
  - Increase FIJI's memory allocation in preferences
  - Reduce image resolution if appropriate

## Technical Details

### Parameter Calculations

Advanced settings parameters are automatically calculated based on image dimensions described in the <a href=google.com>original paper</a>:

- **Rolling ball radius**: `0.0306 × image_width`
- **Min colony size**: `0.01 × image_width`
- **Max colony size**: `image_width`
- **Sigma**: `0.001 × image_width` (if units unknown)
  - Or: `(1.9e-6) × dpi² + (6.3e-4) × dpi + 1.3` (if units known)

### Weibull Distribution

Colony size distributions often follow Weibull distributions. The grapher fits a two-parameter Weibull distribution using maximum likelihood estimation:

- **Shape parameter (k)**: Controls distribution shape
- **Scale parameter (λ)**: Characteristic size
- **KS test p-value**: Assesses goodness of fit (p < 0.05 suggests good fit)

## Citation

If you use countPHICS2 in your research, please cite the original countPHICS paper:
- https://doi.org/10.1007/s00411-018-00772-z

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## Version History

- **v2.5.5** (Current GUI)
  - Full Python GUI implementation
  - Advanced plotting with Weibull fitting
  - Enhanced metadata tracking

## Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Contact the authors: 
    - Dennis Simpson: dennis@unc.edu
    - Paolo Guerra: pguerra@unc.edu

## Acknowledgments

- Original countPHICS software by Beata Brzozowska et al. 2019
    - https://doi.org/10.1007/s00411-018-00772-z
