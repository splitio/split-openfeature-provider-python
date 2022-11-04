from json import JSONDecodeError

from open_feature.provider import provider
from open_feature.evaluation_context.evaluation_context import EvaluationContext
from open_feature.exception import exceptions
from open_feature.flag_evaluation.reason import Reason
from open_feature.flag_evaluation.flag_evaluation_details import FlagEvaluationDetails
from numbers import Number
from splitio import get_factory
from splitio.exceptions import TimeoutException
import json


class SplitProvider(provider.AbstractProvider):

    def __init__(self, api_key="", client=None):
        if api_key == "" and client is None:
            raise Exception("Must provide apiKey or Split Client")
        if api_key != "":
            factory = get_factory(api_key)
            try:
                factory.block_until_ready(1)
            except TimeoutException:
                raise exceptions.GeneralError("Error occurred initializing the client.")
            self.split_client = factory.client()
        else:
            self.split_client = client

    def get_metadata(self) -> provider.Metadata:
        return provider.Metadata("Split")

    def get_boolean_details(
        self,
        flag_key: str,
        default_value: bool,
        evaluation_context: EvaluationContext = EvaluationContext()
    ):
        try:
            evaluated = self.evaluate_treatment(flag_key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_provider_evaluation(flag_key, default_value, evaluated, Reason.DEFAULT, exceptions.ErrorCode.FLAG_NOT_FOUND)
            evaluated_lower = evaluated.lower()
            if evaluated_lower in ["true", "on"]:
                value = True
            elif evaluated_lower in ["false", "off"]:
                value = False
            else:
                raise exceptions.ParseError("Could not convert treatment to boolean")
            return SplitProvider.construct_provider_evaluation(flag_key, value, evaluated)
        except exceptions.OpenFeatureError:
            raise
        except Exception:
            raise exceptions.GeneralError("Error getting boolean evaluation")

    def get_string_details(
        self,
        flag_key: str,
        default_value: str,
        evaluation_context: EvaluationContext = EvaluationContext()
    ):
        try:
            evaluated = self.evaluate_treatment(flag_key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_provider_evaluation(flag_key, default_value, evaluated, Reason.DEFAULT, exceptions.ErrorCode.FLAG_NOT_FOUND)
            return SplitProvider.construct_provider_evaluation(flag_key, evaluated, evaluated)
        except exceptions.OpenFeatureError:
            raise
        except Exception:
            raise exceptions.GeneralError("Error getting boolean evaluation")

    def get_number_details(
        self,
        flag_key: str,
        default_value: Number,
        evaluation_context: EvaluationContext = EvaluationContext()
    ):
        try:
            evaluated = self.evaluate_treatment(flag_key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_provider_evaluation(flag_key, default_value, evaluated, Reason.DEFAULT, exceptions.ErrorCode.FLAG_NOT_FOUND)
            try:
                value = int(evaluated)
            except ValueError:
                value = float(evaluated)
            return SplitProvider.construct_provider_evaluation(flag_key, value, evaluated)
        except ValueError:
            raise exceptions.ParseError("Could not convert treatment to number")
        except exceptions.OpenFeatureError:
            raise
        except Exception:
            raise exceptions.GeneralError("Error getting boolean evaluation")

    def get_object_details(
        self,
        flag_key: str,
        default_value: dict,
        evaluation_context: EvaluationContext = EvaluationContext()
    ):
        try:
            evaluated = self.evaluate_treatment(flag_key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_provider_evaluation(flag_key, default_value, evaluated, Reason.DEFAULT, exceptions.ErrorCode.FLAG_NOT_FOUND)
            value = json.loads(evaluated)
            return SplitProvider.construct_provider_evaluation(flag_key, value, evaluated)
        except JSONDecodeError:
            raise exceptions.ParseError("Could not convert treatment to dict")
        except exceptions.OpenFeatureError:
            raise
        except Exception:
            raise exceptions.GeneralError("Error getting boolean evaluation")

    # *** --- Helpers --- ***

    def evaluate_treatment(
            self,
            key: str,
            evaluation_context: EvaluationContext):
        if evaluation_context is None:
            raise exceptions.GeneralError("Evaluation Context must be provided for the Split Provider")

        targeting_key = evaluation_context.targeting_key
        if not targeting_key:
            raise exceptions.TargetingKeyMissingError("Missing targeting key")

        attributes = SplitProvider.transform_context(evaluation_context)
        return self.split_client.get_treatment(targeting_key, key, attributes)

    @staticmethod
    def transform_context(
            evaluation_context: EvaluationContext
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
            value,
            variant: str,
            reason: Reason = Reason.TARGETING_MATCH,
            error_code: exceptions.ErrorCode = None
    ):
        return FlagEvaluationDetails(
            flag_key=key,
            value=value,
            reason=reason,
            error_code=error_code,
            variant=variant
        )
