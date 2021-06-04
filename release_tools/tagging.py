# class Tagger:
#     def __init__(self, get_version):
#         """
#         Tags releases based on the branch name
#         """
#         self.get_version = get_version

#     def tag(self, release):
#         return
#         version_script = ".deploy/version"

#         if not os.path.exists(version_script):
#             click.echo(f"Can't find version executable at {version_script}")
#             exit(1)

#         version = run(version_script).strip()

#         branch = get_current_branch_name()

#         branch = "next"  # TODO

#         # Validate branch name:
#         if not re.match(r"^\w+$", branch):
#             click.echo(f"Branch must have word characters only, got `{branch}`")
#             exit(1)

#         if not re.match(r"^(.+-)?v\d+\.\d+\.\d+$", version):
#             click.echo(f"Version is not of the expected format "
#                         "`[<dbg prefix>-]v<major>.<minor>.<patch>`, got `{version}`")
#             exit(1)

#         ## Now, based on all available tags, we need to find one that is of the same version and increase
#         ## the postfix
#         click.echo(f"Tag will be based on version={version}, branch={branch}")

#         our_version = Version.parse(version)
#         print(our_version)

#         # Find all versions that we already have for this
#         versions = [v for v in get_versions() if v.version_tuple == (9, 1, 1)]

#         print("stuffo", versions)
