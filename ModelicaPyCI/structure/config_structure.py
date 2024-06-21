import distutils.dir_util
import glob
import os
import shutil
from pathlib import Path

from ModelicaPyCI.utils import logger


def check_arguments_settings(**kwargs):
    logger.info(f'*** --- Argument setting --- ****')
    for var, val in kwargs.items():
        if val is None:
            logger.error(
                f'Variable "{var.strip()}" has value '
                f'"{val}". "{var}" is not set!'
            )
            exit(1)
        else:
            logger.info(
                f'Setting: Variable "{var.strip()}"  is set as: '
                f'"{val}"'
            )


def check_path_setting(create_flag: bool = False, **kwargs):
    logger.info(f'*** --- Check path setting --- ****')
    for var, path in kwargs.items():
        if os.path.isdir(path) is True:
            logger.info(
                f'Setting: Path variable "{var}" is set as: '
                f'"{path}" and exists.')
        else:
            logger.error(
                f'Path variable '
                f'"{var}" in "{path}"'
                f' does not exist in path {Path().absolute()} with content {os.listdir(os.getcwd())}.')
            if create_flag is True:
                create_path(path)
            else:
                exit(1)


def check_file_setting(create_flag: bool = False, **kwargs):
    logger.info(f'*** --- Check file setting --- ****')
    for var, file in kwargs.items():
        if os.path.isfile(file) is True:
            logger.info(
                f'Setting: File "{var}" is set as: '
                f'"{file}" and exists.')
        else:
            logger.error(
                f'File_variable "{var}" in "{file}"'
                f' does not exist in path {Path().absolute()} with content {os.listdir(os.getcwd())}.')
            if create_flag is True:
                create_files(file)
            else:
                exit(1)


def create_path(*args):
    for arg in args:
        if not os.path.exists(arg):
            logger.info(f'Create Folder: {arg}')
            os.makedirs(arg, exist_ok=True)


def create_files(*args):
    for file in args:
        if os.path.exists(file):
            logger.info(f'File: {file} does exist.')
        else:
            logger.error(
                f'File: {file} does not exist. '
                f'Create a new one under {file}')
            with open(file, 'w') as write_file:
                pass


def delete_files_in_path(*args: Path):
    """
    Remove Structure
    Args:
        *args ():
    """
    logger.info(f'\n**** Delete folder ****\n')
    for arg in args:
        logger.info(f'Delete files: {arg}')
        for filename in os.listdir(arg):
            file_path = os.path.join(arg, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.error('Failed to delete %s. Reason: %s' % (file_path, e))


def delete_spec_file(root: str = None, pattern: str = None):
    if root is not None and pattern is not None:
        for filename in os.listdir(root):
            file = os.path.join(root, filename)
            if os.path.isfile(file) and filename.find(pattern) > -1:
                os.remove(file)


def prepare_data(source_target_dict: dict,
                 del_flag: bool = False):
    """
    Prepare Result:
        Args:
        file_path_dict (): {dst:src}
        del_flag (): True: delete files if True, dont delete files if False
    """
    logger.info(f'\n**** Prepare Data ****')
    for source, target_path in source_target_dict.items():
        if not os.path.exists(target_path):
            logger.info(f'Create path: {target_path}')
            os.makedirs(target_path)
        if os.path.isfile(source) is True:
            path, file_name = os.path.split(source)
            target = os.path.join(target_path, file_name)
            shutil.copyfile(source, target)
            logger.info(
                f'Result file {source} '
                f'was copied to {target}'
            )
            if del_flag is True:
                os.remove(source)
        if os.path.isdir(source) is True:
            distutils.dir_util.copy_tree(source, str(target_path))
            logger.info(
                f'Result Folder {source} '
                f'was copied to {target_path}'
            )
            if del_flag is True:
                shutil.rmtree(source)
