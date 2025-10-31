from splitio import get_factory
from splitio.client.client import Client
from splitio.exceptions import TimeoutException
import logging

_LOGGER = logging.getLogger(__name__)

class SplitClientWrapper():
    
    def __init__(self, initial_context):
        self.sdk_ready = False
        self.split_client = None
        
        if not self._validate_context(initial_context):
            raise AttributeError()                

        if initial_context.get("SplitClient") != None:
            self.split_client = initial_context.get("SplitClient")
            self._factory = self.split_client._factory
            return

        api_key = initial_context.get("ApiKey")
        config = {}
        if initial_context.get("ConfigOptions") != None:
            config = initial_context.get("ConfigOptions")
        
        self._factory = get_factory(api_key, config=config)
        ready_block_time = 10
        if initial_context.get("ReadyBlockTime") != None:
            ready_block_time = initial_context.get("ReadyBlockTime")
        
        try:
            self._factory.block_until_ready(ready_block_time)
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
        
    def _validate_context(self, initial_context):
        if initial_context != None and not isinstance(initial_context, dict):
            _LOGGER.error("SplitClientWrapper: initial_context must be of type `dict`")
            return False
        
        if initial_context.get("SplitClient") == None and initial_context.get("ApiKey") == None:
            _LOGGER.error("SplitClientWrapper: initial_context must contain keys `SplitClient` or `ApiKey`")
            return False

        if initial_context.get("ApiKey") != None and not isinstance(initial_context.get("ApiKey"), str):
            _LOGGER.error("SplitClientWrapper: key `ApiKey` must be of type `str`")
            return False

        if initial_context.get("ConfigOptions") != None and not isinstance(initial_context.get("ConfigOptions"), dict):
            _LOGGER.error("SplitClientWrapper: key `ConfigOptions` must be of type `dict`")
            return False
        
        return True