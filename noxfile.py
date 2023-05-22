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
    session.install(
        "-e",
        ".[docs]",
        "pylint",
        "pytest",
        "sybil",
        "nox",
        "async-solipsism",
        "hypothesis",
    )
    session.run("pylint", *check_dirs, *check_files)


@nox.session
def mypy(session: nox.Session) -> None:
    """Run mypy to check type hints."""
    session.install(
        "-e",
        ".[docs]",
        "pytest",
        "nox",
        "mypy",
        "async-solipsism",
        "hypothesis",
    )

    common_args = [
        "--namespace-packages",
        "--non-interactive",
        "--install-types",
        "--explicit-package-bases",
        "--strict",
    ]

    pkg_args = []
    for pkg in check_dirs:
        if pkg == "src":
            pkg = "frequenz.channels"
        pkg_args.append("-p")
        pkg_args.append(pkg)

    session.run("mypy", *common_args, *pkg_args)
    session.run("mypy", *common_args, *check_files)


@nox.session
def docstrings(session: nox.Session) -> None:
    """Check docstring tone with pydocstyle and param descriptions with darglint."""
    session.install("pydocstyle", "darglint", "tomli")

    session.run("pydocstyle", *check_dirs, *check_files)

    # Darglint checks that function argument and return values are documented.
    # This is needed only for the `src` dir, so we exclude the other top level
    # dirs that contain code.
    session.run("darglint", "-v2", "src")


@nox.session
def pytest(session: nox.Session) -> None:
    """Run all tests using pytest."""
    session.install(
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "pytest-asyncio",
        "async-solipsism",
        "hypothesis",
        "sybil",
        "pylint",
    )
    session.install("-e", ".")
    session.run(
        "pytest",
        "-W=all",
        "-vv",
        "--cov=frequenz.channels",
        "--cov-report=term",
        "--cov-report=html:.htmlcov",
    )
