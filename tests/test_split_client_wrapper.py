import pytest
from splitio import get_factory
from split_openfeature import SplitClientWrapper
import unittest

class TestSplitClientWrapper(unittest.TestCase):

    def test_using_external_splitclient(self):
        split_factory = get_factory("localhost", config={"splitFile": "split.yaml"})
        split_factory.block_until_ready(5)
        split_client = split_factory.client()
        wrapper = SplitClientWrapper({"SplitClient": split_client})
        assert wrapper.split_client != None
        assert wrapper.is_sdk_ready()

    def test_using_internal_splitclient(self):
        wrapper = SplitClientWrapper({"ReadyBlockTime": 1, "SdkKey": "localhost", "ConfigOptions": {"splitFile": "split.yaml"}})
        assert wrapper.split_client != None
        assert wrapper.is_sdk_ready()
        assert wrapper.sdk_ready == 1


    def test_sdk_not_ready(self):
        wrapper = SplitClientWrapper({"ReadyBlockTime": 0.1, "SdkKey": "api", "ConfigOptions": {}})        
        assert not wrapper.is_sdk_ready()

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
