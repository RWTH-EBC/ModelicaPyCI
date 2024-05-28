import os
from typing import Union
import uuid
from pathlib import Path

from ModelicaPyCI.config import CI_CONFIG, ColorConfig
from ModelicaPyCI.structure import config_structure


COLORS = ColorConfig()


def create_changed_files_file(repo_root: Union[str, Path] = None, to_branch: str = None):
    old_cwd = os.getcwd()
    if repo_root is not None:
        os.chdir(repo_root)
    if not os.path.isdir(Path().joinpath(".git")):
        print(
            f"{COLORS.CRED}Error: {COLORS.CEND} Current path {os.getcwd()} is not a "
            f"git-directory, can't check changed models: {os.listdir()}"
        )
        exit(1)

    changed_files_file = CI_CONFIG.get_file_path("ci_files", "changed_file")
    config_structure.check_path_setting(ci_files=CI_CONFIG.get_dir_path("ci_files"), create_flag=True)

    if to_branch is None:
        compare_to = "HEAD^^"
    else:
        compare_to = os_system_with_return(f"git rev-parse origin/{to_branch}")

    return_value = os_system_with_return(f"git diff --raw --diff-filter=AMT --name-only {compare_to}")

    os.chdir(old_cwd)

    with open(changed_files_file, "w") as file:
        file.write(return_value)
    config_structure.check_file_setting(changed_files_file=changed_files_file)

    return changed_files_file


def os_system_with_return(command):
    file_name = f"{uuid.uuid4()}.txt"
    os.system(f"{command} > {file_name}")
    with open(file_name, "r") as file:
        return_value = file.read()
    os.remove(file_name)
    if return_value.endswith("\n"):
        return return_value[:-1]
    return return_value
