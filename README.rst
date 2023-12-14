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

Find out more by running::

    update-template --help
