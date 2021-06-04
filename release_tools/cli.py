import click
import yaml
from release_tools.github import GithubProvider
from release_tools.workflow import Workflow, Conventions, DEVELOP_BRANCH


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
    print "Latest version: {}".format(latest_version)
    print "  - Next version version would be: {}".format(next_version)
    print "  - Next hotfix version would be: {}".format(hotfix_version)

    # TODO: Report all release tags too

    print ""
    print "Branches:"
    for branch in branch_names:
        print "  {}{}".format(branch, " *" if (branch in queue) else "")

    print ""
    print "Queue:"
    # TODO: Use cache for api calls when possible
    for branch in queue:
        pull_requests = len(workflow.provider.get_pull_requests(branch))
        print "  {} (PRs={})".format(branch, pull_requests)

    # TODO: Compare relevant branches
    print ""


def cli_main():
    cli(obj={})

if __name__ == "__main__":
    cli_main()

