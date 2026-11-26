# What is it?
These tests validate the html syntax or the dymola style.

## html_tidy_errors.py
The Test html_tidy_errors.py validate and correct the HTML code. 
Return a log file.
#### Parser Arguments
| Parser Arguments  | Description      | 
|-------------------| ------------------------- | 
| --correct-overwrite  |correct html code in modelica files and overwrite old files.|
| --correct-backup  | backup old files.|
| --single-package  | Package tested for correct html syntax.|
| --log | create logfile of model with errors.|
| --path  | Path where top-level package.mo of the library is located.|
| --whitelist | Create a new whitelist for a Library.|
| --correct-view  | Check and print the Correct HTML Code.|
| --library  | library tested for correct html syntax.|
| --whitelist-library | library tested for correct html syntax.|
| --git-url  | Url repository of a library for which a whitelist is written.|
| --filter-whitelist | Argument that models on the whitelist are not tested (default: True).|


#### Example: Execution on gitlab runner (linux)
    python modelicapyci_tests/CITests/SyntaxTests/html_tidy_errors.py --s AixLib --correct-view --log  --filter-whitelist
    python modelicapyci_tests/CITests/SyntaxTests/html_tidy_errors.py --s AixLib --correct-overwrite --filter-whitelist --log
    python modelicapyci_tests/CITests/SyntaxTests/html_tidy_errors.py --whitelist --git-url https://github.com/ibpsa/modelica-ibpsa.git --whitelist-library IBPSA

![ModelManagement_StyleChecking.PNG](../../Documentation/Images/HTMLProcess.png)
For more information look at following [Repository](https://github.com/RWTH-EBC/HTML-Tidy-Modelica).

For the implementation in gitlab-yaml go to the following [link](https://git.rwth-aachen.de/EBC/EBC_all/gitlab_ci/templates/-/tree/AixLib/dymola-ci-tests/ci_templates)
## style_checking.py
`style_checking.py` uses the *ModelManagement* library of Dymola to check the style of the models of a library
(documentation, description strings, naming, ...).
The result is written to `<library>_StyleCheckLog.html` and copied to the syntax result folder
(`ci-tests/result/syntax`, see `CI_PYTHON_CONFIG_FILE`).
The script exits with 1 if the log contains style violations, otherwise with 0.
#### Parser Arguments
| Parser Arguments  | Description      | 
|-------------------| ------------------------- | 
| --library         | Name of the library to test (top-level `package.mo` in `<library>/package.mo`).|
| --min-number-of-unused-licences | Number of unused Dymola licences required to start. Used to avoid blocking licences of real users. 0 disables the check (default: 1).|
| --startup-mos     | Optional startup mos script, e.g. to load additional libraries.|
| --changed-flag    | Check only changed models instead of the whole library. If more than 100 models changed, the whole library is checked.|
| --main-branch     | Only with `--changed-flag`: branch to compare with, e.g. `main` (models changed compared to `origin/<main-branch>`, i.e. all changes of a branch or pull request). Default: compare with the last two commits (`HEAD^^`).|

#### Example: Execution in a CI job (linux)
    # whole library
    xvfb-run -n 77 python -m ModelicaPyCI.syntax.style_checking --library AixLib --startup-mos startup.mos --min-number-of-unused-licences 5
    # only models changed in the current branch compared to main (needs origin/main, e.g. checkout with fetch-depth 0)
    xvfb-run -n 77 python -m ModelicaPyCI.syntax.style_checking --library AixLib --startup-mos startup.mos --min-number-of-unused-licences 5 --changed-flag --main-branch main

![ModelManagement_StyleChecking.PNG](../../Documentation/Images/ModelManagement_StyleChecking.PNG)













