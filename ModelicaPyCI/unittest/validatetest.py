import argparse
import glob
import os
from natsort import natsorted
from pathlib import Path

from ebcpy import DymolaAPI

from ModelicaPyCI.load_global_config import CI_CONFIG
from ModelicaPyCI.structure import sort_mo_model as mo
from ModelicaPyCI.structure import config_structure
from ModelicaPyCI.pydyminterface import python_dymola_interface
from ModelicaPyCI.utils import logger


class CheckPythonDymola:

    def __init__(self,
                 dymola_api: DymolaAPI,
                 library: str,
                 library_package_mo: Path,
                 ):
        """
        The class check or simulate models. Return an error-log. Can filter models from a whitelist
        Args:
            library_package_mo: root path of library (e.g. ../AixLib/package.mo)
            dymola_api (DymolaAPI): python_dymola_interface class.
            library (): library to test.
        """
        # [Libraries]
        self.library_package_mo = library_package_mo
        self.library = library
        # [Start Dymola]
        self.dymola_api = dymola_api
        self.dymola_log = Path(self.library_package_mo).parent.joinpath(f'{self.library}-log.txt')

    def check_dymola_model(self,
                           check_model_list: list = None,
                           exception_list: list = None,
                           sim_ex_flag: bool = False):
        """
        Check models and return an error log, if the check failed
        Args:
            sim_ex_flag (): list of examples
            exception_list ():  models not to check
            check_model_list (): list of models to be checked
        Returns:
            error_model_message_dic (): dictionary with models and its error message
        """
        error_model_message_dic = {}
        if len(check_model_list) == 0 or check_model_list is None:
            logger.error(f'Found no models.')
            exit(0)
        else:
            for dym_model in check_model_list:
                try:
                    res = self.dymola_api.dymola.checkModel(dym_model, simulate=sim_ex_flag)
                    if res is True:
                        logger.info(f'Successful:  {dym_model}')
                    if res is False:
                        # Second test for model
                        sec_result = self.dymola_api.dymola.checkModel(dym_model, simulate=sim_ex_flag)
                        if sec_result is True:
                            logger.info(f'Successful:  {dym_model}')
                        if sec_result is False:
                            log = self.dymola_api.dymola.getLastError()
                            err_list, warning_list = sort_warnings_from_log(log=log, exception_list=exception_list)
                            if len(err_list) > 0:
                                logger.error(f' {dym_model} \n{err_list}')
                            if len(warning_list) > 0:
                                logger.warning(f'Warning:  {dym_model} \n{warning_list}')
                            error_model_message_dic[dym_model] = log
                except Exception as ex:
                    logger.error("Simulation failed: " + str(ex))
                    continue
        self.dymola_api.dymola.savelog(f'{self.dymola_log}')
        self.dymola_api.close()
        return error_model_message_dic

    def write_error_log(self,
                        pack: str = None,
                        error_dict: dict = None,
                        exception_list: list = None):
        """
        Write an error log with all models, that don´t pass the check.
        Args:
            pack (): Package to check.
            exception_list (): Exceptions like certain warnings that are not recognized as errors.
            error_dict (): Dictionary of models with log message, that does not pass the check.
        """
        if error_dict is not None:
            if pack is not None:
                ch_log = Path(CI_CONFIG.get_file_path("result", "check_result_dir"),
                              f'{self.library}.{pack}-check_log.txt')
                error_log = Path(CI_CONFIG.get_file_path("result", "check_result_dir"),
                                 f'{self.library}.{pack}-error_log.txt')
                os.makedirs(Path(ch_log).parent, exist_ok=True)
                with open(ch_log, 'w') as check_log, open(error_log, "w") as err_log:
                    for error_model in error_dict:
                        err_list, warning_list = sort_warnings_from_log(log=error_dict[error_model],
                                                                        exception_list=exception_list)
                        if len(err_list) > 0:
                            check_log.write(f'\nError in model:  {error_model} \n')
                            err_log.write(f'\nError in model:  {error_model} \n')
                            for err in err_list:
                                check_log.write(str(err) + "\n")
                                err_log.write(str(err) + "\n")
                            if len(warning_list) > 0:
                                for warning in warning_list:
                                    check_log.write(str(warning) + "\n")
                        else:
                            if len(warning_list) > 0:
                                check_log.write(f'\n\nWarning in model:  {error_model} \n')
                                for warning in warning_list:
                                    check_log.write(str(warning) + "\n")
                return error_log, ch_log
        else:
            logger.info(f"Check was successful.")
            exit(0)

    def read_error_log(self, pack: str, err_log: Path, check_log):
        """
        Args:
            pack:Package to test
            err_log:
            check_log:
        Returns:
        """
        with open(err_log, "r") as error_log:
            lines = error_log.readlines()
            error_log_list = []
            for line in lines:
                if "Error in model" in line:
                    error_log_list.append(line)
                    line = line.strip("\n")
                    logger.error(f'{line}')

        config_structure.prepare_data(source_target_dict={
            check_log: Path(CI_CONFIG.get_file_path("result", "check_result_dir"), f'{self.library}.{pack}'),
            err_log: Path(CI_CONFIG.get_file_path("result", "check_result_dir"), f'{self.library}.{pack}')},
            del_flag=True)
        if len(error_log_list) > 0:
            logger.error(f'Dymola check failed')
            return 1
        else:
            logger.info(f'Dymola check was successful')
            return 0


class CreateWhitelist:

    def __init__(self,
                 library: str,
                 dymola_api: DymolaAPI,
                 library_package_mo: str
                 ):
        """
        The class creates a whitelist of faulty models based on library.
        Args:
            dymola_api (): python_dymola_interface class.
        """
        self.library = library
        self.library_package_mo = library_package_mo
        # [Start Dymola]
        self.dymola_api = dymola_api

    def check_whitelist_model(self, model_list: list, whitelist_files: Path, version: float, simulate_examples: bool):
        """
        Check library models for creating whitelist and create a whitelist with failed models.
        Write an error log with all models, that don´t pass the check.
        Args:
            model_list (): List of models that are being tested
            version (): version number of whitelist based on the latest Aixlib conversion script.
            whitelist_files (): Path to whitelist file
            simulate_examples() : bool simulate or not
        """
        error_model_message_dic = {}
        err_log = Path(Path(self.library_package_mo).parent, f'{self.library}-error_log.txt')
        dymola_log = Path(Path(self.library_package_mo).parent, f'{self.library}-log.txt')
        if model_list is None or len(model_list) == 0:
            logger.error(f'Found no models')
            exit(0)
        try:
            with open(whitelist_files, "w") as whitelist_file, open(err_log, "w") as error_log:
                logger.info(
                    f'Write new whitelist for {self.library} library\n'
                    f'New whitelist was created with the version {version}'
                )
                whitelist_file.write(f'\n{version} \n \n')
                for model in model_list:
                    result = self.dymola_api.dymola.checkModel(model, simulate=simulate_examples)
                    if result is True:
                        logger.info(f'Successful: {model}')
                    if result is False:
                        log = self.dymola_api.dymola.getLastError()
                        logger.error(f'\n{model}\n{log}')
                        error_model_message_dic[model] = log
                        whitelist_file.write(f'\n{model} \n \n')
                        error_log.write(f'\n \n Error in model:  {model} \n{log}')
                self.dymola_api.dymola.savelog(f'{dymola_log}')
                self.dymola_api.close()
            logger.info(f'Whitelist check finished.')
            config_structure.prepare_data(source_target_dict={
                err_log: Path(CI_CONFIG.get_file_path("result", "whitelist_dir")).joinpath(self.library),
                dymola_log: Path(CI_CONFIG.get_file_path("result", "whitelist_dir")).joinpath(self.library),
                whitelist_files: Path(CI_CONFIG.get_file_path("result", "whitelist_dir")).joinpath(
                    self.library)
            })
            return error_model_message_dic
        except IOError:
            logger.error(f'File {whitelist_files} or {err_log} does not exist.')
            exit(1)


def sort_warnings_from_log(log: str = None, exception_list: list = None):
    err_list, warning_list = [], []
    """result = ' '.join(map(str, log))
    exception_flag = False
    if exception_list is not None:
        for exception in exception_list:
            if exception in result:
                exception_flag = True
                warning_list.append(result)
        if exception_flag is False:
            err_list.append(result)
        else:
            err_list.append(result)"""
    if log is not None:
        for line in log:
            if isinstance(line, int) is True:
                continue
            exception_flag = False
            if exception_list is not None:
                for exception in exception_list:
                    if exception in line:
                        exception_flag = True
                        warning_list.append(line)
                if exception_flag is False:
                    err_list.append(line)
            else:
                err_list.append(line)
    return err_list, warning_list


def return_exit_var(package_results: dict):
    var = 0
    for package, opt_check_dict in package_results.items():
        for opt, value in opt_check_dict.items():
            if value != 0:
                logger.error(f'Check {opt} for package {package} failed.')
                var = 1
            else:
                logger.info(f'Check {opt} or package {package} was successful.')
    if var == 1:
        exit(var)


def write_exit_log(vers_check: bool):
    """
    Write entry in exit file. Necessary for CI templates.
    Args:
        vers_check (): Boolean that check if the version number is up-to-date.
    """
    try:
        with open(CI_CONFIG.get_file_path("ci_files", "exit_file"), "w") as exit_file:
            if vers_check is False:
                exit_file.write(f'FAIL')
            else:
                exit_file.write(f'successful')
    except IOError:
        logger.error(f'File {CI_CONFIG.get_file_path("ci_files", "exit_file")} does not exist.')
        exit(1)


def read_script_version(library_package_mo):
    """
    Returns:
        version (): return the latest version number of conversion script.
    """
    path = Path(Path.cwd(), Path(library_package_mo).parent, "Resources", "Scripts")
    filelist = (glob.glob(f'{path}{os.sep}*.mos'))
    if len(filelist) == 0:
        logger.error(f'Cannot find a Conversion Script in {Path(library_package_mo).parent} repository.')
        exit(0)
    else:
        last_conversion_script = natsorted(filelist)[(-1)]
        last_conversion_script = last_conversion_script.split(os.sep)
        vers = (last_conversion_script[len(last_conversion_script) - 1])
        logger.info(f'Latest {Path(library_package_mo).parent} version: {vers}')
        return vers


def create_whitelist(args, dymola_api, library_package_mo):
    config_structure.create_path(CI_CONFIG.get_dir_path("ci_files"), CI_CONFIG.get_dir_path("whitelist"))
    version = read_script_version(library_package_mo=library_package_mo)
    for options in args.dym_options:
        simulate_flag = options == "DYM_SIM"
        if options == "DYM_SIM":
            ci_file = CI_CONFIG.get_file_path("whitelist", "dymola_simulate_file")
        else:
            ci_file = CI_CONFIG.get_file_path("whitelist", "dymola_check_file")

        config_structure.create_files(ci_file, CI_CONFIG.get_file_path("ci_files", "exit_file"))

        wh = CreateWhitelist(
            dymola_api=dymola_api,
            library=args.library,
            library_package_mo=library_package_mo
        )

        model_list = mo.get_model_list(
            library=args.library,
            package=".",
            changed_flag=False,
            simulate_flag=simulate_flag,
            dymola_api=dymola_api,
            filter_whitelist_flag=False,
            extended_examples_flag=args.extended_examples,
            library_package_mo=library_package_mo
        )
        wh.check_whitelist_model(
            model_list=model_list,
            whitelist_files=ci_file,
            version=version,
            simulate_examples=simulate_flag
        )


def validate_only(args, dymola_api, library_package_mo):
    check_python_dymola = CheckPythonDymola(
        dymola_api=dymola_api,
        library=args.library,
        library_package_mo=library_package_mo
    )

    package_results = {}
    for package in args.packages:
        option_check_dictionary = {}
        for options in args.dym_options:
            simulate_flag = options == "DYM_SIM"
            model_list = mo.get_model_list(
                library=args.library,
                package=package,
                changed_flag=args.changed_flag,
                dymola_api=dymola_api,
                extended_examples_flag=args.extended_examples,
                simulate_flag=simulate_flag,
                filter_whitelist_flag=args.filter_whitelist_flag,
                library_package_mo=library_package_mo
            )

            error_model_dict = check_python_dymola.check_dymola_model(
                check_model_list=model_list,
                exception_list=None,
                sim_ex_flag=simulate_flag
            )
            error_log, ch_log = check_python_dymola.write_error_log(
                pack=package,
                error_dict=error_model_dict,
                exception_list=None
            )
            var = check_python_dymola.read_error_log(pack=package, err_log=error_log, check_log=ch_log)
            option_check_dictionary[options] = var
        package_results[package] = option_check_dictionary
    return_exit_var(package_results=package_results)


def parse_args():
    parser = argparse.ArgumentParser(description="Check and validate single packages")
    check_test_group = parser.add_argument_group("Arguments to run check tests")
    # [Library - settings]
    check_test_group.add_argument("--library",
                                  help="Library to test (e.g. AixLib")
    check_test_group.add_argument("--packages",
                                  nargs="+",
                                  help="Library to test (e.g. Airflow.Multizone)")
    check_test_group.add_argument(
        "--additional-libraries-to-load",
        default=[],
        nargs="*",
        help="Libraries to load aside from maim library"
    )

    # [Dymola - settings]
    check_test_group.add_argument("--dymola-version",
                                  default=None,
                                  help="Version of dymola (Give the number e.g. 2020")
    check_test_group.add_argument(
        "--startup-mos",
        default=None,
        help="Possible startup-mos script to e.g. load additional libraries"
    )
    # [ bool - flag]
    check_test_group.add_argument("--changed-flag", action="store_true")
    check_test_group.add_argument("--filter-whitelist-flag", default=False, action="store_true")
    check_test_group.add_argument(
        "--extended-examples",
        default=False,
        action="store_true"
    )
    check_test_group.add_argument(
        "--create-whitelist-flag",
        help="Create a whitelist of a library with failed models.",
        action="store_true"
    )
    # [dym - Options: DYM_CHECK, DYM_SIM]
    check_test_group.add_argument("--dym-options",
                                  nargs="+",
                                  help="Chose between openmodelica check, compare or simulate")
    return parser.parse_args()


if __name__ == '__main__':
    # Load Parser arguments
    ARGS = parse_args()
    # [Check arguments, files, path]
    LIBRARY_PACKAGE_MO = Path(CI_CONFIG.library_root).joinpath(ARGS.library, "package.mo")
    config_structure.check_arguments_settings(library=ARGS.library, packages=ARGS.packages)
    config_structure.check_file_setting(LIBRARY_PACKAGE_MO=LIBRARY_PACKAGE_MO)
    for lib in ARGS.additional_libraries_to_load:
        add_lib_path = Path(ARGS.additional_libraries_to_load[lib], lib, "package.mo")
        config_structure.check_file_setting(add_lib_path=add_lib_path)
    DYMOLA_API = python_dymola_interface.load_dymola_api(
        packages=[LIBRARY_PACKAGE_MO] + ARGS.additional_libraries_to_load, requires_license=True,
        startup_mos=ARGS.startup_mos)

    if ARGS.create_whitelist_flag is False:
        validate_only(
            args=ARGS,
            dymola_api=DYMOLA_API,
            library_package_mo=LIBRARY_PACKAGE_MO
        )
    if ARGS.create_whitelist_flag is True:
        create_whitelist(
            args=ARGS,
            dymola_api=DYMOLA_API,
            library_package_mo=LIBRARY_PACKAGE_MO
        )
