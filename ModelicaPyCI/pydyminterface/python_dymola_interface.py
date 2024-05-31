import os
import sys
import time

from ebcpy import DymolaAPI

from ModelicaPyCI.config import ColorConfig

COLORS = ColorConfig()


def load_dymola_api(dymola_version: str, packages: list, requires_license: bool = True) -> DymolaAPI:
    dymola_api = _start_dymola_api(dymola_version=dymola_version, packages=packages)
    if requires_license:
        lic_counter = 0
        dym_sta_lic_available = dymola_api.license_is_available
        while not dym_sta_lic_available:
            print(f'{COLORS.CRED} No Dymola License is available {COLORS.CEND} \n '
                  f'Check Dymola license after 180.0 seconds')
            dymola_api.close()
            time.sleep(180.0)
            dymola_api = _start_dymola_api(dymola_version=dymola_version, packages=packages)
            dym_sta_lic_available = dymola_api.license_is_available
            lic_counter += 1
            if lic_counter > 10:
                print(f'There are currently no available Dymola licenses available. Please try again later.')
                dymola_api.close()
                exit(1)
        print(f'2: Using Dymola port {str(dymola_api.dymola._portnumber)} \n '
              f'{COLORS.green} Dymola License is available {COLORS.CEND}')

    dymola_api.dymola.ExecuteCommand("Advanced.TranslationInCommandLog:=true;")
    return dymola_api


def _start_dymola_api(dymola_version: str, packages: list) -> DymolaAPI:
    if "win" in sys.platform:
        dymola_exe_path = None
    else:
        dymola_exe_path = "/usr/local/bin/dymola"
    return DymolaAPI(
        working_directory=os.getcwd(),
        packages=packages,
        #dymola_version=str(dymola_version),
        dymola_exe_path=dymola_exe_path,
        model_name=None,
        show_window=True
    )
