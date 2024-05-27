from ModelicaPyCI.config import ColorConfig
import platform
from pathlib import Path
import time
import os
import sys

COLORS = ColorConfig()


class PythonDymolaInterface:

    def __init__(
            self,
            dymola: classmethod = None,
            dymola_exception: classmethod = None
    ):
        super().__init__()
        self.dymola = dymola
        self.dymola_exception = dymola_exception
        if self.dymola is not None:
            self.dymola.ExecuteCommand("Advanced.TranslationInCommandLog:=true;")

    def dym_check_lic(self):
        """
            Check dymola license.
        """
        lic_counter = 0
        dym_sta_lic_available = self.dymola.ExecuteCommand('RequestOption("Standard");')
        while dym_sta_lic_available is False:
            print(
                f'{COLORS.CRED} No Dymola License is available {COLORS.CEND} \n Check Dymola license after 180.0 seconds')
            self.dymola.close()
            time.sleep(180.0)
            dym_sta_lic_available = self.dymola.ExecuteCommand('RequestOption("Standard");')
            lic_counter += 1
            if lic_counter > 10:
                if dym_sta_lic_available is False:
                    print(f'There are currently no available Dymola licenses available. Please try again later.')
                    self.dymola.close()
                    exit(1)
        print(
            f'2: Using Dymola port {str(self.dymola._portnumber)} \n {COLORS.green} Dymola License is available {COLORS.CEND}')

    def load_library(self, library_package_mo: Path = None, additional_libraries_to_load: dict = None):
        """
        Open library in dymola and  checks if the library was opened correctly.
        """
        if library_package_mo is not None:
            print(f'Library path: {library_package_mo}')
            pack_check = self.dymola.openModel(str(library_package_mo))
            if pack_check is True:
                print(
                    f'{COLORS.green}Found {library_package_mo.parent} Library and start checks. {COLORS.CEND}\n')
            elif pack_check is False:
                print(
                    f'{COLORS.CRED}Error: {COLORS.CEND} Library path is wrong.Please check the path of {library_package_mo} library path.')
                exit(1)
        else:
            print(f'Library path is not set.')
            exit(1)
        if additional_libraries_to_load is None:
            return
        for library in additional_libraries_to_load:
            lib_path = Path(additional_libraries_to_load[library], library, "package.mo")
            load_add_bib = self.dymola.openModel(lib_path)
            if load_add_bib is True:
                print(f'{COLORS.green}Load library {library}:{COLORS.CEND} {lib_path}')
            else:
                print(
                    f'{COLORS.CRED}Error:{COLORS.CEND} Load of library {library} with path {lib_path} failed!')
                exit(1)

def set_environment_path(dymola_version):
    """
    Checks the Operating System, Important for the Python-Dymola Interface
    Args:
        dymola_version (): Version von dymola-docker image (e.g. 2022)
    Set path of python dymola interface for windows or linux
    """
    if platform.system() == "Windows":
        set_environment_variables("PATH",
                                  os.path.join(os.path.abspath('.'), "Resources", "Library",
                                               "win32"))
        sys.path.insert(0, os.path.join('C:\\',
                                        'Program Files',
                                        'Dymola ' + dymola_version,
                                        'Modelica',
                                        'Library',
                                        'python_interface',
                                        'dymola.egg'))
    else:
        set_environment_variables("LD_LIBRARY_PATH",
                                  os.path.join(os.path.abspath('.'), "Resources", "Library",
                                               "linux32") + ":" +
                                  os.path.join(os.path.abspath('.'), "Resources", "Library",
                                               "linux64"))
        sys.path.insert(0, os.path.join('/opt',
                                        'dymola-' + dymola_version + '-x86_64',
                                        'Modelica',
                                        'Library',
                                        'python_interface',
                                        'dymola.egg'))
    print(f'Operating system {platform.system()}')
    sys.path.append(os.path.join(os.path.abspath('.'), "..", "..", "BuildingsPy"))


def load_dymola_python_interface(dymola_version: int = 2022):
    """
    Load dymola python interface and dymola exception
    Args:
        dymola_version ():
    Returns:
    """
    set_environment_path(dymola_version=dymola_version)
    from dymola.dymola_interface import DymolaInterface
    from dymola.dymola_exception import DymolaException
    print(f'1: Starting Dymola instance')
    if platform.system() == "Windows":
        dymola = DymolaInterface()
        dymola_exception = DymolaException()
    else:
        dymola = DymolaInterface(dymolapath="/usr/local/bin/dymola")
        dymola_exception = DymolaException()
    dymola.cd(os.getcwd())
    return dymola, dymola_exception


def set_environment_variables(var, value):
    if var in os.environ:
        if platform.system() == "Windows":
            os.environ[var] = value + ";" + os.environ[var]
        else:
            os.environ[var] = value + ":" + os.environ[var]
    else:
        os.environ[var] = value
