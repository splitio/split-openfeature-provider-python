from splitio import get_factory, get_factory_async
from splitio.exceptions import TimeoutException
import logging

try:
    from splitio.models.events import SdkEvent
except ImportError:
    SdkEvent = None  # type: ignore  # Split < 10.6: no events API

_LOGGER = logging.getLogger(__name__)

# Sentinel for block_until_ready timeout (not a Split SdkEvent)
SPLIT_EVENT_BUR_TIMEOUT = "block_until_ready_timeout"


class SplitClientWrapper():

    def __init__(self, initial_context):
        self.sdk_ready = False
        self.split_client = None
        self._event_receiver = None

        if not self._validate_context(initial_context):
            raise AttributeError()

        self._api_key = initial_context.get("SdkKey")
        self._config = {}
        if initial_context.get("ConfigOptions") != None:
            self._config = initial_context.get("ConfigOptions")

        self._ready_block_time = 10
        if initial_context.get("ReadyBlockTime") != None:
            self._ready_block_time = initial_context.get("ReadyBlockTime")

        if initial_context.get("ThreadingMode") != None:
            self._threading_mode = initial_context.get("ThreadingMode")
            if self._threading_mode == "asyncio":
                self._initial_context = initial_context
                return

        if initial_context.get("SplitClient") != None:
            self.split_client = initial_context.get("SplitClient")
            self._factory = self.split_client._factory
            return

        try:
            self._factory = get_factory(self._api_key, config=self._config)
            self._factory.block_until_ready(self._ready_block_time)
            self.sdk_ready = True
        except TimeoutException:
            _LOGGER.debug("Split SDK timed out")
            self._notify_receiver(SPLIT_EVENT_BUR_TIMEOUT, None)

        self.split_client = self._factory.client()

    async def create(self):
        if self._initial_context.get("SplitClient") != None:
            self.split_client = self._initial_context.get("SplitClient")
            self._factory = self.split_client._factory
            await self._register_split_events_async()
            return

        try:
            self._factory = await get_factory_async(self._api_key, config=self._config)
            await self._factory.block_until_ready(self._ready_block_time)
            self.sdk_ready = True
        except TimeoutException:
            _LOGGER.debug("Split SDK timed out")
            self._notify_receiver(SPLIT_EVENT_BUR_TIMEOUT, None)

        self.split_client = self._factory.client()
        await self._register_split_events_async()

    def is_sdk_ready(self):
        if self.sdk_ready:
            return True

        try:
            self._factory.block_until_ready(0.1)
            self.sdk_ready = True
        except TimeoutException:
            _LOGGER.debug("Split SDK timed out")

        return self.sdk_ready

    def set_event_receiver(self, receiver):
        """Set the receiver that will be notified of Split SDK events (e.g. the provider)."""
        self._event_receiver = receiver

    def register_for_split_events(self):
        """Register for Split SDK events (SDK_READY, SDK_UPDATE). Pass the provider as receiver (or call set_event_receiver first)."""
        self._register_split_events()

    def unregister_for_split_events(self):
        """Stop receiving Split SDK events."""
        self._event_receiver = None

    def _notify_receiver(self, split_event, event_metadata):
        if self._event_receiver is None:
            _LOGGER.debug("Split event %s: no receiver registered", split_event)
            return
        try:
            self._event_receiver._on_split_event(split_event, event_metadata)
        except Exception as ex:
            _LOGGER.debug("Split event callback error: %s", ex)

    def _register_split_events(self):
        if self._factory is None:
            _LOGGER.warning("SplitClientWrapper: _factory is None, cannot register for SDK events")
            return
        if SdkEvent is None:
            _LOGGER.debug("SplitClientWrapper: SdkEvent not available (Split SDK < 10.6?), skipping event registration")
            return
        try:
            em = self._factory._events_manager
            if not hasattr(em, "register"):
                _LOGGER.warning("SplitClientWrapper: events_manager has no register method")
                return
            em.register(SdkEvent.SDK_READY, lambda m: self._notify_receiver(SdkEvent.SDK_READY, m))
            em.register(SdkEvent.SDK_UPDATE, lambda m: self._notify_receiver(SdkEvent.SDK_UPDATE, m))
            _LOGGER.info("SplitClientWrapper: registered for SDK_READY and SDK_UPDATE")
        except Exception as ex:
            _LOGGER.warning("Could not register Split events: %s", ex)

    def destroy(self, destroy_event=None):
        self._factory.destroy(destroy_event)

    async def _register_split_events_async(self):
        if self._factory is None or SdkEvent is None:
            return
        try:
            em = self._factory._events_manager
            if hasattr(em, "register"):
                await em.register(SdkEvent.SDK_READY, lambda m: self._notify_receiver(SdkEvent.SDK_READY, m))
                await em.register(SdkEvent.SDK_UPDATE, lambda m: self._notify_receiver(SdkEvent.SDK_UPDATE, m))
        except Exception as ex:
            _LOGGER.debug("Could not register Split events: %s", ex)

    async def destroy_async(self):
        await self._factory.destroy()

    async def is_sdk_ready_async(self):
        if self.sdk_ready:
            return True

        try:
            await self._factory.block_until_ready(0.1)
            self.sdk_ready = True
        except TimeoutException:
            _LOGGER.debug("Split SDK timed out")

        return self.sdk_ready

    def _validate_context(self, initial_context):
        if initial_context != None and not isinstance(initial_context, dict):
            _LOGGER.error("SplitClientWrapper: initial_context must be of type `dict`")
            return False

        if initial_context.get("SplitClient") == None and initial_context.get("SdkKey") == None:
            _LOGGER.error("SplitClientWrapper: initial_context must contain keys `SplitClient` or `SdkKey`")
            return False

        if initial_context.get("SdkKey") != None and not isinstance(initial_context.get("SdkKey"), str):
            _LOGGER.error("SplitClientWrapper: key `SdkKey` must be of type `str`")
            return False

        if initial_context.get("ConfigOptions") != None and not isinstance(initial_context.get("ConfigOptions"), dict):
            _LOGGER.error("SplitClientWrapper: key `ConfigOptions` must be of type `dict`")
            return False

        return True
