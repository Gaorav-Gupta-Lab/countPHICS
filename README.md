# countPHICS2 - Colony Counter Interface

A Python-based graphical interface for automated cell colony counting and analysis using FIJI/ImageJ. This tool provides a user-friendly GUI for processing images of colonies with advanced image analysis, statistical visualization, and batch processing capabilities.<br>
**Originally developed by Beata Brzozowska and published DOI: 10.1007/s00411-018-00772-z.**

## Overview

Count and Plot HIstograms of Colony Size 2 (countPHICS2) is designed to automate the tedious process of counting colonies. It combines the power of FIJI/ImageJ's image processing capabilities with Python's data analysis and visualization tools through an intuitive desktop interactive interface.

### Key Features

- **User-friendly GUI** - Clean, modern interface built with PySide6
- **Automated colony detection** - Advanced image processing with customizable parameters
- **Batch processing** - Process multiple images or multi-well plates automatically
- **Statistical analysis** - Weibull distribution fitting, KS tests, and descriptive statistics
- **Data visualization** - Automatic generation of histograms, boxplots, and distribution plots
- **6-well plate support (beta)** - Specialized analysis mode for multi-well imaging
- **Comprehensive reporting** - Detailed summary files with metadata and parameters

## Requirements

### Software Dependencies

- **FIJI/ImageJ** - Must be installed and accessible on your system
- **Python 3.12+** - With the following packages:
  - PySide6 (Qt6 bindings)
  - pandas
  - numpy
  - matplotlib
  - seaborn
  - scipy
  - natsort

### Installation
#### Manual Download and Setup
1. **FIJI/ImageJ Installation**
    - The project comes prepackaged with an installation of ImageJ, so no prior installation is necessary. 

2. **Install Python dependencies (if not using executable)**
   ```bash
   pip install PySide6 pandas numpy matplotlib seaborn scipy natsort
   ```

3. **Clone or download this repository**
   ```bash
   git clone <repository-url>
   cd countPHICS
   ```
## Project Structure

```
countPHICS/
├── countPHICS2.exe        # One Step Executable
├── main_window.py         # Main GUI application
├── macros/
│   └── macro_moj.py       # FIJI/ImageJ macro (Jython)
│   └── grapher.py         # Data visualization and analysis
├── layout.qss             # Qt stylesheet (optional)
├── assets/
│   └── countphics.ico     # Application icon
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
   - **6-well plate analysis** - Enable if images contain 6-well plates
   - **Generate plots after processing** - Automatically create visualization plots
   - **Enable advanced settings (deprecated, will be removed)** - Access fine-tuning parameters

   **Advanced Settings** :
   - **Rolling Ball Radius** - Background subtraction parameter
   - **Min Colony Size** - Minimum area to count as colony
   - **Max Colony Size** - Maximum area to count as colony
   - **Min Circularity** - Shape filter (0.0 = any shape, 1.0 = perfect circle)
   - **Sigma** - Gaussian blur strength before detection
   - **ROI Thickness** - Line thickness when selecting plate ROI

5. **Launch processing**
   - Click "▶ LAUNCH FIJI" to start analysis
   - Monitor progress in the console window
   - FIJI will open and process images automatically

6. **Review results**
   - Results are saved in the user defined output directory with the following structure:
     ```
     countPHICS_output/
     ├── countPHICS_params.txt          # Analysis parameters
     ├── Summary.txt                    # Main results table
     ├── plots/                         # Visualization plots
     │   ├── all_colony_counts_boxplot.png
     │   └── *_area_hist.png
     ├── size_distribution_files/       # Per-image colony sizes
     │   └── *_size_distribution.txt
     └── image_outputs/                 # Annotated images
         └── *_counted.jpg
     ```

## Output Files

### Summary.txt

Tab-separated values file containing:
- **Metadata** - Macro version, run timestamp, parameters
- **Per-image results**:
  - Image name
  - Group (derived from filename prefix)
  - Number of colonies
  - Min/max counted colony size
  - Median colony size
  - Geometric mean colony size
  - ROI coordinates

Example:
```
# countPHICS v2.2.2 run: 2026-02-11 11:30:22

# Parameters: 
# AutoThreshold= False
# SameROI=True
# SixWell=False
# RollingBall=62
# MinColony=150
# MaxColony=10000
# Circularity=0.75
# Sigma=3.0
# MinThresh=0.0
# MaxThresh=240.0

Image - Group - Num colonies - MinCountedSize - MaxCountedSize - MedianSize - GeomMeanSize - ImageROI
sampleWT_01.tif - sampleWT - 145 - 152 - 8234 - 1024 - 987.42 - Roi[Oval, x, y, width, height, pos]
sampleWT_02.tif - sampleWT - 138 - 156 - 7891 - 1012 - 953.18 - Roi[Oval, x, y, width, height, pos]
sampleKO_01.tif - sampleKO - 89 - 150 - 5621 - 894 - 915.23 - Roi[Oval, x, y, width, height, pos]
sampleWT_02.tif - sampleKO - 94 - 153 - 5963 - 942 - 907.42 - Roi[Oval, x, y, width, height, pos]
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

- Boxplot summarizing colony counts among replicates in each described group. **(WIP: needs group implementation)**

- Violin plot summarizing colony size distribution in each described group. **(WIP: needs group implementation)**

- Individual histograms for each image summarizing size ditribution:

<img src=examples/example_size_distribution_area_hist.png alt="plot" height="300">


### Available Plot Types

- **histogram()** - Distribution with Weibull fit and KS test
- **boxplot()** - Group comparisons with overlaid strip plots
- **scatter()** - Correlation analysis
- **violin()** - Distribution shape visualization

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

## Advanced Usage

### 6-Well Plate Mode (Beta)

When enabled, the macro:
- Automatically divides the image into 6 equal regions (2 rows × 3 columns)
- Processes each well independently
- Generates separate counts and statistics per well
- Useful for high-throughput screening

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

- **v2.2.2** (Current)
  - Full Python GUI implementation
  - Advanced plotting with Weibull fitting
  - Improved 6-well plate support
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