"""Contains Pydantic models for the project updater."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from tabulate import tabulate


class Status(Enum):
    """The update status a project can be in."""

    UP_TO_DATE = "Up to date"
    UPDATED_THIS_RUN = "Updated this run -> {}"
    EXISTING_PR = "Existing PR for {} days ({}) -> {}"


class PullRequest(BaseModel):
    """Contains information about a pull request for a template update."""

    url: str
    date: datetime


class SkippedProject(BaseModel):
    """Contains information about a skipped project and why it was skipped."""

    name: str
    url: str
    reason: str


class Project(BaseModel):
    """Contains information about a Python project that is maintained via a template."""

    name: str
    maintainer: str
    default_branch: str
    template_branch: str
    old_template_commit: str
    status: Status
    pull_request: Optional[PullRequest] = None


class Summary(BaseModel):
    """A summary of the checked and updates projects."""

    projects: list[Project] = []
    skipped_projects: list[SkippedProject] = []

    def __str__(self) -> str:
        """Returns a string representation of this summary."""
        output = ""

        if len(self.projects) > 0:
            output += _table_of_projects(self.projects)

        if len(self.skipped_projects) > 0:
            output += "\n\n" + _table_of_skipped_projects(self.skipped_projects)

        return output


def _table_of_projects(projects: list[Project]) -> str:
    headers = ("Project", "Maintainer", "Default Branch", "Template Branch", "Status")
    data: list[tuple] = []

    for project in sorted(projects, key=lambda x: x.maintainer):
        project_data: tuple[str, ...] = (
            project.name,
            project.maintainer,
            project.default_branch,
            project.template_branch,
        )

        if project.status == Status.UP_TO_DATE:
            project_data = project_data + (project.status.value,)
        elif project.status == Status.UPDATED_THIS_RUN:
            assert project.pull_request is not None
            project_data = project_data + (project.status.value.format(project.pull_request.url),)
        else:
            assert project.pull_request is not None
            creation_date = datetime.strftime(project.pull_request.date, "%Y-%m-%d")
            open_since = (datetime.now().replace(tzinfo=None) - project.pull_request.date.replace(tzinfo=None)).days

            project_data = project_data + (
                project.status.value.format(open_since, creation_date, project.pull_request.url),
            )

        data.append(project_data)

    return tabulate(data, headers=headers) + "\n"


def _table_of_skipped_projects(projects: list[SkippedProject]) -> str:
    headers = ("Skipped Project", "Reason", "URL")
    data = [(p.name, p.reason, p.url) for p in projects]

    return tabulate(data, headers=headers) + "\n"
