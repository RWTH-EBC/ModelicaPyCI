import os
import shutil
import uuid
from pathlib import Path

from ModelicaPyCI.config import CI_CONFIG, ColorConfig
from ModelicaPyCI.structure import config_structure


COLORS = ColorConfig()


def create_changed_files_file():
    if not os.path.isdir(Path().joinpath(".git")):
        print(
            f"{COLORS.CRED}Error: {COLORS.CEND} Current path is not a "
            f"git-directory, can't check changed models."
        )
        exit(1)

    changed_files_file = CI_CONFIG.get_file_path("ci_files", "changed_file")
    config_structure.check_path_setting(ci_files=CI_CONFIG.get_dir_path("ci_files"), create_flag=True)

    path = f"temp_file_{uuid.uuid4()}"

    os.system(f"git diff --raw --diff-filter=AMT HEAD^^ > {path}")
    shutil.copy(path, changed_files_file)
    os.remove(path)
    config_structure.check_file_setting(changed_files_file=changed_files_file)

    return changed_files_file
