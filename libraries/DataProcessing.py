"""
Module for statistical analysis and data processing of cell survival studies.

This module provides methods for loading and normalizing cell survival data,
performing statistical significance analysis, and organizing results for
downstream visualization or comparison. The statistical analysis incorporates
ANOVA using survival data across various treatments and cell lines.

"""

import csv
import os
import pathlib
import pandas as pd
import statsmodels.api as sm
# from numba.core.types import none
from statsmodels.formula.api import ols
import scipy.stats
# import Tool_Box
# from statsmodels.stats.multicomp import pairwise_tukeyhsd
# from scipy.optimize import curve_fit

def test_data():
    """
    Lists used for testing.
    :return:
    """

    treatment1 = ['0','0','0','0','0','0',
                  '15','15','15','15','15','15',
                  '30','30','30','30','30','30',
                  '45','45','45','45','45','45',
                  '60','60','60','60','60','60',
                  ]

    treatment2 = ['0','0','0','0','0','0','0','0','0',
                  '15','15','15','15','15','15','15','15','15',
                  '30','30','30','30','30','30','30','30','30',
                  '45','45','45','45','45','45','45','45','45',
                  '60','60','60','60','60','60','60','60','60',
                  ]
    treatment3 = ['0', '0', '0', '0', '0', '0', '0', '0', '0',
                  '15', '15', '15', '15', '15', '15', '15', '15', '15',
                  '30', '30', '30', '30', '30', '30', '30', '30', '30',
                  '45', '45', '45', '45', '45', '45', '45', '45', '45',
                  '60', '60', '60', '60', '60', '60', '60', '60', '60']

    cell_line1 = ['TP53','TP53','TP53','V3','V3','V3',
                  'TP53','TP53','TP53','V3','V3','V3',
                  'TP53','TP53','TP53','V3','V3','V3',
                  'TP53','TP53','TP53','V3','V3','V3',
                  'TP53','TP53','TP53','V3','V3','V3',]

    cell_line2 = ['TP53','TP53','TP53','V1','V1','V1','V3','V3','V3',
                  'TP53','TP53','TP53','V1','V1','V1','V3','V3','V3',
                  'TP53','TP53','TP53','V1','V1','V1','V3','V3','V3',
                  'TP53','TP53','TP53','V1','V1','V1','V3','V3','V3',
                  'TP53','TP53','TP53','V1','V1','V1','V3','V3','V3',]

    cell_line3 = ['TP53', 'TP53', 'TP53', 'V1', 'V1', 'V1', 'V3', 'V3', 'V3',
                  'TP53', 'TP53', 'TP53', 'V1', 'V1', 'V1', 'V3', 'V3', 'V3',
                  'TP53', 'TP53', 'TP53', 'V1', 'V1', 'V1', 'V3', 'V3', 'V3',
                  'TP53', 'TP53', 'TP53', 'V1', 'V1', 'V1', 'V3', 'V3', 'V3',
                  'TP53', 'TP53', 'TP53', 'V1', 'V1', 'V1', 'V3', 'V3', 'V3']

    survival1 = [97.16,94.43,108.41,93.42,97.37,109.21,
                 91.02,101.25,97.84,92.98,100.88,116.23,
                 92.05,92.73,97.16,99.56,106.58,111.84,
                 72.27,94.09,87.27,86.4,95.18,92.54,
                 57.27,68.52,78.07,91.67,65.35,100]

    survival2 = [97.16,94.43,108.41,103.22,99.89,96.89,93.42,97.37,109.21,
                 91.02,101.25,97.84,62.93,76.25,70.92,92.98,100.88,116.23,
                 92.05,92.73,97.16,62.26,57.27,58.6,99.56,106.58,111.84,
                 72.27,94.09,87.27,34.3,33.63,25.64,86.4,95.18,92.54,
                 57.27,68.52,78.07,20.31,15.65,15.65,91.67,65.35,100]

    survival3 = [97.16, 94.43, 108.41, 103.22, 99.89, 96.89, 93.42, 97.37, 109.21,
                 91.02, 101.25, 97.84, 62.93, 76.25, 70.92, 92.98, 100.88, 116.23,
                 92.05, 92.73, 97.16, 62.26, 57.27, 58.6, 99.56, 106.58, 111.84,
                 72.27, 94.09, 87.27, 34.3, 33.63, 25.64, 86.4, 95.18, 92.54,
                 57.27, 68.52, 78.07, 20.31, 15.65, 15.65, 91.67, 65.35, 100.0]

def significance(df, cell_list, output_string):
    """
    Performs statistical significance analysis on survival data.
    :return:
    """
    control_cell_line = cell_list[0]
    for cell_line in cell_list[1:]:
        # print(f"Comparing {control_cell_line} vs {cell_line}")
        filtered_df = df.loc[df['Cell_Line'].isin([control_cell_line, cell_line])].copy()
        model = ols('Survival ~ C(Cell_Line) * C(Treatment)', data=filtered_df).fit()
        anova_table = sm.stats.anova_lm(model, typ=2)
        # output_string += f'{control_cell_line} vs {cell_line}\t{round(anova_table.iat[2, 3], 4)}\n'
        output_string += f'{control_cell_line} vs {cell_line}\t{anova_table.iat[2, 3]}\n'
        # print(anova_table)
        # print(f'Anova p_Val for {control_cell_line} vs {cell_line}\t {round(anova_table.iat[2, 3], 4)}\n')
    return output_string


def data_processing(input_path=None, output_path=None):
    input_path = "D:{0}Colony Images{0}".format(os.sep)
    cell_line = ""
    cell_line_names = []
    cell_line_count = 0
    treatment = ""
    raw_data_dict = {}

    # find all txt files in the input_path directory and process them one by one.
    for file in pathlib.Path(input_path).glob("*.txt"):
        ctrl_sample = False
        open_file = csv.reader(open(file), delimiter='\t')

        for line in open_file:
            # Skip empty lines
            if not line:
                continue

            # Convert the control sample flag to boolean
            if line[0] == '# CTRL_Sample':
                ctrl_sample = line[1].lower() in ("yes", "y", "true", "1")

            # Get the cell line name from the file
            elif line[0] == "# Cell Line=":
                cell_line = line[1]
                cell_line_names.append(cell_line)
                cell_line_count += 1

            # Get the treatment name from the file
            elif line[0] == "# Treatment=":
                treatment = line[1]

            # Get the group values and colony counts into a dictionary.
            elif ".tif" in line[0]:
                concentration = line[1]
                cell_line_key = "{}|{}|{}|{}".format(cell_line, treatment, concentration, ctrl_sample)
                if cell_line_key not in raw_data_dict:
                    raw_data_dict[cell_line_key] = []
                raw_data_dict[cell_line_key].append(int(line[2]))

    # Tool_Box.debug_messenger(raw_data_dict)
    normalized_average_colonies = {}
    ctrl_normal_dict = {}
    survival_dict = {}
    # Normalize the colony counts by the control group
    for cell_line_key, colonies in raw_data_dict.items():
        colony_average = round(sum(colonies) / len(colonies), 2)
        cell_line_name = cell_line_key.split("|")[0]
        group_value = cell_line_key.split("|")[2]
        survival_key = "{}|{}".format(group_value,cell_line_name)

        if group_value == "0":
            ctrl_average = colony_average

        if cell_line_key not in ctrl_normal_dict:
            ctrl_normal_dict[cell_line_key] = []

        for colony in colonies:
            ctrl_normal_dict[cell_line_key].append(round((colony/ctrl_average)*100, 1))

        survival = ctrl_normal_dict[cell_line_key]
        normalized_colony_sem = round(scipy.stats.sem(ctrl_normal_dict[cell_line_key]), 2)
        normalized_colony_average = round(sum(ctrl_normal_dict[cell_line_key]) / len(ctrl_normal_dict[cell_line_key]), 1)

        # This is the data for plotting the survival curve
        normalized_average_colonies[cell_line_key].append((normalized_colony_average, float(normalized_colony_sem)))

        survival_dict[survival_key] = survival

    anova_dict = {}
    for survival_key, survival_values in survival_dict.items():

        group_value = survival_key.split("|")[0]
        cell_line_name = survival_key.split("|")[1]
        if group_value not in anova_dict:
            anova_dict[group_value] = [[],[],[]]

        for i in range(len(survival_values)):
            anova_dict[group_value][0].append(group_value)
            anova_dict[group_value][1].append(cell_line_name)
            anova_dict[group_value][2].append(survival_values[i])

    treatment_list = []
    cell_line_list = []
    survival_list = []
    for group_value, data in anova_dict.items():
        treatment_list.extend(data[0])
        cell_line_list.extend(data[1])
        survival_list.extend(data[2])

    df = pd.DataFrame({
        "Treatment":treatment_list,
        "Cell_Line":cell_line_list,
        "Survival":survival_list
    })

    # Tool_Box.debug_messenger(df)
    print("Number of Cell Lines in the Dataset", cell_line_count)
    print("Cell Line Names", cell_line_names)
    output_string = "Comparison\tp-Value\n"
    for i in range(cell_line_count-1):
        output_string = significance(df, cell_line_names[i:], output_string)
    print("Final Output String \n", output_string)
    """
    output_file = "C:{0}Users{0}dennis{0}Documents{0}Anova_output.csv".format(os.sep)
    with open(output_file, 'w') as f:
        f.write(output_string)
    """


if __name__ == '__main__':
    data_processing()
