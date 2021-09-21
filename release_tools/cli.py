import os
import click
import yaml
from release_tools.github import GithubProvider
from release_tools.workflow import Workflow, Conventions, DEVELOP_BRANCH
from release_tools.app import create_version_service
from jinja2 import PackageLoader, Environment
from release_tools.utils import find_single_package
import logging
from subprocess import check_call


special_branches = ["develop", "rc", "hotfix", "main"]

DEFAULT_CONFIG = ".release-tools.yml"

def create_workflow(owner, repo, whatif, config):
    access_token = config["access_token"] if config and "access_token" in config else None
    provider = GithubProvider(owner, repo, access_token)
    return Workflow(provider, Conventions, whatif)

def raise_require_config():
    click.echo("A config file is missing for the project. Call `release-tools init` to "
               "generate an example")
    exit(1)


@click.group()
@click.option('--whatif/--not-whatif', default=False)
@click.option('--log-level', default="WARN")
@click.option('--config')
@click.pass_context
def cli(ctx, whatif, config, log_level):
    logging.basicConfig(level=log_level)
    ctx.obj['whatif'] = whatif

    if not config and os.path.exists(DEFAULT_CONFIG):
        config = DEFAULT_CONFIG

    # Read config file containing access token:
    if config:
        with open(config) as f:
            ctx.obj["config"] = yaml.safe_load(f)
    else:
        ctx.obj["config"] = None

    if whatif:
        click.echo("*** Running with whatif ON - no writes ***")


@cli.command()
@click.argument('owner')
@click.argument('repo')
@click.option('--major', is_flag=True)
@click.pass_context
def create_candidate(ctx, owner, repo, major):
    click.echo("Creating a release candidate from {}".format(DEVELOP_BRANCH))
    workflow = create_workflow(
        owner, repo, ctx.obj['whatif'], ctx.obj['config'])
    workflow.create_release_candidate(major_inc=major)


@cli.command('create-hotfix')
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def create_hotfix(ctx, owner, repo):
    click.echo("Creating a hotfix branch")
    workflow = create_workflow(
        owner, repo, ctx.obj['whatif'], ctx.obj['config'])
    workflow.create_hotfix()


@cli.command('accept')
@click.argument('owner')
@click.argument('repo')
@click.option('--force/--not-force', default=False)
@click.pass_context
def accept(ctx, owner, repo, force):
    click.echo("Accepting the current release candidate")
    workflow = create_workflow(
        owner, repo, ctx.obj['whatif'], ctx.obj['config'])
    workflow.accept_release_candidate(force)


@cli.command('download')
@click.argument('owner')
@click.argument('repo')
@click.argument('path')
@click.option('--force/--not-force', default=False)
@click.pass_context
def download(ctx, owner, repo, path, force):
    click.echo("Downloading the next release in the queue")
    workflow = create_workflow(
        owner, repo, ctx.obj['whatif'], ctx.obj['config'])
    workflow.download_next_in_queue(path, force)


@cli.command('download-release-history')
@click.argument('owner')
@click.argument('repo')
@click.argument('directory')
@click.pass_context
def download_release_history(ctx, owner, repo, directory):
    click.echo("Downloading release history")
    workflow = create_workflow(
        owner, repo, ctx.obj['whatif'], ctx.obj['config'])
    workflow.download_release_history(directory)


@cli.command()
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def latest(ctx, owner, repo):
    workflow = create_workflow(
        owner, repo, ctx.obj['whatif'], ctx.obj['config'])
    latest_version = workflow.get_latest_version()
    click.echo("Latest version: {0}".format(latest_version))


@cli.command()
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def status(ctx, owner, repo):
    workflow = create_workflow(
        owner, repo, ctx.obj['whatif'], ctx.obj['config'])

    branches = workflow.provider.get_branches()
    branch_names = [branch["name"] for branch in branches]

    queue = workflow.get_queue()

    latest_version = workflow.get_latest_version()
    next_version = workflow.get_candidate_version()
    hotfix_version = workflow.get_hotfix_version()
    click.echo("Latest version: {}".format(latest_version))
    click.echo("  - Next version version would be: {}".format(next_version))
    click.echo("  - Next hotfix version would be: {}".format(hotfix_version))

    # TODO: Report all release tags too

    click.echo("")
    click.echo("Branches:")
    for branch in branch_names:
        click.echo("  {}{}".format(branch, " *" if (branch in queue) else ""))

    click.echo("")
    click.echo("Queue:")
    # TODO: Use cache for api calls when possible
    for branch in queue:
        pull_requests = len(workflow.provider.get_pull_requests(branch))
        click.echo("  {} (PRs={})".format(branch, pull_requests))

    # TODO: Compare relevant branches
    click.echo("")


@cli.command()
@click.option("--force/--no-force", default=False)
@click.option("--tools-path", default=".release")
@click.option("--debug/--no-debug", default=False)
def init(force, tools_path, debug):
    """
    Initializes a SNP&SEQ project for CI/CD. Assumes that we are using the the gitlab server.

    Currently assumes that there exists a setup.py file and a Python module.
    """

    if not os.path.exists(tools_path):
        click.echo(f"Tools are not available at {tools_path}")
        exit(1)

    custom_path = os.path.join(tools_path, "custom")

    if not os.path.exists(custom_path):
        os.mkdir(custom_path)

    env = Environment(loader=PackageLoader('release_tools', 'resources'))

    if debug:
        branches = []
        # We use other special branches when testing the chain
        for branch in special_branches:
            test_branch = "{}_dbg".format(branch)
            branches.append(test_branch)
    else:
        branches = special_branches

    # TODO: Figure out package from location of __init__.py
    package_root = find_single_package()

    templates = [
        dict(source="gitlab-ci.yml.j2",
             target=".gitlab-ci.yml",
             mode=0o644,
             kwargs=dict(special_branches=branches)),
        dict(source="build.j2",
             target=f"{tools_path}/custom/build",
             mode=0o755),
        dict(source="test.j2",
             target=f"{tools_path}/custom/test",
             mode=0o755),
        dict(source="version.j2",
             target=f"{tools_path}/custom/version",
             mode=0o755),
        dict(source="VERSION.j2",
             target=f"{package_root}/VERSION",
             mode=0o644),
        dict(source="setup.py.j2",
             target="setup.py",
             mode=0o644),
        dict(source="pkg_init.py.j2",
             target=f"{package_root}/__init__.py",
             mode=0o644),
    ]

    for info in templates:
        source = info["source"]
        target = info["target"]
        mode = info["mode"]
        kwargs = info.get("kwargs", dict())
        click.echo(f"Creating {target}...")
        template = env.get_template(source)

        if os.path.exists(target) and not force:
            click.echo(f"File already exists {target}.")
            continue

        with open(target, "w") as fs:
            fs.write(template.render(**kwargs))
        os.chmod(target, mode)


@cli.command()
@click.argument("candidate")
@click.option("--tools-path", default=".release")
def tag(tools_path, candidate):
    """
    We expect an executable called `version` in the same directory as we are. It must write
    the current version on the format `<major>.<minor>.<patch>`. It should not include a candidate
    postfix (e.g. -rc1). It can though for debug reasons include a prefix.

    Examples of a valid version:
        1.0.0
        dbg-1.0.0

    The `candidate` is a string that gets added to indicate what kind of build this is. If it's
    empty, this is considered a release build.
    """
    click.echo(f"Tagging a special branch. Candidate='{candidate}'...")

    custom_tools_path = os.path.join(tools_path, "custom")
    version_service = create_version_service(custom_tools_path, candidate)
    next_version = version_service.get_next_version()

    click.echo("Tagging version as {}".format(next_version))
    version_service.tag(next_version)


@cli.command()
@click.pass_context
@click.option("--install-requirements/--no-install-requirements", default=True)
def package_python_libraries(ctx, install_requirements):
    """
    Packages all python libraries configured in the config file (python_packages).

    The version number for the libraries will reflect the git tag we are on, and
    will fail if it doesn't look like a release.
    """

    if install_requirements:
        click.echo("Installing pip requirements")
        check_call("python -m pip install --upgrade pip setuptools wheel".split())




    config = ctx.obj["config"]
    if config is None:
        raise_require_config()

    packages = config.get("python_packages", [])

    if len(packages) == 0:
        click.echo("No packages configured for updating")

    from release_tools.versions import (VersionFileInPythonPackageBaseVersionProvider,
                                        GitCandidateProvider,
                                        GitVersionHistoryProvider,
                                        VersionService)

    candidate_provider = GitCandidateProvider()
    prev_versions_provider = GitVersionHistoryProvider()

    print(candidate_provider.get_candidate())
    print(list(prev_versions_provider.get_versions()))

    exit()

    # base_version_provider = VersionFileInPythonPackageBaseVersionProvider()

    # version_service = VersionService(candidate_provider, base_version_provider, prev_versions_provider)
    return



    version_service = create_version_service()
    #version = version_service.get_current()

    for package in packages:
        click.echo(f"Applying git tag to package {package}...")


    # if not os.path.exists("setup.py"):
    #     click.echo(
    #         "WARNING: Can't find setup.py and don't know how to tag anything else")
    #     return

    # custom_tools_path = os.path.join(tools_path, "custom")
    # version_service = create_version_service(custom_tools_path, "")
    # version = version_service.get_current()

    # from setuptools import find_packages
    # pkg = [pkg for pkg in find_packages(exclude=["test*"]) if "." not in pkg]

    # if len(pkg) != 1:
    #     pass
    # pkg = pkg[0]

    # click.echo(f"Updating VERSION file to '{version}'...")

    # with open(os.path.join(pkg, "VERSION"), "w") as fs:
    #     fs.write(str(version))

@cli.command()
def version():
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, 'VERSION')) as version_file:
        version = version_file.read().strip()
    click.echo(version)


def cli_main():
    cli(obj={})


if __name__ == "__main__":
    cli_main()
