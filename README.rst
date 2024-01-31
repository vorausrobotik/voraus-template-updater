===============================
voraus Template Updater
===============================


A CLI to keep projects up to date that were bootstrapped with `cruft <https://cruft.github.io/cruft/>`_ + `cookiecutter <https://cookiecutter.readthedocs.io/en/stable/>`_.

Install with::

    pip install git@github.com:vorausrobotik/voraus-template-updater.git

Run with::

    update-template <user or organization>

A GitHub token will be retrieved from the ``GITHUB_TOKEN`` environment variable.
It can also be passed via the ``--github-access-token`` option.

Any dependencies required by a template's pre/post-generate hooks must be installed into the same environment
as the template updater.

Find out more by running::

    update-template --help
