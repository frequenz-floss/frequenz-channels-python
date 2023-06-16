# License: MIT
# Copyright © 2023 Frequenz Energy-as-a-Service GmbH

"""Tests for the Selector implementation."""

from unittest import mock

import pytest

from frequenz.channels import Receiver, ReceiverStoppedError
from frequenz.channels.util import Selected, selected_from


class TestSelected:
    """Tests for the Selected class."""

    def test_with_value(self) -> None:
        """Test selected from a receiver with a value."""
        recv = mock.MagicMock(spec=Receiver[int])
        recv.consume.return_value = 42
        selected = Selected[int](recv)

        assert selected_from(selected, recv)
        assert selected.value == 42
        assert selected.exception is None
        assert not selected.was_stopped()

    def test_with_exception(self) -> None:
        """Test selected from a receiver with an exception."""
        recv = mock.MagicMock(spec=Receiver[int])
        exception = Exception("test")
        recv.consume.side_effect = exception
        selected = Selected[int](recv)

        assert selected_from(selected, recv)
        with pytest.raises(Exception, match="test"):
            _ = selected.value
        assert selected.exception is exception
        assert not selected.was_stopped()

    def test_with_stopped(self) -> None:
        """Test selected from a stopped receiver."""
        recv = mock.MagicMock(spec=Receiver[int])
        exception = ReceiverStoppedError[int](recv)
        recv.consume.side_effect = exception
        selected = Selected[int](recv)

        assert selected_from(selected, recv)
        with pytest.raises(
            ReceiverStoppedError,
            match=r"Receiver <MagicMock spec='_GenericAlias' id='\d+'> was stopped",
        ):
            _ = selected.value
        assert selected.exception is exception
        assert selected.was_stopped()
