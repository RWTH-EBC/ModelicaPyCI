import inspect
import re
import os
import shutil
import glob
from pathlib import Path
import distutils.dir_util

from ModelicaPyCI.config import CI_CONFIG, ColorConfig
COLORS = ColorConfig()


def check_arguments_settings(**kwargs):
    print(f'*** --- Argument setting --- ****')
    for var, val in kwargs.items():
        if val is None:
            print(
                f'{COLORS.CRED}Error:{COLORS.CEND} {COLORS.blue}Variable "{var.strip()}"{COLORS.CEND} has value '
                f'{COLORS.CRED}"{val}". "{var}"{COLORS.CEND} is not set!'
            )
            exit(1)
        else:
            print(
                f'{COLORS.green}Setting:{COLORS.CEND} {COLORS.blue}Variable "{var.strip()}" {COLORS.CEND} is set as: '
                f'{COLORS.blue}"{val}"{COLORS.CEND}'
            )


def check_path_setting(*args: Path, create_flag: bool = False):
    frame = inspect.currentframe().f_back
    s = inspect.getframeinfo(frame).code_context[0]
    r = re.search(r"\((.*)\)", s).group(1)
    var_names = r.split(", ")
    print(f'*** --- Check path setting --- ****')
    for i, (var, path) in enumerate(zip(var_names, args)):
        if os.path.isdir(path) is True:
            print(
                f'{COLORS.green}Setting:{COLORS.CEND} {COLORS.blue}Path variable "{var}"{COLORS.CEND} is set as: '
                f'{COLORS.blue}"{path}"{COLORS.CEND} and exists.')
        else:
            print(
                f'{COLORS.CRED}Error:{COLORS.CEND} {COLORS.blue}Path variable '
                f'"{var}"{COLORS.CEND} in {COLORS.blue}"{path}"'
                f'{COLORS.CEND} does not exist in path {Path().absolute()} with content {os.listdir(os.getcwd())}.')
            if create_flag is True:
                create_path(path)
            else:
                exit(1)


def check_file_setting(*args, create_flag: bool = False):
    frame = inspect.currentframe().f_back
    s = inspect.getframeinfo(frame).code_context[0]
    r = re.search(r"\((.*)\)", s).group(1)
    var_names = r.split(", ")
    print(f'*** --- Check file setting --- ****')
    for i, (var, file) in enumerate(zip(var_names, args)):
        if os.path.isfile(file) is True:
            print(
                f'{COLORS.green}Setting:{COLORS.CEND} {COLORS.blue}File "{var}"{COLORS.CEND} is set as: '
                f'{COLORS.blue}"{file}"{COLORS.CEND} and exists.')
        else:
            print(
                f'{COLORS.CRED}Error:{COLORS.CEND} {COLORS.blue}File_variable "{var}"{COLORS.CEND} in {COLORS.blue}"{file}"'
                f'{COLORS.CEND} does not exist in path {Path().absolute()} with content {os.listdir(os.getcwd())}.')
            if create_flag is True:
                create_files(file)
            else:
                exit(1)


def create_path(*args):
    for arg in args:
        if not os.path.exists(arg):
            print(f'{COLORS.green}Create Folder:{COLORS.CEND} {arg}')
            os.makedirs(arg, exist_ok=True)


def create_files(*args):
    for file in args:
        if os.path.exists(file):
            print(f'{COLORS.green}File:{COLORS.CEND} {file} does exist.')
        else:
            print(
                f'{COLORS.CRED}File: {COLORS.CEND}  {file} does not exist. '
                f'Create a new one under {COLORS.green}{file}{COLORS.CEND}')
            with open(file, 'w') as write_file:
                if os.path.basename(file) == os.path.basename(CI_CONFIG.get_file_path("ci_files", "eof_file")):
                    write_file.write(f'y\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\n')


def delete_files_in_path(*args: Path):
    """
    Remove Structure
    Args:
        *args ():
    """
    print(f'\n**** Delete folder ****\n')
    for arg in args:
        print(f'{COLORS.green}Delete files:{COLORS.CEND} {arg}')
        for filename in os.listdir(arg):
            file_path = os.path.join(arg, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))


def delete_spec_file(root: str = None, pattern: str = None):
    """

    Args:
        root ():
        pattern ():
    """
    if root is not None and pattern is not None:
        for filename in os.listdir(root):
            file = os.path.join(root, filename)
            if os.path.isfile(file) and filename.find(pattern) > -1:
                os.remove(file)


# TODO: Check unused methods
def delete_files_path(root: str = None, pattern: str = None, subfolder: bool = False):
    if subfolder is True:
        files = glob.glob(f'{root}/**/*{pattern}', recursive=True)
    else:
        files = glob.glob(f'{root}/**/*{pattern}')
    print(f'Remove files path {root} with {pattern}')
    for file in files:
        os.remove(file)


def remove_files(file_list: list = None):
    if file_list is not None:
        for file in file_list:
            if os.path.exists(file):
                if os.path.isfile(file) is True:
                    os.remove(file)
                    print(f'Remove file: {file}')
                else:
                    print(f'File {file} does not exist')


def remove_path(path_list: list = None):
    if path_list is not None:
        for path in path_list:
            if os.path.isdir(path) is True:
                os.rmdir(path)
                print(f'Remove folder: {path}')
            else:
                print(f'Path {path} does not exist.')


def prepare_data(source_target_dict: dict,
                 del_flag: bool = False):
    """
    Prepare Result:
        Args:
        file_path_dict (): {dst:src}
        del_flag (): True: delete files if True, dont delete files if False
    """
    print(f'\n{COLORS.blue}**** Prepare Data ****{COLORS.CEND}')
    for source, target_path in source_target_dict.items():
        if not os.path.exists(target_path):
            print(f'Create path: {target_path}')
            os.makedirs(target_path)
        if os.path.isfile(source) is True:
            path, file_name = os.path.split(source)
            target = os.path.join(target_path, file_name)
            shutil.copyfile(source, target)
            print(
                f'Result file {COLORS.blue}{source}{COLORS.CEND} '
                f'was copied to {COLORS.blue}{target}{COLORS.CEND}'
            )
            if del_flag is True:
                remove_files([source])
        if os.path.isdir(source) is True:
            distutils.dir_util.copy_tree(source, str(target_path))
            print(
                f'Result Folder {COLORS.blue}{source}{COLORS.CEND} '
                f'was copied to {COLORS.blue}{target_path}{COLORS.CEND}'
            )
            if del_flag is True:
                remove_path([source])
