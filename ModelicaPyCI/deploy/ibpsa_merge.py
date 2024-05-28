from pathlib import Path
import argparse
import os
import glob
import shutil
from natsort import natsorted
from buildingspy.development import merger

from ModelicaPyCI.config import CI_CONFIG


def merge_workflow(
        library: str,
        library_dir: str,
        library_mos_scripts: str,
        merge_library: str,
        merge_library_dir: str,
        merge_library_mos_scripts: str,
        temporary_mos_path: str,
):
    mer = merger.IBPSA(
        ibpsa_dir=str(Path(merge_library_dir).joinpath(merge_library)),
        dest_dir=str(Path(library_dir).joinpath(library))
    )
    mer.set_excluded_directories(["Experimental", "Obsolete"])
    mer.merge()
    print("Merged.")

    temporary_mos_path = Path().joinpath(temporary_mos_path)
    merge_library_scripts_dir = Path(merge_library_dir).joinpath(merge_library, merge_library_mos_scripts)
    last_mlibrary_conversion = _copy_merge_mos_script(
        merge_library_scripts_dir=merge_library_scripts_dir, temporary_mos_path=temporary_mos_path
    )
    library_scripts_dir = Path(library_dir).joinpath(library, library_mos_scripts)
    library_conversions = _read_library_conversions(library_scripts_dir=library_scripts_dir)

    result, last_library_conversion = _compare_conversion(library=library,
                                                          merge_library=merge_library,
                                                          last_mlibrary_conversion=last_mlibrary_conversion,
                                                          library_conversions=library_conversions)
    if result is True:
        print(
            f'The {library} conversion script '
            f'{last_library_conversion} is up to date with '
            f'{merge_library} conversion script {last_mlibrary_conversion}'
        )
    else:
        file_new_conversion_script, old_to_numb, new_to_numb = _create_convert(
            library=library,
            merge_library=merge_library,
            temporary_mos_path=temporary_mos_path,
            last_mlibrary_conversion=last_mlibrary_conversion,
            last_library_conversion=last_library_conversion
        )
        new_conversion_script = shutil.copy(
            file_new_conversion_script,
            library_scripts_dir.joinpath(file_new_conversion_script.name)
        )
        shutil.rmtree(temporary_mos_path)
        _add_conversion_script_to_package_mo(
            library=library,
            last_library_conversion=last_library_conversion,
            new_conversion_script=new_conversion_script,
            old_to_numb=old_to_numb,
            new_to_numb=new_to_numb
        )
        print(f'New {library} Conversion scrip was created: {new_conversion_script}')
    correct_user_guide(library_dir)


def _read_library_conversions(library_scripts_dir: Path):
    """
    Read the last conversion mos script of library to update, e.g. AixLib

    Returns:
        Return the latest library conversion script
    """
    filelist = (glob.glob(f'{library_scripts_dir}{os.sep}*.mos'))
    if len(filelist) == 0:
        print(f"Cant find a Conversion Script in {library_scripts_dir}")
        exit(1)
    filelist = natsorted(filelist)[::-1]
    print(f'Conversion scripts: {filelist}')
    return filelist


def _copy_merge_mos_script(
        merge_library_scripts_dir: Path,
        temporary_mos_path: Path,
):
    """
    Copy the Convert_IBPSA_mos Script
    Returns: return the latest conversion script
    """
    if os.path.isdir(temporary_mos_path):
        pass
    else:
        os.mkdir(temporary_mos_path)
    mos_file_list = (glob.glob(f"{merge_library_scripts_dir}{os.sep}*.mos"))
    if len(mos_file_list) == 0:
        print(f'Cant find a Conversion Script in path {merge_library_scripts_dir}')
        exit(1)
    last_ibpsa_conv = natsorted(mos_file_list)[(-1)]
    last_ibpsa_conv = last_ibpsa_conv.replace("/", os.sep)
    last_ibpsa_conv = last_ibpsa_conv.replace("\\", os.sep)
    print(f'Latest IBPSA Conversion script: {last_ibpsa_conv}')
    shutil.copy(last_ibpsa_conv, temporary_mos_path)
    return last_ibpsa_conv


def _create_convert(
        library: str,
        merge_library: str,
        temporary_mos_path: Path,
        last_mlibrary_conversion: str,
        last_library_conversion: str
):
    """
    Change the paths in the script from e.g.
    IBPSA.Package.model -> AixLib.Package.model

    Args:
        last_mlibrary_conversion (str): latest merge library conversion script
        last_library_conversion (str): Name of latest library conversion script

    Returns:
        file_new_conv (str): file with new conversion script
        old_to_numb (str): old to number
        new_to_numb (str): new to number
    """
    # Name is usually: ConvertLIBRARYNAME_from_X.X.X_to_Y.Y.Y.mos
    start_name = f"Convert{library}_from_"
    conversion_number = last_library_conversion.replace(start_name, "").replace(".mos", "")
    # Now: X.X.X_to_Y.Y.Y
    print(f'Latest conversion number: {conversion_number}')
    old_to_numb = conversion_number.split("_to_")[-1]

    # Update TO Number 1.0.2 old_to_numb == new_from_numb
    first_numb, sec_numb = old_to_numb.split(".")[:2]
    new_to_numb = f'{first_numb}.{int(sec_numb) + 1}.0'
    # Write new conversion number
    new_conv_number = old_to_numb + "_to_" + new_to_numb
    file_new_conv = temporary_mos_path.joinpath(f"Convert{library}_from_{new_conv_number}.mos")
    with open(last_mlibrary_conversion, "r") as file:
        lines = file.readlines()
    with open(file_new_conv, "w+") as library_file:
        for line in lines:
            if line.find(f'Conversion script for {merge_library} library') > -1:
                library_file.write(line)
            elif line.find(f'{merge_library}') > - 1:
                library_file.write(line.replace(f'{merge_library}', f'{library}'))
            else:
                library_file.write(line)

    return file_new_conv, old_to_numb, new_to_numb


def _compare_conversion(library: str, merge_library: str, last_mlibrary_conversion, library_conversions):
    """
    Compare the latest library conversion script with the latest merge library conversion script
    Args:
        last_mlibrary_conversion (): latest merge library conversion script
        library_conversions (): library conversion scripts
    Returns:
        False (): Boolean argument: True - Conversion script is up-to-date , False Conversion script is not up-to-date
    """
    with open(last_mlibrary_conversion) as file_1:
        file_1_lines = file_1.readlines()[:3]
    for file in library_conversions:
        with open(file) as file_2:
            file_2_lines = file_2.readlines()[:3]
        if all(line_1 == line_2 for line_1, line_2 in zip(file_1_lines, file_2_lines)):
            return True, file
    return False, library_conversions[0]


def _add_conversion_script_to_package_mo(
        library: str,
        last_library_conversion: str,
        new_conversion_script: str,
        old_to_numb: str,
        new_to_numb: str
):
    """
    Write the new conversion script in the package.mo of the library

    Args:
        last_library_conversion (): latest library conversion script
        new_conversion_script (): new library conversion script
        old_to_numb (): old to number
        new_to_numb (): new to number
    """
    last_library_conversion = last_library_conversion.replace('\\', '/')
    new_conversion_script = new_conversion_script.replace('\\', '/')
    file = open(f'{library}{os.sep}package.mo', "r")
    version_list = []
    for line in file:
        if line.find("version") == 0 or line.find('script="modelica://') == 0:
            version_list.append(line)
            continue
        if line.find(f'  version = "{old_to_numb}",') > -1:
            version_list.append(line.replace(old_to_numb, new_to_numb))
            continue
        if line.find(f'{last_library_conversion}') > -1:
            version_list.append(line.replace(")),", ","))
            version_list.append(f'    version="{old_to_numb}",\n')
            version_list.append(f'                      script="modelica://{new_conversion_script}")),\n')
            continue
        else:
            version_list.append(line)
            continue
    file.close()
    pack = open(f'{library}{os.sep}package.mo', "w")
    for version in version_list:
        pack.write(version)
    pack.close()


def correct_user_guide(library_dir: Path):
    """
    Correct user guide folder
    """
    for root, dirs, files in os.walk(library_dir):
        if root[root.rfind(os.sep) + 1:] != "UsersGuide":
            continue
        for file in files:
            if file == "package.order":
                old_order_file = open(f'{root}{os.sep}{file}', "r")
                lines = old_order_file.readlines()
                old_order_file.close()
                new_order_file = open(f'{root}{os.sep}{file}', "w")
                for line in lines:
                    if line.strip("\n") != "UsersGuide":
                        new_order_file.write(line)
                new_order_file.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Variables to start a library merge")
    check_test_group = parser.add_argument_group("Arguments to set environment variables")
    check_test_group.add_argument("--library",
                                  default="AixLib",
                                  help="Library to be merged into")
    check_test_group.add_argument("--library-dir",
                                  default="AixLib/Resources/Scripts",
                                  help="path to the library scripts")
    check_test_group.add_argument("--library-mos-scripts",
                                  default='Resources/Scripts',
                                  help="path to the library scripts, relative to Modelica package")
    check_test_group.add_argument("--merge-library",
                                  default='IBPSA',
                                  help="Library to be merged")
    check_test_group.add_argument("--merge-library-dir",
                                  default='modelica-ibpsa/IBPSA/Resources/Scripts/Conversion/ConvertIBPSA_*',
                                  help="path to the merge library")
    check_test_group.add_argument("--temporary-mos-path",
                                  default="Convertmos",
                                  help="Folder where the conversion scripts are stored temporarily")
    check_test_group.add_argument("--merge-library-mos-scripts",
                                  default='Resources/Scripts/Conversion',
                                  help="path to the merge library scripts, relative to Modelica package")
    return parser.parse_args()


if __name__ == '__main__':
    ARGS = parse_args()

    CI_CONFIG.library_root = ARGS.library_dir

    merge_workflow(
        library=ARGS.library,
        library_dir=ARGS.library_dir,
        library_mos_scripts=ARGS.library_mos_scripts,
        merge_library=ARGS.merge_library,
        merge_library_dir=ARGS.merge_library_dir,
        merge_library_mos_scripts=ARGS.merge_library_mos_scripts,
        temporary_mos_path=ARGS.temporary_mos_path,
    )
