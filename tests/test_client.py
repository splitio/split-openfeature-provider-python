import pytest
from open_feature import open_feature_api
from open_feature.evaluation_context.evaluation_context import EvaluationContext
from open_feature.exception.error_code import ErrorCode
from open_feature.flag_evaluation.reason import Reason
from splitio import get_factory
from split_openfeature import SplitProvider


class TestClient(object):

    # The following are splits with treatments defined in the split.yaml file
    my_feature = "my_feature"  # 'on' when targeting_key='key', else 'off'
    some_other_feature = "some_other_feature"  # 'off'
    int_feature = "int_feature"  # '32'
    float_feature = "float_feature"  # '50.5'
    obj_feature = "obj_feature"  # '{\"key\": \"value\"}'

    @pytest.fixture
    def provider(self):
        factory = get_factory("localhost", config={"splitFile": "split.yaml"})
        factory.block_until_ready(5)
        return SplitProvider(client=factory.client())

    @pytest.fixture
    def set_provider(self, provider):
        open_feature_api.set_provider(provider)

    @pytest.fixture
    def client(self, set_provider):
        return open_feature_api.get_client("Split Client")

    @pytest.fixture(autouse=True)
    def targeting_key(self, client):
        client.context = EvaluationContext(targeting_key="key")

    def test_use_default(self, client):
        # flags that do not exist should return the default value
        flag_name = "random-non-existent-feature"

        result = client.get_boolean_value(flag_name, False)
        assert not result
        result = client.get_boolean_value(flag_name, True)
        assert result

        default_string = "blah"
        result = client.get_string_value(flag_name, default_string)
        assert result == default_string

        default_int = 100
        result = client.get_integer_value(flag_name, default_int)
        assert result == default_int

        default_float = 100.5
        result = client.get_float_value(flag_name, default_float)
        assert result == default_float

        default_obj = {"foo": "bar"}
        result = client.get_object_value(flag_name, default_obj)
        assert result == default_obj

    def test_missing_targeting_key(self, client):
        # Split requires a targeting key and should return the default treatment
        # and throw an error if not provided
        client.context = EvaluationContext()
        details = client.get_boolean_details("non-existent-feature", False)
        assert not details.value
        assert details.error_code == ErrorCode.TARGETING_KEY_MISSING

    def test_control_variant_non_existent_split(self, client):
        # split returns a treatment = "control" if the flag is not found.
        # This should be interpreted by the Split provider to mean not found and therefore use the default value.
        # This control treatment should still be recorded as the variant.
        details = client.get_boolean_details("non-existent-feature", False)
        assert not details.value
        assert details.variant == "control"
        assert details.error_code == ErrorCode.FLAG_NOT_FOUND

    def test_boolean_split(self, client):
        # This should be false as defined as "off" in the split.yaml
        result = client.get_boolean_value(self.some_other_feature, True)
        assert not result

    def test_boolean_with_key(self, client):
        # the key "key" was set in fixture. Therefore, the treatment of true should be received as defined in split.yaml
        result = client.get_boolean_value(self.my_feature, False)
        assert result

        # if we override the evaluation context for this check to use a different key,
        # this should take priority, and therefore we should receive a treatment of off
        result = client.get_boolean_value(self.my_feature, True, evaluation_context=EvaluationContext(targeting_key="randomKey"))
        assert not result

    def test_string_split(self, client):
        result = client.get_string_value(self.some_other_feature, "on")
        assert result == "off"

    def test_int_split(self, client):
        result = client.get_integer_value(self.int_feature, 0)
        assert result == 32

    def test_float_split(self, client):
        result = client.get_float_value(self.float_feature, 2.3)
        assert result == 50.5

    def test_obj_split(self, client):
        result = client.get_object_value(self.obj_feature, {})
        assert result == {"key": "value"}

    def test_get_metadata(self):
        assert open_feature_api.get_provider().get_metadata().name == "Split"

    def test_boolean_details(self, client):
        details = client.get_boolean_details(self.some_other_feature, True)
        assert details.flag_key == self.some_other_feature
        assert details.reason == Reason.TARGETING_MATCH
        assert not details.value
        # the flag has a treatment of "off", this is returned as a value of false but the variant is still "off"
        assert details.variant == "off"
        assert details.error_code is None

    def test_int_details(self, client):
        details = client.get_integer_details(self.int_feature, 0)
        assert details.flag_key == self.int_feature
        assert details.reason == Reason.TARGETING_MATCH
        assert details.value == 32
        assert details.variant == "32"
        assert details.error_code is None

    def test_float_details(self, client):
        details = client.get_float_details(self.float_feature, 2.3)
        assert details.flag_key == self.float_feature
        assert details.reason == Reason.TARGETING_MATCH
        assert details.value == 50.5
        assert details.variant == "50.5"
        assert details.error_code is None

    def test_string_details(self, client):
        details = client.get_string_details(self.some_other_feature, "blah")
        assert details.flag_key == self.some_other_feature
        assert details.reason == Reason.TARGETING_MATCH
        assert details.value == "off"
        assert details.variant == "off"
        assert details.error_code is None

    def test_obj_details(self, client):
        details = client.get_object_details(self.obj_feature, {})
        assert details.flag_key == self.obj_feature
        assert details.reason == Reason.TARGETING_MATCH
        assert details.value == {"key": "value"}
        assert details.variant == "{\"key\": \"value\"}"
        assert details.error_code is None

    def test_boolean_fail(self, client):
        # attempt to fetch an object treatment as a Boolean. Should result in the default
        value = client.get_boolean_value(self.obj_feature, False)
        assert not value

        details = client.get_boolean_details(self.obj_feature, False)
        assert not details.value
        assert details.error_code == ErrorCode.PARSE_ERROR
        assert details.reason == Reason.ERROR
        assert details.variant is None

    def test_int_fail(self, client):
        # attempt to fetch an object treatment as an int. Should result in the default
        value = client.get_integer_value(self.obj_feature, 10)
        assert value == 10

        details = client.get_integer_details(self.obj_feature, 10)
        assert details.value == 10
        assert details.error_code == ErrorCode.PARSE_ERROR
        assert details.reason == Reason.ERROR
        assert details.variant is None

    def test_float_fail(self, client):
        # attempt to fetch an object treatment as an int. Should result in the default
        value = client.get_float_value(self.obj_feature, 2.3)
        assert value == 2.3

        details = client.get_float_details(self.obj_feature, 2.3)
        assert details.value == 2.3
        assert details.error_code == ErrorCode.PARSE_ERROR
        assert details.reason == Reason.ERROR
        assert details.variant is None

    def test_obj_fail(self, client):
        # attempt to fetch a string treatment as an object. Should result in the default
        default_treatment = {"foo": "bar"}
        value = client.get_object_value(self.some_other_feature, default_treatment)
        assert value == default_treatment

        details = client.get_object_details(self.some_other_feature, default_treatment)
        assert details.value == default_treatment
        assert details.error_code == ErrorCode.PARSE_ERROR
        assert details.reason == Reason.ERROR
        assert details.variant is None
