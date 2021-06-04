# Tests the tag command
import pytest
from unittest.mock import MagicMock
from release_tools.versions import VersionService, Version, VersionHasAlreadyBeenReleased


def create_svc(base_version, candidate, old_versions):
    """Returns a real VersionService where all providers are mocked"""
    base_version_provider = MagicMock()
    base_version_provider.get_version.return_value = base_version

    candidate_provider = MagicMock()
    candidate_provider.get_candidate.return_value = candidate

    prev_versions_provider = MagicMock()
    prev_versions_provider.get_versions.return_value = old_versions
    return VersionService(candidate_provider, base_version_provider, prev_versions_provider)


def test_with_no_rc__provides_next_rc():
    service = create_svc(
        base_version="v1.0.0",
        candidate="rc",
        old_versions=[]
    )
    version = service.get_next_version()
    assert str(version) == "v1.0.0-rc1"


def test_with_one_rc__provides_next_rc():
    service = create_svc(
        base_version="v1.0.0",
        candidate="rc",
        old_versions=[
            "v1.0.0-rc1"
        ]
    )
    version = service.get_next_version()
    assert str(version) == "v1.0.0-rc2"


def test_with_two_rc__provides_next_rc():
    service = create_svc(
        base_version="v1.0.0",
        candidate="rc",
        old_versions=[
            "v1.0.0-rc1",
            "v1.0.0-rc2"
        ]
    )
    version = service.get_next_version()
    assert str(version) == "v1.0.0-rc3"

@pytest.mark.testme
def test__regression__when_10th__next_is_11th():
    service = create_svc(
        base_version="v1.0.0",
        candidate="rc",
        old_versions=[
            "v1.0.0-rc10",
        ]
    )
    version = service.get_next_version()
    assert str(version) == "v1.0.0-rc11"


def test_already_have_released_it__should_fail():
    service = create_svc(
        base_version="v1.0.0",
        candidate="rc",
        old_versions=[
            "v1.0.0",  # We have released this version already
        ]
    )
    with pytest.raises(VersionHasAlreadyBeenReleased):
        service.get_next_version()


def test_with_one_rc__can_release():
    service = create_svc(
        base_version="v1.0.0",
        candidate="",
        old_versions=[
            "v1.0.0-rc1",
        ]
    )
    version = service.get_next_version()
    assert str(version) == "v1.0.0"


