from subprocess import check_output
from setuptools import find_packages

def run(cmd):
    return check_output(cmd.split(" ")).decode("utf-8")


def find_single_package():
    packages = [item for item in find_packages(
        exclude=["test*"]) if "." not in item]

    if len(packages) != 1:
        raise AssertionError(f"Found {len(packages)} root packages(s) but expecting exactly one")

    return packages[0]
