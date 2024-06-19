import logging
import os
import uuid
from pathlib import Path
from typing import Union

from ModelicaPyCI.config import ColorConfig
from ModelicaPyCI.load_global_config import CI_CONFIG
from ModelicaPyCI.structure import config_structure

COLORS = ColorConfig()
logger = logging.getLogger("ModelicaPyCI")


class ColoredFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    def __init__(self, fmt: str):
        super().__init__(fmt=fmt)
        self.colored_formats = {
            logging.DEBUG: logging.Formatter(COLORS.yellow + fmt + COLORS.CEND),
            logging.INFO: logging.Formatter(COLORS.green + fmt + COLORS.CEND),
            logging.WARNING: logging.Formatter(COLORS.blue + fmt + COLORS.CEND),
            logging.ERROR: logging.Formatter(COLORS.CRED + fmt + COLORS.CEND),
            logging.CRITICAL: logging.Formatter(COLORS.CRED + fmt + COLORS.CEND)
        }

    def format(self, record):
        return self.colored_formats.get(record.levelno).format(record)


def setup_logging():
    root_logger = logging.getLogger()
    if not root_logger.hasHandlers():
        logging.basicConfig(level=logging.INFO)
        root_logger = logging.getLogger()
        root_logger.handlers[0].setFormatter(
            ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logging.info("Logging is set up.")
    else:
        print("Root logger was already set up with level", root_logger.level)


setup_logging()


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
