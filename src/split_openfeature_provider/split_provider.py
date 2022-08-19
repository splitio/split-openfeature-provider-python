from open_feature import provider
from open_feature import Reason
from open_feature import TypeMismatchError
from open_feature import OpenFeatureError
from open_feature import GeneralError
from open_feature import FlagEvaluationDetails
from numbers import Number
from splitio import get_factory
from splitio.exceptions import TimeoutException
import typing


class SplitProvider(provider):

    def __init__(self, api_key: str):
        factory = get_factory(api_key)
        try:
            factory.block_until_ready(5)
        except TimeoutException:
            raise Exception("Could not initialize Split Python SDK")
        self.split_client = factory.client()

    def get_name(self) -> str:
        return "Split"

    def get_boolean_details(
        self,
        key: str,
        default_value: bool,
        evaluation_context: typing.Any = None,
        flag_evaluation_options: typing.Any = None,
    ):
        try:
            evaluated = self.evaluate_treatment(key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_provider_evaluation(key, default_value, evaluated, Reason.DEFAULT, "Flag not found")
            evaluated_lower = evaluated.lower()
            if evaluated_lower in ["true", "on"]:
                value = True
            elif evaluated_lower in ["false", "off"]:
                value = False
            else:
                raise TypeMismatchError("Could not convert treatment to boolean")
            return SplitProvider.construct_provider_evaluation(key, value, evaluated)
        except OpenFeatureError:
            raise
        except Exception:
            raise GeneralError("Error getting boolean evaluation")

    def get_string_details(
        self,
        key: str,
        default_value: str,
        evaluation_context: typing.Any = None,
        flag_evaluation_options: typing.Any = None,
    ):
        try:
            evaluated = self.evaluate_treatment(key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_provider_evaluation(key, default_value, evaluated, Reason.DEFAULT, "Flag not found")
            return SplitProvider.construct_provider_evaluation(key, evaluated, evaluated)
        except OpenFeatureError:
            raise
        except Exception:
            raise GeneralError("Error getting boolean evaluation")

    def get_number_details(
        self,
        key: str,
        default_value: Number,
        evaluation_context: typing.Any = None,
        flag_evaluation_options: typing.Any = None,
    ):
        try:
            evaluated = self.evaluate_treatment(key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_provider_evaluation(key, default_value, evaluated, Reason.DEFAULT, "Flag not found")
            try:
                value = int(evaluated)
            except ValueError:
                value = float(evaluated)
            return SplitProvider.construct_provider_evaluation(key, value, evaluated)
        except ValueError:
            raise TypeMismatchError("Could not convert treatment to number")
        except OpenFeatureError:
            raise
        except Exception:
            raise GeneralError("Error getting boolean evaluation")

    def get_object_details(
        self,
        key: str,
        default_value: dict,
        evaluation_context: typing.Any = None,
        flag_evaluation_options: typing.Any = None,
    ):
        try:
            evaluated = self.evaluate_treatment(key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_provider_evaluation(key, default_value, evaluated, Reason.DEFAULT, "Flag not found")
            # TODO: how do we turn this into an object?
            return SplitProvider.construct_provider_evaluation(key, evaluated, evaluated)
        except OpenFeatureError:
            raise
        except Exception:
            raise GeneralError("Error getting boolean evaluation")

    # *** --- Helpers --- ***

    def evaluate_treatment(
            self,
            key: str,
            evaluation_context: typing.Any):
        if evaluation_context is None:
            raise Exception("Missing Evaluation Context")

        targeting_key = evaluation_context.targeting_key
        if not targeting_key:
            raise Exception("Missing targeting key")

        attributes = SplitProvider.transform_context(evaluation_context)
        return self.split_client.get_treatment(key, targeting_key, attributes)

    @staticmethod
    def transform_context(
            evaluation_context: typing.Any
    ):
        return evaluation_context.attributes

    @staticmethod
    def no_treatment(
            treatment: str
    ):
        return not treatment or treatment == "control"

    @staticmethod
    def construct_provider_evaluation(
            key: str,
            default_value,
            variant: str,
            reason: Reason = Reason.TARGETING_MATCH,
            error_code: str = None
    ):
        return FlagEvaluationDetails(
            key=key,
            value=default_value,
            reason=reason,
            error_code=error_code,
            variant=variant
        )
