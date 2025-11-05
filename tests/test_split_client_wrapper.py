import pytest
import unittest
from threading import Event

from splitio import get_factory, get_factory_async
from split_openfeature import SplitClientWrapper

class TestSplitClientWrapper(unittest.TestCase):
    def test_using_external_splitclient(self):
        split_factory = get_factory("localhost", config={"splitFile": "split.yaml"})
        split_factory.block_until_ready(5)
        split_client = split_factory.client()
        wrapper = SplitClientWrapper({"SplitClient": split_client})
        assert wrapper.split_client != None
        assert wrapper.is_sdk_ready()
        
        destroy_event = Event()
        wrapper.destroy(destroy_event)
        destroy_event.wait()
        assert split_factory.destroyed

    def test_using_internal_splitclient(self):
        wrapper = SplitClientWrapper({"ReadyBlockTime": 1, "SdkKey": "localhost", "ConfigOptions": {"splitFile": "split.yaml"}})
        assert wrapper.split_client != None
        assert wrapper.is_sdk_ready()
        assert wrapper.sdk_ready == 1
        destroy_event = Event()
        wrapper.destroy(destroy_event)
        destroy_event.wait()
        assert wrapper._factory.destroyed

    def test_sdk_not_ready(self):
        wrapper = SplitClientWrapper({"ReadyBlockTime": 0.1, "SdkKey": "api", "ConfigOptions": {}})        
        assert not wrapper.is_sdk_ready()
        wrapper.destroy()

    def test_invalid_apikey(self):
        with self.assertRaises(AttributeError) as context:
            wrapper = SplitClientWrapper({"SdkKey": 123})

    def test_invalid_config(self):
        with self.assertRaises(AttributeError) as context:
            wrapper = SplitClientWrapper({"SdkKey": "123", "ConfigOptions": "234"})

    def test_no_params(self):
        with self.assertRaises(AttributeError) as context:
            wrapper = SplitClientWrapper({})

    def test_reqwuired_params(self):
        with self.assertRaises(AttributeError) as context:
            wrapper = SplitClientWrapper({"ConfigOptions": {}})

class TestSplitClientWrapperAsync(object):
    @pytest.mark.asyncio
    async def test_using_external_splitclient_async(self):
        split_factory = await get_factory_async("localhost", config={"splitFile": "split.yaml"})
        await split_factory.block_until_ready(5)
        split_client = split_factory.client()
        wrapper = SplitClientWrapper({"SplitClient": split_client, "ThreadingMode": "asyncio"})
        await wrapper.create()
        assert wrapper.split_client != None
        assert await wrapper.is_sdk_ready_async()
        await wrapper.destroy_async()
        assert split_factory.destroyed

    @pytest.mark.asyncio
    async def test_using_internal_splitclient_async(self):
        wrapper = SplitClientWrapper({"ReadyBlockTime": 1, "SdkKey": "localhost", "ConfigOptions": {"splitFile": "split.yaml"}, "ThreadingMode": "asyncio"})
        await wrapper.create()
        assert wrapper.split_client != None
        assert await wrapper.is_sdk_ready_async()
        assert wrapper.sdk_ready == True
        await wrapper.destroy_async()
        assert wrapper._factory.destroyed

    @pytest.mark.asyncio
    async def test_sdk_not_ready_async(self):
        wrapper = SplitClientWrapper({"ReadyBlockTime": 0.1, "SdkKey": "api", "ConfigOptions": {}, "ThreadingMode": "asyncio"})        
        await wrapper.create()
        assert not await wrapper.is_sdk_ready_async()
        await wrapper.destroy_async()
