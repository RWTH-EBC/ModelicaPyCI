"""
Summarise reference results for reviewers.

* Reference changes: compares the reference result files a branch changes with the
  reference results of the main branch and plots old against new values.
* Regression errors: summarises the deviations of failed regression tests from the
  funnel_comp folders written by BuildingsPy.

Writes HTML plots to <result dir>/reference_changes and a Markdown summary that a CI
can post in the pull request. The summary also contains the numbers, so it stays
readable when the plots are no longer published.
"""
import argparse
import os
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from ModelicaPyCI.utils import logger

REFERENCE_CHANGES_DIR = "reference_changes"
SUMMARY_MARKER = "<!-- modelica-ci-summary -->"
_VALUES_PATTERN = re.compile(r'^\s*([^\s=]+)\s*=\s*\[(.*?)\]', re.DOTALL | re.MULTILINE)
_SKIP_KEYS = ("last-generated", "statistics-initialization", "statistics-simulation")


# ---------------------------------------------------------------------------
# Reading data
# ---------------------------------------------------------------------------
def parse_reference_text(text: str) -> dict:
    """
    Parse a BuildingsPy reference result file.

    The file contains time=[t_start, t_end] and for each variable a list of values,
    equally spaced between t_start and t_end (constant variables have two values).

    Returns:
        dict: variable name -> pandas.Series indexed by time
    """
    matches = _VALUES_PATTERN.findall(text)
    raw = {}
    for name, values in matches:
        if name in _SKIP_KEYS:
            continue
        try:
            raw[name] = np.array([float(v) for v in values.replace("\n", " ").split(",") if v.strip()])
        except ValueError:
            logger.warning("Could not read values of %s in reference results", name)
    if "time" not in raw or len(raw["time"]) < 2:
        raise ValueError("Reference results contain no valid time=[start, end]")
    t_start, t_end = raw.pop("time")[[0, -1]]
    series = {}
    for name, values in raw.items():
        if len(values) == 0:
            continue
        time = np.linspace(t_start, t_end, len(values)) if len(values) > 1 else np.array([t_start])
        series[name] = pd.Series(values, index=time, name=name)
    return series


def read_reference_file(path) -> dict:
    with open(path, "r") as file:
        return parse_reference_text(file.read())


def compare_series(old: pd.Series, new: pd.Series) -> dict:
    """Maximum absolute and relative deviation of new from old (new interpolated to old times)."""
    new_on_old = np.interp(old.index.values, new.index.values, new.values)
    abs_diff = np.abs(new_on_old - old.values)
    max_abs = float(np.max(abs_diff)) if len(abs_diff) else 0.0
    scale = float(np.max(np.abs(old.values))) if len(old) else 0.0
    max_rel = max_abs / scale if scale > 0 else (0.0 if max_abs == 0 else float("inf"))
    return {"max_abs": max_abs, "max_rel": max_rel}


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------
def _git(*args) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def get_changed_reference_files(ref_dir: str, main_branch: str) -> list:
    """
    Reference files changed compared to origin/<main_branch>.

    Returns:
        list of (status, path) with status A (added), M (modified) or D (deleted)
    """
    from ModelicaPyCI.utils import _get_commit_of_remote_branch
    compare_to = _get_commit_of_remote_branch(main_branch)
    merge_base = _git("merge-base", compare_to, "HEAD").strip()
    output = _git("diff", "--name-status", "--no-renames", merge_base, "HEAD", "--", ref_dir)
    changed = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[1].endswith(".txt") and parts[0][0] in "AMD":
            changed.append((parts[0][0], parts[1]))
    return sorted(changed, key=lambda item: item[1]), merge_base


def read_reference_file_at(commit: str, path: str) -> dict:
    return parse_reference_text(_git("show", f"{commit}:{path}"))


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def plot_reference_change(name: str, old: dict, new: dict, variables: list, output_file: Path):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=len(variables), cols=1, shared_xaxes=True)
    for i, variable in enumerate(variables, 1):
        for label, data, color in (("main", old, "blue"), ("branch", new, "red")):
            if variable in data:
                fig.add_trace(go.Scatter(
                    x=data[variable].index, y=data[variable].values,
                    name=f"{variable} ({label})", line=dict(color=color),
                    mode="lines", legendgroup=f"group{i}",
                    legendgrouptitle_text=variable if label == "main" else None
                ), row=i, col=1)
        fig.update_yaxes(title_text=variable, row=i, col=1)
    fig.update_xaxes(title_text="Time in s", row=len(variables), col=1)
    fig.update_layout(height=300 * len(variables), title_text=f"{name}: main (blue) vs. branch (red)")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_file)


def write_index(output_dir: Path, files: list):
    links = "\n".join(f'<li><a href="{f}">{Path(f).stem}</a></li>' for f in files)
    html = ("<!doctype html><html><head><meta charset='UTF-8'><title>Changed reference results</title>"
            f"</head><body><h1>Changed reference results</h1><ul>{links}</ul></body></html>")
    (output_dir / "index.html").write_text(html)


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------
def _fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    return f"{value:.3g}"


def summarize_reference_changes(library: str, ref_dir: str, main_branch: str, result_dir: Path,
                                page_url: str = None) -> str:
    changed, merge_base = get_changed_reference_files(ref_dir=ref_dir, main_branch=main_branch)
    if not changed:
        logger.info("No reference results changed compared to %s", main_branch)
        return ""
    output_dir = result_dir / REFERENCE_CHANGES_DIR
    plot_files = []
    rows = []
    added, deleted = [], []
    for status, path in changed:
        name = Path(path).stem
        if status == "A":
            added.append(name)
            continue
        if status == "D":
            deleted.append(name)
            continue
        old = read_reference_file_at(merge_base, path)
        new = read_reference_file(path)
        variables = sorted(set(old) | set(new))
        for variable in variables:
            if variable not in old or variable not in new:
                rows.append((name, variable, "only in " + ("branch" if variable in new else main_branch), "", ""))
                continue
            deviation = compare_series(old[variable], new[variable])
            if deviation["max_abs"] > 0:
                rows.append((name, variable, "changed", _fmt(deviation["max_abs"]), _fmt(deviation["max_rel"])))
        plot_file = f"{name}.html"
        plot_reference_change(name, old, new, variables, output_dir / plot_file)
        plot_files.append(plot_file)
    if plot_files:
        write_index(output_dir, plot_files)

    lines = [f"### Changed reference results (compared to `{main_branch}`)", ""]
    if page_url and plot_files:
        lines += [f"Plots main vs. branch: {page_url}/{REFERENCE_CHANGES_DIR}/index.html", ""]
    if rows:
        lines += ["| Reference | Variable | Change | Max. abs. deviation | Max. rel. deviation |",
                  "|---|---|---|---|---|"]
        lines += [f"| `{r[0]}` | `{r[1]}` | {r[2]} | {r[3]} | {r[4]} |" for r in rows]
        lines.append("")
    elif plot_files:
        lines += ["Reference files changed, but all values are identical.", ""]
    if added:
        lines += ["New reference results: " + ", ".join(f"`{n}`" for n in added), ""]
    if deleted:
        lines += ["Deleted reference results: " + ", ".join(f"`{n}`" for n in deleted), ""]
    return "\n".join(lines)


def summarize_regression_errors(regression_dir: Path, page_url: str = None) -> str:
    """Summarise failed regression tests from <regression_dir>/<package>/funnel_comp/<model>.mat_<variable>."""
    rows = []
    for folder in sorted(Path(regression_dir).glob("*/funnel_comp/*")):
        if not folder.is_dir() or ".mat_" not in folder.name:
            continue
        reference_csv, test_csv = folder / "reference.csv", folder / "test.csv"
        if not reference_csv.exists() or not test_csv.exists():
            continue
        model, variable = folder.name.rsplit(".mat_", 1)
        package = folder.parent.parent.name
        try:
            ref = pd.read_csv(reference_csv)
            test = pd.read_csv(test_csv)
            deviation = compare_series(pd.Series(ref["y"].values, index=ref["x"].values),
                                       pd.Series(test["y"].values, index=test["x"].values))
        except (KeyError, ValueError) as err:
            logger.warning("Could not read funnel results in %s: %s", folder, err)
            continue
        link = ""
        if page_url:
            link = f"[plot]({page_url}/charts/{package}/{model.replace('.', '_')}.html)"
        rows.append((model, variable, _fmt(deviation["max_abs"]), _fmt(deviation["max_rel"]), link))
    if not rows:
        return ""
    lines = ["### Failed regression tests", ""]
    if page_url:
        lines += [f"All plots: {page_url}/charts/index.html", ""]
    lines += ["| Model | Variable | Max. abs. deviation | Max. rel. deviation | |", "|---|---|---|---|---|"]
    lines += [f"| `{r[0]}` | `{r[1]}` | {r[2]} | {r[3]} | {r[4]} |" for r in rows]
    lines.append("")
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Summarise reference results for pull requests")
    parser.add_argument("--library", required=True, help="Library to check, e.g. AixLib")
    parser.add_argument("--main-branch", default="main", help="Branch to compare reference results with")
    parser.add_argument("--page-url", default=None,
                        help="URL of the published results of this branch, used for links in the summary")
    parser.add_argument("--summary-file", default=None,
                        help="Markdown file for the summary (default: <result dir>/ci_summary.md)")
    parser.add_argument("--reference-changes-flag", action="store_true",
                        help="Compare changed reference results with the main branch")
    parser.add_argument("--regression-errors-flag", action="store_true",
                        help="Summarise failed regression tests from the funnel_comp folders")
    return parser.parse_args()


if __name__ == '__main__':
    from ModelicaPyCI.load_global_config import CI_CONFIG

    args = parse_args()
    result_dir = Path(CI_CONFIG.get_dir_path("result"))
    sections = []
    if args.regression_errors_flag:
        sections.append(summarize_regression_errors(
            regression_dir=CI_CONFIG.get_file_path("result", "regression_dir"), page_url=args.page_url))
    if args.reference_changes_flag:
        sections.append(summarize_reference_changes(
            library=args.library,
            ref_dir=str(Path(args.library).joinpath(CI_CONFIG.artifacts.library_ref_results_dir).as_posix()),
            main_branch=args.main_branch, result_dir=result_dir, page_url=args.page_url))
    summary = "\n".join(section for section in sections if section)
    summary_file = Path(args.summary_file) if args.summary_file else result_dir / "ci_summary.md"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(summary)
    logger.info("Wrote summary with %s characters to %s", len(summary), summary_file)
