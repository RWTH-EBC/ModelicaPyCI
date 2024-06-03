import argparse
import logging
import math
import os
import re
import shutil
import sys
from pathlib import Path
from typing import List, Union, Dict

import toml
from pydantic import BaseModel

from ModelicaPyCI.api_script.api_github import PullRequestGithub
from ModelicaPyCI.config import ColorConfig, CI_CONFIG
from ModelicaPyCI.structure import sort_mo_model as mo

COLORS = ColorConfig()


class NamingGuidelineConfig(BaseModel):
    modelica_special_names: List[str] = [
        "parameter",
        "constant",
        "replaceable",
        "import",
        "extends",
        "in",
        "of",
        "input",
        "output",
        "final",
        "protected",
        "public",
        "function",
        "model",
        "package",
        "inner",
        "outer"
    ]

    modelica_types: List[str] = [
        "Real",
        "real",
        "Boolean",
        "boolean",
        "Integer",
        "String"
    ]

    libraries: List[str] = ["Modelica"]

    special_names: List[str] = [
        "energyDynamics",
        "massDynamics",
        "substanceDynamics",
        "traceDynamics",
        "linearizeFlowResistance",
        "computeFlowResistance",
        "homotopyInitialization",
        "linearized",
        "allowFlowReversal",
        "extrapolation",
        "smoothness",
        "initType"
    ]
    special_parts_with_upper: List[str] = [
        "COP",
        "PID",
        "deltaM"
    ]

    special_parts: Dict[str, Union[List[str], str]] = {
        # Physical quantities
        # Buildings naming convention
        "T": "temperature",
        "p": "pressure",
        "dp": "pressure",
        "P": "power",
        "E": "energy",
        "Q": "heat",
        "X": "mass",  # mass fraction per total mass
        # "x": "humidity",       # mass fraction per mass of dry air (is now absHum)
        "u": "input",
        "y": "output",

        "port": "port",
        "terminal": "terminal",

        # namespaces table (desired naming)
        "absHum": "humidity",
        "A": "area",
        "hCon": "convective",
        "I": "current",
        "rho": "density",
        "d": "diameter",
        "eta": "efficiency",
        "R": "resistance",
        "C": "capacity",
        "lambda": "conductivity",
        "height": "height",
        "U": "energy",
        "nu": "viscosity",
        "lat": "latitude",
        "len": "length",
        "lon": "longitude",
        "eps": "emissivity",
        "m": "mass",
        "n": "number",
        "Pr": "prandtl",
        "relHum": "humidity",
        "Re": "reynolds",
        "solabs": "absorptance",
        "H": "solar",
        "cp": "capacity",
        "h": "enthalpy",
        "c": "capacity",
        "UA": "conductance",
        "s": "thickness",
        "time": "time",
        "tau": "transmittance",
        "vel": "velocity",
        "V": ["volume", "voltage"],
        "width": "width"
    }

    two_character_words: List[str] = [
        "is",
        "to",
        "no",
        "or",
        "on"
    ]

    four_character_words: List[str] = [
        "const",
        "flow",
        "gain",
        "year",
        "time"

    ]

    special_ends: List[str] = [  # Order is important as break is used
        "_flow",
        "_start",
        "_flow_nominal",
        "_nominal",
        "_flow_internal",
        "_internal",
        "_small",
        "_flow_small",
        "1",
        "2",
        "_a",
        "_b",
        "_p",
        "_n",
        "_x1",
        "_x2",
        "_in",
        "_out",
        ";",
        "_min",
        "_max",
        "_const"
    ]

    SPECIAL_STARTS: List[str] = [
        "use_",
        "port_",
        "have_",
        "terminal_",
        "heatport_"
        "from_"
    ]


def is_valid_modelica_type(string, naming_config: NamingGuidelineConfig):
    return (
            (string in naming_config.modelica_types) or
            any([string.startswith(lib + ".") for lib in naming_config.libraries])
    )


def get_all_repo_files(repo_path):
    list_of_files = []
    for path, subdirs, files in os.walk(repo_path):
        for name in files:
            if name.endswith(".mo"):
                list_of_files.append(Path(os.path.join(path, name)))
    return list_of_files


def remove_annotation(line, naming_config: NamingGuidelineConfig):
    if "annotation" not in line:
        return line
    # Case for annotation occurring multiple times:
    return "annotation".join(line.split("annotation")[:-1])


def get_possibly_wrong_code_sections(
        files: list, library: str, naming_config: NamingGuidelineConfig
):
    output = ""
    for model_name in files:
        parts = model_name.split(".")
        parts[-1] += ".mo"
        file = Path(CI_CONFIG.library_root).joinpath(*parts)
        if file.name == "package.mo":
            continue
        try:
            expressions = get_expressions(
                filepath_model=file,
                naming_config=naming_config
            )
        except Exception as err:
            print(f"{COLORS.CRED} Error: {COLORS.CEND} Can't process file {file} due to error: {err}")
        problematic_expressions = {}
        for expression in expressions[2:]:  # First two expressions are always the model and within statement
            # Extend modifiers include no new names
            if expression.startswith("extends"):
                continue
            # The model annotation includes no new names
            if expression.startswith("annotation"):
                continue
            # If no equation is present, the model ends with a line "end "
            if expression.startswith("end "):
                continue
            expression_without_annotation = remove_annotation(expression, naming_config=naming_config)
            name_is_ok, doc_is_ok, reason_name, reason_doc, list_parts_not_okay = line_is_ok(
                expression_without_annotation, naming_config=naming_config
            )

            if not name_is_ok and not doc_is_ok:
                problematic_expressions[expression] = f"{reason_doc}, {reason_name}"
            elif not name_is_ok:
                problematic_expressions[expression] = reason_name
            elif not doc_is_ok:
                problematic_expressions[expression] = reason_doc
            else:
                pass

        if problematic_expressions:
            output += "\n\n\n" + str(file) + "\n"
            output += "\n\n".join([
                f"{i + 1}: {problematic_expressions[key]}. "
                f"Affected line: {key}" for i, key in enumerate(problematic_expressions)
            ])

    filename = f"wrong_code_parts_{library}.txt"
    with open(filename, "w+", encoding="utf-8") as file:
        file.write(output)
    # with open("wrong_code_parts_buildings.txt", "w+", encoding="utf-8") as file:
    #     file.write(output)
    # print dictionary of problematic expressions as csv
    # with open('problematic_expressions.csv', 'w', encoding="utf-8") as f:
    #     for key in dict_problematic_expressions.keys():
    #         f.write("%s,%s\n" % (key, dict_problematic_expressions[key]))

    return problematic_expressions, filename


def get_expressions(filepath_model: str, naming_config: NamingGuidelineConfig):
    """
    This function extracts specific expressions out of modelica models.

    :param str,os.path.normpath filepath_model:
        Full path of modelica model on the given os
        e.g. path_model = "C://MyLibrary//TestModel.mo"

    :return: list matches
        List with all lines matching the given expression.
    """
    # Open the file
    with open(filepath_model, "r", encoding="utf-8") as file:
        file.seek(0)
        script = file.read()
    # Get position of "equation" or "initial equation"
    equation_start = re.search(
        r'\nequation\n|\ninitial equation\n|\ninitial algorithm\n|\nalgorithm\n',
        script
    )
    pos_equation = equation_start.span()[0] if equation_start else math.inf

    def _filter_text(text):
        return " ".join(text.split())

    # Find desired expression in modelica script
    sep = ";\n"
    _pattern = r"%s" % sep
    # Get position of expressions
    expressions = []
    last_loc = 0
    for match in re.finditer(_pattern, script, re.MULTILINE):
        if last_loc > pos_equation:
            break
        loc = match.span()[0] + len(sep)
        expressions.append(script[last_loc:loc])
        last_loc = loc
    else:
        expressions.append(script[last_loc:])

    expressions = [_filter_text(expression).replace("\n", "") for expression in expressions]

    # Join lines if not full modelica line:
    expressions_joined = []
    expression_join = ""
    last_one_valid = True
    for expression in expressions:
        if is_full_modelica_line(line=expression, naming_config=naming_config):
            if not last_one_valid:
                expressions_joined.append(expression_join)
            expressions_joined.append(expression)
            last_one_valid = True
        else:
            if last_one_valid:
                expression_join = expression
            else:
                expression_join += expression
            last_one_valid = False
    if not expressions_joined and expressions:
        expressions_joined = [expression_join]
    if pos_equation != math.inf:
        return expressions_joined
    return expressions_joined


def line_is_ok(line, naming_config: NamingGuidelineConfig):
    # Only a comment line
    if line.startswith("//") or line.__contains__("***") or line.__contains__("</"):
        return True, True, None, None, []
    if line.startswith("within"):
        return True, True, None, None, []
    doc = get_documentation_from_line(line=line)
    if doc is None:
        doc_is_ok = False
        line_without_doc = line
        reason_doc = "Missing documentation"
    else:
        # Assert minimal doc length.
        if len(doc) < 5:
            doc_is_ok = False
            reason_doc = "Documentation too short"
        else:
            doc_is_ok = True
            reason_doc = "Documentation ok"
        line_without_doc = line.split(f'"{doc}')[0]
    name = get_name_from_line(line=line_without_doc, naming_config=naming_config)
    name_is_ok, reason_name, list_parts_not_okay = check_if_name_is_ok(name=name, naming_config=naming_config)
    return name_is_ok, doc_is_ok, reason_name, reason_doc, list_parts_not_okay


def check_if_name_is_ok(name: str, naming_config: NamingGuidelineConfig):
    name_clean = name
    if name in naming_config.special_names:
        return True, "Name is correct", []
    if " " in name:
        return False, ("Could not extract name from line and check correctness, "
                       "is your type specification correct (full library path)?"), []
    for special_parts_with_cap in naming_config.special_parts_with_upper:
        name = name.replace(special_parts_with_cap, "")
    name_parts = split_camel_case(string=name)

    parts_ok = []
    for idx, part in enumerate(name_parts):
        if idx < len(name_parts) - 1:
            next_part = name_parts[idx + 1]
        else:
            next_part = ""
        # separates SPECIAL_END from parts
        for special_end in naming_config.special_ends:
            if part.endswith(special_end):
                name_parts = [s.replace(part, part[:-len(special_end)]) for s in name_parts]
                part = part[:-len(special_end)]
                break
        # separates SPECIAL_STARTS from parts
        for special_start in naming_config.SPECIAL_STARTS:
            if part.startswith(special_start):
                part = part[len(special_start):]
                break

        part_is_ok = (
                (part in naming_config.special_parts) or
                (len(part) == 3) or
                (len(part) == 0) or
                (part.lower() in naming_config.two_character_words) or
                (part.lower() in naming_config.four_character_words) or
                part == "d" and next_part == "T"  # Case for dT
        )
        parts_ok.append(part_is_ok)
    if not all(parts_ok):
        parts_not_ok = [part for part, ok in zip(name_parts, parts_ok) if not ok]
        return False, f"Name '{name_clean}' contains parts with more/less than " \
                      f"3 characters or which are not part of special cases. " \
                      f"Affected parts: {', '.join(parts_not_ok)}", parts_not_ok
    else:
        return True, f"Name '{name_clean}' is correct", []


def split_camel_case(string):
    parts = []
    last_upper = 0
    for i, char in enumerate(string):
        if char.isupper() and last_upper != i:
            parts.append(string[last_upper:i])
            last_upper = i
    parts.append(string[last_upper:len(string)])
    return parts


def get_documentation_from_line(line: str):
    def find_all_char_locs_in_string(string, char):
        return [i for i, ltr in enumerate(string) if ltr == char]

    locs = find_all_char_locs_in_string(line, '"')
    if not locs:
        return None
    if len(locs) < 2:
        print(f'{COLORS.CRED} Error: {COLORS.CEND} Only one " in line {line}')
        return None
    return line[locs[-2] + 1:locs[-1]]


def get_name_from_line(line, naming_config: NamingGuidelineConfig):
    parts = line.split(" ")
    _filtered_parts = []
    for part in parts:
        if is_valid_modelica_type(part, naming_config=naming_config) or part in naming_config.modelica_special_names:
            continue
        _filtered_parts.append(part)
    line_clean = " ".join(_filtered_parts)
    possible_breakers = ["(", "=", " if ", "constrainedby", "["]
    locs = [line_clean.find(possible_breaker) for possible_breaker in possible_breakers]
    locs = [loc for loc in locs if loc != -1] + [len(line_clean)]
    return line_clean[:min(locs)].strip()


def is_full_modelica_line(line, naming_config: NamingGuidelineConfig):
    """
    Check if expression found by regex is a full
    modelica line or if some ";" is used, for example
    in the case of arrays.
    Assumption:
    A valid Modelica line must
    - Have a type
    - End with ";" (this is checked by the regex in find_expressions)
    - Opening brackets should be closed again, e.g. '{', '[' and '('

    Syntax will be checked by vendor tools, this function assumes
    that correct Modelica syntax is correct.

    :params str line:
        Line of possible modelica-code
    """
    # Remove possible docs to avoid a case like
    # Real array[2, 2] = [0, 0; 0, 0] "An array of type Real with 2-2 dimensions";
    # This would be valid, but "Real" is in the documentation and the type.
    contains_type = False
    line_without_doc = re.sub(r'\".*?\"', "", line, re.DOTALL)
    for part in line.split(" "):
        if is_valid_modelica_type(part, naming_config=naming_config):
            contains_type = True
            break
    if not contains_type:
        return False
    for opening_bracket, closing_bracket in zip(["(", "[", "{"], [")", "]", "}"]):
        if line_without_doc.count(opening_bracket) != line_without_doc.count(closing_bracket):
            return False
    return True


def parse_args():
    parser = argparse.ArgumentParser(description="Check the Style of Packages")
    check_test_group = parser.add_argument_group("Arguments to start style tests")
    check_test_group.add_argument(
        "--library",
        help="Path where top-level package.mo of the library is located")
    check_test_group.add_argument(
        "--config",
        help="Path to the config file of the naming guidelines"
    )
    check_test_group.add_argument(
        "--main-branch",
        help="your base branch (main)"
    )
    check_test_group.add_argument(
        "--github-repository",
        help="Environment Variable owner/RepositoryName"
    )
    check_test_group.add_argument(
        "--working-branch",
        help="Your current working Branch",
        default="$CI_COMMIT_BRANCH"
    )
    check_test_group.add_argument(
        "--github-token",
        default="${GITHUB_API_TOKEN}",
        help="Your Set GITHUB Token"
    )
    check_test_group.add_argument(
        "--gitlab-page",
        default="${GITLAB_Page}",
        help="Set your gitlab page url"
    )
    check_test_group.add_argument("--changed-flag", action="store_true")


    return parser.parse_args()


def convert_csv_to_excel(csv_file, excel_file):
    import pandas as pd

    valid_lines = []
    with open(csv_file, 'r', encoding='utf-8') as file:
        for line in file:
            if line.count(',') == 1:
                valid_lines.append(line.strip())
            else:
                print(f"Skipping problematic line: {line.strip()}")

    df = pd.DataFrame([line.split(',') for line in valid_lines], columns=["Name", "Frequency"])

    # Convert the 'Frequency' column to numeric
    df["Frequency"] = pd.to_numeric(df["Frequency"])

    with pd.ExcelWriter(excel_file) as writer:
        df.to_excel(writer, index=False)


def move_output_to_artifacts_and_post_comment(file, args):
    pull_request = PullRequestGithub(
        github_repo=args.github_repository,
        working_branch=args.working_branch,
        github_token=args.github_token
    )
    shutil.copy(file, CI_CONFIG.get_file_path("result", "naming_violation_file"))
    page_url = f'{args.gitlab_page}/{CI_CONFIG.get_dir_path("result").as_posix()}'
    print(f'Setting gitlab page url: {page_url}')
    pr_number = pull_request.get_pr_number()
    message = (f'Naming convention is possibly violated or documentation is missing in changed files. '
               f'Check the output here and either correct the issues or discuss with your reviewer if '
               f'an exception should be added to the naming-guideline. File: \\n {page_url}')
    pull_request.post_pull_request_comment(
        pull_request_number=pr_number,
        post_message=message
    )


if __name__ == '__main__':
    logging.basicConfig(level="INFO")
    ARGS = parse_args()

    with open(ARGS.config, "r") as FILE:
        NAMING_CONFIG = NamingGuidelineConfig(**toml.load(FILE))

    FILES_TO_CHECK = mo.get_model_list(
        library=ARGS.library,
        package=".",
        filter_whitelist_flag=False,
        simulate_flag=False,
        changed_flag=ARGS.changed_flag,
        changed_to_branch=ARGS.main_branch
    )
    print(f"Checking {len(FILES_TO_CHECK)} files")
    PROBLEMATIC_EXPRESSIONS, FILENAME = get_possibly_wrong_code_sections(
        files=FILES_TO_CHECK,
        library=ARGS.library,
        naming_config=NAMING_CONFIG
    )
    if PROBLEMATIC_EXPRESSIONS:
        move_output_to_artifacts_and_post_comment(
            file=FILENAME, args=ARGS
        )
