from pytest import fail
from mock import MagicMock
from mock import patch
from open_feature.exception import exceptions
from open_feature.evaluation_context.evaluation_context import EvaluationContext
from split_openfeature_provider.split_provider import SplitProvider


class TestProvider(object):

    client = MagicMock()
    provider = SplitProvider(client=client)
    eval_context = EvaluationContext("someKey")

    # commented out until Split SDK bug is fixed
    # def test_fail_with_bad_api_key():
    #     try:
    #         provider = SplitProvider(api_key="someKey")
    #         fail("Should have thrown an exception")
    #     except exceptions.GeneralError as e:
    #         # assert true
    #         assert e.error_message == "Error occurred initializing the client."
    #     except Exception:
    #         # fail
    #         fail("Unexpected exception occurred. Expected a GeneralError.")

    def test_eval_boolean_none_empty(self):
        # if a treatment is null or empty it should return the default treatment
        flag_name = "flagName"

        self.client.get_treatment.return_value = None
        result = self.provider.get_boolean_details(flag_name, True, self.eval_context)
        assert result.value
        result = self.provider.get_boolean_details(flag_name, False, self.eval_context)
        assert not result.value

        self.client.get_treatment.return_value = ""
        result = self.provider.get_boolean_details(flag_name, True, self.eval_context)
        assert result.value
        result = self.provider.get_boolean_details(flag_name, False, self.eval_context)
        assert not result.value

    # TODO: figure out how to mock if certain params are passed in, with different return value otherwise. will need it later





