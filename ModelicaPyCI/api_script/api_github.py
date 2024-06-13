import argparse
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

    def return_owner(self):
        owner = self.github_repo.split("/")
        return owner[0]

    def post_pull_request(self, owner, main_branch, pull_request_title, pull_request_message):
        url = f'https://api.github.com/repos/{self.github_repo}/pulls'
        title = f'\"title\": \"{pull_request_title}\"'
        body = f'\"body\":\"{pull_request_message}\"'
        head = f'\"head\":\"{owner}:{self.working_branch}\"'
        base = f'\"base\": \"{main_branch}\"'
        message = f'\n	{title},\n	{body},\n	{head},\n	{base}\n'
        payload = "{" + message + "}"
        headers = {
            'Authorization': 'Bearer ' + self.github_token,
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        if not response.ok:
            logger.error(response.text)
            if "A pull request already exists" in str(response.text):
                logger.info("The pull-request seems to already exist, won't update it.")
                exit(0)
            exit(1)
        else:
            logger.info(response.text)
        return response

    def update_pull_request_assignees(self, pull_request_number, assignees_owner, label_name):
        url = f'https://api.github.com/repos/{self.github_repo}/issues/{str(pull_request_number)}'
        assignees = f'\"assignees\":[\"{assignees_owner}\"]'
        labels = f'\"labels\":[\"CI\", \"{label_name}\"]'
        payload = "{\r\n" + assignees + ",\r\n" + labels + "\r\n}"
        headers = {
            'Authorization': 'Bearer ' + self.github_token,
            'Content-Type': 'application/json'
        }
        response = requests.request("PATCH", url, headers=headers, data=payload)
        if str(response).find(f'<Response [422]>') > -1:
            assignees_owner = "ebc-aixlib-bot"
            assignees = f'\"assignees\":[\"{assignees_owner}\"]'
            payload = "{\r\n" + assignees + ",\r\n" + labels + "\r\n}"
            requests.request("PATCH", url, headers=headers, data=payload)
        logger.info(f'User {assignees_owner} assignee to pull request Number {str(pull_request_number)}')

    def post_pull_request_comment(self, pull_request_number, post_message):
        url = f'https://api.github.com/repos/{self.github_repo}/issues/{str(pull_request_number)}/comments'
        message = f'{post_message}'
        body = f'\"body\":\"{message}\"'
        payload = "{" + body + "}"
        headers = {
            'Authorization': 'Bearer ' + self.github_token,
            'Content-Type': 'application/json'
        }
        requests.request("POST", url, headers=headers, data=payload)


def parse_args():
    parser = argparse.ArgumentParser(description="Set Github Environment Variables")
    check_test_group = parser.add_argument_group("Arguments to set Environment Variables")
    # [Github - settings]
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
        "--main-branch",
        help="your base branch (main)"
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

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    pull_request = PullRequestGithub(
        github_repo=args.github_repository,
        working_branch=args.working_branch,
        github_token=args.github_token
    )
    if not args.post_pr_comment_flag and not args.create_pr_flag:
        raise TypeError("Can't do anything, neither comment nor pr flag is set.")
    if args.post_pr_comment_flag is True:
        if not os.path.isdir(CI_CONFIG.get_file_path("result", "plot_dir")):
            logger.info("No results to report, won't post PR comment")
            exit(0)
        page_url = f'{args.gitlab_page}/{args.working_branch}/{CI_CONFIG.result.plot_dir}'
        logger.info(f'Setting gitlab page url: {page_url}')
        pr_number = pull_request.get_pr_number()
        if args.prepare_plot_flag is True:
            message = (f'Errors in regression test. '
                       f'Compare the results on the following page\\n {page_url}')
        elif args.show_plot_flag is True:
            message = (f'Reference results have been displayed graphically '
                       f'and are created under the following page {page_url}')
        else:
            raise TypeError("No message option requested, either show_plot_flag "
                            "or prepare_plot_flag is required.")
        pull_request.post_pull_request_comment(
            pull_request_number=pr_number,
            post_message=message
        )
    if args.create_pr_flag is True:
        working_branch = str
        main_branch = str
        pull_request_title = str
        label_name = str
        if args.correct_html_flag is True:
            pull_request_title = f'Corrected HTML Code in branch {args.working_branch}'
            message = (
                f'Merge the corrected HTML Code. '
                f'After confirm the pull request, '
                f'**pull** your branch to your local repository. '
                f'**Delete** the Branch {args.working_branch}'
            )
            label_name = f'Correct HTML'
            main_branch = f'{args.working_branch.replace("correct_HTML_", "")}'
            working_branch = f'{args.working_branch.replace("correct_HTML_", "")}'
        elif args.ibpsa_merge_flag is True:
            pull_request_title = f'IBPSA Merge'
            message = (
                f'**Following you will find the instructions for the IBPSA merge:**\\n  '
                f'1. Please pull this branch ibpsamerge to your local repository.\\n '
                f'2. As an additional saftey check please open the AixLib library in '
                f'dymola and check whether errors due to false package orders may have occurred. '
                f'You do not need to translate the whole library or simulate any models. '
                f'This was already done by the CI.\\n '
                f'3. If you need to fix bugs or perform changes to the models of the AixLib, '
                f'push these changes using this commit message to prevent to run the automatic '
                f'IBPSA merge again: **`fix errors manually`**. \\n '
                f'4. You can also output the different reference files between the IBPSA and '
                f'the AixLib using the CI or perform an automatic update of the referent files '
                f'which lead to problems. To do this, use one of the following commit messages '
                f'\\n **`ci_dif_ref`** \\n  **`ci_update_ref`** \\n '
                f'The CI outputs the reference files as artifacts in GitLab. '
                f'To find them go to the triggered pipeline git GitLab and find the '
                f'artifacts as download on the right site. \\n '
                f'5. If the tests in the CI have passed successfully, merge the branch ibpsamerge '
                f'to development branch. **Delete** the Branch {args.working_branch}'
            )
            label_name = f'ibpsamerge'
            main_branch = args.main_branch
            working_branch = args.working_branch
        else:
            raise TypeError("No message option requested, either correct_html_flag "
                            "or ibpsa_merge_flag is required.")

        assignees_owner = pull_request.get_github_username(branch=working_branch)
        owner = pull_request.return_owner()
        pr_response = pull_request.post_pull_request(owner=owner, main_branch=main_branch,
                                                     pull_request_title=pull_request_title,
                                                     pull_request_message=message)
        pr_number = pull_request.get_pr_number()
        pull_request.update_pull_request_assignees(pull_request_number=pr_number, assignees_owner=assignees_owner,
                                                   label_name=label_name)
