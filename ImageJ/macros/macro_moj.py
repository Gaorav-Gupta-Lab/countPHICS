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

macro_version = '2.1.2'

# --- 1. Parameter Parsing ---
def parse_parameter_file():
    od = OpenDialog("Select countPHICS parameter file", None)
    param_dir = od.getDirectory()
    param_name = od.getFileName()

    if param_dir is None or param_name is None:
        IJ.log("No parameter file selected. Aborting.")
        sys.exit()

    param_path = os.path.join(param_dir, param_name)

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

# Create list of images from the parameter string
all_images = images_raw.split(";")

# Helper for boolean conversion
def as_bool(v):
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
units_known = True

if units == 'mm':
    dpi = 1.0 / (x / 254.0)
elif units == 'cm':
    dpi = 1.0 / (x / 2.54)
elif units == 'inch':
    dpi = 1.0 / x
else:
    units_known = False

# --- 3. Parameter Setup ---
threshold_flag = as_bool(params.get("auto_threshold"))
same_roi_flag = as_bool(params.get("same_roi"))
six_well_flag = as_bool(params.get("six_well"))
advanced_flag = as_bool(params.get("advanced"))

if six_well_flag:
    w = imp.getWidth()/2
    h = imp.getHeight()/3
else:
    w = imp.getWidth()
    h = imp.getHeight()

# Advanced Parameters
if advanced_flag:
    rolling_ball = int(params.get("rolling_ball", int(w * 0.0306)))
    minimum_col  = int(params.get("min_colony", int(0.01 * w)))
    maximum_col  = int(params.get("max_colony", int(w)))
    circ         = float(params.get("circularity", 0.5))
    if not units_known:
        sigma = float(params.get("sigma", 0.001 * w))
    else:
        sigma = float(params.get("sigma", (1.9e-6) * dpi**2 + (6.3e-4) * dpi + 1.3))
else:
    rolling_ball = int(w * 0.0306)
    minimum_col  = int(0.01 * w)
    maximum_col  = int(w)
    circ         = 0.5
    sigma = 0.001 * w if not units_known else ((1.9e-6) * dpi**2 + (6.3e-4) * dpi + 1.3)

imp.close() # Close the calibration image

# --- 4. The Refactored Count Function ---
def count_colonies(imp, original_path, is_first, Roi_flag, threshold_flag, thres_iteration_flag, image_output_path, roi_def=None):
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

    # Auto-select best channel based on contrast (StdDev), virtually always green
    roi_chk = OvalRoi(w/4, h/4, w/2, h/2)
    red.setRoi(roi_chk); green.setRoi(roi_chk); blue.setRoi(roi_chk)
    
    stats_red = red.getStatistics(Measurements.STD_DEV).stdDev
    stats_green = green.getStatistics(Measurements.STD_DEV).stdDev
    stats_blue = blue.getStatistics(Measurements.STD_DEV).stdDev
    std_max = max(stats_red, stats_green, stats_blue)

    if std_max == stats_red: proc_imp = red
    elif std_max == stats_green: proc_imp = green
    else: proc_imp = blue

    proc_imp.getProcessor().blurGaussian(sigma)
    BackgroundSubtracter().subtractBackround(proc_imp.getProcessor(), int(rolling_ball))

    # --- ROI Management ---
    def ROI_manager():
        IJ.run("Roi Defaults...", "color=orange stroke=3.0 group=0")
        proc_imp.setRoi(OvalRoi(w/10, h/10, w/1.2, h/1.2))
        proc_imp.show()

        class MyListener(ActionListener):
            def actionPerformed(self, event):
                proc_imp.setRoi(OvalRoi(w/10, h/10, w/1.2, h/1.2))
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
print("Processing " + str(len(all_images)) + " images...")
thresh_flag_score = True

summary_path = os.path.join(output_directory, 'Summary.txt')

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

    # --- 6-Well Logic ---
    if six_well_flag:
        w_img = imp.getWidth()
        h_img = imp.getHeight()
        well_count = 1
        
        for row in range(3):
            for col in range(2):
                # Calculate Crop ROI for this well
                roi = Roi(col*(w_img/2), row*(h_img/3), w_img/2, h_img/3)
                imp.setRoi(roi)
                imp_well = imp.crop()
                imp_well.setTitle(file_name_base + "_Well" + str(well_count))
                
                # Determine output filename
                out_name = file_name_base + "_Well" + str(well_count) + ".txt"
                out_path = os.path.join(output_directory, out_name)
                
                # Check if this is the very first well of the very first image
                is_first_well = (is_global_first and well_count == 1)

                # Analyze
                res = count_colonies(imp_well, img_path, is_first_well, same_roi_flag, 
                                     threshold_flag, thresh_flag_score, out_path)
                
                # Write individual text file
                area_list = res[0]
                count = len(area_list) if area_list else 0
                
                f = open(out_path, 'w')
                f.write("Number of colonies: " + str(count) + "\n")
                f.write("Units: " + res[3] + "\n")
                if area_list:
                    for area in area_list:
                        # Unit conversion logic preserved from original
                        if res[3] == 'cm': area *= 100
                        elif res[3] == 'inch': area = area * 2.54**2 * 100
                        f.write(str(area) + "\n")

                # Write to Summary
                mode = 'w' if is_first_well else 'a'
                f_sum = open(summary_path, mode)
                if is_first_well:
                    f_sum.write("Image\tWell\tCount\tMinThresh\tMaxThresh\n")
                
                # Threshold retrieval
                t_min = globals().get('thres_min', 0)
                t_max = globals().get('thres_max', 0)
                    
                f_sum.write(file_name_base + "\t" + str(well_count) + "\t" + str(count) + "\t" + str(t_min) + "\t" + str(t_max) + "\n")

                print(file_name_base + " Well " + str(well_count) + ": " + str(count))
                if count > 10: thresh_flag_score = False
                well_count += 1

    # --- Standard Single Image Logic ---
    else:
        # out_name = file_name_base + "size_distribution" + ".txt"
        # out_path = os.path.join(output_directory, out_name)

        size_output_file_name = file_name_base + "_size_distribution.txt"
        size_output_path = os.path.join(output_directory, "size_distribution_files/", size_output_file_name)

        image_output_file_name = file_name_base + "_counted.jpg"
        image_output_path = os.path.join(output_directory, "image_outputs/", image_output_file_name)

        if not os.path.exists(os.path.dirname(size_output_path)):
            os.makedirs(os.path.dirname(size_output_path))
        if not os.path.exists(os.path.dirname(image_output_path)):
            os.makedirs(os.path.dirname(image_output_path))

        group_name = file_name_base[:file_name_base.rfind('_')] if '_' in file_name_base else file_name_base
        # print("Group Name: " + group_name + " for image: " + file_name_base)
        
        res = count_colonies(imp, img_path, is_global_first, same_roi_flag, 
                             threshold_flag, thresh_flag_score, image_output_path)
        
        area_list = res[0]
        count = len(area_list) if area_list else 0

        # Write single image colony distribution file
        f = open(size_output_path, 'w')
        f.write("Number of colonies: " + str(count) + "\n")
        # f.write("Units: " + res[3] + "\n")
        f.write("Colony Area\n")

        if area_list:
            area_list = [area * 645.16 * 100 for area in area_list]  # convert from pixels^2 to mm^2
            for area in area_list:
                # if res[3] == 'cm': area *= 100
                # elif res[3] == 'inch': area = area * 2.54**2 * 100
                f.write(str(area) + "\n")

        def calculate_median_area(area_list):
            sorted_areas = sorted(area_list)
            n = len(sorted_areas)
            if n == 0:
                return 0
            elif n % 2 == 1:
                return sorted_areas[n // 2]
            else:
                mid1 = sorted_areas[n // 2 - 1]
                mid2 = sorted_areas[n // 2]
                return (mid1 + mid2) / 2

        def calculate_geometric_mean(area_list):
            if not area_list:
                return 0.0

            log_sum = 0.0
            n = len(area_list)

            for area in area_list:
                if area <= 0:
                    continue
                log_sum += math.log(area)

            return math.exp(log_sum / n)

        if count > 0:
            median_area = calculate_median_area(area_list)
            geom_mean_area = calculate_geometric_mean(area_list)

        # Write to Summary
        mode = 'w' if is_global_first else 'a'
        f_sum = open(summary_path, mode)
        current_time = str(java.time.ZonedDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")))

        metadata = '# countPHICS v' + macro_version + ' run: '+ current_time + '\n'

        parameters = '# Parameters: \n' + \
                    '# AutoThreshold= ' + str(threshold_flag) + '\n' + \
                    '# SameROI=' + str(same_roi_flag) + '\n' + \
                    '# SixWell=' + str(six_well_flag) + '\n' + \
                    '# RollingBall=' + str(rolling_ball) + '\n' + \
                    '# MinColony=' + str(minimum_col) + '\n' + \
                    '# MaxColony=' + str(maximum_col) + '\n' + \
                    '# Circularity=' + str(circ) + '\n' + \
                    '# Sigma=' + str(sigma) + '\n'

        header = (metadata + "\n" + parameters + "\n" + 'Image\tGroup\tNum colonies\tMedianSize\tGeomMeanSize\tMin Thresh\tMax Thresh\tImage ROI\n')
        if is_global_first:
                f_sum.write(header)
                # f_sum.write("Image\tCount\tMinThresh\tMaxThresh\tROI")
            
        t_min = globals().get('thres_min', 0)
        t_max = globals().get('thres_max', 0)
        # f_sum.write(file_name_base + "\t" + group_name + "\t" + str(count) + "\t" + str(t_min) + "\t" + str(t_max) + "\t" + str(roi2) + "\n")
        f_sum.write(file_name_base + ".tif\t" + group_name + "\t" + str(count) + "\t" + str(median_area) + "\t" + str(geom_mean_area) + "\t" + str(t_min) + "\t" + str(t_max) + "\t" + str(roi2) + "\n")
        f_sum.close()
        print(file_name_base + ": " + str(count))
        if count > 10: thresh_flag_score = False

    imp.close()

WaitForUserDialog("Analysis complete!", "Results saved in:\n" + 
                  output_directory + 
                  "\nFIJI will now automatically close...").show()

IJ.run("Quit")