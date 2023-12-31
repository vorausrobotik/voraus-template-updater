"""Contains an example summary for testing printed output."""

from datetime import datetime
from unittest.mock import MagicMock

from github.PullRequest import PullRequest

from voraus_template_updater._schemas import Project, SkippedProject, Status, Summary


def _get_mocked_pull_request(url: str, date: datetime) -> MagicMock:
    pull_request_mock = MagicMock(spec=PullRequest)
    pull_request_mock.html_url = url
    pull_request_mock.created_at = date
    return pull_request_mock


summary = Summary(
    projects=[
        Project(
            name="project-1",
            url="https://project1.com",
            maintainer="maintainer-1",
            default_branch="master",
            template_url="https://first-template.com",
            template_branch="main",
            old_template_commit="abc123",
            status=Status.UP_TO_DATE,
        ),
        Project(
            name="project-2",
            url="https://project2.com",
            maintainer="maintainer-2",
            default_branch="main",
            template_url="https://second-template.com",
            template_branch="development",
            old_template_commit="abc123",
            status=Status.UP_TO_DATE,
        ),
        Project(  # No maintainer
            name="project-3",
            url="https://project3.com",
            default_branch="master",
            template_url="https://first-template.com",
            template_branch="main",
            old_template_commit="abc123",
            status=Status.UPDATED_THIS_RUN,
            pull_request=_get_mocked_pull_request(url="https://pr3.com", date=datetime(2023, 12, 15)),
        ),
        Project(
            name="project-4",
            url="https://project4.com",
            maintainer="maintainer-2",
            default_branch="main",
            template_url="https://second-template.com",
            template_branch="development",
            old_template_commit="abc123",
            status=Status.UPDATED_THIS_RUN,
            pull_request=_get_mocked_pull_request(url="https://pr4.com", date=datetime(2023, 12, 15)),
        ),
        Project(
            name="project-5",
            url="https://project5.com",
            maintainer="maintainer-1",
            default_branch="main",
            template_url="https://first-template.com",
            template_branch="main",
            old_template_commit="abc123",
            status=Status.EXISTING_PR,
            pull_request=_get_mocked_pull_request(url="https://pr5.com", date=datetime(2023, 12, 12)),
        ),
        Project(
            name="project-6",
            url="https://project6.com",
            maintainer="maintainer-2",
            default_branch="main",
            template_url="https://second-template.com",
            template_branch="development",
            old_template_commit="abc123",
            status=Status.EXISTING_PR,
            pull_request=_get_mocked_pull_request(url="https://pr6.com", date=datetime(2023, 12, 12)),
        ),
        Project(
            name="project-7",
            url="https://project7.com",
            maintainer="maintainer-3",
            default_branch="main",
            template_url="https://second-template.com",
            template_branch="development",
            old_template_commit="abc123",
            status=Status.UP_TO_DATE,
        ),
    ],
    skipped_projects=[
        SkippedProject(name="project-9", url="https://project9.com", reason="No .cruft.json"),
        SkippedProject(name="project-10", url="https://project10.com", reason="Project archived"),
        SkippedProject(name="project-11", url="https://project11.com", reason="No .cruft.json"),
    ],
)

# Uncomment to see what would get printed to the console
# summary.print()
