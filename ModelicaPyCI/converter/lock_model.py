import argparse
import os
from pathlib import Path
from ModelicaPyCI.load_global_config import CI_CONFIG
from ModelicaPyCI.utils import logger

FLAG = '__Dymola_LockedEditing="Model from IBPSA");'


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
        line = line.replace("\n", "")
        if line.endswith("package") or line.find("UsersGuide") > -1:
            continue
        mo = line.replace(".", os.sep).strip()
        model_list.append(Path(mo + ".mo"))
    return model_list


def call_lock_model():
    """
    lock models
    """
    model_list = _sort_whitelist_model()
    for model in model_list:
        if model.is_file():
            model_contents, flag_exists = get_last_line(model_file=model)
            if not flag_exists:
                new_content = lock_model(model, model_contents)
                write_lock_model(model, new_content)
            else:
                logger.info(f'Already locked: {model}')
                continue
        else:
            logger.error(f'\n{model} file does not exist.')
            continue


def get_last_line(model_file):
    """
    Search for each model  for the __Dymola_LockedEditing="Model from IBPSA"); flag
    Args:
        model_file (): file of a model
    Returns:
    """
    flag_tag = False
    with open(model_file, "r") as file:
        model_parts = file.readlines()
    for line in model_parts:
        if line.find(FLAG) > -1:
            flag_tag = True
    return model_parts, flag_tag


def lock_model(model, content):
    model_name = model.stem
    last_entry = content[len(content) - 1]
    flag = f'   {FLAG}'
    old_html_flag = '</html>"));'
    new_html_flag = '</html>"),  \n' + flag
    old = ');'
    new = ', \n' + flag
    if last_entry.find(model_name) > -1 and last_entry.find("end") > -1:
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
    logger.info("lock object: %s", model)
    with open(model, "w") as file:
        file.writelines(new_content)


def parse_args():
    parser = argparse.ArgumentParser(description='Lock models.')
    return parser.parse_args()


if __name__ == '__main__':
    import os
    #os.chdir(r"D:\04_git\AixLib")
    #os.environ["CI_PYTHON_CONFIG_FILE"] = r"D:\04_git\AixLib\ci\config\modelica_py_ci_config.toml"

    args = parse_args()
    call_lock_model()
