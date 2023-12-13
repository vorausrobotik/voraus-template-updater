"""Contains unit tests for template updates."""

import logging
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from github import GithubException
from github.ContentFile import ContentFile
from github.PullRequest import PullRequest
from requests.exceptions import HTTPError

from voraus_template_updater._schemas import CruftConfig, Status
from voraus_template_updater._update_projects import (
    PR_TITLE,
    _check_and_update_projects,
    _clone_repo,
    _get_cruft_config,
)

ORGANIZATION = "dummy-organization"
TEMPLATE_URL = "some-template-url"


@pytest.fixture(autouse=True)
def _set_up_mocks(
    cloned_repo_mock: MagicMock,  # pylint: disable=unused-argument
    cruft_config: MagicMock,  # pylint: disable=unused-argument
    organization_mock: MagicMock,
    repo_mock: MagicMock,
) -> Generator[None, None, None]:
    organization_mock.get_repos.return_value = [repo_mock]

    yield


@pytest.fixture(name="repo_mock")
def _repo_mock_fixture() -> Generator[MagicMock, None, None]:
    repo_mock = MagicMock()
    repo_mock.name = "repo"
    repo_mock.homepage = "https://some-repo.com"
    repo_mock.default_branch = "default-branch"
    repo_mock.archived = False

    content_file_mock = MagicMock(spec=ContentFile)
    content_file_mock.download_url = "some_url"
    repo_mock.get_contents.return_value = content_file_mock

    pull_request_mock = MagicMock(spec=PullRequest)
    pull_request_mock.created_at = datetime(2023, 12, 12)
    pull_request_mock.html_url = "https://some-pr.com"
    repo_mock.create_pull.return_value = pull_request_mock

    yield repo_mock


@pytest.fixture(name="organization_mock")
def _organization_mock_fixture() -> Generator[MagicMock, None, None]:
    """Returns an organization mock that can be used to register repositories via its `get_repos` method."""
    with patch("voraus_template_updater._update_projects.Github") as github_class_mock:
        github_instance_mock = MagicMock()
        github_class_mock.return_value = github_instance_mock

        organization_mock = MagicMock(name="org")
        github_instance_mock.get_organization.return_value = organization_mock

        yield organization_mock


@pytest.fixture(name="cruft_config")
def _cruft_config_fixture(request: pytest.FixtureRequest) -> Generator[CruftConfig, None, None]:
    config = CruftConfig(
        template=TEMPLATE_URL,
        context={"cookiecutter": {"full_name": "Some Maintainer"}},
        checkout="dev",
        commit="abc",
        directory=None,
    )

    if "no_get_cruft_config_mock" in request.keywords:
        yield MagicMock()
    else:
        with patch("voraus_template_updater._update_projects._get_cruft_config") as get_cruft_config_mock:
            get_cruft_config_mock.return_value = config

            yield config


@pytest.fixture(name="cloned_repo_mock")
def _cloned_repo_mock_fixture(request: pytest.FixtureRequest) -> Generator[MagicMock, None, None]:
    if "no_clone_repo_mock" in request.keywords:
        yield MagicMock()
    else:
        with patch("voraus_template_updater._update_projects._clone_repo") as clone_repo_mock:
            cloned_repo_mock = MagicMock()
            cloned_repo_mock.working_dir = "workdir"
            clone_repo_mock.return_value = cloned_repo_mock
            yield cloned_repo_mock


@patch("voraus_template_updater._update_projects.Github")
def test_github_access_token_gets_retrieved_from_env_var(
    github_class_mock: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    github_instance_mock = MagicMock()
    github_class_mock.return_value = github_instance_mock

    organization_mock = MagicMock(name="org")
    github_instance_mock.get_organization.return_value = organization_mock

    monkeypatch.setenv("GITHUB_TOKEN", "some_token")

    _check_and_update_projects(ORGANIZATION)

    github_class_mock.assert_called_once_with("some_token")


def test_archived_repos_get_skipped(repo_mock: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
    repo_mock.archived = True

    with caplog.at_level(logging.INFO):
        summary = _check_and_update_projects(ORGANIZATION)

    assert caplog.record_tuples == [
        ("voraus_template_updater", logging.INFO, f"Skipped '{repo_mock.name}'. Project archived.")
    ]

    assert len(summary.skipped_projects) == 1
    assert summary.skipped_projects[0].name == repo_mock.name
    assert summary.skipped_projects[0].reason == "Project archived"


def test_get_cruft_config_raises_error_if_more_than_one_cruft_json_found(repo_mock: MagicMock) -> None:
    content_file_mock = MagicMock(spec=ContentFile)

    repo_mock.get_contents.return_value = [content_file_mock, content_file_mock]

    with pytest.raises(
        RuntimeError,
        match=(
            "Repository 'repo' contains more than one '.cruft.json' file. This use case is currently not supported."
        ),
    ):
        _get_cruft_config(repo_mock)


@pytest.mark.no_get_cruft_config_mock
def test_repos_are_skipped_if_no_cruft_json(repo_mock: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
    repo_mock.get_contents.side_effect = GithubException(status=1)

    with caplog.at_level(logging.INFO):
        summary = _check_and_update_projects(ORGANIZATION)

    assert caplog.record_tuples == [
        (
            "voraus_template_updater",
            logging.INFO,
            f"Skipped '{repo_mock.name}'. Project does not have a '.cruft.json' file.",
        )
    ]

    assert len(summary.skipped_projects) == 1
    assert summary.skipped_projects[0].name == repo_mock.name
    assert summary.skipped_projects[0].reason == "No '.cruft.json' file"


@pytest.mark.no_get_cruft_config_mock
@patch("voraus_template_updater._update_projects.requests")
def test_repos_are_skipped_if_cruft_json_cannot_be_downloaded(
    requests_mock: MagicMock, repo_mock: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    response_mock = MagicMock()
    response_mock.raise_for_status.side_effect = HTTPError()
    requests_mock.get.return_value = response_mock

    with caplog.at_level(logging.WARNING):
        summary = _check_and_update_projects(ORGANIZATION)

    assert requests_mock.get.called_once_with(repo_mock.get_contents.return_value.download_url, timeout=10)
    assert response_mock.raise_for_status.called_once()

    assert caplog.record_tuples == [
        (
            "voraus_template_updater",
            logging.WARNING,
            f"Skipped '{repo_mock.name}'. Failed to retrieve '.cruft.json' file although the project has one.",
        )
    ]

    assert len(summary.skipped_projects) == 1
    assert summary.skipped_projects[0].name == repo_mock.name
    assert summary.skipped_projects[0].reason == "Cannot download '.cruft.json' file"


@pytest.mark.no_get_cruft_config_mock
@patch("voraus_template_updater._update_projects.requests.get")
def test_successful_cruft_config_retrieval(requests_get_mock: MagicMock, repo_mock: MagicMock) -> None:
    expected_config = CruftConfig(
        template=TEMPLATE_URL,
        context={"cookiecutter": {"full_name": "Some Maintainer"}},
        checkout="dev",
        commit="abc",
        directory=None,
    )

    repo_mock.get_contents.return_value.download_url = "http://example.com/.cruft.json"

    mock_response = MagicMock()
    mock_response.content = expected_config.model_dump_json()

    requests_get_mock.return_value = mock_response

    result = _get_cruft_config(repo_mock)

    assert result == expected_config


@pytest.mark.parametrize(["pr_title"], [("chore: Update Python template",), ("chore(template): Update template",)])
def test_repos_are_skipped_if_pull_request_exists(
    pr_title: str,
    repo_mock: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pr_mock = MagicMock()
    pr_mock.title = pr_title
    pr_mock.created_at = datetime(2023, 12, 12)
    pr_mock.html_url = "https://some-pr.com"

    repo_mock.get_pulls.return_value = [pr_mock]

    with caplog.at_level(logging.INFO):
        summary = _check_and_update_projects(ORGANIZATION)

    repo_mock.get_pulls.assert_called_once()

    assert caplog.record_tuples == [
        (
            "voraus_template_updater",
            logging.INFO,
            f"Skipped '{repo_mock.name}'. Project already has an active pull request for a template update.",
        )
    ]

    assert len(summary.projects) == 1
    assert summary.projects[0].status == Status.EXISTING_PR
    assert summary.projects[0].pull_request == pr_mock


@pytest.mark.no_clone_repo_mock
@patch("voraus_template_updater._update_projects.git.Repo.clone_from")
def test_clone_repo_modifies_url(clone_from_mock: MagicMock) -> None:
    _clone_repo("git@github.com:organization/repo.git", "token", Path())

    clone_from_mock.assert_called_once_with(
        url="https://x-access-token:token@github.com/organization/repo", to_path=Path()
    )


@patch("voraus_template_updater._update_projects.cruft.check")
def test_up_to_date_project(
    cruft_check_mock: MagicMock, repo_mock: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    cruft_check_mock.return_value = True

    with caplog.at_level(logging.INFO):
        summary = _check_and_update_projects(ORGANIZATION)

    assert caplog.record_tuples == [("voraus_template_updater", logging.INFO, f"Checking '{repo_mock.name}'")]

    assert len(summary.projects) == 1
    assert summary.projects[0].status == Status.UP_TO_DATE


@patch("voraus_template_updater._update_projects._get_pr_body")
@patch("voraus_template_updater._update_projects.cruft.update")
@patch("voraus_template_updater._update_projects.cruft.check")
def test_update_project_success(
    cruft_check_mock: MagicMock,
    cruft_update_mock: MagicMock,
    get_pr_body_mock: MagicMock,
    repo_mock: MagicMock,
    cloned_repo_mock: MagicMock,
    cruft_config: CruftConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    cruft_check_mock.return_value = False
    get_pr_body_mock.return_value = "pr body"

    branch_mock = MagicMock()
    branch_mock.name = "chore/update-template-"
    cloned_repo_mock.create_head.return_value = branch_mock

    with caplog.at_level(logging.INFO):
        summary = _check_and_update_projects(ORGANIZATION)

    cloned_repo_mock.create_head.assert_called_once()
    cloned_repo_mock.create_head.call_args[0][0].startswith(branch_mock.name)

    branch_mock.checkout.assert_called_once()
    cruft_update_mock.assert_called_once_with(Path("workdir"), checkout="dev")

    cloned_repo_mock.git.add.assert_called_with(all=True)
    cloned_repo_mock.index.commit.assert_called_with(PR_TITLE)
    cloned_repo_mock.git.push.assert_called_with("--set-upstream", "origin", branch_mock)

    repo_mock.create_pull.assert_called_once_with(
        base=repo_mock.default_branch, head=branch_mock.name, title=PR_TITLE, body="pr body"
    )

    assert caplog.record_tuples[1] == (
        "voraus_template_updater",
        logging.INFO,
        f"Created pull request for '{repo_mock.name}' to get up to date "
        f"with the template's '{cruft_config.checkout}' branch.",
    )

    assert len(summary.projects) == 1
    assert summary.projects[0].status == Status.UPDATED_THIS_RUN
    assert summary.projects[0].pull_request is not None
    assert summary.projects[0].pull_request.html_url == "https://some-pr.com"
