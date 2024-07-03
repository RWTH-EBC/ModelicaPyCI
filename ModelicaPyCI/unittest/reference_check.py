import argparse
from pathlib import Path
import os
import yaml

import buildingspy.development.validator as validate
import buildingspy.development.regressiontest as regression
from ModelicaPyCI.structure import sort_mo_model as mo
from ModelicaPyCI.structure import config_structure
from ModelicaPyCI.pydyminterface import python_dymola_interface
from ModelicaPyCI.load_global_config import CI_CONFIG
from ModelicaPyCI.utils import create_changed_files_file, logger


def write_exit_file(message: str = None):
    """
    write an exit file, use for gitlab ci.
    """
    exit_file_path = CI_CONFIG.get_file_path("ci_files", "exit_file").absolute()
    os.makedirs(exit_file_path.parent, exist_ok=True)
    with open(exit_file_path, "a") as ex_file:
        ex_file.write(message)
        logger.info(f"Wrote content {message} {exit_file_path}.")
    with open(exit_file_path, "r") as ex_file:
        logger.info(f"Exit file contents: {ex_file.read()}")


class BuildingspyRegressionCheck:

    def __init__(self, n_pro, tool, batch, show_gui, path, library, startup_mos: str = None):
        """
        Args:
            n_pro (): number of processors
            tool (): dymola or Openmodelica
            batch (): boolean: - False: interactive with script (e.g. generate new regression-tests) -
                True: No interactive with script
            show_gui (): show_gui (): True - show dymola, false - dymola hidden.
            path (): Path where top-level package.mo of the library is located.
            startup_mos (): Path to possible startup mos
        """
        self.n_pro = n_pro
        self.tool = tool
        self.batch = batch
        self.show_gui = show_gui
        self.path = path
        self.library = library
        if startup_mos is not None:
            libraries_to_load = python_dymola_interface.add_libraries_to_load_from_mos_to_modelicapath(startup_mos)

        self.ut = WhitelistTester(tool=self.tool)

    def check_regression_test(self, package_list, create_results: bool):
        """
        start regression test for a package
        Args:
            package_list ():
        Returns:
        """
        if create_results:
            self.ut.batchMode(self.batch, createNewReferenceResultsInBatchMode=create_results)
        else:
            self.ut.batchMode(self.batch)

        self.ut.setLibraryRoot(self.path)
        self.ut.setNumberOfThreads(self.n_pro)
        self.ut.pedanticModelica(False)
        self.ut.showGUI(self.show_gui)

        err_list = list()
        new_ref_list = list()
        for package_modelica_name in package_list:
            sinlge_package_name = package_modelica_name.split(".")[-1]
            if create_results:
                new_ref_list.append(package_modelica_name)
                logger.info(f'Generate new reference results for package:  {package_modelica_name}')
            else:
                logger.info(f'Regression test for package: {package_modelica_name}')
            try:
                self.ut.setSinglePackage(package_modelica_name)
            except ValueError as err:
                logger.error(f"Can't perform regression test for package '{package_modelica_name}', "
                             f"no valid scripts are available: {err}")
                continue

            # Add whitelist
            from ModelicaPyCI.structure.sort_mo_model import get_whitelist_models
            ci_whitelist_ibpsa_file = CI_CONFIG.get_file_path("whitelist", "ibpsa_file")
            if os.path.exists(ci_whitelist_ibpsa_file):
                self.ut.whitelist_models = get_whitelist_models(
                    whitelist_file=ci_whitelist_ibpsa_file,
                    library=self.library,
                    single_package=sinlge_package_name
                )

            response = self.ut.run()

            result_path = Path(CI_CONFIG.get_file_path("result", "regression_dir"), sinlge_package_name)
            source_target_dict = {}
            for file in self.ut.get_unit_test_log_files():
                source_target_dict[file] = result_path
            source_target_dict["funnel_comp"] = result_path.joinpath("funnel_comp")
            config_structure.prepare_data(source_target_dict=source_target_dict, del_flag=True)

            if response != 0:
                err_list.append(package_modelica_name)
                if self.batch is False:
                    logger.error(f'Error in package:  {package_modelica_name}')
                    continue
                else:
                    logger.error(f'Regression test for model {package_modelica_name} was not successfully')
                    continue
            else:
                if self.batch is False:
                    logger.info(f'New reference results in package:  {package_modelica_name}\n')
                    continue
                else:
                    logger.info(f'Regression test for model {package_modelica_name} was successful ')
                    continue
        if len(err_list) > 0:
            logger.error(f'The following packages in regression test failed:')
            for error in err_list:
                logger.error(f'{error}')
            return 1
        elif len(new_ref_list) > 0:
            return 1
        else:
            logger.info(f'Regression test was successful ')
            return 0

class WhitelistTester(regression.Tester):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.whitelist_models = []

    def _write_runscripts(self):
        skipped_ref = 0
        nUniTes = 0

        # Build array of models that need to be translated, simulated, or exported as an FMU
        tra_data = []
        if self._modelica_tool == 'dymola':
            for dat in self._data:
                if self._isPresentAndTrue('translate', dat[self._modelica_tool]) or self._isPresentAndTrue(
                        'exportFMU', dat[self._modelica_tool]):
                    if dat['model_name'] not in self.whitelist_models:
                        tra_data.append(dat)
                    else:
                        skipped_ref += 1
        elif self._modelica_tool != 'dymola':
            for dat in self._data:
                if self._isPresentAndTrue('translate', dat[self._modelica_tool]):
                    tra_data.append(dat)
        else:
            raise RuntimeError("Tool is not supported.")
        logger.info("Added %s models to whitelist config already tested in IBPSA.", skipped_ref)

        # Count how many tests need to be translated.
        nTes = len(tra_data)
        # Reduced the number of processors if there are fewer examples than processors
        if nTes < self._nPro:
            self.setNumberOfThreads(nTes)

        # Print number of processors
        import multiprocessing
        print(
            f"Using {self._nPro} of {multiprocessing.cpu_count()} processors to run unit tests for {self._modelica_tool}.")

        # Create temporary directories. This must be called after setNumberOfThreads.
        if not self._useExistingResults:
            self._setTemporaryDirectories()

        for iPro in range(self._nPro):
            for i in range(iPro, nTes, self._nPro):
                # Store ResultDirectory into data dict.
                tra_data[i]['ResultDirectory'] = self._temDir[iPro]
                # This directory must also be copied into the original data structure.
                found = False
                for k in range(len(self._data)):
                    if self._data[k]['ScriptFile'] == tra_data[i]['ScriptFile']:
                        self._data[k]['ResultDirectory'] = tra_data[i]['ResultDirectory']
                        found = True
                        break
                if not found:
                    raise RuntimeError(
                        f"Failed to find the original data for {tra_data[i]['ScriptFile']}")

        self._data = tra_data

        for iPro in range(self._nPro):

            tra_data_pro = []
            for i in range(iPro, nTes, self._nPro):
                # Copy data used for this process only.
                tra_data_pro.append(tra_data[i])

            if self._modelica_tool == 'dymola':
                # Case for dymola
                self._write_runscript_dymola(iPro, tra_data_pro)

            nUniTes = nUniTes + self._write_python_runscripts(iPro, tra_data_pro)
            self._write_run_all_script(iPro, tra_data_pro)

        if nUniTes == 0:
            raise RuntimeError(
                f"Wrong invocation, generated {nUniTes} unit tests. There seem to be no model to translate.")

        print("Generated {} regression tests.\n".format(nUniTes))


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
            logger.info(f'Update reference file: {Path(ref_dir, ref)} \n')
            if os.path.exists(Path(ref_dir, ref)) is True:
                os.remove(Path(ref_dir, ref))
            else:
                logger.error(f'File {Path(ref_dir, ref)} does not exist\n')

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
            logger.info(f'Generate new reference results for model:  {model}')
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
            logger.error(
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
        filepath = CI_CONFIG.get_file_path("ci_files", "dymola_reference_file")
        os.makedirs(filepath.parent, exist_ok=True)
        with open(filepath, "w") as whitelist_file:
            for mos in mos_list:
                whitelist_file.write(f'\n{mos}\n')

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
                        logger.error(
                            f'This mos script is not suitable for regression testing: {filepath}')
        if len(mos_list) == 0:
            logger.error(f'No feasible mos script for regression test in {CI_CONFIG.artifacts.library_resource_dir}.')
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
                logger.info(
                    f'Don´t Create reference results for model {package} This package is '
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
    filepath = CI_CONFIG.get_file_path("whitelist", "dymola_reference_file")
    try:
        with open(filepath, "r") as ref_wh:
            lines = ref_wh.readlines()
            for line in lines:
                if len(line.strip()) == 0:
                    continue
                else:
                    whitelist_list.append(line.strip())
        for whitelist_package in whitelist_list:
            logger.error(
                f' Don´t create reference results for package {whitelist_package}: '
                f'This Package is '
                f'on the whitelist')
        return whitelist_list
    except FileNotFoundError:
        logger.info(f'File {filepath} does not exist, not using any whitelist.')
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
        logger.error(f'No Reference result for Model: {package}')
    return mos_script_list


def get_update_ref():
    """
    get a model to update
    Returns:
    """
    update_ref_list = []
    filepath = CI_CONFIG.interact.get_path(CI_CONFIG.interact.update_ref_file)
    try:
        with open(filepath, "r") as file:
            lines = file.readlines()
        for line in lines:
            if len(line) == 0:
                continue
            elif line.find(".txt") > -1:
                update_ref_list.append(line.strip())
        if len(update_ref_list) == 0:
            logger.error(
                f'No reference files in file {CI_CONFIG.interact.get_path(CI_CONFIG.interact.update_ref_file)}. '
                f'Please add here your reference files you '
                f'want to update')
        return update_ref_list
    except FileNotFoundError:
        logger.error(f'File {filepath} does not exist.')
    return update_ref_list


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
                logger.error("The following malformed html syntax has been found:\n%s" % err_msg[i])
            else:
                logger.error(err_msg[i])
        if n_msg == 0:
            return 0
        else:
            logger.error(f'html check failed.')
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
            try:
                ut.setSinglePackage(package)
            except ValueError as err:
                logger.error("Package %s has no regression scripts, can't get coverage: %s",
                             package, err)
                return
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

        temp_data = self._data[:]

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
        n_tested_examples = len(temp_data)
        n_examples = len(all_examples)
        if n_examples > 0:
            coverage = round(n_tested_examples / n_examples, 2) * 100
        else:
            coverage = 100

        tested_model_names = [
            nam['ScriptFile'].split(os.sep)[-1][:-1] for nam in temp_data
        ]

        missing_examples = [
            i for i in all_examples if not any(
                xs in i for xs in tested_model_names)
        ]

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
            logger.info('***\n\nThe following examples are not tested\n')
            for i in missing_examples:
                logger.info(i.split(self._libHome)[1])

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
        "--min-number-of-unused-licences",
        default=1,
        help="Number of unused licences for Dymola to start. "
             "Used to avoid license blocking of real users. "
             "Set to 0 to disable this check."
    )
    unit_test_group.add_argument(
        "--startup-mos",
        default=None,
        help="Possible startup-mos script to e.g. load additional libraries"
    )
    # [ bool - flag]
    unit_test_group.add_argument(
        "-b", "--batch",
        action="store_true",
        default=True,
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
    # todo: /bin/sh: 1: xdg-settings: not found
    args = parse_args()
    CI_CONFIG.library_root = args.library_root
    LIBRARY_PACKAGE_MO = Path(CI_CONFIG.library_root).joinpath(args.library, "package.mo")
    if args.startup_mos is not None:
        STARTUP_MOS = Path(CI_CONFIG.library_root).joinpath(args.startup_mos)
    else:
        STARTUP_MOS = None

    ref_check = BuildingspyRegressionCheck(
        n_pro=args.number_of_processors,
        tool=args.tool,
        batch=args.batch,
        show_gui=args.show_gui,
        path=args.path,
        library=args.library,
        startup_mos=STARTUP_MOS
    )
    exit_var = 0
    if args.validate_html_only:
        var = BuildingspyValidateTest(
            validate=validate,
            path=args.path
        ).validate_html()
        exit_var = max(exit_var, var)
    elif args.validate_experiment_setup:  # Match the mos file parameters with the mo files only, and then exit
        var = BuildingspyValidateTest(
            validate=validate,
            path=args.path
        ).validate_experiment_setup()
        exit_var = max(exit_var, var)
    all_packages_list = []
    for package in args.packages:
        package = f"{args.library}.{package}"
        if args.coverage_only:
            BuildingspyValidateTest(
                validate=validate,
                path=args.path
            ).run_coverage_only(
                batch=args.batch,
                tool=args.tool,
                package=package
            )
            continue
        ref_model = ReferenceModel(library=args.library)
        package_list = []
        if args.ref_list:
            ref_model.write_regression_list()

        if args.create_ref:
            package_list, created_ref_list = ref_model.get_update_model()
            if not package_list:
                logger.info("All regression tests for package %s exist", package)
                continue
            logger.info(f'Start regression Test.\nTest following packages: {package_list}')
            val = ref_check.check_regression_test(package_list=package_list, create_results=True)
            if len(created_ref_list) > 0:
                for ref in created_ref_list:
                    config_structure.prepare_data(
                        source_target_dict={
                            f'{CI_CONFIG.artifacts.library_ref_results_dir}{os.sep}{ref.replace(".", "_")}.txt':
                                CI_CONFIG.get_file_path("result", "regression_dir").joinpath("referencefiles")}
                    )
                write_exit_file(message="GENERATED_NEW_RESULTS")
            exit_var = max(exit_var, val)
        elif args.update_ref:
            ref_list = get_update_ref()
            ref_model.delete_ref_file(ref_list=ref_list)
            package_list = get_update_package(ref_list=ref_list)
        else:
            config_structure.check_path_setting(ci_files=CI_CONFIG.get_dir_path("ci_files"), create_flag=True)
            config_structure.create_files(CI_CONFIG.get_file_path("ci_files", "exit_file"))
            if args.changed_flag is False:
                package_list = [package]
            if args.changed_flag is True:
                changed_files_file = create_changed_files_file(repo_root=args.library_root)

                dymola_api = python_dymola_interface.load_dymola_api(
                    packages=[LIBRARY_PACKAGE_MO],
                    min_number_of_unused_licences=args.min_number_of_unused_licences,
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
        if package_list is None or len(package_list) == 0:
            if args.changed_flag is False:
                logger.info('No reference results in package %s', package)
                continue
            elif args.changed_flag is True:
                logger.info('No changed models in package %s', package)
                continue
        all_packages_list.extend(package_list)
    logger.info(f'Start regression Test.\nTest following packages: {all_packages_list}')
    val = ref_check.check_regression_test(package_list=all_packages_list, create_results=False)
    exit_var = max(exit_var, val)
    write_exit_file(message="FAIL" if exit_var == 1 else "Successfull")
    exit(exit_var)
