from release_tools.versions import (VersionFileInPythonPackageBaseVersionProvider,
                                    ConstantCandidateProvider,
                                    GitVersionHistoryProvider,
                                    VersionService)


def create_version_service(postfix):
    candidate_provider = ConstantCandidateProvider(postfix)
    base_version_provider = VersionFileInPythonPackageBaseVersionProvider()
    prev_versions_provider = GitVersionHistoryProvider()

    return VersionService(candidate_provider, base_version_provider, prev_versions_provider)
