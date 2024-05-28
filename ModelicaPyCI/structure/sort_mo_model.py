import os
from ModelicaPyCI.config import CI_CONFIG, ColorConfig
from ModelicaPyCI.pydyminterface.model_management import ModelManagement
from pathlib import Path
from ModelicaPyCI.structure import config_structure
from ModelicaPyCI.utils import create_changed_files_file

COLORS = ColorConfig()


def get_option_model(
        library: str,
        package: str,
        dymola=None,
        dymola_exception=None,
        changed_flag: bool = False,
        simulate_flag: bool = False,
        filter_whitelist_flag: bool = False,
        extended_ex_flag: bool = False,
        dymola_version: int = 2022,
        library_package_mo: Path = None,
        root_package: Path = None,
        changed_to_branch: str = None):
    # todo: flag mit einbauen: In zukunft sollen die pfade gegeben werden, nach wunsch auch in modelica form
    """
    Args:
        library ():
        package ():
        dymola ():
        dymola_exception ():
        changed_flag ():
        simulate_flag ():
        filter_whitelist_flag ():
        extended_ex_flag ():
        dymola_version ():
        library_package_mo ():
        root_package ():
    Returns:
    """
    config_structure.check_arguments_settings(
        package=package,
        library=library,
        changed_flag=changed_flag,
        simulate_flag=simulate_flag,
        filter_whitelist_flag=filter_whitelist_flag,
        extended_ex_flag=extended_ex_flag,
    )
    if library_package_mo is None:
        library_package_mo = Path().joinpath(library, "package.mo")
    config_structure.check_file_setting(library_package_mo=library_package_mo)
    if root_package is None:
        if package == ".":
            root_package = Path(Path(library_package_mo).parent)
        else:
            root_package = Path(Path(library_package_mo).parent, package.replace(".", os.sep))
    config_structure.check_path_setting(root_package=root_package)
    if dymola is None:
        extended_ex_flag = False
    if changed_flag is True:
        changed_files_file = create_changed_files_file(to_branch=changed_to_branch)

        result = get_changed_models(changed_files=changed_files_file,
                                    library=library,
                                    single_package=package,
                                    simulate_examples=simulate_flag)
        model_list = result[0]
        if extended_ex_flag is True:
            simulate_list = get_extended_model(dymola=dymola,
                                               dymola_exception=dymola_exception,
                                               model_list=result[1],
                                               library=library,
                                               dymola_version=dymola_version)
            model_list.extend(simulate_list)
            model_list = list(set(model_list))
    else:
        whitelist_list_models = []
        config_structure.check_path_setting(whitelist=CI_CONFIG.get_dir_path("whitelist"), create_flag=True)

        ci_whitelist_ibpsa_file = CI_CONFIG.get_file_path("whitelist", "ibpsa_file")
        if os.path.exists(ci_whitelist_ibpsa_file):
            whitelist_list_models.extend(
                get_whitelist_models(
                    whitelist_file=ci_whitelist_ibpsa_file, library=library, single_package=package
                )
            )
        if filter_whitelist_flag is True:
            if simulate_flag is True:
                ci_whitelist_file = CI_CONFIG.get_file_path("whitelist", "simulate_file")
            else:
                ci_whitelist_file = CI_CONFIG.get_file_path("whitelist", "check_file")

            whitelist_list_models.extend(
                get_whitelist_models(
                    whitelist_file=ci_whitelist_file, library=library, single_package=package
                )
            )
        # Remove possible duplicates
        whitelist_list_models = list(set(whitelist_list_models))

        result = get_models(path=root_package,
                            library=library,
                            simulate_flag=simulate_flag,
                            extended_ex_flag=extended_ex_flag)
        model_list = result[0]
        if extended_ex_flag is True:
            simulate_list = get_extended_model(dymola=dymola,
                                               dymola_exception=dymola_exception,
                                               model_list=result[1],
                                               library=library,
                                               dymola_version=dymola_version)
            model_list.extend(simulate_list)
            model_list = list(set(model_list))
        model_list = filter_whitelist_models(models=model_list,
                                             whitelist_list=whitelist_list_models)
    if len(model_list) == 0 or model_list is None:
        print(f'Find no models in package {package}')
        exit(0)
    else:
        return model_list


def get_changed_regression_models(
        dymola,
        dymola_exception,
        dymola_version: int,
        root_package: Path,
        library: str,
        changed_files: Path,
        package: str):
    """
    Returns:
    """
    changed_models = open(changed_files, "r", encoding='utf8')
    changed_lines = changed_models.readlines()
    changed_models.close()
    # List all type of files from changed file
    mos_script_list = get_changed_mos_script(changed_lines=changed_lines, library=library, package=package)
    modelica_model_list = get_changed_model(changed_lines=changed_lines, library=library, package=package)
    reference_list = changed_reference_files(changed_lines=changed_lines, library=library, package=package)
    # get all models from page package
    model_list, no_example_list = get_models(path=root_package,
                                             library=library,
                                             simulate_flag=True,
                                             extended_ex_flag=False)
    extended_list = get_extended_model(dymola=dymola,
                                       dymola_exception=dymola_exception,
                                       model_list=model_list,
                                       dymola_version=dymola_version,
                                       library=library)

    changed_model_list = get_changed_used_model(
        changed_lines=changed_lines, extended_list=extended_list, library=library
    )

    changed_list = return_type_list(
        ref_list=reference_list,
        mos_list=mos_script_list,
        modelica_list=modelica_model_list,
        changed_model_list=changed_model_list,
        library=library, package=package,
    )
    if len(changed_list) == 0:
        print(f'No models to check and cannot start a regression test')
        exit(0)
    else:
        print(f'Number of checked packages: {str(len(changed_list))}')
        return changed_list


def get_extended_model(
        dymola: object,
        dymola_exception: object,
        model_list: list,
        dymola_version: int = 2022,
        library: str = "AixLib"):
    mm = ModelManagement(dymola=dymola,
                         dymola_exception=dymola_exception,
                         dymola_version=dymola_version)

    mm.load_model_management()
    simulate_list = list()
    for model in model_list:
        print(f' **** Check structure of model {model} ****')
        extended_list = mm.get_extended_examples(model=model)
        used_list = mm.get_used_models(model=model)
        extended_list.extend(used_list)
        for ext in extended_list:
            print(f'Extended model {ext} ')
            filepath = f'{ext.replace(".", os.sep)}.mo'
            example_test = _get_icon_example(filepath=filepath,
                                             library=library)
            if example_test is None:
                print(f'File {filepath} is no example.')
            else:
                simulate_list.append(model)
                simulate_list.append(ext)
    simulate_list = list(set(simulate_list))
    return simulate_list


def get_changed_mos_script(changed_lines: list, library: str, package: str):
    _list = []
    for line in changed_lines:
        if line.rfind(".mos") > -1 and line.rfind("Scripts") > -1 and line.find(
                ".package") == -1 and line.rfind(package) > -1:
            line = line.replace("Dymola", library)
            _list.append(line[line.rfind(library):line.rfind(".mos")])
    return _list


def get_changed_model(changed_lines: list, library: str, package: str):
    _list = []
    for line in changed_lines:
        if line.rfind(".mo") > -1 and line.find("package.") == -1 and line.rfind(
                package) > -1 and line.rfind("Scripts") == -1:
            _list.append(line[line.rfind(library):line.rfind(".mo")])
    return _list


def changed_reference_files(changed_lines: list, library: str, package: str):
    _list = []
    for line in changed_lines:
        if (line.rfind(".txt") > -1 and
                line.find("package.") == -1 and
                line.rfind(package) > -1
                and line.rfind("Scripts") == -1
        ):
            _list.append(line[line.rfind(library):line.rfind(".txt")])
    return _list


def get_whitelist_models(whitelist_file: str,
                         library: str,
                         single_package: str):
    """
    Returns: return models that are on the whitelist
    """
    whitelist_list_models = list()
    try:
        whitelist_file = open(whitelist_file, "r")
        lines = whitelist_file.readlines()
        for line in lines:
            model = line.lstrip()
            model = model.strip().replace("\n", "")
            if model.find(f'{library}.{single_package}') > -1:
                print(f'Dont test {library} model: {model}. Model is on the whitelist.')
                whitelist_list_models.append(model)
        whitelist_file.close()
        return whitelist_list_models
    except IOError:
        print(f'Error: File {whitelist_file} does not exist.')
        return whitelist_list_models


def filter_whitelist_models(models, whitelist_list):
    """
    Args:
        models (): models from library.
        whitelist_list (): model from whitelist.
    Returns:
        return models from library who are not on the whitelist.
    """
    whitelist_list_mo = list()
    if len(models) == 0:
        exit(0)
    else:
        for element in models:
            for sub_element in whitelist_list:
                if element == sub_element:
                    whitelist_list_mo.append(element)
        whitelist_list_mo = list(set(whitelist_list_mo))
        for example in whitelist_list_mo:
            models.remove(example)
        return models


def _get_icon_example(filepath, library):
    """
    Args:
        filepath (): file of a dymola model.
        library (): library to test.
    Returns:
        example: return examples that have the string extends Modelica.Icons.Examples
    """
    try:
        ex_file = open(filepath, "r", encoding='utf8', errors='ignore')
        lines = ex_file.readlines()
        for line in lines:
            if line.find("extends") > -1 and line.find("Modelica.Icons.Example") > -1:
                example = filepath.replace(os.sep, ".")
                example = example[example.rfind(library):example.rfind(".mo")]
                ex_file.close()
                return example
    except IOError:
        print(f'Error: File {filepath} does not exist.')


def _model_to_ref_exist(ref_file, library: str, package: str):
    model_file = ref_file.replace("_", os.sep)
    for subdir, dirs, files in os.walk(package.replace(".", os.sep)):
        for file in files:
            filepath = f'{library}{os.sep}{subdir}{os.sep}{file}'
            if filepath.endswith(".mo") and filepath.find(package.replace(".", os.sep)) > -1:
                if filepath.find(model_file) > -1:
                    return model_file.replace(os.sep, ".")


def _mos_script_to_model_exist(model, library: str, package: str):
    test_model = model.replace(f'{library}.', "")
    test_model = test_model.replace(".", os.sep)
    for subdir, dirs, files in os.walk(CI_CONFIG.artifacts.library_resource_dir):
        for file in files:
            filepath = subdir + os.sep + file
            if filepath.endswith(".mos") and filepath.find(package.replace(".", os.sep)) > -1:
                if filepath.find(test_model) > -1:
                    infile = open(filepath, "r")
                    lines = infile.read()
                    infile.close()
                    if lines.find("simulateModel") > -1:
                        return model
                    if lines.find("simulateModel") == -1:
                        return None


def model_to_mos_script_exist(mos_script, library: str, package: str):
    model_file = mos_script.replace(".", os.sep)
    for subdir, dirs, files in os.walk(package.replace(".", os.sep)):
        for file in files:
            filepath = f'{library}{os.sep}{subdir}{os.sep}{file}'
            if filepath.endswith(".mo") and filepath.find(package.replace(".", os.sep)) > -1:
                if filepath.find(model_file) > -1:
                    return mos_script


def return_type_list(
        ref_list,
        mos_list,
        modelica_list,
        changed_model_list,
        library: str,
        package: str):
    """
    return models, scripts, reference results and used models, that changed
    Args:
        ref_list (): list of reference files
        mos_list (): list of .mos files
        modelica_list (): list of modelica files
        changed_model_list (): list of changed models
    Returns:
    """
    changed_list = []
    print(f'\n ------The last modified files ------\n')
    if ref_list is not None:
        for ref in ref_list:
            model_file = _model_to_ref_exist(ref_file=ref, library=library, package=package)
            if model_file is not None:
                model = _mos_script_to_model_exist(model=model_file, library=library, package=package)
                if model is not None:
                    print(f'Changed reference files: {ref}')
                    changed_list.append(ref[:ref.rfind("_")].replace("_", "."))
    if mos_list is not None:
        for mos in mos_list:
            mos_script = model_to_mos_script_exist(mos_script=mos, library=library, package=package)
            if mos_script is not None:
                model = _mos_script_to_model_exist(model=mos_script, library=library, package=package)
                if model is not None:
                    print(f'Changed mos script files: {mos}')
                    changed_list.append(mos[:mos.rfind(".")])
    if modelica_list is not None:
        for model in modelica_list:
            model = _mos_script_to_model_exist(model=model, library=library, package=package)
            if model is not None:
                print(f'Changed model files: {model}')
                changed_list.append(model[:model.rfind(".")])
    if changed_model_list is not None:
        for used_model in changed_model_list:
            model = _mos_script_to_model_exist(model=used_model, library=library, package=package)
            if model is not None:
                print(f'Changed used model files: {used_model}')
                changed_list.append(used_model[:used_model.rfind(".")])
    print(f'\n -----------------------------------\n')
    changed_list = list(set(changed_list))
    return changed_list


def get_changed_used_model(changed_lines: list, extended_list: list, library: str):
    """
    return all used models, that changed
    Args:
        changed_lines (): lines from changed models
        extended_list (): models to check
    Returns:
        changed_model_list () : return a list of changed models
    """

    changed_model_list = []
    for line in changed_lines:
        for model in extended_list:
            if line[line.find(library):line.rfind(".mo")].strip() == model:
                changed_model_list.append(model)
    return changed_model_list


def get_changed_models(
        changed_files: Path,
        library: str,
        single_package: str,
        simulate_examples: bool = False,
        extended_ex_flag: bool = False):
    """
    Returns: return a list with changed models.
    """
    try:
        file = open(changed_files, "r", encoding='utf8', errors='ignore')
        lines = file.readlines()
        modelica_models = []
        no_example_list = []
        for line in lines:
            line = line.lstrip()
            line = line.strip().replace("\n", "")
            if line.rfind(".mo") > -1 and line.find("package") == -1:
                if (
                        line.find(Path(library).joinpath(single_package).as_posix()) > -1 and
                        not line.startswith(Path(library).joinpath("Resources").as_posix())
                ):
                    if simulate_examples is True:
                        model_name = line[line.rfind(library):line.rfind('.mo') + 3]
                        example_test = _get_icon_example(filepath=model_name,
                                                         library=library)
                        if example_test is None:
                            print(
                                f'Model {model_name} is not a simulation example because it '
                                f'does not contain the following "Modelica.Icons.Example"'
                            )
                            if extended_ex_flag is True:
                                no_example = line.replace(os.sep, ".")
                                no_example = no_example[no_example.rfind(library):no_example.rfind(".mo")]
                                no_example_list.append(no_example)
                            continue
                        else:
                            modelica_models.append(example_test)
                            continue
                    else:
                        model_name = line[line.rfind(library):line.rfind('.mo')]
                        model_name = model_name.replace(os.sep, ".")
                        model_name = model_name.replace('/', ".")
                        modelica_models.append(model_name)
                        continue
        if len(modelica_models) == 0:
            print(f'No models in Package: {single_package}')
            exit(0)
        file.close()
        return modelica_models, no_example_list
    except IOError:
        print(f'Error: File {changed_files} does not exist.')
        exit(0)


def get_models(
        path: Path,
        library: str = "AixLib",
        simulate_flag: bool = False,
        extended_ex_flag: bool = False):
    """
        Args:
            simulate_flag ():
            extended_ex_flag ():
            path (): whitelist library or library path.
            library (): library to test.
        Returns:
            model_list (): return a list with models to check.
    """
    model_list = list()
    no_example_list = list()
    for subdir, dirs, files in os.walk(path):
        for file in files:
            filepath = subdir + os.sep + file
            if filepath.endswith(".mo") and file != "package.mo":
                if simulate_flag is True:
                    example_test = _get_icon_example(filepath=filepath,
                                                     library=library)
                    if example_test is None:
                        print(
                            f'Model {filepath} is not a simulation example because '
                            f'it does not contain the following "Modelica.Icons.Example"')
                        if extended_ex_flag is True:
                            no_example = filepath.replace(os.sep, ".")
                            no_example = no_example[no_example.rfind(library):no_example.rfind(".mo")]
                            no_example_list.append(no_example)
                        continue
                    else:
                        model_list.append(example_test)
                        continue
                else:
                    model = filepath.replace(os.sep, ".")
                    model = model[model.rfind(library):model.rfind(".mo")]
                    model_list.append(model)
    if model_list is None or len(model_list) == 0:
        print(f'No models in package {path}')
        return model_list, no_example_list

    else:
        return model_list, no_example_list
