import argparse
import json
import os
from pathlib import Path

import requests
from git import Repo

from ModelicaPyCI.utils import logger


def clone_repository(clone_into_folder: Path, git_url: str):
    """
    Pull git repository.

    Args:
        clone_into_folder ():  Folder of the cloned project.
        git_url (): Git url of the cloned project.
    """
    if os.path.exists(clone_into_folder):
        logger.info(f'{clone_into_folder} folder already exists.')
        return
    logger.info(f'Clone {clone_into_folder} Repo')
    if "@" in git_url:
        url, branch = git_url.split("@")
        logger.info(f"Converted {git_url=} to {url=} with {branch=}")
        Repo.clone_from(url, clone_into_folder, branch=branch)
    else:
        Repo.clone_from(git_url, clone_into_folder)


class PullRequestGithub(object):

    def __init__(self, github_repo, working_branch, github_token):
        self.github_repo = github_repo
        self.working_branch = working_branch
        self.github_token = github_token

    def get_pr_number(self):
        url = f'https://api.github.com/repos/{self.github_repo}/pulls'
        payload = {}
        headers = {'Content-Type': 'application/json'}
        response = requests.request("GET", url, headers=headers, data=payload)
        pull_request_json = response.json()
        for pull in pull_request_json:
            name = pull["head"].get("ref")
            if name == self.working_branch:
                pr_number = pull["number"]
                if pr_number is None:
                    logger.error(f'Cant find Pull Request Number')
                    exit(1)
                else:
                    logger.info(f'Setting pull request number: {pr_number}')
                    return pr_number

    def get_github_username(self, branch):
        url = f'https://api.github.com/repos/{self.github_repo}/branches/{branch}'
        payload = {}
        headers = {}
        response = requests.request("GET", url, headers=headers, data=payload)
        branch = response.json()
        commit = branch["commit"]
        commit = commit["commit"]
        commit = commit["author"]
        if commit is not None:
            assignees_owner = commit["name"]
            if assignees_owner is not None:
                logger.info(f'Setting login name: {assignees_owner}')
            else:
                assignees_owner = "ebc-aixlib-bot"
                logger.info(f'Setting login name: {assignees_owner}')
        else:
            assignees_owner = "ebc-aixlib-bot"
            logger.info(f'Setting login name: {assignees_owner}')
        return assignees_owner

    def get_owner(self):
        return self.github_repo.split("/")[0]

    def post_pull_request(self, owner, main_branch, pull_request_title, pull_request_message):
        url = f'https://api.github.com/repos/{self.github_repo}/pulls'
        title = f'\"title\": \"{pull_request_title}\"'
        body = f'\"body\":\"{pull_request_message}\"'
        head = f'\"head\":\"{owner}:{self.working_branch}\"'
        base = f'\"base\": \"{main_branch}\"'
        message = f'\n	{title},\n	{body},\n	{head},\n	{base}\n'
        payload = "{" + message + "}"
        headers = self._get_headers()
        response = requests.request("POST", url, headers=headers, data=payload)
        if not response.ok:
            logger.error(response.text)
            if "A pull request already exists" in str(response.text):
                logger.info("The pull-request seems to already exist, won't update it.")
                return
            exit(1)
        else:
            logger.info(response.text)
        return response

    def update_pull_request_assignees(self, assignees_owner, label_name):
        pull_request_number = pull_request.get_pr_number()
        url = f'https://api.github.com/repos/{self.github_repo}/issues/{str(pull_request_number)}'
        assignees = f'\"assignees\":[\"{assignees_owner}\"]'
        labels = f'\"labels\":[\"CI\", \"{label_name}\"]'
        payload = "{\r\n" + assignees + ",\r\n" + labels + "\r\n}"
        headers = self._get_headers()
        response = requests.request("PATCH", url, headers=headers, data=payload)
        if str(response).find(f'<Response [422]>') > -1:
            assignees_owner = "ebc-aixlib-bot"
            assignees = f'\"assignees\":[\"{assignees_owner}\"]'
            payload = "{\r\n" + assignees + ",\r\n" + labels + "\r\n}"
            requests.request("PATCH", url, headers=headers, data=payload)
        logger.info(f'User {assignees_owner} assignee to pull request Number {str(pull_request_number)}')

    def post_pull_request_comment(self, post_message):
        requests.post(
            self._get_commands_url(),
            headers=self._get_headers(),
            data=json.dumps({"body": post_message})
        )

    def _get_headers(self):
        return {
            'Authorization': 'Bearer ' + self.github_token,
            'Content-Type': 'application/json'
        }

    def _get_commands_url(self):
        return f'https://api.github.com/repos/{self.github_repo}/issues/{pull_request.get_pr_number()}/comments'

    def get_pull_request_comments(self):
        response = requests.get(self._get_commands_url(), headers=self._get_headers())

        if response.status_code != 200:
            logger.error("Error retrieving comments (%s): %s", response.status_code, response.text)
            return None
        return response.json()


def post_pr_guideline(pull_request: PullRequestGithub, library: str, page_url: str, github_repository: str):
    comments = pull_request.get_pull_request_comments()
    if comments is None:
        logger.info("No PR associated to branch, won't post comment")
        return
    for comment in comments:
        if "Our CI pipeline will help you finalize your contribution" in comment['body']:
            logger.info(
                "Already posted the initial pull request information. "
                "Won't post it again."
            )
            return

    message = f"""
Thank you for making a Pull Request to {library}!

Our CI pipeline will help you finalize your contribution. 
Here's what is typically checked:
- HTML syntax of your models, primarily in your documentation.
- Adherence to the naming convention in all changed files.
- Ability to check all models.
- Ability to simulate all models, if they are examples.
- If your contribution changes existing reference results.

If HTML errors occur, I will fix the issues using a separate pull request.
For the other checks, I will post the results here: {page_url}/index.html

Tips to fix possible naming violations:
- Stick to the naming guidelines, e.g. [Namespace Requirements](https://github.com/{github_repository}/wiki/Namespaces)
- Do all paramaters, variables, models, etc. have a description?
- Use absolute paths to classes! -> {library}.Fluid.HeatExchangers.Radiator - Avoid: HeatExchangers.Radiator

If all CI stages pass and you have addressed possible naming violations, please consider the following:

- Use "group" and "tab" annotations to achieve a good visualization window.
- Use units consistently.
- Instantiate the replaceable medium package as:
replaceable package Medium = Modelica.Media.Interfaces.PartialMedium "Medium model";
instead of using a full media model like `{library}.Media.Water` directly.
- Never using absolute paths to files (e.g., `C:` or `D:`). Replace them with `modelica://{library}/...`.
- Ensure your documentation is helpful and concise.
- Make sure icons are clear. Please avoid using images!
- Stick to 80 characters per line, as long as it makes sense.
- Add or modify examples for new or revised models.
- Include a simulate-and-plot script as a regression test for new models. 
  How? Follow the documentation here: https://github.com/ibpsa/modelica-ibpsa/wiki/Unit-Tests#how-to-include-models-as-part-of-the-unit-tests
  Tip: To create the initial script, you can use Dymolas script generator, explained here: https://www.claytex.com/tech-blog/how-to-use-a-plot-script/)

Once you have addressed these points, you can assign a reviewer.
Although this process may seem tedious, ensuring CI passes allows the reviewer to focus 
their time on the actual modeling rather than syntax and unintended breakages caused by your changes.

If you have any questions or issues, please tag a library developer.
Once again, thank you for your valuable contribution!
"""
    pull_request.post_pull_request_comment(
        post_message=message
    )


def post_pr(
        pull_request,
        working_branch: str,
        main_branch: str,
        message: str,
        pull_request_title: str,
        label_name: str
):
    assignees_owner = pull_request.get_github_username(branch=working_branch)
    owner = pull_request.get_owner()
    pull_request.post_pull_request(owner=owner, main_branch=main_branch,
                                   pull_request_title=pull_request_title,
                                   pull_request_message=message)
    pull_request.update_pull_request_assignees(assignees_owner=assignees_owner,
                                               label_name=label_name)


def parse_args():
    parser = argparse.ArgumentParser(description="Set Github Environment Variables")
    check_test_group = parser.add_argument_group("Arguments to set Environment Variables")
    # [Github - settings]
    check_test_group.add_argument(
        "--github-repository",
        help="Environment Variable owner/RepositoryName"
    )
    check_test_group.add_argument(
        "--library",
        help="Library to test"
    )
    check_test_group.add_argument(
        "--working-branch",
        help="Your current working Branch",
        default="$CI_COMMIT_BRANCH"
    )
    check_test_group.add_argument(
        "--main-branch",
        help="your base branch (main)"
    )
    check_test_group.add_argument(
        "--github-token",
        default="${GITHUB_API_TOKEN}",
        help="Your Set GITHUB Token"
    )
    check_test_group.add_argument(
        "--page",
        help="Set your gitlab page url"
    )
    # [ bool - flag
    check_test_group.add_argument(
        "--prepare-plot-flag",
        action="store_true",
        default=False
    )
    check_test_group.add_argument(
        "--show-plot-flag",
        action="store_true",
        default=False
    )
    check_test_group.add_argument(
        "--post-pr-comment-flag",
        action="store_true",
    )
    check_test_group.add_argument(
        "--create-pr-flag",
        action="store_true",
    )
    check_test_group.add_argument(
        "--correct-html-flag",
        action="store_true",
    )
    check_test_group.add_argument(
        "--ibpsa-merge-flag",
        action="store_true",
    )
    check_test_group.add_argument(
        '--post-initial-pr-comment',
        action="store_true",
    )

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    pull_request = PullRequestGithub(
        github_repo=args.github_repository,
        working_branch=args.working_branch,
        github_token=args.github_token
    )
    page_url = f'{args.page}/{args.working_branch}'
    logger.info(f'Setting page url: {page_url}')

    from ModelicaPyCI.load_global_config import CI_CONFIG
    if args.post_pr_comment_flag is True:
        if not os.path.isfile(
                CI_CONFIG.get_file_path("result", "plot_dir").joinpath("index.html")
        ):
            logger.info("No results to report, won't post PR comment")
        else:
            plots_url = f'{page_url}/{CI_CONFIG.result.plot_dir}'
            pr_number = pull_request.get_pr_number()
            if args.prepare_plot_flag is True:
                message = (f'Errors in regression test. '
                           f'Compare the results on the following page\\n {plots_url}')
            elif args.show_plot_flag is True:
                message = (f'Reference results have been displayed graphically '
                           f'and are created under the following page {plots_url}')
            else:
                raise TypeError("No message option requested, either show_plot_flag "
                                "or prepare_plot_flag is required.")
            pull_request.post_pull_request_comment(
                post_message=message
            )

    if args.post_initial_pr_comment is True:
        post_pr_guideline(
            pull_request=pull_request, library=args.library,
            page_url=page_url, github_repository=args.github_repository
        )
    if args.correct_html_flag is True:
        MESSAGE = (
            f'Merge the corrected HTML Code. '
            f'After confirm the pull request, '
            f'**pull** your branch to your local repository. '
            f'**Delete** the Branch {args.working_branch}'
        )
        post_pr(
            pull_request=pull_request,
            message=MESSAGE,
            label_name='Correct HTML',
            main_branch=f'{args.working_branch.replace("correct_HTML_", "")}',
            working_branch=f'{args.working_branch.replace("correct_HTML_", "")}',
            pull_request_title=f'Corrected HTML Code in branch {args.working_branch}'
        )
    if args.ibpsa_merge_flag is True:
        MESSAGE = (
            f'**Following you will find the instructions for the IBPSA merge:**\\n  '
            f'1. Please pull this branch to your local repository.\\n '
            f'2. If you need to fix bugs or perform changes to the models of the {args.library}, '
            f'push these changes using any commit message but the configured merge trigger '
            f'(default is `ci_trigger_ibpsa`) to prevent to run the automatic IBPSA merge again.\\n '
            f'3. If the tests in the CI have passed successfully, merge this pull request'
        )
        post_pr(
            pull_request=pull_request,
            message=MESSAGE,
            label_name='ibpsamerge',
            main_branch=args.main_branch,
            working_branch=args.working_branch,
            pull_request_title='IBPSA Merge'
        )
