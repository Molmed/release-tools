from __future__ import print_function
import subprocess
import re
from dataclasses import dataclass
from subprocess import check_output
from copy import copy


@dataclass
class Version:
    # A prefix, used for debugging the tool itself without cluttering real tags
    prefix: str

    # Semver:
    major: int
    minor: int
    patch: int

    # The candidate type
    candidate: str

    # A sequential number after the branch name
    candidate_seq: int

    @property
    def release_tuple(self):
        """
        Returns the part of the version that ignores the candidate type
        """
        return self.prefix, self.major, self.minor, self.patch

    @property
    def is_release(self):
        return self.candidate is None

    @staticmethod
    def parse(version_str: str):
        version_pattern = (r"^"                   # Match from the start of the whole string
                           r"(?P<prefix>.+)?"     # Optional prefix (for debug reasons only)
                           r"(?P<major>\d+)\."    # Major
                           r"(?P<minor>\d+)\."    # Minor
                           r"(?P<patch>\d+)"      # Patch
                           r"(-(?P<candidate>.+)"      # Postfix follows all candidates
                           # A sequential number is included for all candidates
                           r"(?P<candidate_seq>\d+)"
                           r")?"
                           r"$"                   # Stop matching at the end of the entire string
                           )

        m = re.match(version_pattern, version_str)
        if not m:
            return None

        matches_dict = m.groupdict()

        def intify(key):
            matches_dict[key] = int(matches_dict[key]) if (
                key in matches_dict and matches_dict[key]) else matches_dict[key]

        intify("major")
        intify("minor")
        intify("patch")
        intify("candidate_seq")

        version = Version(**matches_dict)
        return version

    def __repr__(self):
        ret = "{}{}.{}.{}".format(self.prefix, self.major, self.minor, self.patch)

        if self.candidate:
            ret = "{}-{}{}".format(ret, self.candidate, self.candidate_seq)

        return ret


class VersionService:
    def __init__(self, candidate_provider, base_version_provider, previous_versions_provider):
        """
        Generates a new version candidate based on a base version
        """
        self.candidate_provider = candidate_provider
        self.base_version_provider = base_version_provider
        self.previous_versions_provider = previous_versions_provider

    def get_next_version(self, is_release=False):
        base_version = self.base_version_provider.get_version()
        base_version = Version.parse(base_version)
        if not base_version:
            raise AssertionError("Version provider is not returning a suggestion")
        if base_version.candidate:
            raise AssertionError("The base version should not have a candidate marker")
        if base_version.candidate_seq:
            raise AssertionError("The base version should not have a candidate sequence")

        if is_release:
            # This is a release so we use the base version
            return base_version

        # This is not a release, so we need to increment the candidate sequence number, or
        # mark this as the first release of this candidate type

        candidate_type = self.candidate_provider.get_candidate()

        def find_same_version_and_branch(version):
            """
            Find matches to `version`, ignoring the information about candidate builds. That is
            if the input is v1.0.0, it will find find both v1.0.0 and v1.0.0-rc1

            Raises an error if it finds a release
            """
            for current in self.get_versions():
                if current.release_tuple == version.release_tuple:
                    if current.is_release:
                        raise VersionHasAlreadyBeenReleased(
                                "Found a release branch when expecting candidates only")

                    if current.candidate == candidate_type:
                        # Found a match:
                        yield current

        versions = list(find_same_version_and_branch(base_version))

        if not versions:
            # We have no version from the same branch
            ret = copy(base_version)
            ret.candidate = candidate_type
            ret.candidate_seq = 1
            return ret

        highest_seq = max(versions, key=lambda x: x.candidate_seq)
        ret = copy(highest_seq)
        ret.candidate_seq += 1
        return ret

    def get_versions(self):
        """
        Returns instances of `Version`, based on raw git tags. Returns only tags that can
        be parsed as git tags.
        """
        for tag in self.previous_versions_provider.get_versions():
            version = Version.parse(tag)
            if version:
                yield version


class GitCandidateProvider:
    def get_candidate(self):
        """
        Returns the current branch
        """
        return subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode("utf-8").strip()


class GitPreviousVersionsProvider:
    @staticmethod
    def get_versions():
        """
        Returns git tags in a raw text format
        """
        for line in subprocess.check_output(["git", "tag"]).splitlines():
            yield line.decode("utf-8")


class FileSystemExecutableBaseVersionProvider:
    """
    Fetches the basic version we want by executing a executable (e.g. a bash script) that the user
    provides
    """

    def __init__(self, executable_path):
        self.executable_path = executable_path

    def get_version(self):
        """
        Returns the target version (the one we're aiming for after release candidates) as a string
        """
        try:
            output = check_output(self.executable_path)
            return output.decode("utf-8")
        except:
            raise FileSystemExecutableDoesNotExist(self.executable_path)


class FileSystemExecutableDoesNotExist(Exception):
    pass


class VersionHasAlreadyBeenReleased(Exception):
    pass
