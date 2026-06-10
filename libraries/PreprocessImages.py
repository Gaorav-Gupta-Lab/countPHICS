"""
Split grouped images into separate files.
"""
import os
import tifffile


def split_10cm_dish(input_path, image_files):
    """
    Splits provided images into sub-images based on predefined dimensions representing dimensions of a
    10 cm dish. The function validates that all images have the same resolution before processing and
    saves cropped sub-images to the specified input path.

    :param input_path: The directory where cropped images will be saved.
    :type input_path: str
    :param image_files: A list of file paths to the images that need to be split.
    :type image_files: list[str]
    :return: A tuple containing an error message (if any), the total number of files checked,
             and the total number of cropped images generated.
    :rtype: tuple[str, int, int]
    """

    # static_file = "D:{}Colony Images{}01.tif".format(os.sep, os.sep, os.sep)

    # Define image start/stop.  These are all millimeters. The order is x_start, x_end, y_start, y_end.
    image_sizes = [(0, 85, 0, 86), (89, 176, 0, 86), (0, 85, 88.5, 176)]
    split_count = len(image_sizes)
    output_count = 0

    file_resolution = 0
    file_count = 0
    error_msg = ""

    for file in image_files:
        # Get image resolution.  For now, it doesn't matter which axis.
        tif = tifffile.TiffFile(file)
        tag = tif.pages[0].tags['XResolution']
        resolution = tag.value[0] / tag.value[1]
        tif.close()
        if file_count == 0:
            file_resolution = resolution
            first_file = file

            #  Convert resolution from dpi to dpmm
            dpmm = round(resolution / 25.4, 2)

        file_count += 1
        if file_resolution != resolution:
            print("Image Resolutions do not match.")
            error_msg = "Image Resolutions do not match for files:\n\t{}\n\t{}.".format(first_file, file)
            return error_msg, file_count, output_count

       # Read the image.
        image = tifffile.imread(file)

        for i in range(split_count):
            x_start, x_end, y_start, y_end = (int(image_sizes[i][0]*dpmm), int(image_sizes[i][1]*dpmm),
                                              int(image_sizes[i][2]*dpmm), int(image_sizes[i][3]*dpmm))
            output_count += 1
            # Adjust the image file name.
            if output_count < 10:
                file_increment = "0" + str(output_count)
            else:
                file_increment = str(output_count)

            # cropped_file = "D:{}Colony Images{}cropped_image_{}.tif".format(os.sep, os.sep, i)
            tifffile.imwrite("{}{}cropped_image_{}.tif"
                             .format(input_path, os.sep, file_increment), image[y_start:y_end, x_start:x_end])
        os.remove(file)

    return error_msg, file_count, output_count


if __name__ == "__main__":
    image_folder = r"D:\Users\Colony Images"
    main(image_folder)