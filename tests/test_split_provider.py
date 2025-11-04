from pytest import fail
import pytest
from mock import MagicMock
from openfeature.exception import ErrorCode, OpenFeatureError
from openfeature.evaluation_context import EvaluationContext
from split_openfeature import SplitProvider, SplitProviderAsync

class TestProvider(object):
    eval_context = EvaluationContext("someKey")
    flag_name = "flagName"

    def reset_client(self):
        self.client = MagicMock()
        self.provider = SplitProvider({"SplitClient": self.client})

    def mock_client_return(self, val):
        self.client.get_treatment_with_config.return_value = (val, "{'prop':'val'}")

    # *** Boolean eval tests ***
    def test_boolean_none_empty(self):
        # if a treatment is None or empty it should return the default treatment
        self.reset_client()

        self.mock_client_return(None)
        result = self.provider.resolve_boolean_details(self.flag_name, True, self.eval_context)
        assert result.value
        result = self.provider.resolve_boolean_details(self.flag_name, False, self.eval_context)
        assert not result.value

    def test_boolean_control(self):
        # if a treatment is "control" it should return the default treatment
        self.reset_client()
        self.mock_client_return("control")
        result = self.provider.resolve_boolean_details(self.flag_name, False, self.eval_context)
        assert not result.value
        result = self.provider.resolve_boolean_details(self.flag_name, True, self.eval_context)
        assert result.value

    def test_boolean_true(self):
        # treatment of "true" should eval to True boolean
        self.reset_client()
        self.mock_client_return("true")
        details = self.provider.resolve_boolean_details(self.flag_name, False, self.eval_context)
        assert details.value
        assert details.flag_metadata["config"] == "{'prop':'val'}"
        assert details.variant == "true"

    def test_boolean_on(self):
        # treatment of "on" should eval to True boolean
        self.reset_client()
        self.mock_client_return("on")
        details = self.provider.resolve_boolean_details(self.flag_name, False, self.eval_context)
        assert details.value
        assert details.flag_metadata["config"] == "{'prop':'val'}"
        assert details.variant == "on"

    def test_boolean_false(self):
        # treatment of "true" should eval to True boolean
        self.reset_client()
        self.mock_client_return("false")
        details = self.provider.resolve_boolean_details(self.flag_name, False, self.eval_context)
        assert not details.value
        assert details.flag_metadata["config"] == "{'prop':'val'}"
        assert details.variant == "false"

    def test_boolean_off(self):
        # treatment of "on" should eval to True boolean
        self.reset_client()
        self.mock_client_return("off")
        details = self.provider.resolve_boolean_details(self.flag_name, False, self.eval_context)
        assert not details.value
        assert details.flag_metadata["config"] == "{'prop':'val'}"
        assert details.variant == "off"

    def test_boolean_error(self):
        # any other random string other than on,off,true,false,control should throw an error
        self.reset_client()
        self.mock_client_return("a random string")
        try:
            self.provider.resolve_boolean_details(self.flag_name, False, self.eval_context)
            fail("Should have thrown an error casting string to boolean")
        except OpenFeatureError as e:
            assert e.error_code == ErrorCode.PARSE_ERROR
        except Exception:
            fail("Unexpected exception occurred")

    # *** String eval tests ***
    def test_string_none_empty(self):
        # if a treatment is None or empty it should return the default treatment
        self.reset_client()
        default_treatment = "defaultTreatment"

        self.mock_client_return(None)
        result = self.provider.resolve_string_details(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

        self.mock_client_return("")
        result = self.provider.resolve_string_details(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    def test_string_control(self):
        # "control" treatment should eval to default treatment
        self.reset_client()
        self.mock_client_return("control")
        default_treatment = "defaultTreatment"
        result = self.provider.resolve_string_details(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    def test_string_regular(self):
        # a string treatment should eval to itself
        self.reset_client()
        treatment = "treatment"
        self.mock_client_return(treatment)
        result = self.provider.resolve_string_details(self.flag_name, "someDefaultTreatment", self.eval_context)
        assert result.value == treatment
        assert result.flag_metadata["config"] == "{'prop':'val'}"
        assert result.variant == "treatment"

    # *** Integer eval tests ***
    def test_int_none_empty(self):
        # if a treatment is null empty it should return the default treatment
        self.reset_client()
        default_treatment = 10

        self.mock_client_return(None)
        result = self.provider.resolve_integer_details(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

        self.mock_client_return("")
        result = self.provider.resolve_integer_details(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    def test_int_control(self):
        # "control" treatment should eval to default treatment
        self.reset_client()
        self.mock_client_return("control")
        default_treatment = 10
        result = self.provider.resolve_integer_details(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    def test_int_regular(self):
        # a parsable int string treatment should eval to that integer
        self.reset_client()

        self.mock_client_return("50")
        result = self.provider.resolve_integer_details(self.flag_name, 1, self.eval_context)
        assert result.value == 50
        assert isinstance(result.value, int)
        assert result.flag_metadata["config"] == "{'prop':'val'}"
        assert result.variant == "50"

    def test_int_error(self):
        # an un-parsable int treatment should throw an error
        self.reset_client()
        self.mock_client_return("notAnInt")
        try:
            self.provider.resolve_integer_details(self.flag_name, 100, self.eval_context)
            fail("Should have thrown an exception casting string to num")
        except OpenFeatureError as e:
            assert e.error_code == ErrorCode.PARSE_ERROR
        except Exception:
            fail("Unexpected exception occurred")

        self.mock_client_return("50.5")
        try:
            self.provider.resolve_integer_details(self.flag_name, 100, self.eval_context)
            fail("Should have thrown an exception casting string to int")
        except OpenFeatureError as e:
            assert e.error_code == ErrorCode.PARSE_ERROR
        except Exception:
            fail("Unexpected exception occurred")

    # *** Float eval tests ***
    def test_float_none_empty(self):
        # if a treatment is null empty it should return the default treatment
        self.reset_client()
        default_treatment = 10.5

        self.mock_client_return(None)
        result = self.provider.resolve_float_details(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

        self.mock_client_return("")
        result = self.provider.resolve_float_details(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    def test_float_control(self):
        # "control" treatment should eval to default treatment
        self.reset_client()
        self.mock_client_return("control")
        default_treatment = 10.5
        result = self.provider.resolve_float_details(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    def test_float_regular(self):
        # a parsable float string treatment should eval to that float
        self.reset_client()
        self.mock_client_return("50.5")
        result = self.provider.resolve_float_details(self.flag_name, 1.5, self.eval_context)
        assert result.value == 50.5
        assert result.flag_metadata["config"] == "{'prop':'val'}"
        assert result.variant == "50.5"

        # it should also be able to handle regular ints
        self.mock_client_return("50")
        result = self.provider.resolve_float_details(self.flag_name, 1.5, self.eval_context)
        assert result.value == 50.0
        assert isinstance(result.value, float)

    def test_float_error(self):
        # an un-parsable float treatment should throw an error
        self.reset_client()
        self.mock_client_return("notAFloat")
        try:
            self.provider.resolve_float_details(self.flag_name, 100.5, self.eval_context)
            fail("Should have thrown an exception casting string to float")
        except OpenFeatureError as e:
            assert e.error_code == ErrorCode.PARSE_ERROR
        except Exception:
            fail("Unexpected exception occurred")

    # *** Object eval tests ***
    def test_obj_none_empty(self):
        # if a treatment is null empty it should return the default treatment
        self.reset_client()
        default_treatment = {"foo": "bar"}

        self.mock_client_return(None)
        result = self.provider.resolve_object_details(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

        self.mock_client_return("")
        result = self.provider.resolve_object_details(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    def test_obj_control(self):
        # "control" treatment should eval to default treatment
        self.reset_client()
        self.mock_client_return("control")
        default_treatment = {"foo": "bar"}
        result = self.provider.resolve_object_details(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    def test_obj_regular(self):
        # an object treatment should eval to that object
        self.reset_client()
        self.mock_client_return('{"foo": "bar"}')
        result = self.provider.resolve_object_details(self.flag_name, {"blah": "blaah"}, self.eval_context)
        assert result.value == {"foo": "bar"}
        assert result.flag_metadata["config"] == "{'prop':'val'}"
        assert result.variant == '{"foo": "bar"}'

    def test_obj_complex(self):
        self.reset_client()
        self.mock_client_return('{"string": "blah", "int": 10, "bool": true, "struct": {"foo": "bar"}, "list": [1, 2]}')
        result = self.provider.resolve_object_details(self.flag_name, {"blah": "blaah"}, self.eval_context)
        assert result.value == {"string": "blah", "int": 10, "bool": True, "struct": {"foo": "bar"}, "list": [1, 2]}

    def test_obj_error(self):
        # a treatment that can not be converted to an object should throw an error
        self.reset_client()
        self.mock_client_return("not an object")
        try:
            self.provider.resolve_object_details(self.flag_name, {"foo": "bar"}, self.eval_context)
            fail("Should have thrown an exception casting string to an object")
        except OpenFeatureError as e:
            assert e.error_code == ErrorCode.PARSE_ERROR
        except Exception:
            fail("Unexpected exception occurred")
            
    def test_sdk_not_ready(self):
        provider = SplitProvider({"ReadyBlockTime": 0.1,"SdkKey": "api"})
        details = provider.resolve_boolean_details(self.flag_name, False, self.eval_context)
        assert details.error_code == ErrorCode.PROVIDER_NOT_READY
        assert details.value == False

class TestProviderAsync(object):
    eval_context = EvaluationContext("someKey")
    flag_name = "flagName"

    async def reset_client(self):
        self.client = MagicMock()
        self._factory = self.client._factory
        
        async def block_until_ready(x):
            pass
        self._factory.block_until_ready = block_until_ready
        
        self.provider = SplitProviderAsync({"SplitClient": self.client})
        await self.provider.create()

    def mock_client_return(self, val):
        async def get_treatment_with_config(*_):
            return (val, "{'prop':'val'}")
        self.client.get_treatment_with_config = get_treatment_with_config

    # *** Boolean eval tests ***
    @pytest.mark.asyncio
    async def test_boolean_none_empty(self):
        # if a treatment is None or empty it should return the default treatment
        await self.reset_client()

        self.mock_client_return(None)
        result = await self.provider.resolve_boolean_details_async(self.flag_name, True, self.eval_context)
        assert result.value
        result = await self.provider.resolve_boolean_details_async(self.flag_name, False, self.eval_context)
        assert not result.value

    @pytest.mark.asyncio
    async def test_boolean_control(self):
        # if a treatment is "control" it should return the default treatment
        await self.reset_client()
        self.mock_client_return("control")
        result = await self.provider.resolve_boolean_details_async(self.flag_name, False, self.eval_context)
        assert not result.value
        result = await self.provider.resolve_boolean_details_async(self.flag_name, True, self.eval_context)
        assert result.value

    @pytest.mark.asyncio
    async def test_boolean_true(self):
        # treatment of "true" should eval to True boolean
        await self.reset_client()
        self.mock_client_return("true")
        details = await self.provider.resolve_boolean_details_async(self.flag_name, False, self.eval_context)
        assert details.value
        assert details.flag_metadata["config"] == "{'prop':'val'}"
        assert details.variant == "true"

    @pytest.mark.asyncio
    async def test_boolean_on(self):
        # treatment of "on" should eval to True boolean
        await self.reset_client()
        self.mock_client_return("on")
        details = await self.provider.resolve_boolean_details_async(self.flag_name, False, self.eval_context)
        assert details.value
        assert details.flag_metadata["config"] == "{'prop':'val'}"
        assert details.variant == "on"

    @pytest.mark.asyncio
    async def test_boolean_false(self):
        # treatment of "true" should eval to True boolean
        await self.reset_client()
        self.mock_client_return("false")
        details = await self.provider.resolve_boolean_details_async(self.flag_name, False, self.eval_context)
        assert not details.value
        assert details.flag_metadata["config"] == "{'prop':'val'}"
        assert details.variant == "false"

    @pytest.mark.asyncio
    async def test_boolean_off(self):
        # treatment of "on" should eval to True boolean
        await self.reset_client()
        self.mock_client_return("off")
        details = await self.provider.resolve_boolean_details_async(self.flag_name, False, self.eval_context)
        assert not details.value
        assert details.flag_metadata["config"] == "{'prop':'val'}"
        assert details.variant == "off"

    @pytest.mark.asyncio
    async def test_boolean_error(self):
        # any other random string other than on,off,true,false,control should throw an error
        await self.reset_client()
        self.mock_client_return("a random string")
        try:
            await self.provider.resolve_boolean_details_async(self.flag_name, False, self.eval_context)
            fail("Should have thrown an error casting string to boolean")
        except OpenFeatureError as e:
            assert e.error_code == ErrorCode.PARSE_ERROR
        except Exception:
            fail("Unexpected exception occurred")

    # *** String eval tests ***
    @pytest.mark.asyncio
    async def test_string_none_empty(self):
        # if a treatment is None or empty it should return the default treatment
        await self.reset_client()
        default_treatment = "defaultTreatment"

        self.mock_client_return(None)
        result = await self.provider.resolve_string_details_async(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

        self.mock_client_return("")
        result = await self.provider.resolve_string_details_async(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    @pytest.mark.asyncio
    async def test_string_control(self):
        # "control" treatment should eval to default treatment
        await self.reset_client()
        self.mock_client_return("control")
        default_treatment = "defaultTreatment"
        result = await self.provider.resolve_string_details_async(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    @pytest.mark.asyncio
    async def test_string_regular(self):
        # a string treatment should eval to itself
        await self.reset_client()
        treatment = "treatment"
        self.mock_client_return(treatment)
        result = await self.provider.resolve_string_details_async(self.flag_name, "someDefaultTreatment", self.eval_context)
        assert result.value == treatment
        assert result.flag_metadata["config"] == "{'prop':'val'}"
        assert result.variant == "treatment"

    # *** Integer eval tests ***
    @pytest.mark.asyncio
    async def test_int_none_empty(self):
        # if a treatment is null empty it should return the default treatment
        await self.reset_client()
        default_treatment = 10

        self.mock_client_return(None)
        result = await self.provider.resolve_integer_details_async(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

        self.mock_client_return("")
        result = await self.provider.resolve_integer_details_async(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    @pytest.mark.asyncio
    async def test_int_control(self):
        # "control" treatment should eval to default treatment
        await self.reset_client()
        self.mock_client_return("control")
        default_treatment = 10
        result = await self.provider.resolve_integer_details_async(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    @pytest.mark.asyncio
    async def test_int_regular(self):
        # a parsable int string treatment should eval to that integer
        await self.reset_client()

        self.mock_client_return("50")
        result = await self.provider.resolve_integer_details_async(self.flag_name, 1, self.eval_context)
        assert result.value == 50
        assert isinstance(result.value, int)
        assert result.flag_metadata["config"] == "{'prop':'val'}"
        assert result.variant == "50"

    @pytest.mark.asyncio
    async def test_int_error(self):
        # an un-parsable int treatment should throw an error
        await self.reset_client()
        self.mock_client_return("notAnInt")
        try:
            await self.provider.resolve_integer_details_async(self.flag_name, 100, self.eval_context)
            fail("Should have thrown an exception casting string to num")
        except OpenFeatureError as e:
            assert e.error_code == ErrorCode.PARSE_ERROR
        except Exception:
            fail("Unexpected exception occurred")

        self.mock_client_return("50.5")
        try:
            await self.provider.resolve_integer_details_async(self.flag_name, 100, self.eval_context)
            fail("Should have thrown an exception casting string to int")
        except OpenFeatureError as e:
            assert e.error_code == ErrorCode.PARSE_ERROR
        except Exception:
            fail("Unexpected exception occurred")

    # *** Float eval tests ***
    @pytest.mark.asyncio
    async def test_float_none_empty(self):
        # if a treatment is null empty it should return the default treatment
        await self.reset_client()
        default_treatment = 10.5

        self.mock_client_return(None)
        result = await self.provider.resolve_float_details_async(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

        self.mock_client_return("")
        result = await self.provider.resolve_float_details_async(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    @pytest.mark.asyncio
    async def test_float_control(self):
        # "control" treatment should eval to default treatment
        await self.reset_client()
        self.mock_client_return("control")
        default_treatment = 10.5
        result = await self.provider.resolve_float_details_async(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    @pytest.mark.asyncio
    async def test_float_regular(self):
        # a parsable float string treatment should eval to that float
        await self.reset_client()
        self.mock_client_return("50.5")
        result = await self.provider.resolve_float_details_async(self.flag_name, 1.5, self.eval_context)
        assert result.value == 50.5
        assert result.flag_metadata["config"] == "{'prop':'val'}"
        assert result.variant == "50.5"

        # it should also be able to handle regular ints
        self.mock_client_return("50")
        result = await self.provider.resolve_float_details_async(self.flag_name, 1.5, self.eval_context)
        assert result.value == 50.0
        assert isinstance(result.value, float)

    @pytest.mark.asyncio
    async def test_float_error(self):
        # an un-parsable float treatment should throw an error
        await self.reset_client()
        self.mock_client_return("notAFloat")
        try:
            await self.provider.resolve_float_details_async(self.flag_name, 100.5, self.eval_context)
            fail("Should have thrown an exception casting string to float")
        except OpenFeatureError as e:
            assert e.error_code == ErrorCode.PARSE_ERROR
        except Exception:
            fail("Unexpected exception occurred")

    # *** Object eval tests ***
    @pytest.mark.asyncio
    async def test_obj_none_empty(self):
        # if a treatment is null empty it should return the default treatment
        await self.reset_client()
        default_treatment = {"foo": "bar"}

        self.mock_client_return(None)
        result = await self.provider.resolve_object_details_async(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

        self.mock_client_return("")
        result = await self.provider.resolve_object_details_async(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    @pytest.mark.asyncio
    async def test_obj_control(self):
        # "control" treatment should eval to default treatment
        await self.reset_client()
        self.mock_client_return("control")
        default_treatment = {"foo": "bar"}
        result = await self.provider.resolve_object_details_async(self.flag_name, default_treatment, self.eval_context)
        assert result.value == default_treatment

    @pytest.mark.asyncio
    async def test_obj_regular(self):
        # an object treatment should eval to that object
        await self.reset_client()
        self.mock_client_return('{"foo": "bar"}')
        result = await self.provider.resolve_object_details_async(self.flag_name, {"blah": "blaah"}, self.eval_context)
        assert result.value == {"foo": "bar"}
        assert result.flag_metadata["config"] == "{'prop':'val'}"
        assert result.variant == '{"foo": "bar"}'

    @pytest.mark.asyncio
    async def test_obj_complex(self):
        await self.reset_client()
        self.mock_client_return('{"string": "blah", "int": 10, "bool": true, "struct": {"foo": "bar"}, "list": [1, 2]}')
        result = await self.provider.resolve_object_details_async(self.flag_name, {"blah": "blaah"}, self.eval_context)
        assert result.value == {"string": "blah", "int": 10, "bool": True, "struct": {"foo": "bar"}, "list": [1, 2]}

    @pytest.mark.asyncio
    async def test_obj_error(self):
        # a treatment that can not be converted to an object should throw an error
        await self.reset_client()
        self.mock_client_return("not an object")
        try:
            await self.provider.resolve_object_details_async(self.flag_name, {"foo": "bar"}, self.eval_context)
            fail("Should have thrown an exception casting string to an object")
        except OpenFeatureError as e:
            assert e.error_code == ErrorCode.PARSE_ERROR
        except Exception:
            fail("Unexpected exception occurred")
            
    @pytest.mark.asyncio
    async def test_sdk_not_ready(self):
        provider = SplitProviderAsync({"ReadyBlockTime": 0.1,"SdkKey": "api"})
        await provider.create()
        details = await provider.resolve_boolean_details_async(self.flag_name, False, self.eval_context)
        assert details.error_code == ErrorCode.PROVIDER_NOT_READY
        assert details.value == False