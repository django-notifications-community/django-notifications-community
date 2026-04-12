# Contributing

Thanks for your interest in helping maintain `django-notifications-community`.
This is a community fork (see the README and [upstream issue #416](https://github.com/django-notifications/django-notifications/issues/416)
for context), and contributions are welcome, especially:

- Bug reports and fixes against current Django and Python versions
- Backporting useful PRs from the upstream repo (with credit to the original author)
- CI, packaging, and documentation improvements
- Translations

## Development setup

```bash
git clone https://github.com/django-notifications-community/django-notifications-community
cd django-notifications-community
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install tox pre-commit
pre-commit install
```

The pre-commit hooks run `ruff` (lint + format) on every commit so issues
get caught before they reach CI.

## Running tests

The full CI matrix runs via `tox`:

```bash
tox                     # all envs
tox -e py312-django52   # a single env
```

Tests live in `notifications/tests/` and use Django's built-in test runner,
invoked through `manage.py test`.

## Opening a pull request

- Fork the repo and create a topic branch off `master`.
- Keep PRs focused. One idea per PR is easier to review and less risky to revert.
- Add or update tests for any behavior change.
- Update `CHANGELOG.md` under an "Unreleased" section at the top if the change
  is user-visible.
- Make sure `tox` passes locally before pushing.
- Squash fixup commits before requesting review.

## Backporting from upstream

If you're porting a change from `django-notifications/django-notifications`,
please preserve authorship by using `git cherry-pick -x` (which records the
original commit SHA in the message) or by crediting the original author in the
PR body. We want upstream authors to get visible credit for their work.

## Releases

Releases are cut by maintainers by tagging `vX.Y.Z` on `master`. The release
workflow publishes to PyPI via Trusted Publishing, gated on a manual approval
in the `pypi` GitHub environment. No API tokens are stored in the repository.

## Code of conduct

Be respectful. Remember that the original `django-notifications` authors did
the hard work this project is built on — treat them and their contributions
with gratitude, even when discussing changes or bugs.
