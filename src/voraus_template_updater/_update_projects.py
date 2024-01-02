"""Checks and updates GitHub repositories that are based on a cookiecutter template and managed with cruft."""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

import cruft
import git
import requests
from git.repo import Repo
from github import Github
from github.GithubException import GithubException
from github.PullRequest import PullRequest as GitHubPullRequest
from github.Repository import Repository
from requests import HTTPError
from typer import Argument, Option, Typer
from typing_extensions import Annotated

from voraus_template_updater._schemas import CruftConfig, Project, SkippedProject, Status, Summary

PR_TITLE_LEGACY = ("chore: Update Python template",)  # Previously used pull request titles
PR_TITLE = "chore(template): Update template"
PR_BODY_HEADER = (
    "Contains the following changes to get up-to-date with the newest version of the template's '{}' branch.\n\n"
)

_logger = logging.getLogger("voraus_template_updater")
_logger.setLevel(logging.INFO)
_console_handler = logging.StreamHandler()
_console_handler.formatter = logging.Formatter("[%(name)-20s][%(levelname)-8s] %(message)s")
_logger.addHandler(_console_handler)

app = Typer(add_completion=False)


@app.command()
def _check_and_update_projects(  # pylint: disable=dangerous-default-value # Only meant for CLI usage
    github_organization: Annotated[str, Argument(help="The GitHub organization in which to update repositories.")],
    github_access_token: Annotated[
        str,
        Option(
            help=(
                "A GitHub token to clone repositories and create pull requests. "
                "Defaults to the 'GITHUB_TOKEN' environment variable."
            )
        ),
    ] = "",
    maintainer_field: Annotated[
        List[str],
        Option(
            help="Cookiecutter variable name that contains the name of a project maintainer. "
            "For example, if one of the templates you are updating contains a 'maintainer' variable, specify this "
            "option as 'maintainer'. Can be provided multiple times if multiple templates are processed and use "
            "different variable names to define a maintainer. The first hit from the list will be used."
        ),
    ] = ["full_name"],
) -> Summary:
    summary = Summary()

    github_access_token = github_access_token or os.environ["GITHUB_TOKEN"]

    for repo in Github(github_access_token).get_organization(github_organization).get_repos():
        if repo.archived:
            _logger.info(f"Skipped '{repo.name}'. Project archived.")
            summary.skipped_projects.append(
                SkippedProject(name=repo.name, url=repo.html_url, reason="Project archived")
            )
            continue

        try:
            cruft_config = _get_cruft_config(repo)
        except GithubException:
            _logger.info(f"Skipped '{repo.name}'. Project does not have a '.cruft.json' file.")
            summary.skipped_projects.append(
                SkippedProject(name=repo.name, url=repo.html_url, reason="No '.cruft.json' file")
            )
            continue
        except HTTPError:
            _logger.warning(
                f"Skipped '{repo.name}'. Failed to retrieve '.cruft.json' file although the project has one."
            )
            summary.skipped_projects.append(
                SkippedProject(name=repo.name, url=repo.html_url, reason="Cannot download '.cruft.json' file")
            )
            continue

        template_url = cruft_config.template

        maintainer = _get_maintainer(maintainer_field, cruft_config)

        project = Project(
            name=repo.name,
            url=repo.html_url,
            maintainer=maintainer,
            default_branch=repo.default_branch,
            template_url=template_url,
            template_branch=cruft_config.checkout or "main",
            old_template_commit=cruft_config.commit,
            status=Status.UP_TO_DATE,
        )

        if (pull_request := _get_existing_pull_request(repo)) is not None:
            _logger.info(f"Skipped '{repo.name}'. Project already has an active pull request for a template update.")
            summary.projects.append(
                project.model_copy(update={"status": Status.EXISTING_PR, "pull_request": pull_request})
            )
            continue

        with TemporaryDirectory() as tmp_path:
            local_repo = _clone_repo(repo.clone_url, github_access_token, Path(tmp_path))

            _logger.info(f"Checking '{repo.name}'")

            if cruft.check(Path(local_repo.working_dir), project.template_branch) is True:
                summary.projects.append(project)
                continue

            pull_request = _update_project(repo, local_repo, project, github_access_token)
            summary.projects.append(
                project.model_copy(update={"status": Status.UPDATED_THIS_RUN, "pull_request": pull_request})
            )

    summary.print()

    return summary


def _get_cruft_config(repo: Repository) -> CruftConfig:
    cruft_json = repo.get_contents(".cruft.json")
    if isinstance(cruft_json, List):
        raise RuntimeError(
            f"Repository '{repo.name}' contains more than one '.cruft.json' file. "
            "This use case is currently not supported."
        )

    response = requests.get(cruft_json.download_url, timeout=10)
    response.raise_for_status()

    return CruftConfig.model_validate_json(response.content)


def _get_maintainer(maintainer_fields: List[str], cruft_config: CruftConfig) -> Optional[str]:
    maintainer = None
    for field_name in maintainer_fields:
        if field_name in cruft_config.context["cookiecutter"]:
            maintainer = cruft_config.context["cookiecutter"][field_name]
            break
    return maintainer


def _clone_repo(repo_url: str, github_access_token: str, target_path: Path) -> Repo:
    url = repo_url.replace("git@github.com:", "https://github.com/")
    url = url[:-4] if url.endswith(".git") else url  # str.removesuffix only supported by Python >= 3.9
    url = url.replace("github.com", f"x-access-token:{github_access_token}@github.com")

    return git.Repo.clone_from(
        url=url,
        to_path=target_path,
    )


def _get_existing_pull_request(repo: Repository) -> Optional[GitHubPullRequest]:
    for pull_request in repo.get_pulls():
        if pull_request.title in (PR_TITLE,) + PR_TITLE_LEGACY:
            return pull_request
    return None


def _update_project(
    remote_repo: Repository, local_repo: Repo, project: Project, github_access_token: str
) -> GitHubPullRequest:
    branch = local_repo.create_head(
        f"chore/update-template-{datetime.isoformat(datetime.now(), timespec='seconds').replace(':', '-')}"
    )
    branch.checkout()

    cruft.update(Path(local_repo.working_dir), checkout=project.template_branch)

    template_commit_messages = _get_template_commit_messages(project, github_access_token)
    local_repo.git.add(all=True)
    if len(template_commit_messages) == 1:
        local_repo.index.commit(template_commit_messages[0])
    else:
        local_repo.index.commit(PR_TITLE)
    local_repo.git.push("--set-upstream", "origin", branch)

    pr_title = _get_pr_title(template_commit_messages)
    pr_body = _get_pr_body(project, template_commit_messages)

    pull_request = remote_repo.create_pull(
        base=remote_repo.default_branch, head=branch.name, title=pr_title, body=pr_body
    )

    _logger.info(
        f"Created pull request for '{remote_repo.name}' to get "
        f"up to date with the template's '{project.template_branch}' branch."
    )

    return pull_request


def _get_template_commit_messages(project: Project, github_access_token: str) -> List[str]:
    with TemporaryDirectory() as tmp_path:
        template_repo = _clone_repo(project.template_url, github_access_token, Path(tmp_path))

        template_repo.git.checkout(project.template_branch)
        newest_template_commit = template_repo.git.rev_parse(project.template_branch)
        commits = list(template_repo.iter_commits(f"{project.old_template_commit}..{newest_template_commit}"))

        commit_messages = [
            commit.message if isinstance(commit.message, str) else commit.message.decode() for commit in commits
        ]

    # The first line of a commit from a pull request usually contains a reference to the GitHub pull request, for
    # example `feat: Added feature (#123)`. However GitHub will resolve these links to the current repository although
    # they refer to pull requests in the template repository. We therefore need to change these links to point to the
    # pull requests in the template repository.
    link = project.template_url.replace("git@github.com:", "https://github.com/")
    link = link[:-4] if link.endswith(".git") else link  # str.removesuffix only supported by Python >= 3.9
    link += "/pull/{}"
    for i_message, message in enumerate(commit_messages):
        commit_messages[i_message] = re.sub(
            r"\(#(\d+)\)", lambda match: f"([PR]({link.format(match.groups()[0])}))", message
        )

    return commit_messages


def _get_pr_title(template_commit_messages: List[str]) -> str:
    if len(template_commit_messages) == 1:
        message = template_commit_messages[0]
        return message.strip().splitlines()[0]

    return PR_TITLE


def _get_pr_body(project: Project, template_commit_messages: List[str]) -> str:
    if len(template_commit_messages) == 1:
        message = template_commit_messages[0]
        lines = message.strip().splitlines()
        if len(lines) > 1:
            return "".join(message.strip().splitlines()[1:])
        return ""

    # Indent all lines after the first line of a commit message by two spaces
    # This leads to nicer bullet points in the pull request body
    template_commit_messages = [
        "\n  ".join(commit_message.strip().splitlines()) for commit_message in template_commit_messages
    ]

    # Construct a pull request message containing the PR header and a bullet point list of changes and their explanation
    return PR_BODY_HEADER.format(project.template_branch) + "- " + "\n\n- ".join(template_commit_messages) + "\n"


if __name__ == "__main__":  # pragma: no cover
    _check_and_update_projects("vorausrobotik")
