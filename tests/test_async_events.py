import pytest
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, call
from openfeature.exception import ErrorCode
from openfeature.event import ProviderEventDetails

from split_openfeature_provider import SplitProvider, SplitProviderAsync
from split_openfeature_provider.split_client_wrapper import SplitClientWrapper, SPLIT_EVENT_BUR_TIMEOUT

try:
    from splitio.models.events import SdkEvent
except ImportError:
    SdkEvent = None


class MockEventReceiver:
    """Mock event receiver for testing async event notifications."""
    def __init__(self):
        self.events = []

    async def _on_split_event_async(self, split_event, event_metadata):
        self.events.append({"event": split_event, "metadata": event_metadata})


class TestSplitClientWrapperAsyncEvents:
    """Tests for async event notification in SplitClientWrapper."""

    @pytest.mark.asyncio
    async def test_notify_receiver_async_with_receiver(self):
        """Test that _notify_receiver_async calls the receiver's async method."""
        wrapper = SplitClientWrapper({"SdkKey": "test", "ConfigOptions": {}, "ThreadingMode": "asyncio"})
        receiver = MockEventReceiver()
        wrapper.set_event_receiver(receiver)

        # Call the async notify method
        test_metadata = {"test": "data"}
        await wrapper._notify_receiver_async("test_event", test_metadata)

        # Verify the receiver was notified
        assert len(receiver.events) == 1
        assert receiver.events[0]["event"] == "test_event"
        assert receiver.events[0]["metadata"] == test_metadata

    @pytest.mark.asyncio
    async def test_notify_receiver_async_without_receiver(self):
        """Test that _notify_receiver_async handles missing receiver gracefully."""
        wrapper = SplitClientWrapper({"SdkKey": "test", "ConfigOptions": {}, "ThreadingMode": "asyncio"})

        # Should not raise an exception when no receiver is set
        await wrapper._notify_receiver_async("test_event", None)

    @pytest.mark.asyncio
    async def test_notify_receiver_async_with_exception(self):
        """Test that _notify_receiver_async handles receiver exceptions gracefully."""
        wrapper = SplitClientWrapper({"SdkKey": "test", "ConfigOptions": {}, "ThreadingMode": "asyncio"})

        # Create a receiver that raises an exception
        receiver = MagicMock()
        receiver._on_split_event_async = AsyncMock(side_effect=Exception("Test exception"))
        wrapper.set_event_receiver(receiver)

        # Should not raise the exception
        await wrapper._notify_receiver_async("test_event", None)

    @pytest.mark.asyncio
    async def test_timeout_calls_notify_receiver_async(self):
        """Test that timeout during async create calls _notify_receiver_async."""
        from splitio.exceptions import TimeoutException

        receiver = MockEventReceiver()
        wrapper = SplitClientWrapper({
            "ReadyBlockTime": 0.1,
            "SdkKey": "invalid_key",
            "ConfigOptions": {},
            "ThreadingMode": "asyncio"
        })
        wrapper.set_event_receiver(receiver)

        # Mock get_factory_async to raise TimeoutException
        with patch('split_openfeature_provider.split_client_wrapper.get_factory_async') as mock_factory:
            mock_factory_instance = AsyncMock()
            mock_factory_instance.block_until_ready = AsyncMock(side_effect=TimeoutException("timeout"))
            mock_factory_instance.client = MagicMock(return_value=MagicMock())
            mock_factory.return_value = mock_factory_instance

            await wrapper.create()

            # Verify that the receiver was notified of the timeout
            assert len(receiver.events) == 1
            assert receiver.events[0]["event"] == SPLIT_EVENT_BUR_TIMEOUT
            assert receiver.events[0]["metadata"] is None


@pytest.mark.skipif(SdkEvent is None, reason="SdkEvent not available in this Split SDK version")
class TestSplitProviderAsyncEvents:
    """Tests for async event handling in SplitProvider."""

    @pytest.mark.asyncio
    async def test_on_split_event_async_sdk_ready(self):
        """Test that _on_split_event_async emits provider ready event."""
        # Create a mock client
        mock_client = MagicMock()
        provider = SplitProviderAsync({"SplitClient": mock_client})

        # Mock the emit_provider_ready method
        provider.emit_provider_ready = MagicMock()

        # Call the async event handler
        test_metadata = {"timestamp": 123456}
        await provider._on_split_event_async(SdkEvent.SDK_READY, test_metadata)

        # Verify that emit_provider_ready was called
        assert provider.emit_provider_ready.called
        call_args = provider.emit_provider_ready.call_args[0][0]
        assert isinstance(call_args, ProviderEventDetails)
        assert call_args.metadata is not None
        assert "split_event" in call_args.metadata

    @pytest.mark.asyncio
    async def test_on_split_event_async_sdk_update(self):
        """Test that _on_split_event_async emits provider configuration changed event."""
        # Create a mock client
        mock_client = MagicMock()
        provider = SplitProviderAsync({"SplitClient": mock_client})

        # Mock the emit_provider_configuration_changed method
        provider.emit_provider_configuration_changed = MagicMock()

        # Call the async event handler with metadata containing changed flags
        test_metadata = {"names": ["flag1", "flag2"]}
        await provider._on_split_event_async(SdkEvent.SDK_UPDATE, test_metadata)

        # Verify that emit_provider_configuration_changed was called
        assert provider.emit_provider_configuration_changed.called
        call_args = provider.emit_provider_configuration_changed.call_args[0][0]
        assert isinstance(call_args, ProviderEventDetails)
        assert call_args.flags_changed == ["flag1", "flag2"]
        assert call_args.metadata is not None
        assert "split_event" in call_args.metadata

    @pytest.mark.asyncio
    async def test_on_split_event_async_bur_timeout(self):
        """Test that _on_split_event_async emits provider error on timeout."""
        # Create a mock client
        mock_client = MagicMock()
        provider = SplitProviderAsync({"SplitClient": mock_client})

        # Mock the emit_provider_error method
        provider.emit_provider_error = MagicMock()

        # Call the async event handler with timeout event
        await provider._on_split_event_async(SPLIT_EVENT_BUR_TIMEOUT, None)

        # Verify that emit_provider_error was called
        assert provider.emit_provider_error.called
        call_args = provider.emit_provider_error.call_args[0][0]
        assert isinstance(call_args, ProviderEventDetails)
        assert call_args.error_code == ErrorCode.PROVIDER_NOT_READY
        assert "Block until ready timed out" in call_args.message
        assert call_args.metadata is not None

    @pytest.mark.asyncio
    async def test_on_split_event_async_with_event_object_metadata(self):
        """Test that _on_split_event_async handles EventsMetadata objects."""
        # Create a mock client
        mock_client = MagicMock()
        provider = SplitProviderAsync({"SplitClient": mock_client})

        # Mock the emit_provider_configuration_changed method
        provider.emit_provider_configuration_changed = MagicMock()

        # Create a mock EventsMetadata object
        mock_metadata = MagicMock()
        mock_metadata.metadata = None  # Ensure the metadata attribute is None
        mock_metadata.get_names.return_value = ["flag_a", "flag_b"]
        mock_metadata.get_type.return_value = MagicMock(value="SPLIT_UPDATE")

        # Call the async event handler
        await provider._on_split_event_async(SdkEvent.SDK_UPDATE, mock_metadata)

        # Verify that emit_provider_configuration_changed was called
        assert provider.emit_provider_configuration_changed.called
        call_args = provider.emit_provider_configuration_changed.call_args[0][0]
        assert isinstance(call_args, ProviderEventDetails)
        assert call_args.flags_changed == ["flag_a", "flag_b"]
        assert "split_names" in call_args.metadata
        assert call_args.metadata["split_names"] == ["flag_a", "flag_b"]

    @pytest.mark.asyncio
    async def test_on_split_event_async_update_with_null_names(self):
        """Test that _on_split_event_async handles SDK_UPDATE with no flag names."""
        # Create a mock client
        mock_client = MagicMock()
        provider = SplitProviderAsync({"SplitClient": mock_client})

        # Mock the emit_provider_configuration_changed method
        provider.emit_provider_configuration_changed = MagicMock()

        # Call the async event handler with no metadata
        await provider._on_split_event_async(SdkEvent.SDK_UPDATE, None)

        # Verify that emit_provider_configuration_changed was called
        assert provider.emit_provider_configuration_changed.called
        call_args = provider.emit_provider_configuration_changed.call_args[0][0]
        assert isinstance(call_args, ProviderEventDetails)
        assert call_args.flags_changed is None


class TestSyncProviderEvents:
    """Tests for sync event handling in SplitProvider (for completeness)."""

    def test_on_split_event_sdk_ready(self):
        """Test that _on_split_event emits provider ready event."""
        if SdkEvent is None:
            pytest.skip("SdkEvent not available")

        # Create a mock client
        mock_client = MagicMock()
        provider = SplitProvider({"SplitClient": mock_client})

        # Mock the emit_provider_ready method
        provider.emit_provider_ready = MagicMock()

        # Call the sync event handler
        test_metadata = {"timestamp": 123456}
        provider._on_split_event(SdkEvent.SDK_READY, test_metadata)

        # Verify that emit_provider_ready was called
        assert provider.emit_provider_ready.called
        call_args = provider.emit_provider_ready.call_args[0][0]
        assert isinstance(call_args, ProviderEventDetails)
        assert call_args.metadata is not None
        assert "split_event" in call_args.metadata

    def test_on_split_event_sdk_update(self):
        """Test that _on_split_event emits provider configuration changed event."""
        if SdkEvent is None:
            pytest.skip("SdkEvent not available")

        # Create a mock client
        mock_client = MagicMock()
        provider = SplitProvider({"SplitClient": mock_client})

        # Mock the emit_provider_configuration_changed method
        provider.emit_provider_configuration_changed = MagicMock()

        # Call the sync event handler with metadata containing changed flags
        test_metadata = {"names": ["flag1", "flag2"]}
        provider._on_split_event(SdkEvent.SDK_UPDATE, test_metadata)

        # Verify that emit_provider_configuration_changed was called
        assert provider.emit_provider_configuration_changed.called
        call_args = provider.emit_provider_configuration_changed.call_args[0][0]
        assert isinstance(call_args, ProviderEventDetails)
        assert call_args.flags_changed == ["flag1", "flag2"]

    def test_on_split_event_bur_timeout(self):
        """Test that _on_split_event emits provider error on timeout."""
        # Create a mock client
        mock_client = MagicMock()
        provider = SplitProvider({"SplitClient": mock_client})

        # Mock the emit_provider_error method
        provider.emit_provider_error = MagicMock()

        # Call the sync event handler with timeout event
        provider._on_split_event(SPLIT_EVENT_BUR_TIMEOUT, None)

        # Verify that emit_provider_error was called
        assert provider.emit_provider_error.called
        call_args = provider.emit_provider_error.call_args[0][0]
        assert isinstance(call_args, ProviderEventDetails)
        assert call_args.error_code == ErrorCode.PROVIDER_NOT_READY
        assert "Block until ready timed out" in call_args.message
