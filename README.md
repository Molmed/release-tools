ARCHIVED - These scripts are outdated and not used anymore. A manual instruction for releases will be replacing this.
-------------

release-tools
-------------

Tools for handling versioned releases. Currently only handle releases using a particular workflow
(see below) and when hosting and tagging versions on Github.

# Install
``python -m pip install -U git+https://github.com/withrocks/release-tools.git#egg=release-tools``

or, with a version:

``python -m pip install -U git+https://github.com/withrocks/release-tools.git@v0.1.2#egg=release-tools``

## Windows
On Windows, ensure that you've got your Python scripts directory in your PATH. That directory is located in ``<python installation dir>\Scripts``. (If you installed this in a virtualenv, you need that scripts directory.)

# Workflows
## Assumptions
The release workflow supported assumes that you've got two permanent branches:
  * ``develop``: The next version to be released. Nothing should be committed in here that cannot safely go
  out with the next scheduled release
  * ``master``: Contains the latest version of the released software and tags for all previous releases

The following transient branches also exist:
  * ``release-#.#.#``: Release branches. Can be deleted after releasing.
  * ``hotfix-#.#.#``: Hotfix branches. Can be deleted after releasing and merging to relevant branches.
  * ``feature-branch-n``: Any number of feature branches. Names can be anything not colliding with 
  the other branches.

## General flow
  * Code has been submitted to the ``develop`` branch, probably through pull requests from feature branches
  * When the next version is ready to be released, run ``release-tools create-cand <owner> <repo> [--major]``
  * This creates a new release branch called ``release-#.#.#``, where the minor or major version has 
    been increased, e.g. 1.0.2 -> 1.1.0.
  * Build and validate (separate workflow). Latest version can be fetched with
  ``release-tools download <owner> <repo> <path>``. Deploy if it passes the QA process.
  * After deploying, call ``release-tools accept <owner> <repo>``. If the queue also contains a hotfix, you
  must release that first.
  * The code has now been merged into master with the applicable tag, e.g. v1.1.0.
  
## Hotfix flow
  * The ``develop`` branch is not available (contains features that can't be deployed),
  and you need to create a hotfix.
  * Run ``release-tools create-hotfix <owner> <repo>``
  * Get your hotfixes into this branch as it were the ``develop`` branch, probably through
  pull requests from feature branches.
  * When ready, run ``release-tools accept <owner> <repo>``. This will accept the hotfix if one exists.
  * A pull request is made from the hotfix branch to ``develop`` and the active release
  branch ``release-#.#.#``. It's not automatically merged since there may be merge conflicts
  or the fix might only make sense in the latest release.
  This acts as a reminder of that the fix might need to go into these branches, but it may
  make more sense to only merge the hotfix->release pull request and then make a separate
  pull request from release->develop, since then fewer merge conflicts might need to be solved.
  
## Release queue
  * Using these workflows, there can only be one hotfix version and one release version
  out at the same time.
  * The hotfix will always be next in the queue.
  * Currently, hotfixes always have an increased patch number and regular releases have an increased minor
  version


*The tool may work in an unexpected manner if the master branch is changed without the use
of this tool or if release/hotfix branches are made manually.*
