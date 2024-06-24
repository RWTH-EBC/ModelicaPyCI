import argparse
import os
import platform
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from OMPython import OMCSessionZMQ
from ebcpy import DymolaAPI, TimeSeriesData
from ebcpy.utils.statistics_analyzer import StatisticsAnalyzer

from ModelicaPyCI.load_global_config import CI_CONFIG
from ModelicaPyCI.structure import config_structure
from ModelicaPyCI.structure import sort_mo_model as mo
from ModelicaPyCI.utils import logger


class StoreDictKeyPair(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._nargs = nargs
        super(StoreDictKeyPair, self).__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, pars, namespace, values, option_string=None):
        my_dict = {}
        for kv in values:
            k, v = kv.split(":")
            if v == "":
                v = os.getcwd()
            else:
                v = Path(os.getcwd(), v)
            my_dict[k] = v
        setattr(namespace, self.dest, my_dict)


class StoreDictKeyPair_list(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._nargs = nargs
        super(StoreDictKeyPair_list, self).__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, pars, namespace, values, option_string=None):
        my_dict = {}
        for kv in values:
            k, v = kv.split(":")
            my_dict[k] = v.split(",")
        setattr(namespace, self.dest, my_dict)


class StoreDictKey(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._nargs = nargs
        super(StoreDictKey, self).__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, pars, namespace, values, option_string=None):
        my_dict = {}
        if values is not None:
            for kv in values:
                k, v = kv.split(":")
                my_dict[k] = v.split(",")
            setattr(namespace, self.dest, my_dict)
        else:
            return None


class CheckOpenModelica:

    def __init__(self,
                 library: str,
                 library_package_mo: Path,
                 additional_libraries_to_load: dict = None,
                 working_path: Path = Path(Path.cwd())):
        """
        Args:
            working_path:
            additional_libraries_to_load ():
            library ():
            library_package_mo ():
        """
        self.library_package_mo = library_package_mo
        self.additional_libraries_to_load = additional_libraries_to_load
        self.working_path = working_path

        self.library = library
        # [start openModelica]
        logger.info(f'1: Starting OpenModelica instance')
        if platform.system() == "Windows":
            self.omc = OMCSessionZMQ()

        else:
            self.omc = OMCSessionZMQ(dockerOpenModelicaPath="/usr/bin/omc_orig")
        logger.info(f'OpenModelica Version number: {self.omc.sendExpression("getVersion()")}')
        # [start dymola api]
        self.dym_api = None

    def __call__(self):
        """

        """
        self.load_library(library_package_mo=self.library_package_mo,
                          library=self.library,
                          additional_libraries_to_load=self.additional_libraries_to_load)

    def simulate_models(self, model_list: list = None, exception_list: list = None):
        """
        Simulate examples or validations
        Args:
            model_list:
            exception_list:
        Returns:
        """

        all_sims_dir = CI_CONFIG.get_file_path("result", "OM_check_result_dir").joinpath("simulate",
                                                                                         f'{self.library}.{package}')
        API_log = Path(self.working_path, "DymolaAPI.log")
        config_structure.create_path(all_sims_dir)
        config_structure.delete_files_in_path(all_sims_dir)
        if model_list is not None:
            logger.info(f'Simulate examples and validations')
            error_model = {}
            for example in model_list:
                err_list = []
                logger.info(f'Simulate example {example}')
                result = self.omc.sendExpression(f"simulate({example})")
                if "The simulation finished successfully" in result["messages"]:
                    logger.info(f'\n Successful: {example}\n')
                    config_structure.prepare_data(source_target_dict={result["resultFile"]: all_sims_dir})
                else:
                    _err_msg = result["messages"]
                    _err_msg += "\n" + self.omc.sendExpression("getErrorString()")
                    for line in _err_msg.split("\n"):
                        exception_flag = False
                        if len(line) == 0:
                            continue
                        if exception_list is not None:
                            for exception in exception_list:
                                if exception in line:
                                    exception_flag = True
                            if exception_flag is False:
                                err_list.append(line)
                        else:
                            err_list.append(line)
                    if len(err_list) > 0:
                        logger.error(f'  Error:     {example}')
                        logger.error(f'{_err_msg}')
                    else:
                        logger.warning(f' Warning:     {example}')
                        logger.warning(f'{_err_msg}')
                    error_model[example] = _err_msg
                config_structure.delete_spec_file(root=os.getcwd(), pattern=example)
            config_structure.prepare_data(source_target_dict={
                API_log: CI_CONFIG.get_file_path("result", "OM_check_result_dir").joinpath(
                    f'{self.library}.{package}')},
                del_flag=True)
            return error_model
        else:
            logger.info(f'No examples to check. ')

    def check_models(self,
                     model_list: list = None,
                     exception_list: list = None):
        """
        Args:
            model_list ():
            exception_list ():
        Returns:
        """
        logger.info(f'Check models with OpenModelica')
        error_model = {}
        if model_list is not None:
            for m in model_list:
                err_list = []
                logger.info(f'Check model {m}')
                result = self.omc.sendExpression(f"checkModel({m})")
                if "completed successfully" in result:
                    logger.info(f' Successful:  {m}')
                else:
                    _err_msg = self.omc.sendExpression("getErrorString()")
                    for line in _err_msg.split("\n"):
                        exception_flag = False
                        if len(line) == 0:
                            continue
                        if exception_list is not None:
                            for exception in exception_list:
                                if exception in line:
                                    exception_flag = True
                            if exception_flag is False:
                                err_list.append(line)
                        else:
                            err_list.append(line)
                    if len(err_list) > 0:
                        logger.error(m)
                        logger.error(_err_msg)
                    else:
                        logger.warning(m)
                        logger.warning(_err_msg)
                    error_model[m] = _err_msg
            return error_model
        else:
            logger.info(f'No models to check')

    def close_OM(self):
        """

        """
        self.omc.sendExpression("quit()")

    def write_errorlog(self,
                       pack: str = None,
                       error_dict: dict = None,
                       exception_list: list = None,
                       options: str = None):
        """
        Write an error log with all models, that don´t pass the check
        Args:
            options:
            pack ():
            exception_list ():
            error_dict ():
        """
        if error_dict is not None:
            if pack is not None:
                ch_log = CI_CONFIG.get_file_path("result", "OM_check_result_dir").joinpath(
                    options, f'{self.library}.{pack}-check_log.txt')
                error_log = CI_CONFIG.get_file_path("result", "OM_check_result_dir").joinpath(
                    options, f'{self.library}.{pack}-error_log.txt')
                os.makedirs(Path(ch_log).parent, exist_ok=True)
                check_log = open(ch_log, "w")
                err_log = open(error_log, "w")
                for error_model in error_dict:
                    err_list = []
                    warning_list = []
                    for line in error_dict[error_model].split("\n"):
                        exception_flag = False
                        if len(line) == 0:
                            continue
                        if exception_list is not None:
                            for exception in exception_list:
                                if exception in line:
                                    exception_flag = True
                                    warning_list.append(line)
                            if exception_flag is False:
                                err_list.append(line)
                        else:
                            err_list.append(line)
                    if len(err_list) > 0:
                        check_log.write(f'\n\nError in model:  {error_model} \n')
                        err_log.write(f'\n\nError in model:  {error_model} \n')
                        for err in err_list:
                            check_log.write(err + "\n")
                            err_log.write(err + "\n")
                        if len(warning_list) > 0:
                            for warning in warning_list:
                                check_log.write(warning + "\n")
                        else:
                            for err in err_list:
                                check_log.write(err + "\n")
                                err_log.write(err + "\n")
                    else:
                        check_log.write(f'\n\nWarning in model:  {error_model} \n')
                        if len(warning_list) > 0:
                            for warning in warning_list:
                                check_log.write(warning + "\n")
                check_log.close()
                err_log.close()
                var = self._read_error_log(pack=pack, err_log=error_log, check_log=ch_log,
                                           options=options)
                if var != 0:
                    exit(var)
                return var
            else:
                logger.error(f'Package is not set.')
                exit(1)
        else:
            logger.info(f"Check was successful.")

    def _read_error_log(self, pack: str, err_log, check_log, options: str = None):
        """

        Args:
            pack:
            err_log:
            check_log:
            options:

        Returns:

        """
        error_log = open(err_log, "r")
        lines = error_log.readlines()
        error_log_list = []
        for line in lines:
            if "Error in model" in line:
                error_log_list.append(line)
                line = line.strip("\n")
                logger.error(line)
        if len(error_log_list) > 0:
            logger.error(f'Open Modelica for package {pack}check failed')
            var = 1
        else:
            logger.info(f'Open Modelica check was successful')
            var = 0
        error_log.close()
        config_structure.prepare_data(source_target_dict={
            check_log: CI_CONFIG.get_file_path("result", "OM_check_result_dir").joinpath(
                options, f'{self.library}.{pack}'
            ),
            err_log: CI_CONFIG.get_file_path("result", "OM_check_result_dir").joinpath(
                options, f'{self.library}.{pack}')},
            del_flag=True)
        return var

    def install_library(self, libraries: list = None):
        load_modelica = self.omc.sendExpression(f'installPackage(Modelica, "4.0.0+maint.om", exactMatch=true)')
        if load_modelica is True:
            logger.info(f'Load library modelica in Openmodelica.')
        else:
            logger.error(f'Load of modelica has failed.')
            exit(1)
        if libraries is not None:
            for inst in libraries:
                lib_name = inst[0]
                version = inst[1]
                exact_match = inst[2]
                install_string = f'{lib_name}, "{version}", {exact_match} '
                inst_lib = self.omc.sendExpression(f'installPackage({install_string})')
                if inst_lib is True:
                    logger.info(f'Install library "{lib_name}" with version "{version}" ')
                else:
                    logger.error(f'Error: Load of "{lib_name}" with version "{version}" failed!')
                    exit(1)
        logger.error(self.omc.sendExpression("getErrorString()"))

    def load_library(self, library_package_mo: Path = None, library: str = None,
                     additional_libraries_to_load: dict = None):
        if library_package_mo is not None:
            load_bib = self.omc.sendExpression(f'loadFile("{library_package_mo}")')
            if load_bib is True:
                logger.info(f'Load library {library}: {library_package_mo}')
            else:
                logger.error(f'Error: Load of {library_package_mo} failed!')
                exit(1)
        else:
            logger.info(f'Library path is not set.')
            exit(1)
        if additional_libraries_to_load is not None:
            for lib in additional_libraries_to_load:
                lib_path = Path(additional_libraries_to_load[lib], lib, "package.mo")
                load_add_bib = self.omc.sendExpression(f'loadFile("{lib_path}")')
                if load_add_bib is True:
                    logger.info(f'Load library {lib}: {lib_path}')
                else:
                    logger.error(f'Error: Load of library {lib} with path {lib_path} failed!')
                    exit(1)
        logger.error(self.omc.sendExpression("getErrorString()"))

    def sim_with_dymola(self, pack: str = None, example_list: list = None):
        all_sims_dir = CI_CONFIG.get_file_path("result", "OM_check_result_dir").joinpath(f'{self.library}.{pack}')
        if example_list is not None:
            if self.dym_api is None:
                lib_path = Path(self.library_package_mo, self.library, "package.mo")
                self.dym_api = DymolaAPI(
                    working_directory=os.getcwd(),
                    model_name=example_list[0],
                    packages=[lib_path],
                    extract_variables=True,
                    load_experiment_setup=True
                )

            for example in example_list:
                logger.info(f'Simulate model: {example}')
                try:
                    self.dym_api.model_name = example
                    logger.info("Setup", self.dym_api.sim_setup)
                    result = self.dym_api.simulate(return_option="savepath")
                except Exception as err:
                    logger.error("Simulation failed: " + str(err))
                    continue
                logger.info(f'\n Successful: {example}\n')
                config_structure.prepare_data(source_target_dict={result: Path(all_sims_dir, "dym")})
            self.dym_api.close()
            API_log = Path(self.library_package_mo, "DymolaAPI.log")
            config_structure.prepare_data(source_target_dict={
                API_log: CI_CONFIG.get_file_path("result", "OM_check_result_dir").joinpath(f'{self.library}.{pack}')},
                del_flag=True)
        else:
            logger.info(f'No examples to check. ')

    def compare_dym_to_om(self,
                          example_list: list = None,
                          stats: dict = None,
                          with_plot: bool = True,
                          pack: str = None):
        if example_list is not None:
            if stats is None:
                stats = {
                    "om": {
                        "failed": 0,
                        "success": 0,
                        "to_big_to_compare": 0
                    },
                    "dymola": {
                        "failed": 0,
                        "success": 0,
                        "to_big_to_compare": 0
                    }
                }
            errors = {}
            all_sims_dir = CI_CONFIG.get_file_path("result", "OM_check_result_dir").joinpath(f'{self.library}.{pack}')
            om_dir = all_sims_dir
            dym_dir = Path(all_sims_dir, "dym")
            plot_dir = Path(all_sims_dir, "plots", pack)
            _tol = 0.0001
            for example in example_list:
                continue_after_for = False
                for tool, _dir in zip(["om", "dymola"], [om_dir, dym_dir]):
                    path_mat = Path(_dir, f'{example}.mat')
                    if not os.path.exists(path_mat):
                        stats[tool]["failed"] += 1
                        continue_after_for = True
                        continue
                    if os.stat(path_mat).st_size / (1024 * 1024) > 400:
                        stats[tool]["to_big_to_compare"] += 1
                        continue_after_for = True
                    stats[tool]["success"] += 1
                if continue_after_for:
                    continue

                om_tsd = TimeSeriesData(Path(om_dir, f'{example}.mat'))
                dym_tsd = TimeSeriesData(Path(dym_dir, f'{example}.mat'))
                om_tsd_ref = om_tsd.copy()

                cols = {}
                for c in dym_tsd.columns:
                    cols[c] = c.replace(" ", "")
                dym_tsd = dym_tsd.rename(columns=cols)
                dym_tsd_ref = dym_tsd.copy()
                # Round index, sometimes it's 0.99999999995 instead of 1 e.g.
                om_tsd.index = np.round(om_tsd.index, 4)
                dym_tsd.index = np.round(dym_tsd.index, 4)
                # Drop duplicate rows, e.g. last point is often duplicate.
                om_tsd = om_tsd.drop_duplicates()
                dym_tsd = dym_tsd.drop_duplicates()
                idx_to_remove = []
                _n_diff_idx = 0
                for idx in om_tsd.index:
                    if idx not in dym_tsd.index:
                        idx_to_remove.append(idx)
                om_tsd = om_tsd.drop(idx_to_remove)
                _n_diff_idx += len(idx_to_remove)
                idx_to_remove = []
                for idx in dym_tsd.index:
                    if idx not in om_tsd.index:
                        idx_to_remove.append(idx)
                dym_tsd = dym_tsd.drop(idx_to_remove)
                _n_diff_idx += len(idx_to_remove)
                _col_err = {}
                _n_diff_cols = 0
                cols_to_plot = []
                for col in om_tsd.columns:
                    if col not in dym_tsd.columns:
                        _n_diff_cols += 1
                        continue
                    dym = dym_tsd.loc[:, col].values
                    om = om_tsd.loc[:, col].values
                    if np.std(om) + np.std(dym) <= 1e-5:
                        continue  # Stationary
                    cols_to_plot.append(col)
                    try:
                        _col_err[col] = StatisticsAnalyzer.calc_rmse(dym, om)
                    except ValueError as err:
                        logger.error(f"Index still differs {example}: {err}")
                        break
                for c in dym_tsd.columns:
                    if c not in _col_err:
                        _n_diff_cols += 1
                if with_plot:
                    _dir = Path(plot_dir, example)
                    if cols_to_plot:
                        os.makedirs(_dir, exist_ok=True)
                    for col in cols_to_plot:
                        plt.plot(om_tsd_ref.loc[:, col], label="OM")
                        plt.plot(dym_tsd_ref.loc[:, col], label="Dymola")
                        plt.legend()
                        plt.xlabel("Time in s")
                        plt.savefig(Path(_dir, f'{col}.png'))
                        plt.cla()

                errors[example] = {
                    "average": np.mean(list(_col_err.values())),
                    "detailed": _col_err,
                    "n_diff_events": _n_diff_idx,
                    "n_different_cols": _n_diff_cols
                }
            logger.info(f'Compare finished.')
            return errors, stats
        else:
            logger.info(f'No Models to compare.')


def parse_args():
    parser = argparse.ArgumentParser(description="Check and validate single packages")
    check_test_group = parser.add_argument_group("Arguments to run check tests")
    # [Library - settings]
    """check_test_group.add_argument("--library", dest="libraries", action=StoreDictKeyPair, nargs="*",
                                  metavar="Library1=Path_Lib1 Library2=Path_Lib2")
    check_test_group.add_argument("--package", dest="packages", action=StoreDictKeyPairList, nargs="*",
                                  metavar="Library1=Package1,Package2 Library2=Package3,Package4")"""
    check_test_group.add_argument("--library", default="AixLib", help="Library to test (e.g. AixLib")
    check_test_group.add_argument("--packages", default=["Airflow"], nargs="+",
                                  help="Library to test (e.g. Airflow.Multizone)")
    check_test_group.add_argument("--whitelist-library",
                                  default="IBPSA",
                                  help="Library on whitelist")
    # [ bool - flag]
    check_test_group.add_argument("--changed-flag",
                                  default=False,
                                  action="store_true")
    check_test_group.add_argument("--filter-whitelist-flag",
                                  default=False,
                                  action="store_true")
    # TODO: Requires ModelManagent, not supported on OpenModelica-Image
    # check_test_group.add_argument("--extended-examples",
    #                               default=False,
    #                               action="store_true")
    # [OM - Options: OM_CHECK, OM_SIM, DYMOLA_SIM, COMPARE]
    check_test_group.add_argument("--om-options",
                                  nargs="+",
                                  default=["OM_CHECK"],
                                  help="Chose between openmodelica check, compare or simulate")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    # [Settings]
    except_list = None
    additional_libraries_to_load = []
    # [Check arguments, files, path]
    LIBRARY_PACKAGE_MO = Path(CI_CONFIG.library_root).joinpath(args.library, "package.mo")

    config_structure.check_arguments_settings(library=args.library, packages=args.packages)
    config_structure.check_file_setting(LIBRARY_PACKAGE_MO=LIBRARY_PACKAGE_MO)
    if additional_libraries_to_load is not None:
        for lib in additional_libraries_to_load:
            add_lib_path = Path(additional_libraries_to_load[lib], lib, "package.mo")
            config_structure.check_file_setting(add_lib_path=add_lib_path)

    OM = CheckOpenModelica(library=args.library,
                           library_package_mo=LIBRARY_PACKAGE_MO,
                           additional_libraries_to_load=additional_libraries_to_load)
    OM()
    get_model_list_kwargs = dict(
        library=args.library,
        changed_flag=args.changed_flag,
        extended_examples_flag=False,
        filter_whitelist_flag=args.filter_whitelist_flag,
        library_package_mo=LIBRARY_PACKAGE_MO,
        tool="om"
    )
    for package in args.packages:
        for options in args.om_options:
            if options == "OM_CHECK":
                simulate_flag = False
                options = "check"
                func = OM.check_models
            else:
                simulate_flag = True
                options = "simulate"
                func = OM.simulate_models
            model_list = mo.get_model_list(
                package=package,
                simulate_flag=simulate_flag,
                **get_model_list_kwargs
            )
            error_model_dict = func(
                model_list=model_list,
                exception_list=except_list)
            exit_var = OM.write_errorlog(
                pack=package,
                error_dict=error_model_dict,
                exception_list=except_list,
                options=options)

            if options == "DYMOLA_SIM":
                model_list = mo.get_model_list(
                    package=package,
                    simulate_flag=True,
                    **get_model_list_kwargs
                )
                OM.sim_with_dymola(example_list=model_list, pack=package)
            if args.om_options == "COMPARE":
                ERROR_DATA = {}
                STATS = None
                model_list = mo.get_model_list(
                    package=package,
                    simulate_flag=True,
                    **get_model_list_kwargs
                )
                STATS = OM.compare_dym_to_om(pack=package,
                                             example_list=model_list,
                                             stats=STATS)

    OM.close_OM()
