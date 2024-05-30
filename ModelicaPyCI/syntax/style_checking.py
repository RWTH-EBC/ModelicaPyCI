import argparse
import codecs
from ModelicaPyCI.config import CI_CONFIG, ColorConfig
from ModelicaPyCI.pydyminterface.model_management import ModelManagement
from ModelicaPyCI.pydyminterface import python_dymola_interface
from ModelicaPyCI.structure import sort_mo_model as mo
from ModelicaPyCI.structure import config_structure
from pathlib import Path

COLORS = ColorConfig()


class StyleCheck:

    def __init__(self,
                 dymola,
                 library: str,
                 dymola_version: int,
                 library_package_mo: Path,
                 additional_libraries_to_load: dict = None,
                 ):
        """
        Class to Check the style of packages and models.
        Export HTML-Log File.
        Args:
            dymola (): dymola_python interface class
            library (): library to test
            dymola_version (): dymola version (e.g. 2022)
        """
        self.library = library
        self.dymola_version = dymola_version
        self.additional_libraries_to_load = additional_libraries_to_load
        self.library_package_mo = library_package_mo
        self.dymola = dymola
        self.dymola.ExecuteCommand("Advanced.TranslationInCommandLog:=true;")

    def __call__(self):
        dym_int = python_dymola_interface.PythonDymolaInterface(
            dymola=self.dymola,
        )
        # dym_int.dym_check_lic()
        dym_int.load_library(
            library_package_mo=self.library_package_mo,
            additional_libraries_to_load=self.additional_libraries_to_load
        )

    def read_log(self, file):
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
                print(f'{COLORS.CRED}Error in model: {COLORS.CEND}{line.lstrip()}')
                error_list.append(line)
        log_file.close()
        config_structure.prepare_data(source_target_dict={file: CI_CONFIG.get_file_path("result", "syntax_dir")})
        if len(error_list) == 0:
            print(f'{COLORS.green}Style check for library {self.library} was successful{COLORS.CEND}')
            return 0
        elif len(error_list) > 0:
            print(f'{COLORS.CRED}Test failed. Look in {self.library}_StyleErrorLog.html{COLORS.CEND}')
            return 1


def parse_args():
    parser = argparse.ArgumentParser(description="Check the Style of Packages")
    check_test_group = parser.add_argument_group("Arguments to start style tests")
    check_test_group.add_argument("--library", default="AixLib",
                                  help="Path where top-level package.mo of the library is located")
    check_test_group.add_argument("--dymola-version", default="2022",
                                  help="Version of Dymola(Give the number e.g. 2022")
    check_test_group.add_argument("--changed-flag", action="store_true")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    dym = python_dymola_interface.load_dymola_python_interface(dymola_version=args.dymola_version)
    dymola = dym
    LIBRARY_PACKAGE_MO = Path(CI_CONFIG.library_root).joinpath(args.library, "package.mo")

    mm = ModelManagement(dymola=dymola,
                         dymola_version=args.dymola_version)
    mm.load_model_management()
    CheckStyle = StyleCheck(dymola=dymola,
                            library=args.library,
                            dymola_version=args.dymola_version,
                            library_package_mo=LIBRARY_PACKAGE_MO,
                            additional_libraries_to_load=None)
    CheckStyle()
    model_list = mo.get_option_model(library=args.library,
                                     package="",
                                     changed_flag=args.changed_flag)
    logfile = mm.mm_style_check(models_list=model_list,
                                library=args.library,
                                changed_flag=args.changed_flag)
    var = CheckStyle.read_log(file=logfile)
    exit(var)
