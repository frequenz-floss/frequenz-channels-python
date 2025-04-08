# License: MIT
# Copyright © 2023 Frequenz Energy-as-a-Service GmbH

"""This module defines macros for use in Markdown files."""

from frequenz.repo.config.mkdocs.mkdocstrings_macros import hook_env_with_everything
from griffe import ModulesCollection, Object
from mkdocs_macros.plugin import MacrosPlugin
from mkdocstrings_handlers.python.handler import PythonHandler


def define_env(env: MacrosPlugin) -> None:
    """Define the hook to create macro functions for use in Markdown.

    Args:
        env: The environment to define the macro functions in.
    """
    python_handler = env.conf["plugins"]["mkdocstrings"].get_handler("python")
    assert isinstance(python_handler, PythonHandler)

    def _get_docstring(symbol: str) -> str:
        symbols = python_handler._modules_collection  # pylint: disable=protected-access
        assert isinstance(symbols, ModulesCollection)

        try:
            obj = symbols[symbol]
        except KeyError as exc:
            raise ValueError(f"Symbol {symbol!r} not found.") from exc
        assert isinstance(obj, Object)

        docstring = obj.docstring
        if not docstring:
            raise ValueError(f"Symbol {symbol!r} has no docstring.")

        return docstring.value

    # The decorator makes the function untyped
    @env.macro  # type: ignore[misc]
    def docstring_summary(symbol: str) -> str:
        """Get the summary of a Python symbol.

        Args:
            symbol: The fully qualified name of the Python symbol to get the summary of.

        Returns:
            The summary of the Python symbol.
        """
        docstring = _get_docstring(symbol)
        summary = docstring.splitlines(keepends=False)[0]
        # The python_handler is untyped here, so ignore the type
        return python_handler.do_convert_markdown(  # type: ignore[no-any-return]
            summary, heading_level=1, strip_paragraph=True
        )

    # This must be at the end to enable all standard features
    hook_env_with_everything(env)
