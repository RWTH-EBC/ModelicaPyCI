import argparse
from ModelicaPyCI.structure import config_structure
from ModelicaPyCI.api_script.api_github import clone_repository
from ModelicaPyCI.structure.sort_mo_model import ModelicaModel
from ModelicaPyCI.config import CI_CONFIG


def write_whitelist(model_list):
    """
    write a whitelist with models
    Args:
        model_list (): models on the whitelist
    """

    file = open(CI_CONFIG.whitelist.html_file, "w")
    for model in model_list:
        file.write("\n" + model + ".mo" + "\n")
    file.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description='Run HTML correction on files')
    parser.add_argument("--whitelist-library",
                        default="IBPSA",
                        help="Library that is written to a whitelist")
    parser.add_argument("--git-url",
                        default="https://github.com/ibpsa/modelica-ibpsa.git",
                        help="url repository of library for whitelist")
    parser.add_argument("--root-whitelist-library",
                        help="library on a whitelist")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    config_structure.create_path(CI_CONFIG.config_ci.dir)
    config_structure.create_files(CI_CONFIG.config_ci.exit_file)
    mo = ModelicaModel()
    config_structure.create_path(CI_CONFIG.whitelist.ci_dir)
    config_structure.create_files(CI_CONFIG.whitelist.html_file)
    clone_repository(clone_into_folder=args.root_whitelist_library, git_url=args.git_url)
    MODEL_LIST = mo.get_models(library=args.whitelist_library,
                               path=args.root_whitelist_library,
                               simulate_flag=False,
                               extended_ex_flag=False)
    write_whitelist(model_list=MODEL_LIST)
    config_structure.prepare_data(
        source_target_dict={CI_CONFIG.whitelist.html_file: CI_CONFIG.result.whitelist_dir}
    )
