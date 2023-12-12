"""Contains an example summary for testing printed output."""

from datetime import datetime

from voraus_template_updater._schemas import Project, PullRequest, Status, Summary

summary = Summary(
    projects=[
        Project(
            name="project-1",
            maintainer="maintainer-1",
            default_branch="master",
            template_branch="main",
            old_template_commit="abc123",
            status=Status.UP_TO_DATE,
        ),
        Project(
            name="project-2",
            maintainer="maintainer-2",
            default_branch="main",
            template_branch="development",
            old_template_commit="abc123",
            status=Status.UP_TO_DATE,
        ),
        Project(
            name="project-3",
            maintainer="maintainer-1",
            default_branch="master",
            template_branch="main",
            old_template_commit="abc123",
            status=Status.UPDATED_THIS_RUN,
            pull_request=PullRequest(url="https://pr3.com", date=datetime(2023, 12, 15)),
        ),
        Project(
            name="project-4",
            maintainer="maintainer-2",
            default_branch="main",
            template_branch="development",
            old_template_commit="abc123",
            status=Status.UPDATED_THIS_RUN,
            pull_request=PullRequest(url="https://pr4.com", date=datetime(2023, 12, 15)),
        ),
        Project(
            name="project-5",
            maintainer="maintainer-1",
            default_branch="main",
            template_branch="main",
            old_template_commit="abc123",
            status=Status.EXISTING_PR,
            pull_request=PullRequest(url="https://pr5.com", date=datetime(2023, 12, 12)),
        ),
        Project(
            name="project-6",
            maintainer="maintainer-2",
            default_branch="main",
            template_branch="development",
            old_template_commit="abc123",
            status=Status.EXISTING_PR,
            pull_request=PullRequest(url="https://pr6.com", date=datetime(2023, 12, 12)),
        ),
    ],
    projects_with_wrong_template_url=[
        ("project-7", "https://wrong-template-url.com"),
        ("project-8", "https://wrong-template-url.com"),
    ],
    projects_without_cruft=[
        "project-9",
        "project-10",
    ],
)
