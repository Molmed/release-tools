#!/usr/bin/env python
import requests
import logging
import click
import re
import zipfile
import StringIO
import os
import sys

# Assumes the following branch structure:
#   - develop:        used for the latest version of the code
#   - release-#.#.#:  0-n release branches for candidates
#   - master:         always contains the latest release, tagged with versions

MASTER_BRANCH = "master"
DEVELOP_BRANCH = "develop"
RELEASE_BRANCH_PRE = "release"

def get_access_token():
    with open('token.secret') as f:
        access_token = f.readline().strip()
        return access_token

def access_token_postfix():
    return "?access_token={}".format(get_access_token())

access_token = get_access_token()

class GithubException(Exception):
    pass

def get_latest_version(owner, repo):
    url = "https://api.github.com/repos/{}/{}/releases/latest{}".format(owner, repo, access_token_postfix())
    response = requests.get(url)
    if response.status_code == 200:
        json = response.json()
        tag_name = json["tag_name"]
        pattern = r"v(?P<major>\d+).(?P<minor>\d+).(?P<patch>\d+)"
        m = re.match(pattern, tag_name)
        return tuple(map(int, (m.group('major'), m.group('minor'), m.group('patch'))))
    else:
        raise GithubException(response.text)

def get_candidate_version(owner, repo):
    latest = get_latest_version(owner, repo)
    return (latest[0], latest[1] + 1, latest[2])

def create_new_branch(owner, repo, token, name):
    pass

def get_refs_heads(owner, repo):
    access_token = get_access_token()
    url = "https://api.github.com/repos/{}/{}/git/refs/heads?access_token={}".format(owner, repo, access_token)
    response = requests.get(url)
    return response.json()

def get_refs_head(owner, repo, ref):
    heads = get_refs_heads(owner, repo)
    filtered = [x for x in heads if x["ref"] == ref]
    assert len(filtered) == 1
    return filtered[0]["object"]["sha"]

def create_branch_from_master(owner, repo, new_branch):
    """
    Creates a new branch from the master branch

    If the branch already exists, it will be ignored without an exception
    """
    sha = get_refs_head(owner, repo, "refs/heads/master")

    body = {"ref": "refs/heads/{}".format(new_branch), "sha": sha}
    url = "https://api.github.com/repos/{}/{}/git/refs{}".format(owner, repo, access_token_postfix())
    response = requests.post(url, json=body)

    if response.status_code == 201:
        print "Release branch successfully created"
    elif response.status_code == 422:
        print "Release branch already exists"

def get_candidate_branch(owner, repo):
    candidate = get_candidate_version(owner, repo)
    candidate_str = ".".join([str(num) for num in candidate])
    candidate_branch = "{}-{}".format(RELEASE_BRANCH_PRE, candidate_str)
    return candidate_branch

def get_release_tag(owner, repo):
    candidate = get_candidate_version(owner, repo)
    candidate_str = ".".join([str(num) for num in candidate])
    tag_name = "v{}".format(candidate_str)
    return tag_name

def merge(owner, repo, base, head, commit_message):
    url = "https://api.github.com/repos/{}/{}/merges{}".format(owner, repo, access_token_postfix())
    json = {"base": base, "head": head, "commit_message": commit_message}
    response = requests.post(url, json=json)
    if response.status_code == 201:
        print "Successfully merged '{}' into '{}'".format(head, base)
    elif response.status_code == 204:
        print "Nothing to merge"
    else:
        msg = "Unexpected result code from Github ({}): {}".format(response.status_code, response.text)
        raise GithubException(msg)

def list_pull_requests(owner, repo):
    url = "https://api.github.com/repos/{}/{}/pulls{}".format(owner, repo, access_token_postfix())
    resp = requests.get(url)
    print resp.json()

def create_pull_request(owner, repo, head, base, title, body):
    url = "https://api.github.com/repos/{}/{}/pulls{}".format(owner, repo, access_token_postfix())
    json = {"head": head, "base": base, "title": title, "body": body}
    resp = requests.post(url, json=json)
    if resp.status_code == 201:
        print "A pull request has been created from '{}' to '{}'".format(head, base)
    else:
        print resp.status_code, resp.text

def download_archive(owner, repo, branch, save_to_path, ball="zipball"):
    """Ball can be either zipball or tarball"""
    # TODO: Test on Windows
    url = "https://api.github.com/repos/{owner}/{repo}/{archive_format}/{ref}{token}"\
              .format(owner=owner, repo=repo, archive_format=ball, ref=branch, token=access_token_postfix())
    response = requests.get(url)
    if response.status_code == 200:
        print "Downloaded the {}".format(ball)
        archive = zipfile.ZipFile(StringIO.StringIO(response.content))
        archive.extractall(save_to_path)

def create_release_candidate(owner, repo, whatif):
    """
    Pre: The master branch has a tagged latest version (TODO: Support if it hasn't)

    The candidate release is based on info from Github about the latest release. For
    this, there should be a new branch, called release-#.#.#. If such a branch already
    exists, no new branch is created.

    The next step is to create a pull request from develop to the new release branch.
    This branch should then be code reviewed and eventually merged.
    """
    candidate_branch = get_candidate_branch(owner, repo)

    print "Creating a new branch, '{}' from master".format(candidate_branch)
    if not whatif:
        create_branch_from_master(owner, repo, candidate_branch)

    # Merge from 'develop' into the new release branch:
    print "Merging from {} to {}".format(DEVELOP_BRANCH, candidate_branch)
    if not whatif:
        merge(owner, repo, candidate_branch, DEVELOP_BRANCH, "Merging '{}' into '{}'".format(DEVELOP_BRANCH, candidate_branch))

def download_release_candidate(owner, repo, path, force, whatif):
    if not force and os.path.exists(path):
        print "The candidate filepath '{}' already exists. Please specify a non-existing path or --force.".format(path)
        sys.exit(1)

    candidate_branch = get_candidate_branch(owner, repo)
    print "Downloading '{}' to '{}'...".format(candidate_branch, path)
    download_archive(owner, repo, candidate_branch, path)

def accept_release_candidate(owner, repo, whatif):
    """
    Merge from release-x.x.x into master and tag master with vx.x.x
    """
    candidate_branch = get_candidate_branch(owner, repo)
    print "Merging candidate from '{}' to '{}'".format(candidate_branch, MASTER_BRANCH)

    # TODO: Some error mechanism, checking if the branch actually exists etc
    if not whatif:
        merge(owner, repo, MASTER_BRANCH, candidate_branch, "Merging '{}' into '{}'".format(candidate_branch, MASTER_BRANCH))

    tag_name = get_release_tag(owner, repo)
    print "Tagging HEAD on {} as release {}".format(MASTER_BRANCH, tag_name)
    if not whatif:
        tag_release(owner, repo, tag_name, MASTER_BRANCH)

def compare(owner, repo, base, head):
    url = "https://api.github.com/repos/{}/{}/compare/{}...{}{}".format(owner, repo, base, head, access_token_postfix())
    response = requests.get(url)
    print response.status_code, response.json()

def get_branches(owner, repo):
    url = "https://api.github.com/repos/{}/{}/branches{}".format(owner, repo, access_token_postfix())
    response = requests.get(url)
    return response.json()

def tag_release(owner, repo, tag_name, branch):
    # Tags a commit as a release on Github
    url = "https://api.github.com/repos/{}/{}/releases{}".format(owner, repo, access_token_postfix())
    # TODO: Release description
    json = {"tag_name": tag_name, "target_commitish": branch,
            "name": tag_name, "body": "", "draft": False, "prerelease": False}
    response = requests.post(url, json=json)
    if response.status_code == 201:
        print "HEAD of master marked as release {}".format(tag_name)
    else:
        raise GithubException(respones.text)

@click.group()
@click.option('--whatif/--not-whatif', default=False)
@click.pass_context
def cli(ctx, whatif):
    ctx.obj['whatif'] = whatif
    if whatif:
        print "*** Running with whatif ON - no writes ***"
    pass

@cli.command('cand-create')
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def create(ctx, owner, repo):
    print "Creating a release candidate from {}".format(DEVELOP_BRANCH)
    create_release_candidate(owner, repo, ctx.obj['whatif'])

@cli.command('cand-accept')
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def accept(ctx, owner, repo):
    print "Accepting the current release candidate"
    accept_release_candidate(owner, repo, ctx.obj['whatif'])

@cli.command('cand-download')
@click.argument('owner')
@click.argument('repo')
@click.argument('path')
@click.option('--force/--not-force', default=False)
@click.pass_context
def download(ctx, owner, repo, path, force):
    print "Downloading the current release candidate"
    download_release_candidate(owner, repo, path, force, ctx.obj['whatif'])

@cli.command()
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def latest(ctx, owner, repo):
    latest = get_latest_version(owner, repo)
    print "Latest version: {0}".format(latest)

@cli.command()
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def status(ctx, owner, repo):
    latest = get_latest_version(owner, repo)
    print "Latest version: {}".format(latest)

    candidate_branch = get_candidate_branch(owner, repo)
    print "Candidate branch based on latest version: {}".format(candidate_branch)

    branches = get_branches(owner, repo)
    branch_names = [branch["name"] for branch in branches]

    print "Branches:"
    for branch in branch_names:
        print "  {}{}".format(branch, " *" if branch == candidate_branch else "")

    # TODO:
    # Differences between master and develop:
    # print "Changes needed to be applied from 'develop'->'branch'"
    # compare(owner, repo, MASTER_BRANCH, DEVELOP_BRANCH)

    # Diff the candidate release with develop, there shouldn't be changes in the other direction

    # Diff the candidate release with master

if __name__ == "__main__":
    cli(obj={})

