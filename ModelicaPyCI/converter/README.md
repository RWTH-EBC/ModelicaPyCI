# What is it?
### lock_model.py
The script sets all models of the library for which a whitelist has been created to read-only mode. 
#### Parser Arguments
| Parser Arguments  | Description | 
|-------------------|------------| 
|--library| Library to test           | 
|--lock-library|    Library to lock        | 

#### Example: Execution on gitlab runner (linux)
    python modelicapyci_tests/CITests/Converter/lock_model.py --library ${library} --lock-library ${whitelist_library}
### google_charts.py
The script visualizes the deviation of failing models that failed the regression test. It also creates graphs of the generated values based on the reference files.
#### Parser Arguments
| Parser Arguments | Description                           | 
|-----------------|---------------------------------------| 
|--line-html| plot a google html chart in line form |  | 
|--create-layout| Create a layout with a plots                                      | 
|--line-matplot|          plot a matlab chart                             |  
|--new-ref|        Plot new models with new created reference files                               |   
|--error|      Plot only model with errors                                 |   
|--update-ref| Plot only updated models |  
|--single-package| Test only the Modelica package Modelica.Package |  
|--library| Library to test|  
|--funnel-comp| Take the datas from funnel_comp |  
|--ref-txt| Take the datas from reference datas |  

#### Example: Execution on gitlab runner (linux)
    python modelicapyci_tests/CITests/Converter/google_charts.py  --create-layout --library AixLib --single-package AixLib

## compare_reference_results.py
Summarises reference results for reviewers of a pull request:

* `--reference-changes-flag`: compares the reference result files that the current branch changes
  (`<library>/Resources/ReferenceResults/Dymola`, compared to the merge base with `origin/<main-branch>`)
  with the version of the main branch. For every modified file, a plot main vs. branch is written to
  `<result dir>/reference_changes/`; added and deleted files are listed. Per file, the summary shows
  whether the regression test would detect the change (funnel comparison with the default tolerance of
  BuildingsPy, `tol=1E-3`), the maximum deviation relative to the range (max - min) of the old values and
  the most affected variable; all changed variables are listed in a collapsed table.
* `--regression-errors-flag`: lists the models with failed regression tests (variables reported in
  `<result dir>/regression/<package>/unitTests-dymola.log`) with links to their plots.

The result is a Markdown summary (default `<result dir>/ci_summary.md`) with tables of the deviations and links
to the plots, e.g. to post it in the pull request. The numbers stay readable in the pull request even when the
plots are no longer published.

#### Parser Arguments
| Parser Arguments | Description |
|------------------|-------------|
| --library | Library to check, e.g. AixLib.|
| --main-branch | Branch to compare reference results with (default: main). Needs `origin/<main-branch>`, e.g. checkout with fetch-depth 0.|
| --page-url | URL of the published results of this branch, used for links in the summary.|
| --summary-file | Markdown file for the summary (default: `<result dir>/ci_summary.md`).|
| --reference-changes-flag | Compare changed reference results with the main branch.|
| --regression-errors-flag | Summarise failed regression tests.|

#### Example
    python -m ModelicaPyCI.converter.compare_reference_results --library AixLib --main-branch main \
        --page-url https://rwth-ebc.github.io/AixLib/my-branch --reference-changes-flag --regression-errors-flag
