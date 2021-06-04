import os
from release_tools.versions import (VersionFileInPythonPackageBaseVersionProvider,
                                    ConstantCandidateProvider,
                                    GitPreviousVersionsProvider,
                                    VersionService)


def create_version_service(custom_tools_path, postfix):
    candidate_provider = ConstantCandidateProvider(postfix)
    base_version_provider = VersionFileInPythonPackageBaseVersionProvider()
    prev_versions_provider = GitPreviousVersionsProvider()

    return VersionService(candidate_provider, base_version_provider, prev_versions_provider)
