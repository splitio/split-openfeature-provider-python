from pytest import fail
from mock import MagicMock
from open_feature.exception import exceptions
from open_feature.exception.error_code import ErrorCode
from open_feature.evaluation_context.evaluation_context import EvaluationContext
from split_openfeature import SplitProvider


class TestProvider(object):
    eval_context = EvaluationContext("someKey")
    flag_name = "flagName"

    def reset_client(self):
        self.client = MagicMock()
        self.provider = SplitProvider(client=self.client)

    def mock_client_return(self, val):
        self.client.get_treatment.return_value = val

    # *** Boolean eval tests ***

    def test_boolean_none_empty(self):
        # if a treatment is None or empty it should return the default treatment
        self.reset_client()

        self.mock_client_return(None)
        result = self.provider.resolve_boolean_details(self.flag_name, True, self.eval_context)
        assert result.value
        result = self.provider.resolve_boolean_details(self.flag_name, False, self.eval_context)
        assert not result.value

        self.mock_client_return("")
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
        assert self.provider.resolve_boolean_details(self.flag_name, False, self.eval_context).value

    def test_boolean_on(self):
        # treatment of "on" should eval to True boolean
        self.reset_client()
        self.mock_client_return("on")
        assert self.provider.resolve_boolean_details(self.flag_name, False, self.eval_context).value

    def test_boolean_false(self):
        # treatment of "true" should eval to True boolean
        self.reset_client()
        self.mock_client_return("false")
        assert not self.provider.resolve_boolean_details(self.flag_name, True, self.eval_context).value

    def test_boolean_off(self):
        # treatment of "on" should eval to True boolean
        self.reset_client()
        self.mock_client_return("off")
        assert not self.provider.resolve_boolean_details(self.flag_name, True, self.eval_context).value

    def test_boolean_error(self):
        # any other random string other than on,off,true,false,control should throw an error
        self.reset_client()
        self.mock_client_return("a random string")
        try:
            self.provider.resolve_boolean_details(self.flag_name, False, self.eval_context)
            fail("Should have thrown an error casting string to boolean")
        except exceptions.OpenFeatureError as e:
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

    def test_int_error(self):
        # an un-parsable int treatment should throw an error
        self.reset_client()
        self.mock_client_return("notAnInt")
        try:
            self.provider.resolve_integer_details(self.flag_name, 100, self.eval_context)
            fail("Should have thrown an exception casting string to num")
        except exceptions.OpenFeatureError as e:
            assert e.error_code == ErrorCode.PARSE_ERROR
        except Exception:
            fail("Unexpected exception occurred")

        self.mock_client_return("50.5")
        try:
            self.provider.resolve_integer_details(self.flag_name, 100, self.eval_context)
            fail("Should have thrown an exception casting string to int")
        except exceptions.OpenFeatureError as e:
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
        except exceptions.OpenFeatureError as e:
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
        except exceptions.OpenFeatureError as e:
            assert e.error_code == ErrorCode.PARSE_ERROR
        except Exception:
            fail("Unexpected exception occurred")
