# Assumes the following branch structure:
#   - develop:        used for the latest version of the code
#   - release-#.#.#:  0-n release branches for candidates
#   - hotfix-#.#.#:   0-n hotfix branches
#   - master:         always contains the latest release, tagged with versions
# Of these branches, there can be 0-1 active hotfix branch and 0-1 active release branch at a time
import sys
import os
import re
from release_tools.github import MergeException

MASTER_BRANCH = "master"
DEVELOP_BRANCH = "develop"
RELEASE_BRANCH_PRE = "release"
HOTFIX_BRANCH_PRE = "hotfix"


class Workflow:
    """
    Methods that have to do directly with the deployment workflow
    but who could work with different providers that look like the GithubProvider
    """
    def __init__(self, provider, conventions, whatif):
        self.provider = provider
        self.conventions = conventions
        self.whatif = whatif

    def get_latest_version(self):
        tag_name = self.provider.get_latest_version_tag_name()
        return self.conventions.get_version_from_tag(tag_name)

    def get_candidate_version(self, major_inc=False):
        return self.get_latest_version().inc_major() if major_inc \
            else self.get_latest_version().inc_minor()

    def get_hotfix_version(self):
        return self.get_latest_version().inc_patch()

    def get_candidate_branch(self, major_inc=False):
        version = self.get_candidate_version(major_inc=major_inc)
        return self.conventions.get_branch_name_from_version(version, RELEASE_BRANCH_PRE)

    def get_hotfix_branch(self):
        version = self.get_hotfix_version()
        return self.conventions.get_branch_name_from_version(version, HOTFIX_BRANCH_PRE)

    def create_release_candidate(self, major_inc=False):
        """
        Pre: The master branch has a tagged latest version (TODO: Support if it hasn't)

        The candidate release is based on info from Github about the latest release. For
        this, there should be a new branch, called release-#.#.#. If such a branch already
        exists, no new branch is created.

        The next step is to create a pull request from develop to the new release branch.
        This branch should then be code reviewed and eventually merged.
        """
        candidate_branch = self.get_candidate_branch(major_inc=major_inc)

        print("Creating a new branch, '{}' from master".format(candidate_branch))
        if not self.whatif:
            self.provider.create_branch_from_master(candidate_branch)

        # Merge from 'develop' into the new release branch:
        msg = "Merging from {} to {}".format(DEVELOP_BRANCH, candidate_branch)
        print(msg)
        if not self.whatif:
            self.provider.merge(candidate_branch, DEVELOP_BRANCH, msg)

    def create_hotfix(self):
        """
        Creates a hotfix branched off the master.

        Hotfix branches are treated similar to release branches, except the patch number
        has been increased instead and they are before the release in the deployment pipeline.
        """
        hotfix_branch = self.get_hotfix_branch()
        print("Creating a new hotfix branch, '{}' from master".format(hotfix_branch))
        if not self.whatif:
            self.provider.create_branch_from_master(hotfix_branch)

        print("Not merging automatically into a hotfix - hotfix patches should be sent as pull requests to it")

    def download_next_in_queue(self, path, force):
        queue = self.get_queue()
        if len(queue) > 1:
            print("There are more than one items in the queue. Downloading the first item.")

        branch = queue[0]
        full_path = os.path.join(path, branch)
        if not force and os.path.exists(full_path):
            print("There already exists a directory for the build at '{}'. Please specify a non-existing path or --force.".format(full_path))
            sys.exit(1)
        print("Downloading and extracting '{}' to '{}'. This may take a few seconds...".format(branch, full_path))
        if not self.whatif:
            self.provider.download_archive(branch, full_path)

    def download_release_history(self, path):
        print("Downloading release history to {}".format(path))
        if not self.whatif:
            self.provider.download_release_history(path)

    @staticmethod
    def get_hotfix_branches(branch_names):
        """
        Returns the version numbers for all hotfix branches defined
        """
        for branch_name in branch_names:
            if branch_name.startswith(HOTFIX_BRANCH_PRE):
                yield branch_name

    @staticmethod
    def get_release_branches(branch_names):
        """
        Returns the version numbers for all hotfix branches defined
        """
        for branch_name in branch_names:
            if branch_name.startswith(RELEASE_BRANCH_PRE):
                yield branch_name

    def get_pending_hotfix_branches(self, current_version, branch_names):
        for branch in self.get_hotfix_branches(branch_names):
            branch_version = Version.from_string(branch.split("-")[1])
            if branch_version[0] == current_version[0] and \
               branch_version[1] == current_version[1] and \
               branch_version[2] > current_version[2]:
                yield branch

    def get_pending_release_branches(self, current_tag, branch_names):
        for branch in self.get_release_branches(branch_names):
            branch_version = Version.from_string(branch.split("-")[1])
            if branch_version[0] > current_tag[0]:
                yield branch
            elif branch_version[0] == current_tag[0] and \
                 branch_version[1] > current_tag[1]:
                yield branch

    def get_queue(self):
        """
        Returns the queue. The queue can only exist of 0..1 release branches
        and 0..1 hotfix branches.

        The hotfix branch will always come before the release branch
        """
        branches = self.provider.get_branches()
        branch_names = [branch["name"] for branch in branches]
        current_version = self.get_latest_version()

        pending_hotfixes = list(self.get_pending_hotfix_branches(current_version, branch_names))
        pending_releases = list(self.get_pending_release_branches(current_version, branch_names))

        if len(pending_hotfixes) > 1:
            raise WorkflowException("Unexpected number of pending hotfixes: {}".format(len(pending_hotfixes)))

        if len(pending_releases) > 1:
            raise WorkflowException("Unexpected number of pending releases: {}".format(len(pending_releases)))

        queue = pending_hotfixes + pending_releases
        return queue

    def accept_release_candidate(self, force):
        """
        Accept the next item in the queue

        Merge from release-x.x.x into master and tag master with vx.x.x

        If force is not set to True, the user will be prompted if more than one
        release is in the queue.
        """
        queue = self.get_queue()

        if len(queue) == 0:
            print("The queue is empty. Nothing to accept.")
            return

        branch = queue[0]

        # TODO: Don't accept the release if it has a pull request.
        # That might be a hotfix waiting to be merged.
        if self.provider.has_pull_requests(branch):
            print("The branch being accepted has pull requests")
            print("which need to be resolved before accepting.")
            sys.exit(1)

        next_release = None

        if len(queue) > 1:
            print("There are more than one item in the queue:")
            for current in queue:
                print("  {}".format(current))

            if not force:
                print("The first branch '{}' will be accepted. Continue?".format(branch))
                accepted = raw_input("y/n> ")

                if accepted != "y":
                    print("Action cancelled by user")
                    return
            else:
                print("Force set to true. The first branch will automatically be accepted")

            next_release = queue[1]

        def merge_cond(base, head):
            msg = "Merging from '{}' to '{}'".format(head, base)
            print(msg)
            if not self.whatif:
                try:
                    self.provider.merge(base, head, msg)
                except MergeException:
                    print("Merge exception while merging '{}' to '{}'. ".format(head, base) +
                          "This can happen if there was a hotfix release in between.")
                    sys.exit(1)

        merge_cond(MASTER_BRANCH, branch)

        tag_name = self.conventions.get_tag_from_branch(branch)
        print("Tagging HEAD on {} as release {}".format(MASTER_BRANCH, tag_name))
        if not self.whatif:
            self.provider.tag_release(tag_name, MASTER_BRANCH)

        if branch.startswith("hotfix"):
            # We don't know if the dev needs this in 'develop' and in the next release, but it's likely
            # so we send a pull request to those.
            print("Hotfix branch merged - sending pull requests to develop and release")
            print("These pull requests need to be reviewed and potential merge conflicts resolved")

            msg = "Apply hotfix '{}' to '{}'".format(branch, DEVELOP_BRANCH)
            body = "Pull request was made automatically by release-tools"
            self.provider.create_pull_request(DEVELOP_BRANCH, branch, msg, body)

            if next_release:
                msg = "Apply hotfix '{}' to '{}'".format(branch, next_release)
                body = "Pull request was made automatically by release-tools"
                self.provider.create_pull_request(next_release, branch, msg, body)


class WorkflowException(Exception):
    pass


class Version(tuple):
    """
    Represents a version as a (major, minor, patch)
    tuple, with methods to alter it conveniently
    """
    def __repr__(self):
        return ".".join([str(num) for num in self])

    def inc_major(self):
        """Increments the major version, setting less significant values to zero"""
        return Version([self.major() + 1, 0, 0])

    def inc_minor(self):
        """Increments the minor version, setting less significant values to zero"""
        return Version([self.major(), self.minor() + 1, 0])

    def inc_patch(self):
        return Version([self.major(), self.minor(), self.patch() + 1])

    def major(self):
        return self[0]

    def minor(self):
        return self[1]

    def patch(self):
        return self[2]

    @staticmethod
    def from_string(s):
        return Version(map(int, s.split(".")))


class Conventions:
    """
    Defines naming conventions between versions, tags and branches.
    """
    @staticmethod
    def get_version_from_tag(tag):
        pattern = r"v(?P<major>\d+).(?P<minor>\d+).(?P<patch>\d+)"
        m = re.match(pattern, tag)
        return Version(map(int, (m.group('major'), m.group('minor'), m.group('patch'))))

    @staticmethod
    def get_branch_name_from_version(version, prefix):
        """Given a version tuple, returns a valid branch name"""
        return "{}-{}".format(prefix, version)

    @staticmethod
    def get_tag_from_branch(branch_name):
        """
        Returns the tag we use for tagging the release. Base it on the
        branch name to avoid errors
        """
        # This is kinda ugly
        tag_name = branch_name.replace(RELEASE_BRANCH_PRE + "-", "v")
        tag_name = tag_name.replace(HOTFIX_BRANCH_PRE + "-", "v")
        return tag_name

