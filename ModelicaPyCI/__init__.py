import os
import shutil
import uuid
from ModelicaPyCI.config import CI_CONFIG
from ModelicaPyCI.structure import config_structure


def create_changed_files_file():
    changed_files_file = CI_CONFIG.get_file_path("ci_files", "changed_file")
    config_structure.check_path_setting(ci_files=CI_CONFIG.get_dir_path("ci_files"), create_flag=True)

    path = f"temp_file_{uuid.uuid4()}"

    os.system(f"git diff --raw --diff-filter=AMT HEAD^^ > {path}")
    shutil.copy(path, changed_files_file)
    os.remove(path)
    config_structure.check_file_setting(changed_files_file=changed_files_file)

    return changed_files_file


if __name__ == '__main__':
    import os
    os.chdir(r"D:\04_git\AixLib")
    create_changed_files_file()
