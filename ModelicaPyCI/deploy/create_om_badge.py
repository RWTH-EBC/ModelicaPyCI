import argparse
import shutil
import os
from pathlib import Path
import urllib.request


def create_badge(badge_name: str, library: str, main_branch: str):
    import anybadge

    website = urllib.request.urlopen(
        f'https://libraries.openmodelica.org/branches/{main_branch}/{library}/{library}.html'
    )
    text = str(website.read())

    # First table, which has the necessary data
    table = text[text.find('<table>'): text.find('</table>')]
    # two subtables for titles and values
    splits = table.split('</tr>')[:2]

    titles = splits[0].split('/th')[:-1]
    values = splits[1].split('/td')[:-1]
    values = [int(i[i.rfind('>') + 1:-1]) for i in values]

    assert (len(titles) == len(values))

    # Finds entry index of "Total" column, in case this ever changes
    total_find = [n for n, i in enumerate(titles) if "Total" in i]
    assert len(total_find) == 1

    # Finds entry index of "Total" column, in case this ever changes
    simulate_find = [n for n, i in enumerate(titles) if "Simulation" in i]
    assert len(simulate_find) == 1

    # om_readiness == n_simulate / n_total
    # column indices for "Total" and "Simulation" define where the corresponding values are stored
    om_readiness = round(values[simulate_find[0]] /
                         values[total_find[0]], 2)

    # Define thresholds: <0.7=red,
    #                    <0.8=orange
    #                    <0.9=yellow
    #                   >=0.9=green

    thresholds = {0.6: 'red',
                  0.7: 'orange',
                  0.8: 'yellow',
                  0.9: 'greenyellow',
                  1: 'green'}

    badge = anybadge.Badge(
        'OpenModelica Readiness',
        om_readiness,
        thresholds=thresholds
    )

    badge_file = Path(badge_name)
    badge.write_badge(badge_file)
    return badge_file


def parse_args():
    parser = argparse.ArgumentParser(description="Check the Style of Packages")
    check_test_group = parser.add_argument_group("Arguments to start style tests")
    check_test_group.add_argument("--library",
                                  help="Path where top-level package.mo of the library is located")
    check_test_group.add_argument("--om-badge-name", default="2022",
                                  help="Version of Dymola(Give the number e.g. 2022")
    check_test_group.add_argument("--badge-folder", action="store_true")
    check_test_group.add_argument(
        "--main-branch",
        help="your base branch (main)"
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    os.makedirs(args.badge_folder, exist_ok=True)
    om_badge_file = create_badge(
        badge_name=args.om_badge_name,
        library=args.library,
        main_branch=args.main_branch
    )
    shutil.copy(
        om_badge_file,
        Path(args.badge_folder).joinpath(args.om_badge_name)
    )
