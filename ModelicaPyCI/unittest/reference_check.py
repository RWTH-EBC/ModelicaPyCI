import argparse
from pathlib import Path
import os
import buildingspy.development.validator as validate
import buildingspy.development.regressiontest as regression
from ModelicaPyCI.structure import sort_mo_model as mo
from ModelicaPyCI.structure import config_structure
from ModelicaPyCI.pydyminterface import python_dymola_interface
from ModelicaPyCI.config import ColorConfig
from ModelicaPyCI.load_global_config import CI_CONFIG
from ModelicaPyCI.utils import create_changed_files_file

COLORS = ColorConfig()


def write_exit_file(var):
    """
    write an exit file, use for gitlab ci.
    """
    try:
        with open(CI_CONFIG.get_file_path("ci_files", "exit_file"), "w") as ex_file:
            if var == 0:
                ex_file.write(f'successful')
            else:
                ex_file.write(f'FAIL')
    except IOError:
        print(f'Error: File {CI_CONFIG.get_file_path("ci_files", "exit_file")} does not exist.')


class BuildingspyRegressionCheck:

    def __init__(self, pack, n_pro, tool, batch, show_gui, path, library):
        """
        Args:
            pack (): package to be checked
            n_pro (): number of processors
            tool (): dymola or Openmodelica
            batch (): boolean: - False: interactive with script (e.g. generate new regression-tests) -
                True: No interactive with script
            show_gui (): show_gui (): True - show dymola, false - dymola hidden.
            path (): Path where top-level package.mo of the library is located.
        """
        self.package = pack
        self.n_pro = n_pro
        self.tool = tool
        self.batch = batch
        self.show_gui = show_gui
        self.path = path
        self.library = library
        libraries_to_load = python_dymola_interface.get_libraries_to_load_from_mos(STARTUP_MOS)
        if "MODELICAPATH" in os.environ:
            libraries_to_load.append(os.environ["MODELICAPATH"])
        os.environ["MODELICAPATH"] = ":".join(libraries_to_load)
        self.ut = regression.Tester(tool=self.tool)

    def check_regression_test(self, package_list):
        """
        start regression test for a package
        Args:
            package_list ():
        Returns:
        """
        self.ut.batchMode(self.batch)
        self.ut.setLibraryRoot(self.path)
        self.ut.setNumberOfThreads(self.n_pro)
        self.ut.pedanticModelica(False)
        self.ut.showGUI(self.show_gui)
        err_list = list()
        new_ref_list = list()
        # if "-y" in sys.argv:
        if package_list is not None and len(package_list) > 0:
            for package in package_list:
                if self.batch is False:
                    new_ref_list.append(package)
                    print(f'{COLORS.green}Generate new reference results for package: {COLORS.CEND} {package}')
                else:
                    print(f'{COLORS.green}Regression test for package:{COLORS.CEND} {package}')
                try:
                    self.ut.setSinglePackage(package)
                except ValueError as err:
                    print(f"{COLORS.CRED}Can't perform regression test for package '{package}', "
                          f"no valid scripts are available{COLORS.CEND}: {err}")
                    continue
                response = self.ut.run()
                config_structure.prepare_data(
                    source_target_dict={
                        f'simulator-dymola.log': Path(CI_CONFIG.get_file_path("result", "regression_dir"),
                                                      package),
                        "unitTests-dymola.log": Path(CI_CONFIG.get_file_path("result", "regression_dir"),
                                                     package),
                        "funnel_comp": Path(CI_CONFIG.get_file_path("result", "regression_dir"), package,
                                            "funnel_comp")})
                if response != 0:
                    err_list.append(package)
                    if self.batch is False:
                        print(f'{COLORS.CRED}Error in package: {COLORS.CEND} {package}')
                        continue
                    else:
                        print(f'{COLORS.CRED}Regression test for model {package} was not successfully{COLORS.CEND}')
                        continue
                else:
                    if self.batch is False:
                        print(f'{COLORS.green}New reference results in package: {COLORS.CEND} {package}\n')
                        continue
                    else:
                        print(f'{COLORS.green}Regression test for model {package} was successful {COLORS.CEND}')
                        continue
        if self.batch is True:
            if len(err_list) > 0:
                print(f'{COLORS.CRED}The following packages in regression test failed:{COLORS.CEND}')
                for error in err_list:
                    print(f'{COLORS.CRED}Error:{COLORS.CEND} {error}')
                return 1
            else:
                print(f'{COLORS.green}Regression test was successful {COLORS.CEND}')
                return 0
        else:
            if len(new_ref_list) > 0:
                return 1


class ReferenceModel:

    def __init__(self, library):
        """
        Args:
            library (): library to test
        """
        self.library = library

    def delete_ref_file(self, ref_list):
        """
        Delete reference files.
        Args:
            ref_list (): list of reference_result files
        """
        ref_dir = Path(CI_CONFIG.library_root, self.library, CI_CONFIG.artifacts.library_ref_results_dir)
        for ref in ref_list:
            print(f'Update reference file: {Path(ref_dir, ref)} \n')
            if os.path.exists(Path(ref_dir, ref)) is True:
                os.remove(Path(ref_dir, ref))
            else:
                print(f'File {Path(ref_dir, ref)} does not exist\n')

    def get_update_model(self):
        """

        Returns: return a package_list to check for regression test

        """
        # todo: Kennzeichnen, wenn reference vorhanden aber kein mos
        mos_script_list = self._get_mos_scripts()  # Mos Scripts
        reference_list = self._get_check_ref()  # Reference files
        mos_list = _compare_ref_mos(mos_script_list=mos_script_list,
                                    reference_list=reference_list)
        whitelist_list = _get_whitelist_package()
        model_list = _compare_whitelist_mos(package_list=mos_list,
                                            whitelist_list=whitelist_list)
        model_list = list(set(model_list))
        package_list = []
        for model in model_list:
            print(f'{COLORS.green}Generate new reference results for model: {COLORS.CEND} {model}')
            package_list.append(model[:model.rfind(".")])
        package_list = list(set(package_list))
        return package_list, model_list

    def _get_check_ref(self):
        """
        Give a reference list.
        Returns:
            ref_list(): return a list of reference_result files
        """
        ref_list = []
        for subdir, dirs, files in os.walk(CI_CONFIG.artifacts.library_ref_results_dir):
            for file in files:
                filepath = subdir + os.sep + file
                if filepath.endswith(".txt"):
                    ref_file = filepath[filepath.rfind(self.library):filepath.find(".txt")]
                    ref_list.append(ref_file)
        if len(ref_list) == 0:
            print(
                f'No reference files in file {CI_CONFIG.artifacts.library_ref_results_dir}. '
                f'Please add here your reference files you want to '
                f'update'
            )
        return ref_list

    def write_regression_list(self):
        """
        Writes a list for feasible regression tests.
        """
        mos_list = self._get_mos_scripts()
        try:
            with open(CI_CONFIG.get_file_path("ci_files", "dymola_reference_file"), "w") as whitelist_file:
                for mos in mos_list:
                    whitelist_file.write(f'\n{mos}\n')
        except IOError:
            print(f'Error: File {CI_CONFIG.get_file_path("ci_files", "dymola_reference_file")} does not exist.')

    def _get_mos_scripts(self):
        """
        Obtain mos scripts that are feasible for regression testing
        Returns:
            mos_list (): return a list with .mos script that are feasible for regression testing
        """
        mos_list = []
        for subdir, dirs, files in os.walk(CI_CONFIG.artifacts.library_resource_dir):
            for file in files:
                filepath = subdir + os.sep + file
                if filepath.endswith(".mos"):
                    with open(filepath, "r") as infile:
                        lines = infile.read()
                    if lines.find("simulateModel") > -1:
                        mos_script = filepath[filepath.find("Dymola"):filepath.find(".mos")].replace(
                            "Dymola", self.library
                        )
                        mos_script = mos_script.replace(os.sep, ".")
                        mos_list.append(mos_script)
                    if lines.find("simulateModel") == -1:
                        print(
                            f'{COLORS.CRED}This mos script is not suitable for regression testing:{COLORS.CEND} {filepath}')
        if len(mos_list) == 0:
            print(f'No feasible mos script for regression test in {CI_CONFIG.artifacts.library_resource_dir}.')
            return mos_list
        else:
            return mos_list


def _compare_whitelist_mos(package_list, whitelist_list):
    """
    Filter model from whitelist.
    Args:
        package_list ():
        whitelist_list ():
    Returns:
    """
    err_list = []
    for package in package_list:
        for whitelist_package in whitelist_list:
            if package[:package.rfind(".")].find(whitelist_package) > -1:
                print(
                    f'{COLORS.green}Don´t Create reference results for model{COLORS.CEND} {package} This package is '
                    f'on the whitelist')
                err_list.append(package)
            else:
                continue
    for err in err_list:
        package_list.remove(err)
    return package_list


def _get_whitelist_package():
    """
    Get and filter package from reference whitelist
    Returns: return files that are not on the reference whitelist
    """
    whitelist_list = []
    try:
        with open(CI_CONFIG.get_file_path("whitelist", "dymola_reference_file"), "r") as ref_wh:
            lines = ref_wh.readlines()
            for line in lines:
                if len(line.strip()) == 0:
                    continue
                else:
                    whitelist_list.append(line.strip())
        for whitelist_package in whitelist_list:
            print(
                f'{COLORS.CRED} Don´t create reference results for package{COLORS.CEND} {whitelist_package}: '
                f'This Package is '
                f'on the whitelist')
        return whitelist_list
    except IOError:
        print(f'Error: File {CI_CONFIG.get_file_path("whitelist", "dymola_reference_file")} does not exist.')
        return whitelist_list


def get_update_package(ref_list):
    """
    Args:
        ref_list (): list of reference files
    Returns:
    """
    ref_package_list = []
    for ref in ref_list:
        if ref.rfind("Validation") > -1:
            ref_package_list.append(ref[:ref.rfind("_Validation") + 11].replace("_", "."))
        elif ref.rfind("Examples") > -1:
            ref_package_list.append(ref[:ref.rfind("_Examples") + 9].replace("_", "."))
    ref_package_list = list(set(ref_package_list))
    return ref_package_list


def _compare_ref_mos(mos_script_list, reference_list):
    """
    compares if both files exists:  mos_script == reference results
    remove all mos script for that a ref file exists
    Args:
        mos_script_list ():
        reference_list ():
    Returns:
    """
    err_list = []
    for mos in mos_script_list:
        for ref in reference_list:
            if mos.replace(".", "_") == ref:
                err_list.append(mos)
                break
    for err in err_list:
        mos_script_list.remove(err)
    for package in mos_script_list:
        print(f'{COLORS.CRED}No Reference result for Model:{COLORS.CEND} {package}')
    return mos_script_list


def get_update_ref():
    """
    get a model to update
    Returns:
    """
    try:
        with open(f'..{os.sep}{CI_CONFIG.interact.get_path(CI_CONFIG.interact.update_ref_file)}', "r") as file:
            lines = file.readlines()
        update_ref_list = []
        for line in lines:
            if len(line) == 0:
                continue
            elif line.find(".txt") > -1:
                update_ref_list.append(line.strip())
        if len(update_ref_list) == 0:
            print(
                f'No reference files in file {CI_CONFIG.interact.get_path(CI_CONFIG.interact.update_ref_file)}. '
                f'Please add here your reference files you '
                f'want to update')
            exit(0)
        return update_ref_list
    except IOError:
        print(
            f'Error: File ..{os.sep}{CI_CONFIG.interact.get_path(CI_CONFIG.interact.update_ref_file)} does not exist.')
        exit(0)


class BuildingspyValidateTest:

    def __init__(self, validate, path):
        """

        Args:
            validate (): validate library from buildingspy
            path (): path to check
        """
        self.path = path
        self.validate = validate

    def validate_html(self):
        """
        validate the html syntax only
        """
        valid = self.validate.Validator()
        err_msg = valid.validateHTMLInPackage(self.path)
        n_msg = len(err_msg)
        for i in range(n_msg):
            if i == 0:
                print("The following malformed html syntax has been found:\n%s" % err_msg[i])
            else:
                print(err_msg[i])
        if n_msg == 0:
            return 0
        else:
            print(f'{COLORS.CRED}html check failed.{COLORS.CEND}')
            return 1

    def validate_experiment_setup(self):
        """
        validate regression test setup
        """
        valid = self.validate.Validator()
        ret_val = valid.validateExperimentSetup(self.path)
        return ret_val

    def run_coverage_only(self, batch, tool, package):
        """
        Specifies which models are tested
        Args:
            batch (): boolean: - False: interactive with script (e.g. generate new regression-tests) - True: No interactive with script
            tool (): dymola or Openmodelica
            package (): package to be checked
        """
        ut = CustomTester(tool=tool)
        ut.batchMode(batch)
        ut.setLibraryRoot(self.path)
        if package is not None:
            ut.setSinglePackage(package)
        coverage_result = ut.getCoverage()
        ut.printCoverage(*coverage_result, printer=print)


class CustomTester(regression.Tester):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._packages = []

    def getCoverage(self):
        """
        Analyse how many examples are tested.
        If ``setSinglePackage`` is called before this function,
        only packages set will be included. Else, the whole library
        will be checked.

        Returns:
            - The coverage rate in percent as float
            - The number of examples tested as int
            - The total number of examples as int
            - The list of models not tested as List[str]
            - The list of packages included in the analysis as List[str]
        """
        # first lines copy and paste from run function
        if self.get_number_of_tests() == 0:
            self.setDataDictionary(self._rootPackage)

        # Remove all data that do not require a simulation or an FMU export.
        # Otherwise, some processes may have no simulation to run and then
        # the json output file would have an invalid syntax

        # to not interact with other code here, we use the temp_data list

        temp_data = [
            element for element in self._data[:]
            if element['mustSimulate'] or element['mustExportFMU']
        ]

        # now we got clean _data to compare
        # next step get all examples in the package (whether whole library or
        # single package)
        if self._packages:
            packages = self._packages
        else:
            packages = list(dict.fromkeys(
                [pac['ScriptFile'].split(os.sep)[0] for pac in self._data])
            )

        all_examples = []
        for package in packages:
            package_path = os.path.join(self._libHome, package)
            for dirpath, dirnames, filenames in os.walk(package_path):
                for filename in filenames:
                    if any(
                            xs in filename for xs in ['Examples', 'Validation']
                    ) and not filename.endswith(('package.mo', '.order')):
                        all_examples.append(os.path.abspath(
                            os.path.join(dirpath, filename))
                        )

        coverage = round(len(temp_data) / len(all_examples), 2) * 100

        tested_model_names = [
            nam['ScriptFile'].split(os.sep)[-1][:-1] for nam in temp_data
        ]

        missing_examples = [
            i for i in all_examples if not any(
                xs in i for xs in tested_model_names)
        ]

        n_tested_examples = len(temp_data)
        n_examples = len(all_examples)
        return coverage, n_tested_examples, n_examples, missing_examples, packages

    def printCoverage(
            self,
            coverage: float,
            n_tested_examples: int,
            n_examples: int,
            missing_examples: list,
            packages: list,
            printer: callable = None
    ) -> None:
        """
        Print the output of getCoverage to inform about
        coverage rate and missing models.
        The default printer is the ``reporter.writeOutput``.
        If another printing method is required, e.g. ``print`` or
        ``logging.info``, it may be passed via the ``printer`` argument.
        """
        if printer is None:
            printer = self._reporter.writeOutput
        printer('***\n\nModel Coverage: ', str(int(coverage)) + '%')
        printer(
            '***\n\nYou are testing : ',
            n_tested_examples,
            ' out of ',
            n_examples,
            'total examples in '
        )
        for package in packages:
            printer(package)
        printer('\n')

        if missing_examples:
            print('***\n\nThe following examples are not tested\n')
            for i in missing_examples:
                print(i.split(self._libHome)[1])

    def setSinglePackage(self, packageName):
        """
        Set the name of one or multiple Modelica package(s) to be tested.

        :param packageName: The name of the package(s) to be tested.

        Calling this method will cause the regression tests to run
        only for the examples in the package ``packageName``, and in
        all its sub-packages.

        For example:

        * If ``packageName = IBPSA.Controls.Continuous.Examples``,
          then a test of the ``IBPSA`` library will run all examples in
          ``IBPSA.Controls.Continuous.Examples``.
        * If ``packageName = IBPSA.Controls.Continuous.Examples,IBPSA.Controls.Continuous.Validation``,
          then a test of the ``IBPSA`` library will run all examples in
          ``IBPSA.Controls.Continuous.Examples`` and in ``IBPSA.Controls.Continuous.Validation``.

        """

        # Create a list of packages, unless packageName is already a list
        packages = list()
        if ',' in packageName:
            # First, split packages in case they are of the form Building.{Examples, Fluid}
            expanded_packages = self.expand_packages(packageName)
            packages = expanded_packages.split(',')
        else:
            packages.append(packageName)
        packages = self._remove_duplicate_packages(packages)
        # Inform the user that not all tests are run, but don't add to warnings
        # as this would flag the test to have failed
        self._reporter.writeOutput(
            """Regression tests are only run for the following package{}:""".format(
                '' if len(packages) == 1 else 's'))
        for pac in packages:
            self._reporter.writeOutput("""  {}""".format(pac))
        # Remove the top-level package name as the unit test directory does not
        # contain the name of the library.

        # Set data dictionary as it may have been generated earlier for the whole library.
        self._data = []
        self._packages = []
        for pac in packages:
            pacSep = pac.find('.')
            pacPat = pac[pacSep + 1:]
            pacPat = pacPat.replace('.', os.sep)
            self._packages.append(pacPat)
            rooPat = os.path.join(self._libHome, 'Resources', 'Scripts', 'Dymola', pacPat)
            # Verify that the directory indeed exists
            if not os.path.isdir(rooPat):
                msg = """Requested to test only package '%s', but directory
        '%s' does not exist.""" % (pac, rooPat)
                raise ValueError(msg)
            self.setDataDictionary(rooPat)


def parse_args():
    parser = argparse.ArgumentParser(description='Run the unit tests or the html validation only.')
    unit_test_group = parser.add_argument_group("arguments to run unit tests")
    # [Library - settings]
    unit_test_group.add_argument(
        "--library",
        help="Library to test (e.g. AixLib")
    unit_test_group.add_argument(
        "--packages",
        nargs="+",
        help="Library to test (e.g. Airflow.Multizone)")
    unit_test_group.add_argument(
        "--library-root",
        help="Library to test (e.g. AixLib")

    unit_test_group.add_argument(
        "-p", "--path",
        default=".",
        help="Path where top-level package.mo of the library is located")
    # [Dymola - settings]
    unit_test_group.add_argument(
        "--show-gui",
        help='Show the GUI of the simulator',
        action="store_true",
        default=False)
    unit_test_group.add_argument(
        "-n",
        "--number-of-processors",
        type=int,
        default=4,
        help='Maximum number of processors to be used')
    unit_test_group.add_argument(
        '-t',
        "--tool",
        metavar="dymola", default="dymola",
        help="Tool for the regression tests. Set to dymola or jmodelica")
    unit_test_group.add_argument(
        "--dymola-version",
        default=None,
        help="Version of Dymola(Give the number e.g. 2022")
    unit_test_group.add_argument(
        "--startup-mos",
        default=None,
        help="Possible startup-mos script to e.g. load additional libraries"
    )
    # [ bool - flag]
    unit_test_group.add_argument(
        "-b", "--batch",
        action="store_true",
        default=False,
        help="Run in batch mode without user interaction")
    unit_test_group.add_argument(
        "--coverage-only",
        help='Only run the coverage test',
        default=False,
        action="store_true")
    unit_test_group.add_argument(
        "--create-ref",
        help='checks if all reference files exist',
        default=False,
        action="store_true")
    unit_test_group.add_argument(
        "--ref-list",
        help='checks if all reference files exist',
        default=False,
        action="store_true")
    unit_test_group.add_argument(
        "--update-ref",
        default=False,
        help='update all reference files',
        action="store_true")
    unit_test_group.add_argument(
        "--changed-flag",
        help='Regression test only for modified models',
        default=False,
        action="store_true")
    unit_test_group.add_argument(
        "--validate-html-only", default=False, action="store_true")
    unit_test_group.add_argument(
        "--validate-experiment-setup", default=False, action="store_true")
    unit_test_group.add_argument(
        "--report", default=False, action="store_true")
    return parser.parse_args()


if __name__ == '__main__':
    # todo: Package list bearbeiten.
    # todo: /bin/sh: 1: xdg-settings: not found
    # todo: Template für push hat changed:flag drin, ist falsch
    args = parse_args()
    CI_CONFIG.library_root = args.library_root
    LIBRARY_PACKAGE_MO = Path(CI_CONFIG.library_root).joinpath(args.library, "package.mo")
    STARTUP_MOS = Path(CI_CONFIG.library_root).joinpath(args.startup_mos)

    with open(STARTUP_MOS, "r") as file:
        print(file.read())

    for package in args.packages:
        if args.validate_html_only:
            var = BuildingspyValidateTest(validate=validate,
                                          path=args.path).validate_html()
            exit(var)
        elif args.validate_experiment_setup:  # Match the mos file parameters with the mo files only, and then exit
            var = BuildingspyValidateTest(validate=validate,
                                          path=args.path).validate_experiment_setup()
            exit(var)
        elif args.coverage_only:
            BuildingspyValidateTest(validate=validate,
                                    path=args.path).run_coverage_only(batch=args.batch,
                                                                      tool=args.tool,
                                                                      package=package)
        else:
            ref_model = ReferenceModel(library=args.library)
            package_list = []
            if args.ref_list:
                ref_model.write_regression_list()
                exit(0)
            ref_check = BuildingspyRegressionCheck(
                pack=args.packages,
                n_pro=args.number_of_processors,
                tool=args.tool,
                batch=args.batch,
                show_gui=args.show_gui,
                path=args.path,
                library=args.library,
                startup_mos=STARTUP_MOS
            )

            # todo: Liste?
            created_ref_list = list()
            if args.create_ref:
                package_list, created_ref_list = ref_model.get_update_model()
            elif args.update_ref:
                ref_list = get_update_ref()
                ref_model.delete_ref_file(ref_list=ref_list)
                package_list = get_update_package(ref_list=ref_list)
            else:
                config_structure.check_path_setting(ci_files=CI_CONFIG.get_dir_path("ci_files"), create_flag=True)
                config_structure.create_files(CI_CONFIG.get_file_path("ci_files", "exit_file"))
                if args.changed_flag is False:
                    package_list = args.packages
                if args.changed_flag is True:
                    changed_files_file = create_changed_files_file(repo_root=args.library_root)

                    dymola_api = python_dymola_interface.load_dymola_api(
                        packages=[LIBRARY_PACKAGE_MO],
                        requires_license=False,
                        startup_mos=STARTUP_MOS
                    )

                    package_list = mo.get_changed_regression_models(
                        dymola_api=dymola_api,
                        root_package=Path(package.replace(".", os.sep)),
                        library=args.library,
                        changed_files=changed_files_file,
                        package=package
                    )
            # Start regression test
            val = 0
            if package_list is None or len(package_list) == 0:
                if args.batch is False:
                    print(f'{COLORS.green}All Reference files exist.{COLORS.CEND}')
                    val = 0
                elif args.changed_flag is False:
                    print(f'{COLORS.CRED}Error:{COLORS.CEND} Package is missing! (e.g. Airflow)')
                    val = 1
                elif args.changed_flag is True:
                    print(f'No changed models in Package {args.packages}')
                    val = 0
            elif args.create_ref is True:
                print(f'Start regression Test.\nTest following packages: {package_list}')
                val = ref_check.check_regression_test(package_list=package_list)
                if len(created_ref_list) > 0:
                    for ref in created_ref_list:
                        config_structure.prepare_data(
                            source_target_dict={
                                f'{CI_CONFIG.artifacts.library_ref_results_dir}{os.sep}{ref.replace(".", "_")}.txt':
                                    CI_CONFIG.get_file_path("result", "regression_dir").joinpath("referencefiles")})
                write_exit_file(var=1)

            else:
                print(f'Start regression Test.\nTest following packages: {package_list}')
                val = ref_check.check_regression_test(package_list=package_list)
                write_exit_file(var=val)
            exit(val)
