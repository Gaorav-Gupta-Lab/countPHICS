from ij import IJ, ImagePlus, WindowManager # type: ignore
from ij.process import ImageProcessor # type: ignore
from ij.plugin.filter import ParticleAnalyzer, RGBStackSplitter, BackgroundSubtracter # type: ignore
from ij.measure import ResultsTable # type: ignore
from ij.plugin.frame import RoiManager # type: ignore
from ij.measure import Measurements # type: ignore
from ij.gui import (OvalRoi, TrimmedButton, NonBlockingGenericDialog, # type: ignore
                    Toolbar, Roi, WaitForUserDialog, Overlay) # type: ignore
from ij.io import OpenDialog # type: ignore

import java.time # type: ignore
from java.awt import Color # type: ignore
from java.awt.event import ActionListener # type: ignore

import os
import sys
import math

macro_version = '2.3.0'

def parse_parameter_file():
    """
    Parses a parameter file and retrieves configurations specified in the file.
    This function first determines the file path of the parameter file, verifies its existence,
    and then reads and parses the parameter contents. Parameter key-value pairs in the file
    should be in the format `key=value`. Lines that are empty or begin with the `#` character
    are ignored. The parsed key-value pairs are returned as a dictionary.

    :raises SystemExit: If no parameter file is selected, or the specified parameter file does not exist.
    :returns: A dictionary containing the parsed configuration as key-value pairs.
    :rtype: dict
    """

    param_path = os.getcwd() + str(os.sep) + "config_dir" + str(os.sep) + "countPHICS_params.txt"
    '''
    if param_path is None or param_name is None:
        IJ.log("No parameter file selected. Aborting.")
        sys.exit()
    '''
    if not os.path.exists(param_path):
        IJ.log("Parameter file does not exist: " + param_path)
        sys.exit()

    def read_params(path):
        raw_params = {}
        f = open(path, "r")
        try:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                raw_params[k.strip()] = v.strip()
        finally:
            f.close()
        return raw_params

    return read_params(param_path)

params = parse_parameter_file()
output_directory = params.get("output")
images_raw = params.get("images")


if not images_raw or not output_directory:
    IJ.log("Missing required parameters (images or output). Aborting.")
    sys.exit()

# Create a list of images from the parameter string
all_images = images_raw.split(";")

# Helper for boolean conversion
def as_bool(v, default=False):
    if v is None:
        return default
    return v == 'true'

# --- 2. Calibration (Based on first image) ---
first_imp_path = all_images[0]
if not os.path.exists(first_imp_path):
    IJ.log("First image not found: " + first_imp_path)
    sys.exit()

imp = IJ.openImage(first_imp_path)
cal = imp.getCalibration()
x = cal.pixelWidth
units = cal.getUnit()
# units_known = True
units_known = False

"""
We are using pixels only
if units == 'mm':
    dpi = 1.0 / (x / 254.0)
elif units == 'cm':
    dpi = 1.0 / (x / 2.54)
elif units == 'inch':
    dpi = 1.0 / x
else:
    units_known = False
"""

# --- 3. Parameter Setup ---
threshold_flag = as_bool(params.get("auto_threshold"))
same_roi_flag = as_bool(params.get("same_roi"))
# six_well_flag = as_bool(params.get("six_well"))
# group_handling = params.get("group_assignment", "None").lower()  # "none", "automatic", or "manual"
group_handling = "manual"

# GROUP ASSIGNMENT
if group_handling == "manual":
    group_assignment_str = params.get("assignments", "")
    # group_assignment_dict = {}
    group_assignment_list = []

    if group_assignment_str:
        group_assignment_list = group_assignment_str.split(",")

    # ForUserDialog("Group List:  " + str(group_assignment_list)).show()
    """
    if group_assignment_str:
        for entry in group_assignment_str.split(";;"):
            entry = entry.strip()
            if not entry:
                continue
            if '|||' not in entry:
                continue
            img_path, group = entry.split("|||", 1)
            img_path = img_path.replace("/", "\\").strip()
            group = group.strip()
            group_assignment_dict[img_path] = group
    """

width = imp.getWidth()
height = imp.getHeight()

# Advanced Parameters
rolling_ball = int(params.get("rolling_ball", int(width * 0.0306)))
minimum_col  = int(params.get("min_colony", int(0.01 * width)))
maximum_col  = int(params.get("max_colony", int(width * 2)))
circ         = float(params.get("circularity", 0.5))
roi_thickness = int(params.get("roi_thickness", 3))
treatment_name = params.get("treatment_name", "")
cell_line = params.get("cell_line", "")

sigma = float(params.get("sigma", 0.001 * width))
"""
We are using pixels only
if units_known:
    sigma = float(params.get("sigma", (1.9e-6) * dpi ** 2 + (6.3e-4) * dpi + 1.3))
else:
    sigma = float(params.get("sigma", 0.001 * w))
"""

imp.close()  # Close the calibration image

# --- 4. The Refactored Count Function ---
def count_colonies(imp,
                   original_path,
                   is_first,
                   Roi_flag,
                   threshold_flag,
                   thres_iteration_flag,
                   image_output_path,
                   roi_def=None):
    """
    Refactored to take original_path instead of image_number strings.
    is_first: boolean, true if this is the very first image/well being analyzed (for initializing ROI).
    output_txt_path: full path where the .txt results will be saved.
    """
    
    splitter = RGBStackSplitter()
    splitter.split(imp.getStack(), True)
    red = ImagePlus("Red", splitter.red)
    green = ImagePlus("Green", splitter.green)
    blue = ImagePlus("Blue", splitter.blue)

    red.setCalibration(cal)
    green.setCalibration(cal)
    blue.setCalibration(cal)

    # Auto-select the best channel based on contrast (StdDev), virtually always green
    roi_chk = OvalRoi(width/4, height/4, width/2, height/2)
    red.setRoi(roi_chk); green.setRoi(roi_chk); blue.setRoi(roi_chk)
    
    stats_red = red.getStatistics(Measurements.STD_DEV).stdDev
    stats_green = green.getStatistics(Measurements.STD_DEV).stdDev
    stats_blue = blue.getStatistics(Measurements.STD_DEV).stdDev
    std_max = max(stats_red, stats_green, stats_blue)

    if std_max == stats_red: proc_imp = red
    elif std_max == stats_green: proc_imp = green
    else: proc_imp = blue

    proc_imp.removeScale()
    proc_imp.getProcessor().blurGaussian(sigma)

    BackgroundSubtracter().subtractBackround(proc_imp.getProcessor(),rolling_ball)

    # --- ROI Management ---
    def ROI_manager():
        IJ.run("Roi Defaults...", "color=orange stroke=" + str(roi_thickness) + " group=0")
        proc_imp.setRoi(OvalRoi(width/10, height/10,width/1.2, height/1.2))
        proc_imp.show()

        class MyListener(ActionListener):
            def actionPerformed(self, event):
                proc_imp.setRoi(OvalRoi(width/10, height/10, width/1.2, height/1.2))
                Toolbar().setTool("oval")

        dia2 = NonBlockingGenericDialog("ROI SELECTION")
        dia2.addMessage("Fit ROI to the inner edge of the dish, then click OK.")
        
        loc = IJ.getInstance().getLocation()
        dia2.setLocation(loc.x, loc.y - 40)
        dia2.hideCancelButton()
        
        bt = TrimmedButton("Recreate ROI", 10)
        bt.addActionListener(MyListener())
        dia2.add(bt)
        dia2.showDialog()
        
        final_roi = proc_imp.getRoi()
        return final_roi

    if Roi_flag:
        if is_first:
            global roi2
            roi2 = ROI_manager()
            roi_def = roi2
        else:
            proc_imp.setRoi(roi2)
            proc_imp.show() # breaks without this for some reason
    else:
        roi2 = ROI_manager()

    # --- Thresholding ---
    global thres_min, thres_max
    
    if threshold_flag:
        IJ.run("Auto Threshold", "method=Yen white")
        thres_min = proc_imp.getProcessor().getMinThreshold()
        thres_max = proc_imp.getProcessor().getMaxThreshold()
    
    elif not threshold_flag and thres_iteration_flag:
        IJ.run("Threshold...")
        WaitForUserDialog("Adjust Threshold", "Adjust threshold, then click OK.").show()
        thres_min = proc_imp.getProcessor().getMinThreshold()
        thres_max = proc_imp.getProcessor().getMaxThreshold()
        IJ.setThreshold(proc_imp, thres_min, thres_max)
        IJ.run(proc_imp, "Convert to Mask", "")
        if WindowManager.getWindow("Threshold"):
            IJ.selectWindow("Threshold")
            IJ.run("Close")
    else:
        IJ.setThreshold(proc_imp, thres_min, thres_max)
        IJ.run(proc_imp, "Convert to Mask", "")

    proc_imp.setRoi(roi2)
    ip = proc_imp.getProcessor()
    ImageProcessor.erode(ip)
    ImageProcessor.dilate(ip)
    IJ.run("Watershed")

    # --- Analysis ---
    table = ResultsTable()
    roim = RoiManager.getRoiManager()
    roim.reset()

    pa = ParticleAnalyzer(ParticleAnalyzer.ADD_TO_MANAGER | ParticleAnalyzer.SHOW_NONE, 
                         Measurements.AREA, table, float(minimum_col),
                         float(maximum_col), float(circ), 1.0)
    
    if pa.analyze(proc_imp):
        # Re-open original for overlay, not necessary?
        imp_result = IJ.openImage(original_path)
        
        roi2.setStrokeColor(Color.orange)
        roi2.setStrokeWidth(3)
        ol = Overlay(roi2)
        
        for r in roim.getRoisAsArray():
            r.setStrokeColor(Color.green)
            ol.add(r)

        proc_imp.setOverlay(ol)
        final_imp = proc_imp.flatten()
        
        # Construct output image path (replace .txt with .jpg)
        jpg_path = image_output_path
        IJ.saveAs(final_imp, "jpg", jpg_path)
        final_imp.close()
    
    areas = table.getColumn(0)
    proc_imp.changes = False
    proc_imp.close()
    
    # Return units for logging
    return [areas, roi2, proc_imp, units]

# --- 5. Main Loop (Iterating over LIST) ---
# print("Processing " + str(len(all_images)) + " images...")
thresh_flag_score = True

summary_path = os.path.join(output_directory, 'Summary.txt')
summary_lines = []

for i, img_path in enumerate(all_images):
    if not os.path.exists(img_path):
        print("File not found, skipping: " + img_path)
        continue
    # Filename handling
    file_name_full = os.path.basename(img_path)
    file_name_base = os.path.splitext(file_name_full)[0] # e.g. "image_01" from "image_01.tif"
    
    imp = IJ.openImage(img_path)
    if imp is None:
        print("Could not open image: " + img_path)
        continue

    # Is this the very first analysis operation? (For ROI initialization)
    is_global_first = (i == 0)

    size_output_file_name = file_name_base + "_size_distribution.txt"
    size_output_path = os.path.join(output_directory, "size_distribution_files/", size_output_file_name)

    image_output_file_name = file_name_base + "_counted.jpg"
    image_output_path = os.path.join(output_directory, "image_outputs/", image_output_file_name)

    if not os.path.exists(os.path.dirname(size_output_path)):
        os.makedirs(os.path.dirname(size_output_path))
    if not os.path.exists(os.path.dirname(image_output_path)):
        os.makedirs(os.path.dirname(image_output_path))

    group_name = group_assignment_list[i]
    """
    if group_handling == "automatic":
        group_name = file_name_base[:file_name_base.rfind('_')] if '_' in file_name_base else file_name_base
    elif group_handling == "manual":
        group_name = group_assignment_dict.get(img_path, "unassigned")
    """
    res = count_colonies(imp, img_path, is_global_first, same_roi_flag,threshold_flag, thresh_flag_score, image_output_path)

    area_list = res[0]
    colony_count = len(area_list) if area_list else 0

    # Write a single image colony distribution file
    current_time = str(java.time.ZonedDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")))
    f = open(size_output_path, 'w')
    f.write("# countPHICS2 v" + macro_version + " --- " + current_time + "\n"
            "# Number of colonies: " + str(colony_count) + "\n"
            "Colony Area in Square Pixels\n")

    if area_list:
        f.write("\n".join(str(area) for area in area_list) + "\n")
    f.close()

    def calculate_median_area(colony_area_list, num_colonies):
        sorted_areas = sorted(colony_area_list)

        if num_colonies % 2 == 1:
            return sorted_areas[num_colonies // 2]
        else:
            mid1 = sorted_areas[num_colonies // 2 - 1]
            mid2 = sorted_areas[num_colonies // 2]
            return (mid1 + mid2) / 2

    def calculate_geometric_mean(colony_area_list, num_colonies):
        log_sum = 0.0

        for pixel_area in colony_area_list:
            if pixel_area <= 0:
                continue
            log_sum += math.log(pixel_area)

        return round(math.exp(log_sum / num_colonies), 2)

    if colony_count > 0:
        median_area = calculate_median_area(area_list, colony_count)
        geom_mean_area = calculate_geometric_mean(area_list, colony_count)
        max_area = int(max(area_list))
        min_area = int(min(area_list))
    else:
        median_area = 0.0
        geom_mean_area = 0.0
        max_area = 0.0
        min_area = 0.0

    # Write to Summary
    if is_global_first:
        current_time = str(java.time.ZonedDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")))

        metadata = '# countPHICS2 v' + macro_version + ' run: '+ current_time + '\n'

        t_min = globals().get('thres_min', 0)
        t_max = globals().get('thres_max', 0)

        parameters = '# Parameters: \n' + \
                    '# AutoThreshold=' + '\t' + str(threshold_flag) + '\n' + \
                    '# SameROI=' + '\t' + str(same_roi_flag) + '\n' + \
                    '# Image ROI=' + '\t' + str(roi2) + '\n' + \
                    '# RollingBall=' + '\t' + str(rolling_ball) + '\n' + \
                    '# MinColony=' + '\t' + str(minimum_col) + '\n' + \
                    '# MaxColony=' + '\t' + str(maximum_col) + '\n' + \
                    '# Circularity=' + '\t' + str(circ) + '\n' + \
                    '# Sigma=' + '\t' + str(sigma) + '\n' \
                    '# MinThresh=' + '\t' + str(t_min) + '\n' \
                    '# MaxThresh=' + '\t' + str(t_max) + '\n' \
                    '# Cell Line=' + '\t' + str(cell_line) + '\n' \
                    '# Treatment=' + '\t' + str(treatment_name) + '\n'

        header = (metadata + "\n" + parameters + '\n' + "\n" + 'ImageName\tGroup\tColonies\tMinCountedSize\tMaxCountedSize\tMedianSize\tGeomMeanSize\n')
        summary_lines.append(header)
        
    row = file_name_base + ".tif\t" + group_name + "\t" + str(colony_count) + "\t" + str(min_area) + "\t" + str(max_area) + "\t" + str(median_area) + "\t" + str(geom_mean_area) + "\n"
    summary_lines.append(row)

    if colony_count > 10: thresh_flag_score = False

    imp.close()

f_sum = open(summary_path, 'w')
f_sum.writelines(summary_lines)

WaitForUserDialog("Analysis complete!", "Results saved in:\n" + 
                  output_directory + "\n" + 
                  "FIJI will now automatically close...").show()

IJ.run("Quit")