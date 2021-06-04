from release_tools.utils import run


def get_current_branch_name():
    return run("git rev-parse --abbrev-ref HEAD").strip()
