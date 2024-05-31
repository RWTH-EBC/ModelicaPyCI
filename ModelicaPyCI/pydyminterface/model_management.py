import codecs
import os
from pathlib import Path

from ebcpy import DymolaAPI

from ModelicaPyCI.config import ColorConfig

COLORS = ColorConfig()


class ModelManagement:

    def __init__(self, dymola_api: DymolaAPI):
        self.dymola_api = dymola_api
        self.load_model_management()

    def load_model_management(self):
        path_libraries = Path(self.dymola_api.dymola_path).joinpath(
            "Modelica", "Library"
        )
        for folder in os.listdir(path_libraries):
            if folder.startswith("ModelManagement") and os.path.isdir(path_libraries.joinpath(folder)):
                mm_path = path_libraries.joinpath(folder, "package.moe")
                if os.path.isfile(mm_path):
                    break
        else:
            print(
                f"{COLORS.CRED}Error: {COLORS.CEND} "
                f"Could not locate ModelManagement library in {path_libraries}. "
            )
            exit(1)
        res = self.dymola_api.dymola.openModel(str(mm_path), changeDirectory=False)
        if res:
            print(f"Load Model Management from path: {mm_path}")
        else:
            log = self.dymola_api.dymola.getLastErrorLog()
            print(
                f"{COLORS.CRED}Error: {COLORS.CEND} "
                f"Could not load ModelManagement from {mm_path}. "
                f"Reason: {log}"
            )

    def mm_style_check(self, library: str, models_list: list = None, changed_flag: bool = False):
        log_file = Path(Path.cwd(), f'{library}_StyleCheckLog.html')
        if changed_flag is True and len(models_list) <= 100:
            changed_model_list = []
            for model in models_list:
                print(f'Check model {model} \n')
                self.dymola_api.dymola.ExecuteCommand(_get_check_library_or_model(model))
                log = codecs.open(str(Path(Path.cwd(), f'{model}_StyleCheckLog.html')), "r",
                                  encoding='utf8')
                for line in log:
                    changed_model_list.append(line)
                log.close()
                os.remove(Path(Path.cwd(), f'{model}_StyleCheckLog.html'))
            all_logs = codecs.open(str(log_file), "w", encoding='utf8')
            for model in changed_model_list:
                all_logs.write(model)
            all_logs.close()
        else:
            print(f'Check all models in {library} library\n')
            self.dymola_api.dymola.ExecuteCommand(_get_check_library_or_model(library))
            self.dymola_api.close()
        return log_file

    def get_extended_examples(self, model: str = ""):
        model_list = self.dymola_api.dymola.ExecuteCommand(
            f'ModelManagement.Structure.AST.Classes.ExtendsInClass("{model}");'
        )
        extended_list = _filter_modelica_types(model_list=model_list)
        return extended_list

    def get_used_models(self, model: str = ""):
        model_list = self.dymola_api.dymola.ExecuteCommand(
            f'ModelManagement.Structure.Instantiated.UsedModels("{model}");'
        )
        extended_list = _filter_modelica_types(model_list=model_list)
        return extended_list


def _filter_modelica_types(model_list: list,
                           type_list=None):
    if type_list is None:
        type_list = ["Modelica", "Real", "Integer", "Boolean", "String"]
    extended_list = list()
    if model_list is not None:
        for extended_model in model_list:
            for types in type_list:
                if extended_model.find(f'{types}') > -1:
                    extended_list.append(extended_model)
                    continue
    extended_list = list(set(extended_list))
    for ext in extended_list:
        model_list.remove(ext)
    model_list = list(set(model_list))
    return model_list


def _get_check_library_or_model(name: str):
    return f'ModelManagement.Check.checkLibrary(false, false, false, true, "{name}", translationStructure=false);'
