"""Unit tests for InterruptHandler."""

import signal

import pytest

from saha.orchestrator.loop import InterruptHandler


class TestInterruptHandler:
    """Test the InterruptHandler context manager."""

    def test_interrupt_handler_initializes_with_zero_count(self):
        """Test that handler starts with zero interrupts."""
        with InterruptHandler() as handler:
            assert handler.interrupt_count == 0
            assert not handler.was_interrupted()

    def test_first_interrupt_sets_flag(self):
        """Test that first interrupt sets the interrupted flag."""
        with InterruptHandler() as handler:
            # Simulate first interrupt
            try:
                handler._signal_handler(signal.SIGINT, None)
            except KeyboardInterrupt:
                pass

            assert handler.interrupt_count == 1
            assert handler.was_interrupted()

    def test_signal_handler_raises_keyboard_interrupt(self):
        """Test that signal handler raises KeyboardInterrupt on first call."""
        with InterruptHandler() as handler:
            with pytest.raises(KeyboardInterrupt):
                handler._signal_handler(signal.SIGINT, None)

    def test_signal_handler_exits_on_second_interrupt(self):
        """Test that second interrupt calls sys.exit."""
        with InterruptHandler() as handler:
            # First interrupt
            try:
                handler._signal_handler(signal.SIGINT, None)
            except KeyboardInterrupt:
                pass

            # Second interrupt should exit
            with pytest.raises(SystemExit) as exc_info:
                handler._signal_handler(signal.SIGINT, None)

            assert exc_info.value.code == 1

    def test_context_manager_restores_signal_handler(self):
        """Test that original signal handler is restored after exit."""
        # Store original handler
        original_handler = signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGINT, original_handler)

        try:
            # Inside context, handler should be different (InterruptHandler._signal_handler)
            with InterruptHandler():
                inside_handler = signal.getsignal(signal.SIGINT)
                # Handler should be different inside context
                assert inside_handler != original_handler
                assert inside_handler is not signal.SIG_DFL

            # After context, should be restored
            restored_handler = signal.getsignal(signal.SIGINT)
            assert restored_handler == original_handler
        finally:
            # Ensure we restore to original in case of test failure
            signal.signal(signal.SIGINT, original_handler)

    def test_multiple_handlers_in_sequence(self):
        """Test that multiple handler contexts work independently."""
        with InterruptHandler() as handler1:
            assert handler1.interrupt_count == 0

        with InterruptHandler() as handler2:
            # New handler should start fresh
            assert handler2.interrupt_count == 0
            assert not handler2.was_interrupted()

    def test_was_interrupted_returns_true_after_interrupt(self):
        """Test that was_interrupted correctly reports interrupt state."""
        with InterruptHandler() as handler:
            assert not handler.was_interrupted()

            try:
                handler._signal_handler(signal.SIGINT, None)
            except KeyboardInterrupt:
                pass

            assert handler.was_interrupted()
