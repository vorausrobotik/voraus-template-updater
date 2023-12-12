"""Contains Pydantic models for the project updater."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from tabulate import tabulate


class Status(Enum):
    UP_TO_DATE = "Up to date"
    UPDATED_THIS_RUN = "Updated this run -> {}"
    EXISTING_PR = "Existing PR for {} days ({}) -> {}"


class PullRequest(BaseModel):
    """Contains information about a pull request for a template update."""

    url: str
    date: datetime


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
    projects_without_cruft: list[str] = []

    def __str__(self) -> str:
        """Returns a string representation of this summary."""
        output = ""

        if len(self.projects) > 0:
            output += _table_of_projects(self.projects)

        if len(self.projects_without_cruft) > 0:
            output += "\nProjects without .cruft.json:\n"
            for project_name in sorted(self.projects_without_cruft):
                output += project_name + "\n"

        return output


def _table_of_projects(projects: list[Project], with_existing_pr: bool = False) -> str:
    headers: tuple[str, ...] = ("Project", "Maintainer", "Default Branch", "Template Branch", "Status")
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
            project_data = project_data + (project.status.value.format(project.pull_request.url),)
        else:
            creation_date = datetime.strftime(project.pull_request.date, "%Y-%m-%d")
            open_since = (datetime.now().replace(tzinfo=None) - project.pull_request.date.replace(tzinfo=None)).days

            project_data = project_data + (
                project.status.value.format(open_since, creation_date, project.pull_request.url),
            )

        data.append(project_data)

    return tabulate(data, headers=headers) + "\n\n"
