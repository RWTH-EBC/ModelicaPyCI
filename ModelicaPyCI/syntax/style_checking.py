import argparse
import codecs

from ModelicaPyCI.load_global_config import CI_CONFIG
from ModelicaPyCI.pydyminterface.model_management import ModelManagement
from ModelicaPyCI.pydyminterface import python_dymola_interface
from ModelicaPyCI.structure import sort_mo_model as mo
from ModelicaPyCI.structure import config_structure
from pathlib import Path


def read_log(library, file):
    """
    Args:
        file (): Read log file, if error exist variable 1 else 0
    """
    log_file = codecs.open(file, "r", encoding='utf8')
    error_list = list()
    for line in log_file:
        line = line.strip()
        if line.find("Check ok") > -1 or line.find("Library style check log") > -1 or len(line) == 0:
            continue
        else:
            logger.error(f'Error in model: {line.lstrip()}')
            error_list.append(line)
    log_file.close()
    config_structure.prepare_data(source_target_dict={file: CI_CONFIG.get_file_path("result", "syntax_dir")})
    if len(error_list) == 0:
        logger.info(f'Style check for library {library} was successful')
        return 0
    elif len(error_list) > 0:
        logger.error(f'Test failed. Look in {library}_StyleErrorLog.html')
        return 1


def parse_args():
    parser = argparse.ArgumentParser(description="Check the Style of Packages")
    check_test_group = parser.add_argument_group("Arguments to start style tests")
    check_test_group.add_argument("--library", default="AixLib",
                                  help="Path where top-level package.mo of the library is located")
    check_test_group.add_argument(
        "--min-number-of-unused-licences",
        default=1,
        help="Number of unused licences for Dymola to start. "
             "Used to avoid license blocking of real users. "
             "Set to 0 to disable this check."
    )
    check_test_group.add_argument(
        "--startup-mos",
        default=None,
        help="Possible startup-mos script to e.g. load additional libraries"
    )
    check_test_group.add_argument("--changed-flag", action="store_true")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    LIBRARY_PACKAGE_MO = Path(CI_CONFIG.library_root).joinpath(args.library, "package.mo")
    dymola_api = python_dymola_interface.load_dymola_api(
        packages=[LIBRARY_PACKAGE_MO],
        min_number_of_unused_licences=args.min_number_of_unused_licences,
        startup_mos=args.startup_mos
    )

    mm = ModelManagement(dymola_api=dymola_api)

    model_list = mo.get_model_list(library=args.library,
                                   package="",
                                   changed_flag=args.changed_flag)
    logfile = mm.mm_style_check(models_list=model_list,
                                library=args.library,
                                changed_flag=args.changed_flag)
    var = read_log(file=logfile, library=args.library)
    exit(var)
