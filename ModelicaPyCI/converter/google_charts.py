import argparse
import os
import shutil
from pathlib import Path

import pandas as pd
from mako.template import Template

from ModelicaPyCI.load_global_config import CI_CONFIG
from ModelicaPyCI.structure import config_structure
from ModelicaPyCI.utils import logger


class PlotCharts:

    def __init__(self, result_path, library):
        self.library = library
        self.f_log = result_path.joinpath("unitTests-dymola.log")
        self.csv_file = Path("reference.csv")
        self.test_csv = Path("test.csv")
        self.temp_chart_path = Path(CI_CONFIG.plots.chart_dir).joinpath(package)
        self.funnel_path = result_path.joinpath("funnel_comp")
        self.ref_path = Path(self.library).joinpath(CI_CONFIG.artifacts.library_ref_results_dir)
        self.index_html_file = self.temp_chart_path.joinpath("index.html")

    @staticmethod
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

    def write_html_plot_templates(self, reference_file_list):
        """
        Args:
            reference_file_list ():
        """
        new_ref_list = self._check_ref_file(reference_file_list=reference_file_list)
        for reference_file in new_ref_list:
            results = self._read_data(reference_file=reference_file)
            self._mako_line_html_new_chart(reference_file=reference_file,
                                           value_list=results[0],
                                           legend_list=results[1])

    def read_show_reference(self):
        """
        Returns:
        """
        if os.path.isfile(CI_CONFIG.interact.get_path(CI_CONFIG.interact.show_ref_file)) is False:
            logger.error(f'File {CI_CONFIG.interact.get_path(CI_CONFIG.interact.show_ref_file)} does not exist.')
            return []
        logger.info(f'Plot results from file {CI_CONFIG.interact.get_path(CI_CONFIG.interact.show_ref_file)}')
        with open(CI_CONFIG.interact.get_path(CI_CONFIG.interact.show_ref_file), "r") as file:
            lines = file.readlines()
        reference_file_list = list()
        for line in lines:
            if len(line) != 0:
                reference_file_list.append(f'{self.ref_path}{os.sep}{line.strip()}')
                continue
        if len(reference_file_list) == 0:
            logger.info(
                f'No reference files in file {CI_CONFIG.interact.get_path(CI_CONFIG.interact.show_ref_file)}. Please add here your reference files you want to '
                f'update')
        return []

    @staticmethod
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

    def get_updated_reference_files(self):
        """
        Returns:
        """
        if os.path.isfile(CI_CONFIG.interact.get_path(CI_CONFIG.interact.update_ref_file)) is False:
            logger.error(f'File {CI_CONFIG.interact.get_path(CI_CONFIG.interact.update_ref_file)} does not exist.')
            return []
        logger.info(f'Plot results from file {CI_CONFIG.interact.get_path(CI_CONFIG.interact.update_ref_file)}')
        with open(CI_CONFIG.interact.get_path(CI_CONFIG.interact.update_ref_file), "r") as file:
            lines = file.readlines()
        reference_list = list()
        for line in lines:
            line = line.strip()
            if line.find(".txt") > -1 and line.find("_"):
                reference_list.append(f'{self.ref_path}{os.sep}{line.strip()}')
                continue
        return reference_list

    def get_new_reference_files(self):
        """
        Returns:
        """
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

    @staticmethod
    def get_values(reference_list):
        """
        Args:
            reference_list ():
        Returns:
        """
        with open(f'{reference_list}', "r") as reference_file:
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

    @staticmethod
    def _get_time_int(time_list, measure_len):
        """
        Args:
            time_list ():
            measure_len ():
        Returns:
        """
        time_val = time_list.split(":")[1]
        time_beg = time_val.split(",")[0]
        time_end = time_val.split(",")[1]
        time_int = float(time_end) - float(time_beg)
        tim_seq = time_int / float(measure_len)
        time_num = float(time_beg)
        time_list = list()
        for time in range(0, measure_len + 1):
            time_list.append(time_num)
            time_num = time_num + tim_seq
        return time_list

    def read_unit_test_log(self):
        """
        Read unitTest_log from regressionTest, write variable and model name with difference
        Returns:
        """
        with open(self.f_log, "r") as log_file:
            lines = log_file.readlines()
        model_variable_list = list()
        for idx, line in enumerate(lines):
            error_indicator = "Errors during result verification"
            error_syntax = "*** Error: "
            if line.startswith(error_syntax) and error_indicator in line:
                # Convert e.g. "*** Error: BESMod_Examples_DesignOptimization_BESNoDHW.txt: Errors during result verification."
                # to BESMod_Examples_DesignOptimization_BESNoDHW
                model = line.replace(error_syntax, "").split(".txt")[0].strip()
                for next_line in lines[idx + 1:]:
                    if not next_line.strip().startswith("Absolute error"):
                        break
                    variable = next_line.strip().split(" ")[-1]
                    model_variable_list.append(f"{model}:{variable}")

            # if line.find("*** Warning:") > -1:
            #     if line.find(".mat") > -1:
            #         model = line[line.find("Warning:") + 9:line.find(".mat")]
            #         var = line[line.find(".mat:") + 5:line.find("exceeds ")].lstrip()
            #         model_variable_list.append(f'{model}:{var}')
            #     if line.find("*** Warning: Numerical Jacobian in 'RunScript") > -1 and line.find(".mos") > -1:
            #         model = line[line.rfind(os.sep) + 1:line.find(".mos")].lstrip()
            #         var = ""
            #         model_variable_list.append(f'{model}:{var}')
            #     if line.find(
            #             "*** Warning: Failed to interpret experiment annotation in 'RunScript") > -1 and line.find(
            #         ".mos") > -1:
            #         model = line[line.rfind(os.sep) + 1:line.find(".mos")].lstrip()
            #         var = ""
            #         model_variable_list.append(f'{model}:{var}')
        return model_variable_list

    def get_ref_file(self, model):
        """
        Args:
            model ():
        Returns:
        """
        for file in os.listdir(self.ref_path):
            if file.find(model) > -1:
                return file
            else:
                continue

    def _read_csv_funnel(self, url):
        """
        Read the differenz variables from csv_file and test_file
        Args:
            url ():

        Returns:

        """
        csv_file = Path(url.strip(), self.csv_file)
        test_csv = Path(url.strip(), self.test_csv)
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

    def mako_line_html_chart(self, model, var):
        """
        Load and read the templates, write variables in the templates
        Args:
            model ():
            var ():
        """
        if var == "":
            path_list = os.listdir((f'{self.library}{os.sep}funnel_comp'.strip()))
            for file in path_list:
                if file[:file.find(".mat")] == model:
                    path_name = f'{self.library}{os.sep}funnel_comp{os.sep}{file}'.strip()
                    var = file[file.find(".mat") + 5:]
                    if os.path.isdir(path_name) is False:
                        logger.error(
                            f'Cant find folder: {model} with variable {var}')
                    else:
                        logger.info(
                            f'Plot model: {model} with variable: {var}')
                        value = self._read_csv_funnel(url=path_name)
                        my_template = Template(filename=CI_CONFIG.plots.templates_chart_file)
                        html_chart = my_template.render(values=value,
                                                        var=[f'{var}_ref', var],
                                                        model=model,
                                                        title=f'{model}.mat_{var}')
                        with open(f'{self.temp_chart_path}{os.sep}{model}_{var.strip()}.html', "w") as file_tmp:
                            file_tmp.write(html_chart)
        else:
            path_name = (f'{self.library}{os.sep}funnel_comp{os.sep}{model}.mat_{var}'.strip())
            if os.path.isdir(path_name) is False:
                logger.error(
                    f'Cant find folder: {model} with variable {var}')
            else:
                logger.info(f'Plot model: {model} with variable: {var}')
                value = self._read_csv_funnel(url=path_name)
                my_template = Template(filename=CI_CONFIG.plots.templates_chart_file)
                html_chart = my_template.render(values=value,
                                                var=[f'{var}_ref', var],
                                                model=model,
                                                title=f'{model}.mat_{var}')
                with open(f'{self.temp_chart_path}{os.sep}{model}_{var.strip()}.html', "w") as file_tmp:
                    file_tmp.write(html_chart)

    def _mako_line_html_new_chart(self, reference_file, value_list, legend_list):
        """
        Load and read the templates, write variables in the templates
        Args:
            reference_file ():
            value_list ():
            legend_list ():
        """
        if os.path.isfile(reference_file) is False:
            logger.error(
                f'Cant find folder: {reference_file[reference_file.rfind(os.sep) + 1:]} with variables: {legend_list}')
        else:
            logger.info(
                f'Plot model: {reference_file[reference_file.rfind(os.sep) + 1:]} with variables:\n{legend_list}\n')
            my_template = Template(filename=CI_CONFIG.plots.templates_chart_file)
            html_chart = my_template.render(values=value_list,
                                            var=legend_list,
                                            model=reference_file,
                                            title=reference_file)
            with open(
                    f'{self.temp_chart_path}{os.sep}{reference_file[reference_file.rfind(os.sep):].replace(".txt", ".html")}',
                    "w") as file_tmp:
                file_tmp.write(html_chart)

    def mako_line_ref_chart(self, model, var):
        """
        Load and read the templates, write variables in the templates
        Args:
            model ():
            var ():
        """
        path_name = (f'{self.library}{os.sep}funnel_comp{os.sep}{model}.mat_{var}'.strip())
        folder_name = os.path.isdir(path_name)
        if folder_name is False:
            logger.error(f'Cant find folder: {model} with variable {var}')
        else:
            logger.info(f'Plot model: {model} with variable: {var}')
            value = self._read_csv_funnel(url=path_name)
            my_template = Template(filename=CI_CONFIG.plots.templates_chart_file)
            html_chart = my_template.render(values=value,
                                            var=[f'{var}_ref', var],
                                            model=model,
                                            title=f'{model}.mat_{var}')
            with open(f'{self.temp_chart_path}{os.sep}{model}_{var.strip()}.html', "w") as file_tmp:
                file_tmp.write(html_chart)

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

    def get_funnel_comp(self):
        return os.listdir(self.funnel_path)

    def delete_folder(self):
        if not os.path.isdir(CI_CONFIG.plots.chart_dir):
            logger.error(f'Directory {CI_CONFIG.plots.chart_dir} does not exist.')
        else:
            shutil.rmtree(CI_CONFIG.plots.chart_dir)


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
    unit_test_group.add_argument("--show-ref-flag",
                                 help='Plot only model on the interact ci list',
                                 default=False,
                                 action="store_true")
    unit_test_group.add_argument("--update-ref-flag",
                                 help='Plot only updated models',
                                 default=False,
                                 action="store_true")
    unit_test_group.add_argument("--show-package-flag",
                                 help='Plot only updated models',
                                 default=False,
                                 action="store_true")
    unit_test_group.add_argument("--ref-txt-flag",
                                 help="Take the datas from reference datas",
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
        charts.delete_folder()
        charts.check_folder_path()
        if args.error_flag is True:
            model_var_list = charts.read_unit_test_log()
            logger.info('Plot line chart with different reference results for %s models.',
                        len(model_var_list))
            for model_variable in model_var_list:
                model_variable = model_variable.split(":")
                if args.funnel_comp_flag is True:
                    charts.mako_line_html_chart(model=model_variable[0],
                                                var=model_variable[1])
                if args.ref_txt_flag is True:
                    ref_file = charts.get_ref_file(model=model_variable[0])
                    if ref_file is None:
                        logger.error(f'Reference file for model {model_variable[0]} does not exist.')
                        continue
                    else:
                        result = charts.get_values(reference_list=ref_file)
                        charts.mako_line_ref_chart(model=model_variable[0],
                                                   var=model_variable[1])
        if args.new_ref_flag is True:
            ref_list = charts.get_new_reference_files()
            charts.write_html_plot_templates(reference_file_list=ref_list)
        if args.update_ref_flag is True:
            ref_list = charts.get_updated_reference_files()
            charts.write_html_plot_templates(reference_file_list=ref_list)
        if args.show_ref_flag is True:
            ref_list = charts.read_show_reference()
            charts.write_html_plot_templates(reference_file_list=ref_list)
        if args.show_package_flag is True:
            folder = charts.get_funnel_comp()
            for ref in folder:
                if args.funnel_comp_flag is True:
                    charts.mako_line_html_chart(model=ref[:ref.find(".mat")],
                                                var=ref[ref.rfind(".mat") + 5:])
        charts.create_index_layout()
    create_central_index_html(
        chart_dir=Path(CI_CONFIG.plots.chart_dir),
        layout_html_file=Path(CI_CONFIG.plots.chart_dir).joinpath("index.html")
    )
