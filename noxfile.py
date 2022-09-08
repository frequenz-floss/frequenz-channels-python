"""Code quality checks.

Copyright
Copyright © 2022 Frequenz Energy-as-a-Service GmbH

License
MIT
"""

import nox


@nox.session
def formatting(session: nox.Session) -> None:
    session.install("black", "isort")
    session.run("black", "--check", "src", "tests", "benchmarks")
    session.run("isort", "--check", "src", "tests", "benchmarks")


@nox.session
def pylint(session: nox.Session) -> None:
    session.install(".", "pylint", "pytest")
    session.run("pylint", "src", "tests", "benchmarks")


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
        "src",
        "tests",
        "benchmarks",
    )


@nox.session
def docstrings(session: nox.Session) -> None:
    """Check docstring tone with pydocstyle and param descriptions with darglint."""
    session.install("pydocstyle", "darglint", "toml")

    session.run("pydocstyle", "src", "tests", "benchmarks")

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
