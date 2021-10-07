#!/usr/bin/env python
from __future__ import print_function
import requests
import zipfile
import StringIO
import dateutil.parser
import sys


class GithubProvider:
    def __init__(self, owner, repo, access_token=None):
        self.owner = owner
        self.repo = repo
        self.access_token = access_token

    @property
    def _authorization_header(self):
        return {'Authorization': 'Bearer {}'.format(self.access_token)}

    def _http_get(self, url):
        return requests.get(url, headers=self._authorization_header)

    def _http_post(self, url, body):
        return requests.post(
            url, json=body,
            headers=self._authorization_header)

    def get_latest_version_tag_name(self):
        url = "https://api.github.com/repos/{}/{}/releases/latest"\
                  .format(self.owner, self.repo)
        response = self._http_get(url)
        if response.status_code == 200:
            json = response.json()
            return json["tag_name"]
        else:
            raise GithubException(response.text)

    def get_refs_heads(self):
        url = "https://api.github.com/repos/{}/{}/git/refs/heads"\
                  .format(self.owner, self.repo)
        response = self._http_get(url)
        return response.json()

    def get_refs_head(self, ref):
        heads = self.get_refs_heads()
        filtered = [x for x in heads if x["ref"] == ref]
        assert len(filtered) == 1
        return filtered[0]["object"]["sha"]

    def create_branch_from_master(self, new_branch):
        """
        Creates a new branch from the master branch

        If the branch already exists, it will be ignored without an exception
        """
        sha = self.get_refs_head("refs/heads/master")

        body = {"ref": "refs/heads/{}".format(new_branch), "sha": sha}
        url = "https://api.github.com/repos/{}/{}/git/refs" \
                  .format(self.owner, self.repo)
        response = self._http_post(url, body)

        if response.status_code == 201:
            print("Branch successfully created")
        elif response.status_code == 422:
            print("Branch already exists")  # TODO: Check error code def in docs

    def merge(self, base, head, commit_message):
        url = "https://api.github.com/repos/{}/{}/merges"\
                  .format(self.owner, self.repo)
        body = {"base": base, "head": head, "commit_message": commit_message}
        response = self._http_post(url, body)
        if response.status_code == 201:
            print("Successfully merged '{}' into '{}'".format(head, base))
        elif response.status_code == 204:
            print("Nothing to merge")
        elif response.status_code == 409:
            raise MergeException(response.text)
        else:
            msg = "Unexpected result code from Github ({}): {}".format(response.status_code, response.text)
            raise GithubException(msg)

    def create_pull_request(self, base, head, title, body):
        url = "https://api.github.com/repos/{}/{}/pulls"\
                  .format(self.owner, self.repo)
        body = {"head": head, "base": base, "title": title, "body": body}
        resp = self._http_post(url, body)
        if resp.status_code == 201:
            print("A pull request has been created from '{}' to '{}'".format(head, base))
        else:
            print(resp.status_code, resp.text)

    def download_archive(self, branch, save_to_path, ball="zipball"):
        """Ball can be either zipball or tarball"""
        # TODO: Test on Windows
        url = "https://api.github.com/repos/{owner}/{repo}/{archive_format}/{ref}"\
              .format(owner=self.owner, repo=self.repo, archive_format=ball, ref=branch)
        response = self._http_get(url)
        if response.status_code == 200:
            print("Downloaded the archive. Extracting...")
            archive = zipfile.ZipFile(StringIO.StringIO(response.content))
            archive.extractall(save_to_path)
            print("Extracted")

    def download_release_history(self, path):
        url = "https://api.github.com/repos/{owner}/{repo}/releases"\
              .format(owner=self.owner, repo=self.repo)
        response = self._http_get(url)
        if response.status_code == 200:
            print("Writing to file...")
            with open(path, 'w') as f:
                f.write(self._release_history_contents(response.json()))
            print("done.")
        else:
            raise GithubException("Something went wrong, contents cannot be downloaded")

    def _release_history_contents(self, json):
        c = []
        for release in json:
            d = dateutil.parser.parse(release['published_at'].encode('utf-8'))
            release_name = release['name'].encode('utf-8')
            release_body = release['body'].encode('utf-8')
            release_body = '\n'.join(release_body.splitlines())
            c.append("{}, {:%Y-%m-%d}\n\n{}".format(release_name, d, release_body))
        return str.join('\n\n\n', c)

    def get_branches(self):
        url = "https://api.github.com/repos/{}/{}/branches"\
                  .format(self.owner, self.repo)
        response = self._http_get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise GithubException(response.text)

    def tag_release(self, tag_name, branch):
        # Tags a commit as a release on Github
        url = "https://api.github.com/repos/{}/{}/releases"\
                  .format(self.owner, self.repo)
        # TODO: Release description
        body = {"tag_name": tag_name, "target_commitish": branch,
                "name": tag_name, "body": "", "draft": False, "prerelease": False}
        response = self._http_post(url, body)
        if response.status_code == 201:
            print("HEAD of master marked as release {}".format(tag_name))
        else:
            raise GithubException(response.text)

    def get_pull_requests(self, base_branch):
        """Returns the list of open pull requests to the base"""
        return self._get("/repos/{owner}/{repo}/pulls", {'base': base_branch})

    def has_pull_requests(self, base_branch):
        return len(self.get_pull_requests(base_branch)) > 0

    def _get(self, resource, params={}):
        url = self._url(resource)
        resp = self._http_get(url)
        if resp.status_code == 200:
            return resp.json()
        else:
            raise GithubException(resp.text)

    def _url(self, templ):
        """
        Returns a github api URL from the template specified
        in the help, similar to /repos/{owner}/{repo}/pulls
        """
        req = templ.format(owner=self.owner,
                           repo=self.repo)
        return "{base}{req}".format(
            base="https://api.github.com",
            req=req)

    def compare(self, base, head):
        url = "https://api.github.com/repos/{}/{}/compare/{}...{}"\
              .format(self.owner, self.repo, base, head)
        response = self._http_get(url)
        print(response.status_code, response.json())


class GithubException(Exception):
    pass


class MergeException(Exception):
    pass

