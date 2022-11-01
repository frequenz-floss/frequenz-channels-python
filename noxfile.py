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

@nox.session
def formatting(session: nox.Session) -> None:
    session.install("black", "isort")
    session.run("black", "--check", *check_dirs)
    session.run("isort", "--check", *check_dirs)


@nox.session
def pylint(session: nox.Session) -> None:
    session.install(".[docs]", "pylint", "pytest")
    session.run("pylint", *check_dirs)


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

    session.run("pydocstyle", *check_dirs)

    # Darglint checks that function argument and return values are documented.
    # This is needed only for the `src` dir, so we exclude the other top level
    # dirs that contain code.
    session.run("darglint", "src")


@nox.session
def pytest(session: nox.Session) -> None:
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
