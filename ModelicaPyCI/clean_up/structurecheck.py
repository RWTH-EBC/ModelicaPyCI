import os
from pathlib import Path
import argparse

from ModelicaPyCI.config import CI_CONFIG, ColorConfig


def return_file_list():
    files_list = []
    file_dic = (vars(ci_config()))
    for file in file_dic:
        if file.find("_file") > -1:
            files_list.append(file_dic[file])
    return files_list


def return_file_dir():
    dir_list = []
    dir_dic = (vars(ci_config()))
    for dirs in dir_dic:
        if dirs.find("_dir") > -1:
            dir_list.append(dir_dic[dirs])
    return dir_list


def check_ci_folder():
    dir_list = return_file_dir()
    for directionary in dir_list:
        dir_check = Path(directionary)
        if dir_check.is_dir():
            print(f'Folder: {dir_check} exist.')
        else:
            print(f'Folder: {dir_check} does not exist and will be new created.')
            os.makedirs(directionary)


def check_ci_files():
    file_list = return_file_list()
    for file in file_list:
        file_check = Path(file)
        if file_check.is_file():
            print(f'File: {file} exist.')
        else:
            print(f'File: {file} does not exist and will be new created.')
            file_check.touch(exist_ok=True)


def _create_folder(path):
    try:
        if not os.path.exists(path):
            print(f'Create path: {path}')
            os.makedirs(path)
        else:
            print(f'Path "{path}" exist.')
    except FileExistsError:
        print(f'Find no folder')
        pass


def parse_args():
    parser = argparse.ArgumentParser(description="Config files for the CI")  # Configure the argument parser
    check_test_group = parser.add_argument_group("Arguments to build the CI structure")
    check_test_group.add_argument("--config-dir", default=False, action="store_true")
    check_test_group.add_argument("--create-path", default=False, action="store_true")
    return parser.parse_args()  # Parse the arguments


if __name__ == '__main__':
    args = parse_args()
    if args.create_path is True:
        if args.config_dir is True:
            _create_folder(path=CI_CONFIG.results.config_dir)
    check_ci_folder()
    check_ci_files()
