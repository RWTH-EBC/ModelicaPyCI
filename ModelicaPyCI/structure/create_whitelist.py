import argparse
from ModelicaPyCI.structure import config_structure
from ModelicaPyCI.api_script.api_github import clone_repository
from ModelicaPyCI.structure import sort_mo_model as mo
from ModelicaPyCI.config import CI_CONFIG, ColorConfig

COLORS = ColorConfig()


def write_whitelist(model_list, library: str, whitelist_library: str):
    file = open(CI_CONFIG.get_file_path("whitelist", "ibpsa_file"), "w")
    for model in model_list:
        model = model.replace(whitelist_library, library)
        file.write("\n" + model + ".mo" + "\n")
    file.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description='Run HTML correction on files')
    parser.add_argument("--library",
                        help="Library that is written to a whitelist")
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

    config_structure.create_path(CI_CONFIG.get_dir_path("ci_files"))
    config_structure.create_files(CI_CONFIG.get_file_path("ci_files", "exit_file"))
    config_structure.create_path(CI_CONFIG.get_dir_path("whitelist"))
    config_structure.create_files(CI_CONFIG.get_file_path("whitelist", "ibpsa_file"))
    clone_repository(clone_into_folder=args.root_whitelist_library, git_url=args.git_url)
    MODEL_LIST, _ = mo.get_models(library=args.whitelist_library,
                                  path=args.root_whitelist_library,
                                  simulate_flag=False,
                                  extended_ex_flag=False)
    write_whitelist(model_list=MODEL_LIST, library=args.library, whitelist_library=args.whitelist_library)
    config_structure.prepare_data(
        source_target_dict={
            CI_CONFIG.get_file_path("whitelist", "ibpsa_file"): CI_CONFIG.get_file_path("result", "whitelist_dir")
        }
    )
