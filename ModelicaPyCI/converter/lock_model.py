import argparse
import os
from pathlib import Path
from ModelicaPyCI.load_global_config import CI_CONFIG
from ModelicaPyCI.utils import logger


def _sort_whitelist_model():
    """
    Read whitelist and return a list.
    Sort List of models.
    Returns:
        model_list (): return a list of models to lock
    """
    html_file = CI_CONFIG.get_file_path("whitelist", "ibpsa_file")
    with open(html_file, "r") as file:
        whitelist_lines = file.readlines()
    model_list = []
    for line in whitelist_lines:
        if len(line) == 1 or line.find("package.mo") > -1 or line.find("package.order") > -1 or line.find(
                "UsersGuide") > -1:
            continue
        else:
            mo = line.replace(".", os.sep, line.count(".") - 1).lstrip()
            mo = mo.strip()
            model_list.append(mo)
    return model_list


def call_lock_model():
    """
    lock models
    """
    mo_li = _sort_whitelist_model()
    for model in mo_li:
        if Path(model).is_file():
            result = get_last_line(model_file=model)
            if len(result[0]) == 0:
                continue
            if result[1] is False:
                new_content = lock_model(model, result[0])
                write_lock_model(model, new_content)
            else:
                logger.info(f'Already locked: {model}')
                continue
        else:
            logger.error(f'\n{model} File does not exist.')
            continue

def get_last_line(model_file):
    """
    Search for each model  for the __Dymola_LockedEditing="Model from IBPSA"); flag
    Args:
        model_file (): file of a model
    Returns:
    """
    model_part = []
    flag = '__Dymola_LockedEditing="Model from IBPSA");'
    flag_tag = False
    try:
        if Path(model_file).is_file():
            infile = open(model_file, "r")
            for lines in infile:
                model_part.append(lines)
                if lines.find(flag) > -1:
                    flag_tag = True
            infile.close()
            return model_part, flag_tag
        else:
            logger.error(f'\n{model_file}\nFile does not exist.')
    except IOError:
        logger.error(f'Error: File {model_file} does not exist.')

def lock_model(model, content):
    mo = model[model.rfind(os.sep) + 1:model.rfind(".mo")]
    last_entry = content[len(content) - 1]
    flag = '   __Dymola_LockedEditing="Model from IBPSA");'
    old_html_flag = '</html>"));'
    new_html_flag = '</html>"),  \n' + flag
    old = ');'
    new = ', \n' + flag
    if last_entry.find(mo) > -1 and last_entry.find("end") > -1:
        flag_lines = content[len(content) - 2]
        if flag_lines.isspace():
            flag_lines = content[len(content) - 3]
            del content[len(content) - 2]
        if flag_lines.find(old_html_flag) > -1:
            flag_lines = flag_lines.replace(old_html_flag, new_html_flag)
        elif flag_lines.find(old) > -1:
            flag_lines = flag_lines.replace(old, new)
        del content[len(content) - 2]
        content.insert(len(content) - 1, flag_lines)
        return content
    else:
        flag_lines = content[len(content) - 1]
        if flag_lines.find(old_html_flag) > -1:
            flag_lines = flag_lines.replace(old_html_flag, new_html_flag)
        elif flag_lines.find(old) > -1:
            flag_lines = flag_lines.replace(old, new)
        del content[len(content) - 1]
        content.insert(len(content), flag_lines)
        return content


def write_lock_model(model, new_content):
    try:
        logger.info("lock object: " + model)
        outfile = open(model, 'w')
        new_content = (' '.join(new_content))
        outfile.write(new_content)
        outfile.close()
    except IOError:
        logger.error(f'Error: File {model} does not exist.')
        exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description='Lock models.')
    unit_test_group = parser.add_argument_group("arguments to run class LockModel")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    call_lock_model()
