"""Contains Pydantic models for the project updater."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from tabulate import tabulate


class ExistingPullRequest(BaseModel):
    """Contains information about an existing pull request for a template update."""

    url: str
    date: datetime


class Project(BaseModel):
    """Contains information about a Python project that is maintained via the template."""

    name: str
    maintainer: str
    default_branch: str
    template_branch: str
    current_template_commit: str
    existing_pr: Optional[ExistingPullRequest] = None


class Summary(BaseModel):
    """A summary of the checked and updates projects."""

    up_to_date_projects: list[Project] = []
    updated_projects: list[Project] = []
    projects_with_existing_pr: list[Project] = []
    projects_with_wrong_template_url: list[tuple[str, str]] = []
    projects_without_cruft: list[str] = []

    def __str__(self) -> str:
        """Returns a string representation of this summary."""
        output = ""

        if len(self.up_to_date_projects) > 0:
            output += "\nAlready up-to-date projects:\n"
            output += _table_of_projects(self.up_to_date_projects)

        if len(self.updated_projects) > 0:
            output += "\nUpdated projects during this run:\n"
            output += _table_of_projects(self.updated_projects)

        if len(self.projects_with_existing_pr) > 0:
            output += "\nProjects with existing template update PRs:\n"
            output += _table_of_projects(self.projects_with_existing_pr, with_existing_pr=True)

        if len(self.projects_with_wrong_template_url) > 0:
            output += "\nProjects with wrong template URL:\n"
            for project_name, url in sorted(self.projects_with_wrong_template_url, key=lambda x: x[0]):
                output += f"Project: {project_name} -> Template URL: {url}\n"

        if len(self.projects_without_cruft) > 0:
            output += "\nProjects without .cruft.json:\n"
            for project_name in sorted(self.projects_without_cruft):
                output += project_name + "\n"

        return output


def _table_of_projects(projects: list[Project], with_existing_pr: bool = False) -> str:
    headers: tuple[str, ...] = ("Maintainer", "Project", "Default Branch", "Template Branch")
    if with_existing_pr:
        headers = headers + ("Existing Pull Request",)

    data: list[tuple] = []
    for project in sorted(projects, key=lambda x: x.maintainer):
        project_data: tuple[str, ...] = (
            project.maintainer,
            project.name,
            project.default_branch,
            project.template_branch,
        )

        if with_existing_pr and project.existing_pr is not None:
            pull_request = project.existing_pr
            creation_date = datetime.strftime(pull_request.date, "%y-%m-%d")
            open_since = (datetime.now().replace(tzinfo=None) - pull_request.date.replace(tzinfo=None)).days

            project_data = project_data + (f"Since {creation_date} ({open_since} days) -> {pull_request.url}",)

        data.append(project_data)

    return tabulate(data, headers=headers) + "\n\n"
