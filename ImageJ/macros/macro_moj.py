from java.io import File
from ij import IJ, WindowManager, ImagePlus, Macro, ImageStack
from ij.process import FloatProcessor,LUT, ByteProcessor, ImageProcessor
from java.util import Random
from jarray import zeros
from ij.plugin.filter import EDM, ParticleAnalyzer, RGBStackSplitter, GaussianBlur, BackgroundSubtracter
from ij.measure import ResultsTable
from ij.plugin.frame import RoiManager, ThresholdAdjuster
from ij.measure import Measurements
from java.lang import Double
from ij.gui import (HistogramWindow, OvalRoi, GenericDialog, TrimmedButton, DialogListener, NonBlockingGenericDialog,
                    Toolbar, ImageWindow, Roi, WaitForUserDialog)
from ij.plugin import ChannelSplitter
import os
import java.time
from ij.io import OpenDialog, DirectoryChooser
from java.awt import Button
from java.awt.event import ActionListener, ActionEvent
from ij.plugin.frame.Editor import actionPerformed

macro_version = '2.0.0'
srcDir = False
output_directory = False

class MyListener (ActionListener):
    def actionPerformed(self, event):
        global od
        od = OpenDialog("Select First Image", None)
        global srcDir
        srcDir = od.getDirectory()

class MyListener2 (ActionListener):
    output_directory = False
    def actionPerformed(self, event):
        global od2
        od2 = DirectoryChooser("Select Output Directory")
        global output_directory
        output_directory = od2.getDirectory()

greet = NonBlockingGenericDialog("Colony Counter")
greet.addMessage("Our Colony Counter is an ImageJ macro which counts the number and calculates sizes of colonies "
                 "located in the given image.")
greet.addMessage("Please press \"Select FIRST image\" to chose images and \"Select output directory\" "
                 "to specify where to save data.")
bt = TrimmedButton("Select FIRST image",10)
bt.addActionListener(MyListener())
greet.add(bt)
bt2 = TrimmedButton("Select output directory",10)
a = bt2.addActionListener(MyListener2())
greet.add(bt2)
greet.showDialog()

while 1<2:
    if greet.wasOKed() and srcDir == False:
        greet = NonBlockingGenericDialog("Colony Counter")
        greet.addMessage("ERROR: Please select the image!")
        greet.addMessage("Colony Counter is an ImageJ macro which counts the number and calculates sizes of the "
                         "colonies located at the given image.")
        greet.addMessage("Please press \"Select FIRST image\" to chose images and \"Select output directory\" "
                         "to specify where to save data.")
        bt = TrimmedButton("Select FIRST image",10)
        bt.addActionListener(MyListener())
        greet.add(bt)
        bt2 = TrimmedButton("Select Output Directory",10)
        bt2.addActionListener(MyListener2())
        greet.add(bt2)
        greet.showDialog()
    else:
        break

if greet.wasOKed() and output_directory == False:
    output_directory = '../output_data'
if output_directory is None:
    output_directory = '../output_data'

nazwa =  od.getFileName()
if '_' in nazwa:
    idx = nazwa.find('_')
    first_image = nazwa[:idx]
    idx2 = nazwa.find('.')
    file_name = nazwa[idx+1:idx2]
    file_full = nazwa[idx:]
else:
    idx2 = nazwa.find('.')
    first_image = nazwa[:idx2]
    file_name = ''
    file_full = nazwa[idx2:]

dia = NonBlockingGenericDialog("SETTINGS")
dia.addMessage("Choose analysis parameters: ")
dia.hideCancelButton()
dia.addCheckbox('Automatic Threshold', False)
dia.addCheckbox('Same ROI for all images', False)
dia.addMessage("Choose image format (check if it's a 6-well plate image): ")
dia.addCheckbox('6-well plate', False)
dia.addMessage("Advanced settings, for manual parameters")
dia.addCheckbox('Advanced settings', False)
dia.addNumericField('Number of the LAST image to analyze:', int(first_image) , 0)
dia.showDialog()
checkboxes = [dia.getNextBoolean(), dia.getNextBoolean(),dia.getNextBoolean(), dia.getNextBoolean()]
last_image = int(dia.getNextNumber())

path_1 = str(int(first_image)) + file_full
path = os.path.join(srcDir, path_1)
imp = IJ.openImage(path)
cal =  imp.getCalibration()
x = cal.pixelWidth
units = cal.getUnit()
units_known = True

if checkboxes[2]:
    w = imp.getWidth()/2
    h = imp.getHeight()/3
else:
    w = imp.getWidth()
    h = imp.getHeight()

if units == 'mm':
    dpi = 1.0 / (x / 254.0)
elif units == 'cm':
    dpi = 1.0 / (x / 2.54)
elif units == 'inch':
    dpi = 1.0 / x
else:
    units_known = False

if checkboxes[3]:
    dia_a = NonBlockingGenericDialog("ADVANCED SETTINGS")
    dia_a.addMessage("These parameters are automatically set by default. \n "
                     "If you want to change them it is recommended to read Instruction.pdf first.")
    dia_a.addNumericField('Rolling ball radius:', int(w*0.0306) , 0)
    dia_a.addNumericField('Minimum colony size:', int(0.01*w), 0)
    dia_a.addNumericField('Circularity:', 0.5, 0 )

    if not units_known:
        dia_a.addNumericField('Sigma:', int(0.001*w), 0 )
    else:
        dia_a.addNumericField('Sigma:', int(( 1.9*10**(-6))*dpi**2 + (6.3*10**(-4))*dpi + 1.3 ), 0 )

    dia_a.showDialog()
    values = [dia_a.getNextNumber(), dia_a.getNextNumber(), dia_a.getNextNumber(),  dia_a.getNextNumber()]
    rolling_ball = values[0]
    minimum_col = values[1]
    circ = values[2]
    sigma = values[3]
    print(circ)
else:
    rolling_ball = int(w*0.0306)
    minimum_col = int(0.01*w)
    circ = 0.5
    if not units_known:
        sigma = 0.001 * w
    else:
        sigma = ( 1.9*10**(-6))*dpi**2 + (6.3*10**(-4))*dpi + 1.3

checkbox_values = ("Automatic Threshold: " + str(checkboxes[0]) + "\nSame ROI for all images: " + str(checkboxes[1]) +
      "\n6-well plate format: " + str(checkboxes[2]) + "\nRolling ball radius: " + str(rolling_ball) +
      "\nMinimum colony size: " + str(minimum_col) + "\nCircularity: " + str(circ) + "\n")

print(checkbox_values)

def count_colonies(imp, image_number, first_image,  Roi_flag, threshold_flag, thres_iteration_flag, path,
                    roi_def = OvalRoi(69, 92, 646, 651)):

    w = imp.getWidth()
    h = imp.getHeight()
    cal =  imp.getCalibration()
#	x = cal.pixelWidth
#	y = cal.pixelHeight
    units = cal.getUnit()

    splitter = RGBStackSplitter()
    splitter.split(imp.getStack(), True)
    red =  ImagePlus("Red", splitter.red)
    green = ImagePlus("Green", splitter.green)
    blue = ImagePlus("Blue", splitter.blue)

    red.setCalibration(cal)
    green.setCalibration(cal)
    blue.setCalibration(cal)

    roi =  OvalRoi(w/4, h/4, w/2, h/2)
    red.setRoi(roi)
    green.setRoi(roi)
    blue.setRoi(roi)
    stats_red = red.getStatistics(Measurements.STD_DEV).stdDev
    stats_green = green.getStatistics(Measurements.STD_DEV).stdDev
    stats_blue = blue.getStatistics(Measurements.STD_DEV).stdDev

    std_max = max (stats_red, stats_green, stats_blue)

    if std_max == stats_red:
        imp = red
    if std_max == stats_green:
        imp = green
    if std_max == stats_blue:
        imp = blue

    imp.getProcessor().blurGaussian(sigma)
    BackgroundSubtracter().subtractBackround(imp.getProcessor(), int(rolling_ball))
    #0.0306 is the const value calculated based on many picturies analysis.

    def ROI_manager():
        IJ.run("Roi Defaults...", "color=orange stroke=3.0 group=0");
        imp.setRoi(OvalRoi(w/10, h/10, w/1.2, h/1.2))
        imp.show()

        class MyListener (ActionListener):
            def actionPerformed(self, event):
                imp.setRoi(OvalRoi(w/10, h/10, w/1.2, h/1.2))
                Toolbar().setTool("oval")

        dia2 = NonBlockingGenericDialog("ROI SELECTION")
        dia2.addMessage("Fit ROI to the inner edge of the dish, then click OK. ")
        roi_x = IJ.getInstance().getLocation().x #+ w
        roi_y = IJ.getInstance().getLocation().y - 40

        dia2.setLocation(roi_x,roi_y)
        dia2.hideCancelButton()
        bt = TrimmedButton("Recreate ROI",10);
        bt.addActionListener(MyListener())
        dia2.add(bt);
        dia2.showDialog()
        roi2 = imp.getRoi()

        return imp.getRoi()

    if Roi_flag:
        if int(image_number) == int(first_image):
            global roi2
            roi2 =  ROI_manager()
            roi_def = roi2
        else:
            imp.setRoi(roi2)
            # roi_def = roi2
            imp.show()

    else:
        roi2 = ROI_manager()

    if threshold_flag:
        # IJ.run("Auto Threshold", "method=Default white")
        IJ.run("Auto Threshold", "method=Yen white")
        # IJ.run("Auto Local Threshold", "method=Yen radius=10 parameter_1=0 parameter_2=0 white")
        """
        Need to capture the threshold values for the summary file.
        """
        thres_min = imp.getProcessor().getMinThreshold()
        thres_max = imp.getProcessor().getMaxThreshold()

    elif threshold_flag == False and thres_iteration_flag == True:

        IJ.run("Threshold...")
        WaitForUserDialog("Adjust threshold level with the scrollbar. \n "
                          "All colonies should be marked and at the same time background should not be.\n "
                          "DO NOT press any button on the threshold window.\n "
                          "Once the threshold value is set click OK below").show()
        global thres_min
        global thres_max
        thres_min = imp.getProcessor().getMinThreshold()
        thres_max = imp.getProcessor().getMaxThreshold()

        IJ.setThreshold(imp, thres_min, thres_max);
        IJ.run(imp, "Convert to Mask", "")
        IJ.selectWindow("Threshold")
        IJ.run("Close")

    else:
        IJ.setThreshold(imp, thres_min, thres_max);
        IJ.run(imp, "Convert to Mask", "")

    imp.setRoi(roi2)
    ip = imp.getProcessor()
    ImageProcessor.erode(ip)
    ImageProcessor.dilate(ip)
    IJ.run("Watershed")

    roim = RoiManager(True)
    table = ResultsTable()

    # Create a ParticleAnalyzer, with arguments:
    # 1. options (could be SHOW_ROI_MASKS, SHOW_OUTLINES, SHOW_MASKS, SHOW_NONE, ADD_TO_MANAGER, and others; combined with bitwise-or)
    # 2. measurement options (see [http://imagej.net/developer/api/ij/measure/Measurements.html Measurements])
    # 3. a ResultsTable to store the measurements
    # 4. The minimum size of a particle to consider for measurement
    # 5. The maximum size (idem)
    # 6. The minimum circularity of a particle
    # 7. The maximum circularity

    pa = ParticleAnalyzer(ParticleAnalyzer.SHOW_ROI_MASKS, Measurements.AREA, table, minimum_col,
                          Double.POSITIVE_INFINITY, circ, 1.0)
    pa.setHideOutputImage(True)

    if pa.analyze(imp):
        pass
    else:
        print("There was a problem in analyzing", blobs)

    areas = table.getColumn(0)
    # The number of colonies is len(areas)

    IJ.saveAs( imp, "png", path )
    imp.changes = False
    imp.close()
    return [areas, roi2, imp, units]

print ("Image: Number of colonies")
thresh_flag_score = True

for image_number in range (int(first_image), last_image + 1):
    path_1 = str(image_number) + file_full
    path = os.path.join(srcDir, path_1)
    imp = IJ.openImage(path)
    iteration = 1

    if checkboxes[2]:
        print("6-well plate format")
        w = imp.getWidth()
        h = imp.getHeight()
        img_number = 1
        for i in range(3):
            for j in range(2):
                roi = Roi(j*(w/2),i*(h/3),w/2,h/3)
                imp.setRoi(roi)
                imp2 = imp.crop()
                path_1 = str(image_number)+ '_' + str(img_number) + file_name + '.txt'
                path = os.path.join(output_directory, path_1)
                if img_number > 1:
                    a = count_colonies( imp2, img_number , 1, checkboxes[1], checkboxes[0], thresh_flag_score ,
                                        path, a[1] )
                elif img_number == 1 and iteration == 1:
                    a = count_colonies( imp2, img_number , 1, checkboxes[1], checkboxes[0], thresh_flag_score, path )
                else:
                    a = count_colonies( imp2, img_number , 1, checkboxes[1], checkboxes[0], thresh_flag_score, path )

                f = open (path, 'w')
                if (a[0] == None):
                    liczba = 0
                else:
                    liczba = len(a[0])
                f.write("Number of colonies on " + str(image_number) + '_' + str(img_number) + ' image: ' + str(liczba) + '\n')
                if a[3] == 'mm':
                    f.write("Size of colonies in mm:" + '\n')
                    if liczba != 0:
                        for area in a[0]:
                            f.write(str(area) + '\n')
                elif a[3] == 'cm':
                    f.write("Size of colonies in mm:" + '\n')
                    if liczba != 0:
                        for area in a[0]:
                            area = area * 100
                        f.write(str(area) + '\n')
                elif a[3] == 'inch':
                    f.write("Size of colonies in mm:" + '\n')
                    if liczba != 0:
                        for area in a[0]:
                            area = area * 2.54 * 2.54 * 100
                            f.write(str(area) + '\n')
                else:
                    f.write("Size of colonies in unknown units (pixels?)" + '\n')
                    if liczba != 0:
                        for area in a[0]:
                            f.write(str(area) + '\n')

                f.close()
                a[2].changes = False
                a[2].close()
                wydruk = str(image_number) + '_' + str(img_number) + ': ' + str(liczba)
                img_number +=1
                print (wydruk)
                if liczba > 10:
                    thresh_flag_score = False

    else:
        path_1 = str(image_number) + file_name +  '.txt'
        path = os.path.join(output_directory, path_1)
        if iteration == 1:
            a = count_colonies( imp, image_number, first_image, checkboxes[1], checkboxes[0], thresh_flag_score, path)
        else:
            a = count_colonies( imp, image_number, first_image, checkboxes[1], checkboxes[0], thresh_flag_score, path)

        f = open (path, 'w')
        if a[0] is None:
            liczba = 0
        else:
            liczba = len( a[0] )
        f.write("Number of colonies on " + nazwa + " image: " + str(liczba)+ '\n')
        if a[3] == 'mm':
            f.write("Size of colonies in mm:" + '\n')
            if liczba != 0:
                for area in a[0]:
                    f.write(str(area) + '\n')
        elif a[3] == 'cm':
            f.write("Size of colonies in mm:" + '\n')
            if liczba != 0:
                for area in a[0]:
                    area = area * 100
                    f.write(str(area) + '\n')
        elif a[3] == 'inch':
            f.write("Size of colonies in mm:" + '\n')
            if liczba != 0:
                for area in a[0]:
                    area = area * 2.54 * 2.54 * 100
                    f.write(str(area) + '\n')
        else:
            f.write("Size of colonies in unknown units (pixels?)" + '\n')
            if liczba != 0:
                for area in a[0]:
                    f.write(str(area) + '\n')
        f.close()

        a[2].changes = False
        a[2].close()
        wydruk = str(image_number) + '.tif' + '\t' + str(liczba)
        path_2 = 'Summary.txt'
        path2 = os.path.join(output_directory, path_2)

        """
        If first image, setup summary file and write header.
        """
        if int(image_number) == int(first_image):
            f = open(path2, 'w')
            min_threshold = 'Minimum Threshold: ' + str(thres_min) + '\n'
            max_threshold = 'Maximum Threshold: ' + str(thres_max) + '\n'
            timeNow = 'countPHICS v' + macro_version + ' run: '+ str(java.time.Instant.now()) + '\n'
            header = (timeNow + checkbox_values +
                      '\nImage\tNumber of colonies\tMin Threshold\tMax Threshold\tImage ROI\n')

            f.write(header)
            f.close()

        f = open(path2, 'a')
        f.write(wydruk + '\t' + str(thres_min) + '\t' + str(thres_max) + '\t' + str(roi2) + '\n')
        f.close()

        print ('Image ' + str(image_number) + ':  ' + str(liczba) + '\n')
        if liczba > 10:
            thresh_flag_score = False
