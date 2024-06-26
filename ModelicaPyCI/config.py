from pathlib import Path
from typing import Union

import toml
from pydantic import BaseModel, ConfigDict


class BaseModelNoExtra(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ModelicaPyCIConfig(BaseModelNoExtra):
    url: str = "https://github.com/RWTH-EBC/ModelicaPyCI.git"
    OM_python_check_model_module: str = "ModelicaPyCI.unittest.om_check"
    test_validate_module: str = "ModelicaPyCI.unittest.validatetest"
    test_reference_module: str = "ModelicaPyCI.unittest.reference_check"
    google_chart_module: str = "ModelicaPyCI.converter.google_charts"
    api_github_module: str = "ModelicaPyCI.api_script.api_github"
    html_tidy_module: str = "ModelicaPyCI.syntax.html_tidy"
    syntax_test_module: str = "ModelicaPyCI.syntax.style_checking"
    naming_guideline_module: str = "ModelicaPyCI.syntax.naming_guideline"
    configuration_module: str = "ModelicaPyCI.config"
    library_merge_module: str = "ModelicaPyCI.deploy.ibpsa_merge"
    lock_model_module: str = "ModelicaPyCI.converter.lock_model"
    config_structure_module: str = "ModelicaPyCI.structure.config_structure"
    create_whitelist_module: str = "ModelicaPyCI.structure.create_whitelist"
    om_badge_module: str = "ModelicaPyCI.deploy.create_om_badge"


class ResultConfig(BaseModelNoExtra):
    dir: str = 'result'
    whitelist_dir: str = 'ci_whitelist'
    plot_dir: str = 'charts'
    syntax_dir: str = 'syntax'
    regression_dir: str = 'regression'
    check_result_dir: str = 'Dymola_check'
    naming_violation_file: str = "naming_violations.txt"
    OM_check_result_dir: str = "OM_check"


class FilesConfig(BaseModelNoExtra):
    dir: str = 'Configfiles'
    exit_file: str = 'exit.sh'
    new_create_ref_file: str = 'ci_new_created_reference.txt'
    changed_file: str = 'ci_changed_model_list.txt'
    ref_file: str = 'ci_reference_list.txt'


class WhitelistConfig(BaseModelNoExtra):
    dir: str = "whitelist"
    dymola_check_file: str = 'dymola_check_whitelist.txt'
    dymola_simulate_file: str = 'dymola_simulate_whitelist.txt'
    ibpsa_file: str = 'ibpsa_whitelist.txt'
    dymola_reference_file: str = "dymola_reference_whitelist.txt"
    om_check_file: str = 'om_check_whitelist.txt'
    om_simulate_file: str = 'om_simulate_whitelist.txt'


class PlotConfig(BaseModelNoExtra):
    chart_dir: str = 'charts'
    templates_chart_dir: str = 'MoCITempGen/templates/google_templates'
    templates_chart_file: str = 'MoCITempGen/templates/google_templates/google_chart.txt'
    templates_index_file: str = 'MoCITempGen/templates/google_templates/index.txt'
    templates_layout_file: str = 'MoCITempGen/templates/google_templates/layout_index.txt'


class ArtifactsConfig(BaseModelNoExtra):
    dir: str = 'artifacts'
    library_ref_results_dir: str = 'Resources/ReferenceResults/Dymola'
    library_resource_dir: str = 'Resources/Scripts/Dymola'


class InteractConfig(BaseModelNoExtra):
    dir: str = 'interact_CI'
    show_ref_file: str = 'show_ref.txt'
    update_ref_file: str = 'update_ref.txt'


class CIConfig(BaseModelNoExtra):
    library_root: str = ""
    dir: str = "ci"
    result: ResultConfig = ResultConfig()
    ci_files: FilesConfig = FilesConfig()
    whitelist: WhitelistConfig = WhitelistConfig()
    artifacts: ArtifactsConfig = ArtifactsConfig()
    interact: InteractConfig = InteractConfig()
    plots: PlotConfig = PlotConfig()
    naming_guideline_file: str = "naming_guideline.toml"

    def get_file_path(self, files_type, file_name, different_library_root: Path = None) -> Path:
        dir_path = self.get_dir_path(files_type=files_type, different_library_root=different_library_root)
        files_type_config = self.dict()[files_type]
        if file_name not in files_type_config:
            raise ValueError(f"Given file_name {file_name} is not a valid key of CI_CONFIG.{files_type}.")
        file_name_str = files_type_config[file_name]
        return dir_path.joinpath(file_name_str)

    def get_dir_path(self, files_type: str = None, different_library_root: Path = None) -> Path:
        if different_library_root is None:
            dir_path = Path(self.library_root).joinpath(self.dir)
        else:
            dir_path = Path(different_library_root).joinpath(self.dir)
        if files_type is None:
            return dir_path
        if files_type not in self.dict():
            raise ValueError(f"'{files_type}' is not a valid key of CI_CONFIG.")
        files_type_config = self.dict()[files_type]
        return dir_path.joinpath(files_type_config["dir"])


def load_toml_config(path: Union[Path, str]):
    with open(path, "r") as file:
        config = toml.load(file)
    return CIConfig(**config)


def save_toml_config(config: BaseModel, path: Union[Path, str]):
    with open(path, "w") as file:
        toml.dump(config.model_dump(), file)
