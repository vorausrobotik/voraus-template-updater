"""Contains Pydantic models for the project updater."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from github.PullRequest import PullRequest
from pydantic import BaseModel, ConfigDict
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text


class CruftConfig(BaseModel):
    """A cruft config as can be found in a '.cruft.json' file."""

    template: str
    commit: str
    checkout: Optional[str]
    context: dict
    directory: Optional[str]


class Status(Enum):
    """The update status a project can be in."""

    UP_TO_DATE = "Up to date"
    UPDATED_THIS_RUN = "Updated this run"
    EXISTING_PR = "Existing PR since {} ({} days)"


class SkippedProject(BaseModel):
    """Contains information about a skipped project and why it was skipped."""

    name: str
    url: str
    reason: str


class Project(BaseModel):
    """Contains information about a Python project that is maintained via a template."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    url: str
    maintainer: Optional[str] = None
    default_branch: str
    template_url: str
    template_branch: str
    old_template_commit: str
    status: Status
    pull_request: Optional[PullRequest] = None


class Summary(BaseModel):
    """A summary of the checked and updates projects."""

    projects: List[Project] = []
    skipped_projects: List[SkippedProject] = []

    def print(self) -> None:
        """Prints the summary."""
        if len(self.projects) > 0:
            _print_table_of_projects(self.projects)

        if len(self.skipped_projects) > 0:
            print("\n")
            _print_table_of_skipped_projects(self.skipped_projects)


def _print_table_of_projects(projects: List[Project]) -> None:
    title = _get_table_title(projects)
    table = Table(title=title, box=box.SQUARE)
    table.add_column("Maintainer")
    table.add_column("Projects")

    projects_by_maintainer = _get_projects_by_maintainer(projects)

    for maintainer, maintainers_projects in projects_by_maintainer.items():
        details = Text()
        maintainer_color = "green"

        for project in maintainers_projects:
            if project.status == Status.UP_TO_DATE:
                project_status = project.status.value
                status_color = "green"
            elif project.status == Status.UPDATED_THIS_RUN:
                project_status = project.status.value
                status_color = "yellow"
                maintainer_color = "red"
            else:
                assert project.pull_request is not None
                creation_date = datetime.strftime(project.pull_request.created_at, "%Y-%m-%d")
                open_since = (
                    datetime.now().replace(tzinfo=None) - project.pull_request.created_at.replace(tzinfo=None)
                ).days

                project_status = project.status.value.format(creation_date, open_since)
                status_color = "red"
                maintainer_color = "red"

            details.append("Project:         ")
            details.append(project.name)
            details.append("\nURL:             ")
            details.append(project.url)
            details.append("\nStatus:          ", status_color)
            details.append(project_status, status_color)

            if project.status != Status.UP_TO_DATE:
                assert project.pull_request is not None
                details.append("\nPull request:    ", status_color)
                details.append(project.pull_request.html_url, status_color)

            details.append("\nDefault branch:  ")
            details.append(project.default_branch)
            details.append("\nTemplate URL:    ")
            details.append(project.template_url)
            details.append("\nTemplate branch: ")
            details.append(project.template_branch)
            details.append("\n\n")

        table.add_row(Text(maintainer or "None", maintainer_color), details)

    Console().print(table)


def _get_table_title(projects: List[Project]) -> str:
    processed_projects = len(projects)
    up_to_date_projects = len(list(filter(lambda p: p.status == Status.UP_TO_DATE, projects)))

    return (
        f"Projects: {processed_projects}   "
        f"Outdated: {processed_projects - up_to_date_projects}   "
        f"Up to date: {up_to_date_projects}"
    )


def _get_projects_by_maintainer(projects: List[Project]) -> Dict[Optional[str], List[Project]]:
    projects_by_maintainer: Dict[Optional[str], List[Project]] = {}

    for project in sorted(
        projects, key=lambda x: x.maintainer or "z" * 100  # Projects without maintainers sorted to end
    ):
        if project.maintainer not in projects_by_maintainer:
            projects_by_maintainer[project.maintainer] = [project]
        else:
            projects_by_maintainer[project.maintainer].append(project)
    return projects_by_maintainer


def _print_table_of_skipped_projects(projects: List[SkippedProject]) -> None:
    table = Table(title=f"Skipped projects: {len(projects)}", box=box.SQUARE)
    table.add_column("Project")
    table.add_column("URL")
    table.add_column("Skip reason")

    for project in sorted(projects, key=lambda p: p.reason):
        table.add_row(project.name, project.url, project.reason)

    Console().print(table)
