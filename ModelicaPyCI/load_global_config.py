import os
from pathlib import Path

from ModelicaPyCI.config import CIConfig, load_toml_config
from ModelicaPyCI.utils import logger


def load_config():
    global CI_CONFIG

    env_var = "CI_PYTHON_CONFIG_FILE"
    if "CI_CONFIG" not in locals():
        if env_var in os.environ:
            config_file = Path(os.environ["CI_PYTHON_CONFIG_FILE"])
            logger.info(f"Using CI_PYTHON_CONFIG_FILE located at {config_file}")
            return load_toml_config(path=config_file)
        logger.warning("No variable CI_PYTHON_CONFIG_FILE defined, using default config.")
        return CIConfig()  # Use default
    return CI_CONFIG


CI_CONFIG = load_config()
