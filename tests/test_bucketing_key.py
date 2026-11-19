import logging

import pytest
from mock import MagicMock
from openfeature.evaluation_context import EvaluationContext
from openfeature.exception import ErrorCode, TargetingKeyMissingError
from splitio.client.key import Key

from split_openfeature_provider import SplitProvider, SplitProviderAsync

FLAG = "flagName"
PROVIDER_LOGGER = "split_openfeature_provider.split_provider"
INVALID = [("", "blank"), ("   ", "blank"), (1, "not a string"), (True, "not a string"), ({"x": 1}, "not a string")]


def _sync_provider(treatment="on"):
    client = MagicMock()
    client.get_treatment_with_config.return_value = (treatment, None)
    return SplitProvider({"SplitClient": client}), client


async def _async_provider(treatment="on"):
    client = MagicMock()

    async def block_until_ready(_):
        pass
    client._factory.block_until_ready = block_until_ready
    calls = []

    async def get_treatment_with_config(*args):
        calls.append(args)
        return (treatment, None)
    client.get_treatment_with_config = get_treatment_with_config
    provider = SplitProviderAsync({"SplitClient": client})
    await provider.create()
    return provider, calls


def _bk_warnings(caplog):
    return [r for r in caplog.records
            if r.name == PROVIDER_LOGGER and r.levelno == logging.WARNING and "bucketingKey" in r.getMessage()]


class TestBucketingKeySync:
    # C8.1
    def test_valid_bucketing_key_builds_split_key(self):
        provider, client = _sync_provider()
        provider.resolve_boolean_details(FLAG, False, EvaluationContext("user", {"bucketingKey": "bucket"}))
        key, flag, attributes = client.get_treatment_with_config.call_args[0]
        assert isinstance(key, Key)
        assert (key.matching_key, key.bucketing_key) == ("user", "bucket")
        assert flag == FLAG

    # C8.4c
    def test_padded_value_is_trimmed(self):
        provider, client = _sync_provider()
        provider.resolve_boolean_details(FLAG, False, EvaluationContext("user", {"bucketingKey": " b1 "}))
        assert client.get_treatment_with_config.call_args[0][0].bucketing_key == "b1"

    # C8.2
    @pytest.mark.parametrize("attrs", [{}, {"bucketingKey": None}])
    def test_absent_or_none_uses_plain_targeting_key(self, attrs, caplog):
        provider, client = _sync_provider()
        provider.resolve_boolean_details(FLAG, False, EvaluationContext("user", attrs))
        assert client.get_treatment_with_config.call_args[0][0] == "user"
        assert not _bk_warnings(caplog)

    # C8.3
    @pytest.mark.parametrize("value,reason", INVALID)
    def test_invalid_is_ignored_with_warning(self, value, reason, caplog):
        provider, client = _sync_provider()
        result = provider.resolve_boolean_details(FLAG, False, EvaluationContext("user", {"bucketingKey": value}))
        assert result.error_code is None and result.value is True
        assert client.get_treatment_with_config.call_args[0][0] == "user"
        warnings = _bk_warnings(caplog)
        assert len(warnings) == 1 and reason in warnings[0].getMessage()

    # C8.4 (+ C3, C1)
    @pytest.mark.parametrize("value", ["bucket", "", "   ", 1, None])
    def test_never_forwarded_as_attribute(self, value):
        provider, client = _sync_provider()
        context = EvaluationContext("user", {"bucketingKey": value, "BucketingKey": "p", "bucketing_key": "s", "plan": "pro"})
        provider.resolve_boolean_details(FLAG, False, context)
        attributes = client.get_treatment_with_config.call_args[0][2]
        assert attributes == {"BucketingKey": "p", "bucketing_key": "s", "plan": "pro"}
        assert "bucketingKey" in context.attributes, "caller's context must not be mutated"

    # C8.4b
    def test_over_length_passed_through_and_control_maps_to_default(self):
        provider, client = _sync_provider(treatment="control")
        result = provider.resolve_boolean_details(FLAG, True, EvaluationContext("user", {"bucketingKey": "b" * 251}))
        assert client.get_treatment_with_config.call_args[0][0].bucketing_key == "b" * 251
        assert result.value is True and result.error_code == ErrorCode.FLAG_NOT_FOUND

    # C8.5
    @pytest.mark.parametrize("targeting_key", [None, ""])
    def test_missing_targeting_key_still_errors(self, targeting_key):
        provider, client = _sync_provider()
        with pytest.raises(TargetingKeyMissingError):
            provider.resolve_boolean_details(FLAG, False, EvaluationContext(targeting_key, {"bucketingKey": "bucket"}))
        client.get_treatment_with_config.assert_not_called()

    # C8.6: the provider has no track (openfeature_sdk 0.8.3 has no Tracking API). Revisit C5 if one is added.
    def test_no_track(self):
        assert not hasattr(SplitProvider, "track") and not hasattr(SplitProviderAsync, "track")


class TestBucketingKeyAsync:
    @pytest.mark.asyncio
    async def test_valid_bucketing_key_builds_split_key(self):
        provider, calls = await _async_provider()
        await provider.resolve_boolean_details_async(FLAG, False, EvaluationContext("user", {"bucketingKey": "bucket"}))
        key = calls[-1][0]
        assert isinstance(key, Key) and (key.matching_key, key.bucketing_key) == ("user", "bucket")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("attrs", [{}, {"bucketingKey": None}])
    async def test_absent_or_none_uses_plain_targeting_key(self, attrs):
        provider, calls = await _async_provider()
        await provider.resolve_boolean_details_async(FLAG, False, EvaluationContext("user", attrs))
        assert calls[-1][0] == "user"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("value,reason", INVALID)
    async def test_invalid_is_ignored_with_warning(self, value, reason, caplog):
        provider, calls = await _async_provider()
        result = await provider.resolve_boolean_details_async(FLAG, False, EvaluationContext("user", {"bucketingKey": value}))
        assert result.error_code is None and calls[-1][0] == "user"
        warnings = _bk_warnings(caplog)
        assert len(warnings) == 1 and reason in warnings[0].getMessage()

    @pytest.mark.asyncio
    async def test_never_forwarded_as_attribute(self):
        provider, calls = await _async_provider()
        await provider.resolve_boolean_details_async(FLAG, False, EvaluationContext("user", {"bucketingKey": "b", "plan": "pro"}))
        assert calls[-1][2] == {"plan": "pro"}

    @pytest.mark.asyncio
    async def test_over_length_passed_through_and_control_maps_to_default(self):
        provider, calls = await _async_provider(treatment="control")
        result = await provider.resolve_boolean_details_async(FLAG, True, EvaluationContext("user", {"bucketingKey": "b" * 251}))
        assert calls[-1][0].bucketing_key == "b" * 251
        assert result.value is True and result.error_code == ErrorCode.FLAG_NOT_FOUND

    @pytest.mark.asyncio
    async def test_missing_targeting_key_still_errors(self):
        provider, calls = await _async_provider()
        with pytest.raises(TargetingKeyMissingError):
            await provider.resolve_boolean_details_async(FLAG, False, EvaluationContext(None, {"bucketingKey": "b"}))
        assert not calls
