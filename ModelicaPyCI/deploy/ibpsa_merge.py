from pathlib import Path
import argparse
import os
import glob
import shutil
from natsort import natsorted
from buildingspy.development import merger


def merge_workflow(
        library_dir: Path,
        merge_library_dir: Path,
        mos_path: Path,
        library: str,
        merge_library: str
):
    mer = merger.IBPSA(merge_library_dir, library_dir)
    mer.set_excluded_directories(["Experimental", "Obsolete"])
    mer.merge()
    print("Merged.")

    last_mlibrary_conversion = _copy_merge_mos_script(
        merge_library_dir=merge_library_dir, mos_path=mos_path
    )
    last_library_conversion = _read_last_library_conversion(
        library_dir=library_dir
    )
    result = _compare_conversion(library=library,
                                 merge_library=merge_library,
                                 last_mlibrary_conversion=last_mlibrary_conversion,
                                 last_library_conversion=last_library_conversion)
    if result is True:
        print(
            f'The latest {library} conversion script '
            f'{last_library_conversion} is up to date with '
            f'{merge_library} conversion script {last_mlibrary_conversion}'
        )
    else:
        file_new_conversion_script, old_to_numb, new_to_numb = _create_convert(
            library=library,
            merge_library=merge_library,
            mos_path=mos_path,
            last_mlibrary_conversion=last_mlibrary_conversion,
            last_library_conversion=last_library_conversion
        )
        new_conversion_script = shutil.copy(file_new_conversion_script, library_dir)
        shutil.rmtree(mos_path)
        _add_conversion_script_to_package_mo(
            library=library,
            last_library_conversion=last_library_conversion,
            new_conversion_script=new_conversion_script,
            old_to_numb=old_to_numb,
            new_to_numb=new_to_numb
        )
        print(f'New {library} Conversion scrip was created: {file_new_conv}')
    correct_user_guide(library_dir)


def _read_last_library_conversion(library_dir: Path, ):
    """
    Read the last conversion mos script of library to update, e.g. AixLib

    Returns:
        Return the latest library conversion script
    """
    filelist = (glob.glob(f'{library_dir}{os.sep}*.mos'))
    if len(filelist) == 0:
        print("Cant find a Conversion Script in IBPSA Repo")
        exit(0)
    last_library_conversion = natsorted(filelist)[(-1)]
    last_library_conversion = last_library_conversion.replace("/", os.sep)
    last_library_conversion = last_library_conversion.replace("\\", os.sep)
    print(f'Latest Conversion script: {last_library_conversion}')
    return last_library_conversion


def _copy_merge_mos_script(
        merge_library_dir: Path,
        mos_path: Path,
):
    """
    Copy the Convert_IBPSA_mos Script
    Returns: return the latest conversion script
    """
    if os.path.isdir(mos_path):
        pass
    else:
        os.mkdir(mos_path)
    mos_file_list = (glob.glob(str(merge_library_dir)))
    if len(mos_file_list) == 0:
        print(f'Cant find a Conversion Script in IBPSA Repo')
        exit(0)
    last_ibpsa_conv = natsorted(mos_file_list)[(-1)]
    last_ibpsa_conv = last_ibpsa_conv.replace("/", os.sep)
    last_ibpsa_conv = last_ibpsa_conv.replace("\\", os.sep)
    print(f'Latest IBPSA Conversion script: {last_ibpsa_conv}')
    shutil.copy(last_ibpsa_conv, mos_path)
    return last_ibpsa_conv


def _create_convert(
        library: str,
        merge_library: str,
        mos_path: Path,
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
    file_new_conv = mos_path.joinpath(f"Convert{library}_from_{new_conv_number}.mos")
    with open(last_mlibrary_conversion, "r") as file:
        lines = file.readlines()
    with open(last_library_conversion, "w+") as library_file:
        for line in lines:
            if line.find(f'Conversion script for {merge_library} library') > -1:
                library_file.write(line)
            elif line.find(f'{merge_library}') > - 1:
                library_file.write(line.replace(f'{merge_library}', f'{library}'))
            else:
                library_file.write(line)

    return file_new_conv, old_to_numb, new_to_numb


def _compare_conversion(library: str, merge_library: str, last_mlibrary_conversion, last_library_conversion):
    """
    Compare the latest library conversion script with the latest merge library conversion script
    Args:
        last_mlibrary_conversion (): latest merge library conversion script
        last_library_conversion (): latest library conversion script
    Returns:
        False (): Boolean argument: True - Conversion script is up-to-date , False Conversion script is not up-to-date
    """
    result = True
    with open(last_mlibrary_conversion) as file_1:
        file_1_text = file_1.readlines()
    with open(last_library_conversion) as file_2:
        file_2_text = file_2.readlines()
    for line1, line2 in zip(file_1_text, file_2_text):
        if line1 == line2.replace(library, merge_library):
            continue
        else:
            result = False
    return result


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
    check_test_group.add_argument("--library-dir",
                                  default="AixLib\\Resources\\Scripts",
                                  help="path to the library scripts")
    check_test_group.add_argument("--merge-library-dir",
                                  default='modelica-ibpsa\\IBPSA\\Resources\\Scripts\\Dymola\\ConvertIBPSA_*',
                                  help="path to the merge library scripts")
    check_test_group.add_argument("--mos-path",
                                  default="Convertmos",
                                  help="Folder where the conversion scripts are stored temporarily")
    check_test_group.add_argument("--library",
                                  default="AixLib",
                                  help="Library to be merged into")
    check_test_group.add_argument("--merge-library",
                                  default='IBPSA',
                                  help="Library to be merged")
    return parser.parse_args()


if __name__ == '__main__':
    ARGS = parse_args()
    merge_workflow(
        library_dir=ARGS.library_dir,
        merge_library_dir=ARGS.merge_library_dir,
        mos_path=ARGS.mos_path,
        library=ARGS.library,
        merge_library=ARGS.merge_library
    )
