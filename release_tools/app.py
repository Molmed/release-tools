from release_tools.versions import (FileSystemExecutableBaseVersionProvider,
                                    GitCandidateProvider, GitPreviousVersionsProvider, VersionService)


def create_version_service():
    candidate_provider = GitCandidateProvider()
    base_version_provider = FileSystemExecutableBaseVersionProvider(".release/version")
    prev_versions_provider = GitPreviousVersionsProvider()

    return VersionService(candidate_provider, base_version_provider, prev_versions_provider)
