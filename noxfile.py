# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Code quality checks."""

import nox

check_dirs = [
    "benchmarks",
    "docs",
    "src",
    "tests",
]

check_files = [
    "noxfile.py",
]


@nox.session
def formatting(session: nox.Session) -> None:
    """Run black and isort to make sure the format is uniform."""
    session.install("black", "isort")
    session.run("black", "--check", *check_dirs, *check_files)
    session.run("isort", "--check", *check_dirs, *check_files)


@nox.session
def pylint(session: nox.Session) -> None:
    """Run pylint to do lint checks."""
    session.install("-e", ".[docs]", "pylint", "pytest", "nox")
    session.run("pylint", *check_dirs, *check_files)


@nox.session
def mypy(session: nox.Session) -> None:
    session.install(".", "mypy")
    session.run(
        "mypy",
        "--ignore-missing-imports",
        "--namespace-packages",
        "--non-interactive",
        "--install-types",
        "--explicit-package-bases",
        "--follow-imports=silent",
        "--strict",
        *check_dirs,
    )


@nox.session
def docstrings(session: nox.Session) -> None:
    """Check docstring tone with pydocstyle and param descriptions with darglint."""
    session.install("pydocstyle", "darglint", "toml")

    session.run("pydocstyle", *check_dirs, *check_files)

    # Darglint checks that function argument and return values are documented.
    # This is needed only for the `src` dir, so we exclude the other top level
    # dirs that contain code.
    session.run("darglint", "src")


@nox.session
def pytest(session: nox.Session) -> None:
    """Run all tests using pytest."""
    session.install("pytest", "pytest-cov", "pytest-mock", "pytest-asyncio")
    session.install("-e", ".")
    session.run(
        "pytest",
        "-W=all",
        "-vv",
        "--cov=frequenz.channels",
        "--cov-report=term",
        "--cov-report=html:.htmlcov",
    )
