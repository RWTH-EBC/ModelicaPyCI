import inspect
import re
import os
import shutil
import glob
from pathlib import Path
import argparse
import distutils.dir_util

from ModelicaPyCI.config import CI_CONFIG
COLOR = CI_CONFIG.color


def check_arguments_settings(*args):
    frame = inspect.currentframe().f_back
    s = inspect.getframeinfo(frame).code_context[0]
    r = re.search(r"check_arguments_settings\((.*)\)", s).group(1)
    var_names = r.split(",")
    print(f'*** --- Argument setting --- ****')
    for i, (var, val) in enumerate(zip(var_names, args)):
        if val is None:
            print(
                f'{COLOR.CRED}Error:{COLOR.CEND} {COLOR.blue}Variable "{var.strip()}"{COLOR.CEND} has value '
                f'{COLOR.CRED}"{val}". "{var}"{COLOR.CEND} is not set!')
            exit(1)
        else:
            print(
                f'{COLOR.green}Setting:{COLOR.CEND} {COLOR.blue}Variable "{var.strip()}" {COLOR.CEND} is set as: '
                f'{COLOR.blue}"{val}"{COLOR.CEND}')


def check_path_setting(*args: Path, create_flag: bool = False):
    frame = inspect.currentframe().f_back
    s = inspect.getframeinfo(frame).code_context[0]
    r = re.search(r"\((.*)\)", s).group(1)
    var_names = r.split(", ")
    print(f'*** --- Check path setting --- ****')
    for i, (var, path) in enumerate(zip(var_names, args)):
        if os.path.isdir(path) is True:
            print(
                f'{COLOR.green}Setting:{COLOR.CEND} {COLOR.blue}Path variable "{var}"{COLOR.CEND} is set as: '
                f'{COLOR.blue}"{path}"{COLOR.CEND} and exists.')
        else:
            print(
                f'{COLOR.CRED}Error:{COLOR.CEND} {COLOR.blue}Path variable "{var}"{COLOR.CEND} in {COLOR.blue}"{path}"'
                f'{COLOR.CEND} does not exist.')
            """if var == "CI_CONFIG.whitelist_scripts.ci_dir":
                print(f"If filter_whitelist_flag is True, a file must be stored under {path}.")
                exit(1)"""
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
                f'{COLOR.green}Setting:{COLOR.CEND} {COLOR.blue}File "{var}"{COLOR.CEND} is set as: '
                f'{COLOR.blue}"{file}"{COLOR.CEND} and exists.')
        else:
            print(
                f'{COLOR.CRED}Error:{COLOR.CEND} {COLOR.blue}File_variable "{var}"{COLOR.CEND} in {COLOR.blue}"{file}"'
                f'{COLOR.CEND} does not exist.')
            if create_flag is True:
                create_files(file)
            else:
                exit(1)


def create_path(*args):
    print(f'\n**** Create folder ****')
    for arg in args:
        print(f'{COLOR.green}Create Folder:{COLOR.CEND} {arg}')
        os.makedirs(arg, exist_ok=True)


def create_files(*args):
    for file in args:
        if os.path.exists(file):
            print(f'{COLOR.green}File:{COLOR.CEND} {file} does exist.')
        else:
            print(
                f'{COLOR.CRED}File: {COLOR.CEND}  {file} does not exist. '
                f'Create a new one under {COLOR.green}{file}{COLOR.CEND}')
            with open(file, 'w') as write_file:
                if os.path.basename(file) == os.path.basename(CI_CONFIG.config_ci.eof_file):
                    write_file.write(f'y\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\n')


def delete_files_in_path(*args: Path):
    """
    Remove Structure
    Args:
        *args ():
    """
    print(f'\n**** Delete folder ****\n')
    for arg in args:
        print(f'{COLOR.green}Delete files:{COLOR.CEND} {arg}')
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


def prepare_data(source_target_dict: dict = None,
                 del_flag: bool = False):
    """
    Prepare Result:
        Args:
        file_path_dict (): {dst:src}
        del_flag (): True: delete files if True, dont delete files if False
    """
    print(f'\n{COLOR.blue}**** Prepare Data ****{COLOR.CEND}')
    if source_target_dict is not None:
        for source in source_target_dict:
            target_path = source_target_dict[source]
            if not os.path.exists(target_path):
                print(f'Create path: {target_path}')
                os.makedirs(target_path)
            if os.path.isfile(source) is True:
                path, file_name = os.path.split(source)
                target = os.path.join(target_path, file_name)
                print(
                    f'Result file {COLOR.blue}{source}{COLOR.CEND} '
                    f'was moved to {COLOR.blue}{target}{COLOR.CEND}'
                )
                shutil.copyfile(source, target)
                if del_flag is True:
                    remove_files([source])
            if os.path.isdir(source) is True:
                print(
                    f'Result Folder {COLOR.blue}{source}{COLOR.CEND} '
                    f'was moved to {COLOR.blue}{target_path}{COLOR.CEND}'
                )
                distutils.dir_util.copy_tree(source, str(target_path))
                if del_flag is True:
                    remove_path([source])
