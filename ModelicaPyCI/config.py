import os
from typing import Union
from pathlib import Path
import toml

from pydantic import BaseModel, Field


class ResultConfig(BaseModel):
    dir: Path = Field(
        title="Result directory to be used for XYZ",
        default='dymola-ci-tests/result'
    )
    whitelist_dir: Path = 'dymola-ci-tests/result/ci_whitelist'
    config_dir: Path = 'dymola-ci-tests/result/configfiles'
    plot_dir: Path = 'dymola-ci-tests/result/charts'
    syntax_dir: Path = 'dymola-ci-tests/result/syntax'
    regression_dir: Path = 'dymola-ci-tests/result/regression'
    interact_ci_dir: Path = 'dymola-ci-tests/result/interact_CI'
    ci_template_dir: Path = 'dymola-ci-tests/result/ci_template'
    check_result_dir: Path = 'dymola-ci-tests/result/Dymola_check'
    OM_check_result_dir: Path = 'dymola-ci-tests/result/OM_check'


class ColorConfig(BaseModel):
    CRED: str = Field(
        description="Start ANSI escape code for red text",
        default=r'\033[91m'
    )
    CEND: str = Field(
        description="End ANSI escape code for colored text",
        default=r'\033[0m'
    )
    green: str = Field(
        description="Start ANSI escape code for green text",
        default=r'\033[0;32m'
    )
    yellow: str = Field(
        description="Start ANSI escape code for yellow text",
        default=r'\033[33m'
    )
    blue: str = Field(
        description="Start ANSI escape code for blue text",
        default=r'\033[44m'
    )


class FilesConfig(BaseModel):
    dir: Path = 'dymola-ci-tests/Configfiles'
    exit_file: Path = 'dymola-ci-tests/Configfiles/exit.sh'
    new_ref_file: Path = 'dymola-ci-tests/Configfiles/ci_new_ref_file.txt'
    new_create_ref_file: Path = 'dymola-ci-tests/Configfiles/ci_new_created_reference.txt'
    changed_file: Path = 'dymola-ci-tests/Configfiles/ci_changed_model_list.txt'
    ref_file: Path = 'dymola-ci-tests/Configfiles/ci_reference_list.txt'
    eof_file: Path = 'dymola-ci-tests/Configfiles/EOF.sh'


class WhitelistConfig(BaseModel):
    ci_dir: Path = "dymola-ci-tests/ci_whitelist"
    check_file: Path = 'dymola-ci-tests/ci_whitelist/ci_check_whitelist.txt'
    simulate_file: Path = 'dymola-ci-tests/ci_whitelist/ci_simulate_whitelist.txt'
    html_file: Path = 'dymola-ci-tests/ci_whitelist/rci_html_whitelist.txt'
    ref_file: Path = 'dymola-ci-tests/ci_whitelist/ci_reference_check_whitelist.txt'


class PlotConfig(BaseModel):
    chart_dir: str = 'dymola-ci-tests/charts'
    templates_chart_dir: str = 'Modelica-CI/templates/google_templates'
    templates_chart_file: str = 'Modelica-CI/templates/google_templates/google_chart.txt'
    templates_index_file: str = 'Modelica-CI/templates/google_templates/index.txt'
    templates_layout_file: str = 'Modelica-CI/templates/google_templates/layout_index.txt'


class ArtifactsConfig(BaseModel):
    dir: Path = 'dymola-ci-tests/templates/artifacts'
    library_ref_results_dir: Path = 'Resources/ReferenceResults/Dymola'
    library_resource_dir: Path = 'Resources/Scripts/Dymola'


class InteractConfig(BaseModel):
    dir: Path = 'dymola-ci-tests/interact_CI'
    show_ref_file: Path = 'dymola-ci-tests/interact_CI/show_ref.txt'
    update_ref_file: Path = 'dymola-ci-tests/interact_CI/update_ref.txt'


class CIConfig(BaseModel):
    dymola_ci_test_dir: str = 'dymola-ci-tests'
    dymola_python_test_dir: str = 'Modelica-CI'
    dymola_python_test_url: str = '--single-branch --branch 03_openModelica https://github.com/RWTH-EBC/Modelica-CI.git'

    result: ResultConfig = ResultConfig()
    color: ColorConfig = ColorConfig()
    config_ci: FilesConfig = FilesConfig()
    whitelist: WhitelistConfig = WhitelistConfig()
    artifacts: ArtifactsConfig = ArtifactsConfig()
    interact: InteractConfig = InteractConfig()


def load_toml_config(path: Union[Path, str]):
    with open(path, "r") as file:
        config = toml.load(file)
    return CIConfig(**config)


def save_toml_config(config: BaseModel, path: Path):
    with open(path, "w") as file:
        toml.dump(config.model_dump(), file)


def load_config():
    global CI_CONFIG

    env_var = "CI_PYTHON_CONFIG_FILE"
    if "CI_CONFIG" not in locals():
        if env_var not in os.environ:
            print("No variable CI_PYTHON_CONFIG_FILE defined, using default config.")
            config_file = Path(__file__).parent.joinpath("config", "ci_test_config.toml")
        else:
            config_file = Path(os.environ["CI_PYTHON_CONFIG_FILE"])
        if config_file.suffix == ".toml":
            return load_toml_config(path=config_file)
        raise TypeError("Currently, only .toml files are supported")
    return CI_CONFIG


CI_CONFIG = load_config()


if __name__ == '__main__':
    print(CI_CONFIG)
    save_toml_config(CI_CONFIG, "config/ci_test_config.toml")
