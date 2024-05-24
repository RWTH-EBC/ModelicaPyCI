import argparse
import glob
import os
import sys
import toml
from natsort import natsorted
from pathlib import Path
from ModelicaPyCI.config import CI_CONFIG
from ModelicaPyCI.structure.sort_mo_model import ModelicaModel
from ModelicaPyCI.structure import config_structure
from ModelicaPyCI.pydyminterface.python_dymola_interface import PythonDymolaInterface
from ModelicaPyCI.api_script.api_github import clone_repository


class CheckPythonDymola:

    def __init__(self,
                 dym,
                 dym_exp,
                 library: str,
                 root_library: Path,
                 working_path: Path = Path(Path.cwd()),
                 add_libraries_loc: dict = None,
                 inst_libraries: list = None):
        """
        The class check or simulate models. Return an error-log. Can filter models from a whitelist
        Args:
            root_library: root path of library (e.g. ../AixLib/package.mo)
            dymola_version: Version of used dymola (2023)
            working_path:
            add_libraries_loc:
            inst_libraries: installed libraries
            dym (): python_dymola_interface class.
            dym_exp (): python_dymola_exception class.
            library (): library to test.
        """
        # [Libraries]
        self.root_library = root_library
        self.add_libraries_loc = add_libraries_loc
        self.install_libraries = inst_libraries
        self.library = library
        self.working_path = working_path
        # [Start Dymola]
        self.dymola = dym
        self.dymola_exception = dym_exp
        if self.dymola is None:
            self.dymola.ExecuteCommand("Advanced.TranslationInCommandLog:=true;")
        self.dymola_log = Path(self.root_library).parent.joinpath(f'{self.library}-log.txt')

    def __call__(self):
        """
        1. Start dymola interface
        2. Check dymola license
        3. load library to check
        4. Install library to check
        """
        dym_int = PythonDymolaInterface(dymola=self.dymola,
                                        dymola_exception=self.dymola_exception)
        dym_int.dym_check_lic()
        dym_int.load_library(root_library=self.root_library, add_libraries_loc=self.add_libraries_loc)
        dym_int.install_library(libraries=self.install_libraries)

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
            print(f'{CI_CONFIG.color.CRED}Error:{CI_CONFIG.color.CEND} Found no models.')
            exit(0)
        else:
            for dym_model in check_model_list:
                try:
                    res = self.dymola.checkModel(dym_model, simulate=sim_ex_flag)
                    if res is True:
                        print(f'{CI_CONFIG.color.green}Successful: {CI_CONFIG.color.CEND} {dym_model}')
                    if res is False:
                        """print(
                            f'Check for Model {dym_model}{CI_CONFIG.color.CRED} failed!{CI_CONFIG.color.CEND}\n\n{CI_CONFIG.color.CRED}Error:{CI_CONFIG.color.CEND} '
                            f'{dym_model}\nSecond Check Test for model {dym_model}')"""
                        # Second test for model
                        sec_result = self.dymola.checkModel(dym_model, simulate=sim_ex_flag)
                        if sec_result is True:
                            print(f'{CI_CONFIG.color.green}Successful: {CI_CONFIG.color.CEND} {dym_model}')
                        if sec_result is False:
                            log = self.dymola.getLastError()
                            err_list, warning_list = self.sort_warnings_from_log(log=log, exception_list=exception_list)
                            if len(err_list) > 0:
                                print(f'{CI_CONFIG.color.CRED}Error: {CI_CONFIG.color.CEND} {dym_model} \n{err_list}')
                            if len(warning_list) > 0:
                                print(
                                    f'{CI_CONFIG.color.yellow} Warning: {CI_CONFIG.color.CEND} {dym_model} \n{warning_list}')
                            error_model_message_dic[dym_model] = log
                except self.dymola_exception as ex:
                    print("Simulation failed: " + str(ex))
                    continue
        self.dymola.savelog(f'{self.dymola_log}')
        self.dymola.close()
        return error_model_message_dic

    def sort_warnings_from_log(self, log: str = None, exception_list: list = None):
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

    def write_error_log(self,
                        pack: str = None,
                        error_dict: dict = None,
                        exception_list: list = None):
        """
        Write an error log with all models, that don´t pass the check.
        Args:
            pack (): Package to check.
            exception_list (): Exceptions like certain warnings that are not recognized as errors.
            error_dict (): Dicitonary of models with log message, that does not pass the check.
        """
        if error_dict is not None:
            if pack is not None:
                ch_log = Path(self.working_path, self.result_check_result_dir, f'{self.library}.{pack}-check_log.txt')
                error_log = Path(self.working_path, self.result_check_result_dir,
                                 f'{self.library}.{pack}-error_log.txt')
                os.makedirs(Path(ch_log).parent, exist_ok=True)
                with open(ch_log, 'w') as check_log, open(error_log, "w") as err_log:
                    for error_model in error_dict:
                        err_list, warning_list = self.sort_warnings_from_log(log=error_dict[error_model],
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
            print(f"{CI_CONFIG.color.green}Check was successful.{CI_CONFIG.color.CEND}")
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
                    print(f'{CI_CONFIG.color.CRED}{line}{CI_CONFIG.color.CEND}')

        config_structure.prepare_data(source_target_dict={
            check_log: Path(self.result_check_result_dir, f'{self.library}.{pack}'),
            err_log: Path(self.result_check_result_dir, f'{self.library}.{pack}')},
            del_flag=True)
        if len(error_log_list) > 0:
            print(f'{CI_CONFIG.color.CRED}Dymola check failed{CI_CONFIG.color.CEND}')
            return 1
        else:
            print(f'{CI_CONFIG.color.green}Dymola check was successful{CI_CONFIG.color.CEND}')
            return 0

    def return_exit_var(self, opt_check_dict, pack):
        var = 0
        for opt in opt_check_dict:
            if opt_check_dict[options] != 0:
                print(f'{CI_CONFIG.color.CRED}Check {opt} for package {pack} failed.{CI_CONFIG.color.CEND}')
                var = 1
            else:
                print(f'{CI_CONFIG.color.green}Check {opt} or package {pack} was successful.{CI_CONFIG.color.CEND}')
        if var == 1:
            exit(var)


class CreateWhitelist:

    def __init__(self,
                 dym,
                 dymola_ex,
                 whitelist_library: str,
                 working_path: Path = Path(Path.cwd()),
                 dymola_version: int = 2022,
                 add_libraries_loc: dict = None,
                 inst_libraries: list = None,
                 git_url: str = None,
                 root_whitelist_library: Path = None):
        """
        The class creates a whitelist of faulty models based on whitelist_library.
        Args:
            working_path:
            dymola_version:
            add_libraries_loc:
            inst_libraries:
            root_whitelist_library:
            dym (): python_dymola_interface class.
            dymola_ex (): python_dymola_exception class.
            library (): library to be tested.
            whitelist_library ():  Library and its models that can be on the whitelist.
            git_url (): Git url of the cloned project.
        """
        self.whitelist_library = whitelist_library
        self.git_url = git_url
        self.working_path = working_path
        self.root_library = root_whitelist_library
        # [libraries]
        self.add_libraries_loc = add_libraries_loc
        self.install_libraries = inst_libraries
        # [dymola version]
        self.dymola_version = dymola_version
        # [Start Dymola]
        self.dymola = dym
        self.dymola_exception = dymola_ex
        self.dymola.ExecuteCommand("Advanced.TranslationInCommandLog:=true;")

    def __call__(self):
        dym_int = PythonDymolaInterface(dymola=self.dymola, dymola_exception=self.dymola_exception)
        dym_int.dym_check_lic()
        dym_int.load_library(root_library=self.root_library, add_libraries_loc=self.add_libraries_loc)
        dym_int.install_library(libraries=self.install_libraries)

    @staticmethod
    def get_root_whitelist_library(whitelist_library, git_url, root_whitelist_library):
        """

        Args:
            whitelist_library (): Library on the whitelist
            git_url (): git url of the whitelist library
            root_whitelist_library (): root of the whitelist library
        Returns:
            root_whitelist_library: Return the full Path of root of the whitelist library
        """
        clone_repository(clone_into_folder=root_whitelist_library, git_url=git_url)
        return Path().joinpath(root_whitelist_library, whitelist_library, "package.mo")

    @staticmethod
    def write_exit_log(vers_check: bool):
        """
        Write entry in exit file. Necessary for CI templates.
        Args:
            vers_check (): Boolean that check if the version number is up-to-date.
        """
        try:
            with open(CI_CONFIG.config_ci.exit_file, "w") as exit_file:
                if vers_check is False:
                    exit_file.write(f'FAIL')
                else:
                    exit_file.write(f'successful')
        except IOError:
            print(f'Error: File {CI_CONFIG.config_ci.exit_file} does not exist.')
            exit(1)

    @staticmethod
    def read_script_version(root_library):
        """
        Returns:
            version (): return the latest version number of aixlib conversion script.
        """
        path = Path(Path.cwd(), Path(root_library).parent, "Resources", "Scripts")
        print(path)
        filelist = (glob.glob(f'{path}{os.sep}*.mos'))
        if len(filelist) == 0:
            print(f'Cannot find a Conversion Script in {Path(root_library).parent} repository.')
            exit(0)
        else:
            l_aixlib_conv = natsorted(filelist)[(-1)]
            l_aixlib_conv = l_aixlib_conv.split(os.sep)
            vers = (l_aixlib_conv[len(l_aixlib_conv) - 1])
            print(f'Latest {Path(root_library).parent} version: {vers}')
            return vers

    @staticmethod
    def check_whitelist_version(version, whitelist_file):
        """
        Check the latest whitelist version with the latest version of Aixlib conversion script.
        Read the last version of whitelist-
        Args:
            version (): Latest version number of aixlib conversion script.
        Returns:
            version_check (): Boolean - return true, if the whitelist version is equal to Aixlib conversion script version
            @param version:
            @param whitelist_file:
            @return:
        """
        try:
            version_file = open(whitelist_file, "r")
            lines = version_file.readlines()
            vers_check = False
            for line in lines:
                line = line.strip()
                if line.strip("\n") == version.strip("\n"):
                    print(f'Whitelist is on version {version}. The whitelist is already up to date')
                    vers_check = True
            version_file.close()
            return vers_check
        except IOError:
            print(f'Error: File {whitelist_file} does not exist.')
            exit(1)

    def check_whitelist_model(self, model_list: list, whitelist_files: Path, version: float, simulate_examples: bool):
        """
        Check whitelist_library models for creating whitelist and create a whitelist with failed models.
        Write an error log with all models, that don´t pass the check.
        Args:
            model_list (): List of models that are being tested
            version (): version number of whitelist based on the latest Aixlib conversion script.
            whitelist_files (): Path to whitelist file
            simulate_examples() : bool simulate or not
        """
        error_model_message_dic = {}
        err_log = Path(Path(self.root_library).parent, f'{self.whitelist_library}-error_log.txt')
        dymola_log = Path(Path(self.root_library).parent, f'{self.whitelist_library}-log.txt')
        if model_list is None or len(model_list) == 0:
            print(f'{CI_CONFIG.color.CRED}Error:{CI_CONFIG.color.CEND} Found no models')
            exit(0)
        try:
            with open(whitelist_files, "w") as whitelist_file, open(err_log, "w") as error_log:
                print(
                    f'Write new whitelist for {self.whitelist_library} library\nNew whitelist was created with the version {version}')
                whitelist_file.write(f'\n{version} \n \n')
                for model in model_list:
                    result = self.dymola.checkModel(model, simulate=simulate_examples)
                    if result is True:
                        print(f'{CI_CONFIG.color.green}Successful:{CI_CONFIG.color.CEND} {model}')
                    if result is False:
                        log = self.dymola.getLastError()
                        print(f'\n{CI_CONFIG.color.CRED}Error:{CI_CONFIG.color.CEND} {model}\n{log}')
                        error_model_message_dic[model] = log
                        whitelist_file.write(f'\n{model} \n \n')
                        error_log.write(f'\n \n Error in model:  {model} \n{log}')
                self.dymola.savelog(f'{dymola_log}')
                self.dymola.close()
            print(f'{CI_CONFIG.color.green}Whitelist check finished.{CI_CONFIG.color.CEND}')
            config_structure.prepare_data(source_target_dict={
                err_log: Path(self.result_whitelist_dir, f'{self.whitelist_library}'),
                dymola_log: Path(self.result_whitelist_dir, f'{self.whitelist_library}'),
                whitelist_files: Path(self.result_whitelist_dir, f'{self.whitelist_library}')})
            return error_model_message_dic
        except IOError:
            print(f'Error: File {whitelist_files} or {err_log} does not exist.')
            exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Check and validate single packages")
    check_test_group = parser.add_argument_group("Arguments to run check tests")
    # [Library - settings]
    check_test_group.add_argument("--library",
                                  help="Library to test (e.g. AixLib")
    check_test_group.add_argument("--packages",
                                  nargs="+",
                                  help="Library to test (e.g. Airflow.Multizone)")
    check_test_group.add_argument("--root-library",
                                  help="root of library",
                                  type=Path)

    # [Dymola - settings]
    check_test_group.add_argument("--dymola-version",
                                  default="2022",
                                  help="Version of dymola (Give the number e.g. 2020")
    # [ bool - flag]
    check_test_group.add_argument("--changed-flag", default=False, action="store_true")
    check_test_group.add_argument("--filter-whitelist-flag", default=False, action="store_true")
    check_test_group.add_argument("--extended-ex-flag", default=False, action="store_true")
    check_test_group.add_argument("--create-whitelist-flag", help="Create a whitelist of a library with failed models.",
                                  action="store_true")
    # [dym - Options: DYM_CHECK, DYM_SIM]
    check_test_group.add_argument("--dym-options",
                                  nargs="+",
                                  help="Chose between openmodelica check, compare or simulate")
    # [repository - setting ]
    check_test_group.add_argument("--git-url", default="https://github.com/ibpsa/modelica-ibpsa.git",
                                  help="url repository of whitelist library")
    check_test_group.add_argument("--whitelist-library",
                                  default="IBPSA",
                                  help="library on a whitelist")
    check_test_group.add_argument("--root-whitelist-library",
                                  help="library on a whitelist")

    return parser.parse_args()


if __name__ == '__main__':
    # Load Parser arguments
    args = parse_args()
    install_libraries = None
    except_list = None
    additional_libraries_local = None
    # [Check arguments, files, path]
    check = config_structure
    config_structure.check_arguments_settings(args.library, args.packages)
    config_structure.check_file_setting(args.root_library)
    if additional_libraries_local is not None:
        for lib in additional_libraries_local:
            add_lib_path = Path(additional_libraries_local[lib], lib, "package.mo")
            config_structure.check_file_setting(add_lib_path)
    dymola, dymola_exception = PythonDymolaInterface.load_dymola_python_interface(dymola_version=args.dymola_version)
    if args.create_whitelist_flag is False:
        dym = CheckPythonDymola(dym=dymola,
                                dym_exp=dymola_exception,
                                library=args.library,
                                root_library=args.root_library,
                                add_libraries_loc=additional_libraries_local,
                                inst_libraries=install_libraries)
        dym()
        mm = ModelicaModel()
        option_check_dictionary = {}
        for package in args.packages:
            for options in args.dym_options:
                if options == "DYM_CHECK":
                    # todo: Funktionen Zusammenfassen
                    model_list = mm.get_option_model(library=args.library,
                                                     package=package,
                                                     whitelist_library=args.whitelist_library,
                                                     changed_flag=args.changed_flag,
                                                     simulate_flag=False,
                                                     filter_whitelist_flag=args.filter_whitelist_flag,
                                                     root_library=args.root_library)

                    error_model_dict = dym.check_dymola_model(check_model_list=model_list,
                                                              exception_list=except_list,
                                                              sim_ex_flag=False)
                    error_log, ch_log = dym.write_error_log(pack=package,
                                                            error_dict=error_model_dict,
                                                            exception_list=except_list)
                    var = dym.read_error_log(pack=package, err_log=error_log, check_log=ch_log)
                    option_check_dictionary[options] = var

                if options == "DYM_SIM":
                    model_list = mm.get_option_model(library=args.library,
                                                     package=package,
                                                     whitelist_library=args.whitelist_library,
                                                     changed_flag=args.changed_flag,
                                                     simulate_flag=True,
                                                     filter_whitelist_flag=args.filter_whitelist_flag,
                                                     root_library=args.root_library)
                    error_model_dict = dym.check_dymola_model(check_model_list=model_list,
                                                              exception_list=except_list,
                                                              sim_ex_flag=True)
                    error_log, ch_log = dym.write_error_log(pack=package,
                                                            error_dict=error_model_dict,
                                                            exception_list=except_list)
                    var = dym.read_error_log(pack=package, err_log=error_log, check_log=ch_log)
                    option_check_dictionary[options] = var
            dym.return_exit_var(opt_check_dict=option_check_dictionary, pack=package)
    if args.create_whitelist_flag is True:
        config_structure.check_arguments_settings(args.whitelist_library)
        mo = ModelicaModel()
        config_structure.create_path(CI_CONFIG.config_ci.dir, CI_CONFIG.whitelist.ci_dir)

        version = CreateWhitelist.read_script_version(root_library=args.root_library)
        for options in args.dym_options:
            if options == "DYM_CHECK":
                config_structure.create_files(CI_CONFIG.whitelist.check_file, CI_CONFIG.config_ci.exit_file)
                version_check = CreateWhitelist.check_whitelist_version(
                    version=version,
                    whitelist_file=CI_CONFIG.whitelist.check_file
                )
                if version_check is False:
                    root_whitelist_library = CreateWhitelist.get_root_whitelist_library(
                        whitelist_library=args.whitelist_library,
                        git_url=args.git_url,
                        root_whitelist_library=args.root_whitelist_library)

                    config_structure.check_file_setting(root_whitelist_library)
                    wh = CreateWhitelist(dym=dymola,
                                         dymola_ex=dymola_exception,
                                         whitelist_library=args.whitelist_library,
                                         git_url=args.git_url,
                                         dymola_version=args.dymola_version,
                                         add_libraries_loc=additional_libraries_local,
                                         root_whitelist_library=root_whitelist_library)
                    wh()
                    model_list = mo.get_option_model(library=args.whitelist_library,
                                                     package=".",
                                                     whitelist_library=args.whitelist_library,
                                                     changed_flag=False,
                                                     simulate_flag=False,
                                                     filter_whitelist_flag=False,
                                                     extended_ex_flag=False,
                                                     root_library=root_whitelist_library)
                    wh.check_whitelist_model(model_list=model_list,
                                             whitelist_files=CI_CONFIG.whitelist.check_file,
                                             version=version,
                                             simulate_examples=False)
                CreateWhitelist.write_exit_log(vers_check=version_check)
            if options == "DYM_SIM":
                config_structure.create_files(CI_CONFIG.whitelist.simulate_file, CI_CONFIG.model_config.exit_file)
                version_check = CreateWhitelist.check_whitelist_version(
                    version=version,
                    whitelist_file=CI_CONFIG.whitelist.simulate_file)
                if version_check is False:
                    root_whitelist_library = CreateWhitelist.get_root_whitelist_library(
                        whitelist_library=args.whitelist_library,
                        git_url=args.git_url,
                        root_whitelist_library=args.root_whitelist_library
                    )
                    config_structure.check_file_setting(root_whitelist_library)
                    wh = CreateWhitelist(dym=dymola,
                                         dymola_ex=dymola_exception,
                                         whitelist_library=args.whitelist_library,
                                         git_url=args.git_url,
                                         dymola_version=args.dymola_version,
                                         add_libraries_loc=additional_libraries_local,
                                         root_whitelist_library=root_whitelist_library)
                    wh()
                    model_list = mo.get_option_model(library=args.whitelist_library,
                                                     package=".",
                                                     whitelist_library=args.whitelist_library,
                                                     changed_flag=False,
                                                     simulate_flag=True,
                                                     filter_whitelist_flag=False,
                                                     extended_ex_flag=False,
                                                     root_library=root_whitelist_library)
                    wh.check_whitelist_model(model_list=model_list,
                                             whitelist_files=CI_CONFIG.whitelist.simulate_file,
                                             version=version,
                                             simulate_examples=True)
                CreateWhitelist.write_exit_log(vers_check=version_check)  # todo: Brauch ich die Datei noch?
