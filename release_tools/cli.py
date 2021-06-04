import click
import yaml
from release_tools.github import GithubProvider
from release_tools.workflow import Workflow, Conventions, DEVELOP_BRANCH
from release_tools.app import create_version_service


def create_workflow(owner, repo, whatif, config):
    access_token = config["access_token"] if config and "access_token" in config else None
    provider = GithubProvider(owner, repo, access_token)
    return Workflow(provider, Conventions, whatif)

@click.group()
@click.option('--whatif/--not-whatif', default=False)
@click.option('--config')
@click.pass_context
def cli(ctx, whatif, config):
    ctx.obj['whatif'] = whatif
    # Read config file containing access token:
    if config:
        with open(config) as f:
            ctx.obj["config"] = yaml.load(f)
    else:
        ctx.obj["config"] = None

    if whatif:
        click.echo("*** Running with whatif ON - no writes ***")


@cli.command('create-cand')
@click.argument('owner')
@click.argument('repo')
@click.option('--major', is_flag=True)
@click.pass_context
def create_cand(ctx, owner, repo, major):
    click.echo("Creating a release candidate from {}".format(DEVELOP_BRANCH))
    workflow = create_workflow(owner, repo, ctx.obj['whatif'], ctx.obj['config'])
    workflow.create_release_candidate(major_inc=major)


@cli.command('create-hotfix')
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def create_hotfix(ctx, owner, repo):
    click.echo("Creating a hotfix branch")
    workflow = create_workflow(owner, repo, ctx.obj['whatif'], ctx.obj['config'])
    workflow.create_hotfix()


@cli.command('accept')
@click.argument('owner')
@click.argument('repo')
@click.option('--force/--not-force', default=False)
@click.pass_context
def accept(ctx, owner, repo, force):
    click.echo("Accepting the current release candidate")
    workflow = create_workflow(owner, repo, ctx.obj['whatif'], ctx.obj['config'])
    workflow.accept_release_candidate(force)


@cli.command('download')
@click.argument('owner')
@click.argument('repo')
@click.argument('path')
@click.option('--force/--not-force', default=False)
@click.pass_context
def download(ctx, owner, repo, path, force):
    click.echo("Downloading the next release in the queue")
    workflow = create_workflow(owner, repo, ctx.obj['whatif'], ctx.obj['config'])
    workflow.download_next_in_queue(path, force)


@cli.command('download-release-history')
@click.argument('owner')
@click.argument('repo')
@click.argument('directory')
@click.pass_context
def download_release_history(ctx, owner, repo, directory):
    click.echo("Downloading release history")
    workflow = create_workflow(owner, repo, ctx.obj['whatif'], ctx.obj['config'])
    workflow.download_release_history(directory)


@cli.command()
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def latest(ctx, owner, repo):
    workflow = create_workflow(owner, repo, ctx.obj['whatif'], ctx.obj['config'])
    latest_version = workflow.get_latest_version()
    click.echo("Latest version: {0}".format(latest_version))


@cli.command()
@click.argument('owner')
@click.argument('repo')
@click.pass_context
def status(ctx, owner, repo):
    workflow = create_workflow(owner, repo, ctx.obj['whatif'], ctx.obj['config'])

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
@click.option("--release/--no-release", default=False)
def tag(release):
    """
    Tag the current branch. Requires there to be a file in `.deploy/version` which needs to
    be provided by the programmer. This file should echo the current version

    We expect an executable called `version` in the same directory as we are. It must write
    the current version on the format `<major>.<minor>.<patch>`. It should not include a candidate
    postfix (e.g. -rc1). It can though for debug reasons include a prefix which must then be
    on the format `<something>-`.

    Examples of a valid version:
        1.0.0
        dbg-1.0.0
    """
    click.echo(f"Tagging a special branch. Release={release}...")

    version_service = create_version_service()
    next_version = version_service.get_next_version()
    click.echo(next_version)


def cli_main():
    cli(obj={})

if __name__ == "__main__":
    cli_main()

