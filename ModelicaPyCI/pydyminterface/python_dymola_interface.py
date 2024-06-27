import os
import sys
import time
from pathlib import Path

from ebcpy import DymolaAPI

from ModelicaPyCI.utils import logger


def load_dymola_api(
        packages: list,
        startup_mos: str = None,
        min_number_of_unused_licences: int = 1
) -> DymolaAPI:
    if min_number_of_unused_licences > 0:
        check_enough_licenses_available(min_number_of_unused_licences=min_number_of_unused_licences)
    dymola_api = _start_dymola_api(
        packages=packages, startup_mos=startup_mos
    )
    logger.info(f'Using Dymola port {str(dymola_api.dymola._portnumber)}.')
    dymola_api.dymola.ExecuteCommand("Advanced.TranslationInCommandLog:=true;")
    return dymola_api


def check_enough_licenses_available(min_number_of_unused_licences: int = 1) -> bool:
    lic = os.environ.get("DYMOLA_RUNTIME_LICENSE", "50064@license2.rz.rwth-aachen.de")
    if "@" in lic:
        port, url = lic.split("@")
    else:
        if not os.path.isfile(lic):
            raise FileNotFoundError(f"License file not found: {lic}")
        else:
            with open(lic, "r") as file:
                lines = file.readlines()
            for line in lines:
                if line.startswith("SERVER"):
                    url, port = line.replace("SERVER ", "").split(" ANY ")
                    break
            else:
                raise ValueError(
                    "Did not find SERVER line in license file content: %s" % "\n".join(lines)
                )
    port = int(port)
    server_is_available = check_server_connection(url=url, port=port)
    if not server_is_available:
        raise ConnectionError("Can't reach license server!")
    lic_counter = 0
    n_licenses = get_number_of_unused_licenses(url=url, port=port)
    while n_licenses < min_number_of_unused_licences:
        msg = (f'Only {n_licenses} Dymola licenses are available, '
               f'mininum number required is set to {min_number_of_unused_licences}.')
        logger.error('%s. Check Dymola license after 180.0 seconds', msg)
        time.sleep(180.0)
        n_licenses = get_number_of_unused_licenses(url=url, port=port)
        lic_counter += 1
        if lic_counter > 10:
            logger.error(f'%s. Stopping, please try again later.', msg)
            exit(1)
    logger.info(f'Enough Dymola licenses (%s) are available.', n_licenses)


def get_number_of_unused_licenses(url, port):
    from ModelicaPyCI.utils import os_system_with_return
    licenses = os_system_with_return(f"lmutil lmstat -c {port}@{url} -a")
    _start_line = "Users of DymolaStandard:  "
    for line in licenses.split("\n"):
        if not line.startswith(_start_line):
            continue
        # line = "(Total of 93 licenses issued;  Total of 36 licenses in use)"
        for delete in [
            _start_line, "Total of", "licenses", "issued",
            "in", "use", "(", ")", " "
        ]:
            line = line.replace(delete, "")
        # line = "93;36"
        num_licenses, num_in_use = line.split(";")
        return int(num_licenses) - int(num_in_use)
    logger.error("Could not find line '%s' in content %s", _start_line, licenses)
    return 0


def check_server_connection(url, port, timeout=5):
    import socket
    try:
        # Create a socket object
        with socket.create_connection((url, port), timeout) as sock:
            logger.info(f"Successfully connected to %s on port %s", url, port)
            return True
    except (socket.timeout, socket.error) as e:
        logger.error(f"Failed to connect to %s on port %s: %s", url, port, e)
        return False


def _start_dymola_api(packages: list, startup_mos: str = None) -> DymolaAPI:
    if "win" in sys.platform:
        dymola_exe_path = None
    else:
        dymola_exe_path = "/usr/local/bin/dymola"
    return DymolaAPI(
        working_directory=os.getcwd(),
        packages=packages,
        dymola_exe_path=dymola_exe_path,
        model_name=None,
        show_window=False,
        mos_script_pre=startup_mos
    )


def add_libraries_to_load_from_mos_to_modelicapath(startup_mos_path):
    libraries_to_load = []
    with open(startup_mos_path, "r") as file:
        lines = file.readlines()
    for line in lines:
        if not line.startswith("openModel("):
            continue
        for delete_string in ["openModel(", ");\n", "'", '"']:
            line = line.replace(delete_string, "")
        path = Path(line.split(",")[0])
        libraries_to_load.append(path.parents[1].as_posix())

    if "MODELICAPATH" in os.environ:
        libraries_to_load.append(os.environ["MODELICAPATH"])
    os.environ["MODELICAPATH"] = ":".join(libraries_to_load)
    logger.info("Changed MODELICAPATH to: %s", os.environ["MODELICAPATH"])
    return libraries_to_load
