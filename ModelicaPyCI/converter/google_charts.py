import argparse
import os
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from ModelicaPyCI.load_global_config import CI_CONFIG
from ModelicaPyCI.structure import config_structure
from ModelicaPyCI.utils import logger
from ModelicaPyCI.structure.sort_mo_model import get_models
from mako.template import Template
from plotly.subplots import make_subplots


class PlotCharts:

    def __init__(self, result_path, library):
        self.library = library
        self.f_log = result_path.joinpath("unitTests-dymola.log")
        self.temp_chart_path = Path(CI_CONFIG.plots.chart_dir).joinpath(package)
        self.funnel_path = result_path.joinpath("funnel_comp")
        self.ref_path = Path(self.library).joinpath(CI_CONFIG.artifacts.library_ref_results_dir)
        self.index_html_file = self.temp_chart_path.joinpath("index.html")

    def plot_new_regression_results(self):
        reference_file_list = get_new_reference_files()
        new_ref_list = _check_ref_file(reference_file_list=reference_file_list)
        for reference_file in new_ref_list:
            df = load_txt_to_dataframe(file_path=reference_file)
            reference_file_name = Path(reference_file).stem
            fig = create_new_reference_plot(df=df, reference_file_name=reference_file_name)
            output_file = self.temp_chart_path.joinpath(f"{reference_file_name}.html")
            fig.write_html(output_file)
            logger.info(f"Plot saved under {output_file}")

    def check_folder_path(self):
        if os.path.isdir(self.funnel_path) is False:
            logger.error(f'Funnel directory does not exist.')
        else:
            logger.info(f'Search for reference result in {self.funnel_path}')
        if os.path.isdir(CI_CONFIG.plots.chart_dir) is False:
            os.mkdir(CI_CONFIG.plots.chart_dir)
        if os.path.isdir(self.temp_chart_path) is False:
            os.mkdir(self.temp_chart_path)
            logger.info(f'Save plot in {self.temp_chart_path}')

    def plot_regression_errors(self):
        model_var_list = read_unit_test_log(self.f_log, library=self.library)
        models = group_models_and_variables(model_var_list)

        logger.info('Plot line chart with different reference results for %s models.', len(models))
        for model, variables in models.items():
            fig = create_regression_error_plot(model, variables, funnel_path=self.funnel_path)
            if fig is None:
                continue
            # Save as interactive HTML in the 'plots' folder
            output_file = self.temp_chart_path.joinpath(f"{model.replace('.', '_')}.html")
            fig.write_html(output_file)
            logger.info(f"Plot saved under {output_file}")

    def create_index_layout(self):
        """
        Create an index layout from a template
        """
        html_file_list = list()
        for file in os.listdir(self.temp_chart_path):
            if file.endswith(".html") and file != "index.html":
                html_file_list.append(file)
        my_template = Template(filename=CI_CONFIG.plots.templates_index_file)
        if len(html_file_list) == 0:
            logger.info(f'No html files in chart path: %s', self.temp_chart_path)
            os.rmdir(self.temp_chart_path)
        else:
            html_chart = my_template.render(html_model=html_file_list)
            with open(self.index_html_file, "w") as file_tmp:
                file_tmp.write(html_chart)
            logger.info(f'Create html file with reference results.')


def get_new_reference_files():
    new_ref_file = CI_CONFIG.get_file_path("ci_files", "new_create_ref_file")
    if os.path.isfile(new_ref_file) is False:
        logger.error(f'File {new_ref_file} does not exist.')
        return []
    logger.info(f'Plot results from file {new_ref_file}')
    with open(new_ref_file, "r") as file:
        lines = file.read()
    logger.info("File contents: %s", lines)
    lines = lines.replace("\n", "").split(" ")
    reference_list = list()
    for line in lines:
        line = line.strip()
        if line.find(".txt") > -1 and line.find("_"):
            reference_list.append(line)
    logger.info("Plotting reference files: %s", reference_list)
    return reference_list


def read_unit_test_log(f_log, library: str):
    """
    Read unitTest_log from regressionTest, write variable and model name with difference
    Returns:
    """
    with open(f_log, "r") as log_file:
        lines = log_file.readlines()
    model_variable_list = list()
    all_models = get_models(
        path=Path().joinpath(library),
        library=library,
        simulate_flag=False
    )
    for idx, line in enumerate(lines):
        error_indicator = "Errors during result verification"
        error_syntax = "*** Error: "
        if line.startswith(error_syntax) and error_indicator in line:
            # Convert e.g. "*** Error: BESMod_Examples_DesignOptimization_BESNoDHW.txt: Errors during result verification."
            # to BESMod_Examples_DesignOptimization_BESNoDHW
            model = line.replace(error_syntax, "").split(".txt")[0].strip()
            model = get_model_name_based_on_underscores(name=model, model_names=all_models)
            for next_line in lines[idx + 1:]:
                if not next_line.strip().startswith("Absolute error"):
                    break
                variable = next_line.strip().split(" ")[-1]
                model_variable_list.append((model, variable))

    return model_variable_list


def get_model_name_based_on_underscores(name: str, model_names: list):
    parts = name.split("_")
    joined_model_name = ".".join(parts)
    if ".".join(parts) in model_names:
        return joined_model_name
    model_names_with_underscore = {model.replace("_", "."): model for model in model_names if "_" in model}
    if joined_model_name not in model_names_with_underscore:
        raise KeyError(f"Model {name} not found in all models")
    return model_names_with_underscore[joined_model_name]


def _check_ref_file(reference_file_list):
    """
    Args:
        reference_file_list ():
    Returns:
    """
    update_ref_list = list()
    for reference_file in reference_file_list:
        if os.path.isfile(reference_file) is False:
            logger.error(f'File {reference_file} does not exist.')
        else:
            update_ref_list.append(reference_file)
            logger.info(f'\nCreate plots for reference result {reference_file}')
    return update_ref_list


def delete_folder():
    if not os.path.isdir(CI_CONFIG.plots.chart_dir):
        logger.error(f'Directory {CI_CONFIG.plots.chart_dir} does not exist.')
    else:
        shutil.rmtree(CI_CONFIG.plots.chart_dir)


def get_values(reference_list):
    with open(reference_list, "r") as reference_file:
        lines = reference_file.readlines()
    measure_list = list()
    measure_len = int
    time_str = str
    for line in lines:  # searches for values and time intervals
        if line.find("last-generated=") > -1:
            continue
        if line.find("statistics-simulation=") > -1:
            continue
        if line.split("="):
            line = line.replace("[", "")
            line = line.replace("]", "")
            line = line.replace("'", "")
            values = (line.replace("\n", "").split("="))
            if len(values) < 2:
                continue
            else:
                legend = values[0]
                measures = values[1]
                if legend.find("time") > -1:
                    time_str = f'{legend}:{measures}'
                else:
                    measure_len = len(measures.split(","))
                    measure_list.append(f'{legend}:{measures}')
    return time_str, measure_list, measure_len


def _read_data(reference_file):
    """
    Read Reference results in AixLib\Resources\ReferenceResults\Dymola\…
    Args:
        reference_file ():
    Returns:
    """
    time_int = list()
    legend_list = list()
    value_list = list()
    distriction_values = {}
    time_interval_list = list()
    time_interval_steps = int
    with open(reference_file, 'r') as ref_file:
        lines = ref_file.readlines()
    for line in lines:
        current_value = list()
        if line.find("last-generated=") > -1 or line.find("statistics-simulation=") > -1 or line.find(
                "statistics-initialization=") > -1:
            continue
        elif line.find("time=") > -1:
            time_int = line.split("=")[1]
            time_int = time_int.split(",")
            continue
        if line.find("=") > -1:
            values = line.split("=")
            if len(values) < 2:
                continue
            legend = values[0]
            numbers = values[1]
            time_interval_steps = len(numbers.split(","))
            distriction_values[legend] = numbers
            legend_list.append(legend)
            number = numbers.split(",")
            for n in number:
                value = n.replace("[", "").lstrip()
                value = value.replace("]", "")
                value = float(value)
                current_value.append(value)
            value_list.append(current_value)
            continue
    first_time_interval = float((time_int[0].replace("[", "").lstrip()))
    last_time_interval = float((time_int[len(time_int) - 1].replace("]", "").lstrip()))
    time_interval = last_time_interval / time_interval_steps
    time = first_time_interval
    for step in range(1, time_interval_steps + 1, 1):
        if time == first_time_interval:
            time_interval_list.append(time)
            time = time + time_interval
        elif step == time_interval_steps:
            time = time + time_interval
            time_interval_list.append(time)
        else:
            time_interval_list.append(time)
            time = time + time_interval
    value_list.insert(0, time_interval_list)
    value_list = list(map(list, zip(*value_list)))
    return value_list, legend_list


def read_csv_funnel(path):
    """
    Read the different variables from csv_file and test_file
    """
    csv_file = "reference.csv"
    test_csv = "test.csv"
    csv_file = Path(path).joinpath(csv_file)
    test_csv = Path(path).joinpath(test_csv)
    try:
        var_model = pd.read_csv(csv_file)
        var_test = pd.read_csv(test_csv)
        temps = var_model[['x', 'y']]
        d = temps.values.tolist()
        test_tmp = var_test[['x', 'y']]
        e = test_tmp.values.tolist()
        e_list = list()
        for i in range(0, len(e)):
            e_list.append((e[i][1]))
        results = zip(d, e_list)
        result_set = list(results)
        value_list = list()
        for i in result_set:
            i = str(i)
            i = i.replace("(", "")
            i = i.replace("[", "")
            i = i.replace("]", "")
            i = i.replace(")", "")
            value_list.append("[" + i + "]")
        return value_list
    except pd.errors.EmptyDataError:
        logger.error(f'{csv_file} is empty')


def create_central_index_html(chart_dir: Path, layout_html_file: Path):
    """
    Creates a layout index that has all links to the subordinate index files.
    """
    package_list = list()
    for folders in os.listdir(chart_dir):
        if folders == "style.css" or folders == "index.html":
            continue
        else:
            package_list.append(folders)
    if len(package_list) == 0:
        logger.info("No html files, won't create central html file")
    else:
        logger.info("Found files %s, writing index.html", package_list)
        my_template = Template(filename=CI_CONFIG.plots.templates_layout_file)
        html_chart = my_template.render(packages=package_list)
        with open(layout_html_file, "w") as file_tmp:
            file_tmp.write(html_chart)
        config_structure.prepare_data(
            source_target_dict={
                chart_dir: CI_CONFIG.get_file_path("result", "plot_dir")
            }
        )


def create_regression_error_plot(model, variables, funnel_path: Path):
    # Determine the number of subplots
    n_subplots = len(variables)

    # Create subplots
    fig = make_subplots(rows=n_subplots, cols=1, shared_xaxes=True)  #, vertical_spacing=0.05)

    for i, variable in enumerate(variables, 1):
        folder = funnel_path.joinpath(f"{model}.mat_{variable}")
        if not os.path.exists(folder):
            logger.error(f'Cant find folder: {folder} for model {model} and variable {variable}')
            return None

        # Read reference and test data
        ref_df = pd.read_csv(folder.joinpath('reference.csv'))
        test_df = pd.read_csv(folder.joinpath('test.csv'))

        # Add traces for reference and test data
        fig.add_trace(
            go.Scatter(
                x=ref_df['x'],
                y=ref_df['y'],
                name=f'{variable} Reference',
                line=dict(color='blue'),
                mode='lines+markers',  # Add markers
                marker=dict(size=5),  # Set marker size
                showlegend=True,
                legendgroup=f"group{i}",
                legendgrouptitle_text=variable
            ),
            row=i, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=test_df['x'],
                y=test_df['y'],
                name=f'{variable} New',
                line=dict(color='red'),
                mode='lines+markers',  # Add markers
                marker=dict(size=5),  # Set marker size
                showlegend=True,
                legendgroup=f"group{i}"
            ),
            row=i, col=1
        )

        # Update y-axis title and show legend for each subplot
        fig.update_yaxes(title_text=variable, row=i, col=1)
        fig.update_xaxes(title_text="Time", row=i, col=1)
        fig.update_layout(showlegend=True)

    # Update layout
    fig.update_layout(
        height=300 * n_subplots,
        title_text=model,
    )

    return fig


def create_new_reference_plot(df: pd.DataFrame, reference_file_name: str):
    # Determine the number of subplots
    n_subplots = len(df.columns)

    # Create subplots
    fig = make_subplots(rows=n_subplots, cols=1, shared_xaxes=True)  #, vertical_spacing=0.05)

    for i, variable in enumerate(df.columns, 1):
        # Read reference and test data
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df.loc[:, variable],
                name=variable,
                line=dict(color='blue'),
                mode='lines+markers',  # Add markers
                marker=dict(size=5),  # Set marker size
                showlegend=True,
                legendgroup=f"group{i}",
                legendgrouptitle_text=variable
            ),
            row=i, col=1
        )

        # Update y-axis title and show legend for each subplot
        fig.update_yaxes(title_text=variable, row=i, col=1)
        fig.update_xaxes(title_text="Time", row=i, col=1)
        fig.update_layout(showlegend=True)

    # Update layout
    fig.update_layout(
        height=300 * n_subplots,
        title_text=reference_file_name,
    )

    return fig


def load_txt_to_dataframe(file_path):
    with open(file_path, 'r') as file:
        content = file.read()

    # Extract time and variable data
    pattern = r'(\w+(?:\.\w+)*(?:\[[^\]]+\])?)=\[(.*?)\]'
    matches = re.findall(pattern, content, re.DOTALL)

    max_lenghts = 0
    data = {}
    data_two_points = {}
    for variable, values in matches:
        values = [float(v) for v in values.split(',')]
        new_lenghts = len(values)
        if new_lenghts == 2:
            data_two_points[variable] = values
            continue
        if max_lenghts == 0:
            max_lenghts = new_lenghts
        elif max_lenghts != new_lenghts:
            raise ValueError("Reference results are not equally sampled")
        data[variable] = values
    # Create DataFrame
    if data:
        df = pd.DataFrame(data)
        for col, points in data_two_points.items():
            df.loc[:, col] = np.NAN
            df.loc[df.index[0], col] = points[0]
            df.loc[df.index[-1], col] = points[1]
    else:
        df = pd.DataFrame(data_two_points)  # Only two points in all results
    df = df.interpolate()
    df = df.set_index("time")
    logger.info("Found the following columns in .txt files with regex: %s", df.columns)
    return df


def group_models_and_variables(model_var_list):
    # Group folders by model
    models = {}
    for model, variable in model_var_list:
        if model not in models:
            models[model] = []
        models[model].append(variable)
    return models


def parse_args():
    parser = argparse.ArgumentParser(description='Plot diagramms')
    unit_test_group = parser.add_argument_group("arguments to plot diagrams")
    # [Library - settings]
    unit_test_group.add_argument("--packages",
                                 nargs="*",
                                 metavar="Modelica.Package",
                                 help="Test only the Modelica package Modelica.Package")
    unit_test_group.add_argument(
        "--library",
        help="Library to test"
    )
    unit_test_group.add_argument(
        "--templates-url",
        help="URL to MoCITempGen repository"
    )
    # [ bool - flag]
    unit_test_group.add_argument("--error-flag",
                                 default=True,
                                 help='Plot only model with errors',
                                 action="store_true")
    unit_test_group.add_argument("--funnel-comp-flag",
                                 default=True,
                                 help="Take the datas from funnel_comp",
                                 action="store_true")
    unit_test_group.add_argument("--line-matplot-flag",
                                 help='plot a matlab chart ',
                                 default=False,
                                 action="store_true")
    unit_test_group.add_argument("--new-ref-flag",
                                 help="Plot new models with new created reference files",
                                 default=False,
                                 action="store_true")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    from ModelicaPyCI.api_script.api_github import clone_repository

    clone_repository(
        clone_into_folder=CI_CONFIG.plots.templates_chart_file.split("/")[0],
        git_url=args.templates_url
    )

    config_structure.create_path(CI_CONFIG.plots.chart_dir)
    config_structure.check_path_setting(
        chart_dir=CI_CONFIG.plots.chart_dir,
        templates_chart_dir=CI_CONFIG.plots.templates_chart_dir
    )
    config_structure.check_file_setting(
        templates_chart_file=CI_CONFIG.plots.templates_chart_file,
        templates_index_file=CI_CONFIG.plots.templates_index_file,
        templates_layout_file=CI_CONFIG.plots.templates_layout_file,
    )
    for package in args.packages:
        result_path = Path(CI_CONFIG.get_file_path("result", "regression_dir"), package)
        if not os.path.isdir(result_path):
            logger.info("Package %s has no regression directory (%s), no plots to prepare.",
                        package, result_path)
            continue
        charts = PlotCharts(result_path=result_path,
                            library=args.library)
        delete_folder()
        charts.check_folder_path()
        if args.error_flag is True and args.funnel_comp_flag is True:
            charts.plot_regression_errors()
        if args.new_ref_flag is True:
            charts.plot_new_regression_results()
        charts.create_index_layout()
    create_central_index_html(
        chart_dir=Path(CI_CONFIG.plots.chart_dir),
        layout_html_file=Path(CI_CONFIG.plots.chart_dir).joinpath("index.html")
    )
