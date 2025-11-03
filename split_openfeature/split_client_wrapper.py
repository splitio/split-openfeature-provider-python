from splitio import get_factory, get_factory_async
from splitio.exceptions import TimeoutException
import logging

_LOGGER = logging.getLogger(__name__)

class SplitClientWrapper():
    
    def __init__(self, initial_context):
        self.sdk_ready = False
        self.split_client = None
        
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
            
        self.split_client = self._factory.client()
        
    async def create(self):
        if self._initial_context.get("SplitClient") != None:
            self.split_client = self._initial_context.get("SplitClient")
            self._factory = self.split_client._factory
            return
        
        try:
            self._factory = await get_factory_async(self._api_key, config=self._config)
            await self._factory.block_until_ready(self._ready_block_time)
            self.sdk_ready = True
        except TimeoutException:
            _LOGGER.debug("Split SDK timed out")
            
        self.split_client = self._factory.client()
        
    def is_sdk_ready(self):
        if self.sdk_ready:
            return True
        
        try:
            self._factory.block_until_ready(0.1)
            self.sdk_ready = True
        except TimeoutException:
            _LOGGER.debug("Split SDK timed out")
        
        return self.sdk_ready

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