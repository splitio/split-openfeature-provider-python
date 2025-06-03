import typing
from json import JSONDecodeError

from openfeature.hook import Hook
from openfeature.evaluation_context import EvaluationContext
from openfeature.exception import ErrorCode, GeneralError, ParseError, OpenFeatureError, TargetingKeyMissingError
from openfeature.flag_evaluation import Reason, FlagResolutionDetails
from openfeature.provider import AbstractProvider, Metadata
from splitio import get_factory
from splitio.exceptions import TimeoutException
import json


class SplitProvider(AbstractProvider):

    def __init__(self, api_key="", client=None):
        if api_key == "" and client is None:
            raise Exception("Must provide apiKey or Split Client")
        if api_key != "":
            factory = get_factory(api_key)
            try:
                factory.block_until_ready(1)
            except TimeoutException:
                raise GeneralError("Error occurred initializing the client.")
            self.split_client = factory.client()
        else:
            self.split_client = client

    def get_metadata(self) -> Metadata:
        return Metadata("Split")

    def get_provider_hooks(self) -> typing.List[Hook]:
        return []

    def resolve_boolean_details(self, flag_key: str, default_value: bool,
                                evaluation_context: EvaluationContext = EvaluationContext()):
        try:
            evaluated = self.evaluate_treatment(flag_key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_flag_resolution(default_value, evaluated, Reason.DEFAULT,
                                                               ErrorCode.FLAG_NOT_FOUND)
            evaluated_lower = evaluated.lower()
            if evaluated_lower in ["true", "on"]:
                value = True
            elif evaluated_lower in ["false", "off"]:
                value = False
            else:
                raise ParseError("Could not convert treatment to boolean")
            return SplitProvider.construct_flag_resolution(value, evaluated)
        except OpenFeatureError:
            raise
        except Exception:
            raise GeneralError("Error getting boolean evaluation")

    def resolve_string_details(self, flag_key: str, default_value: str,
                               evaluation_context: EvaluationContext = EvaluationContext()):
        try:
            evaluated = self.evaluate_treatment(flag_key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_flag_resolution(default_value, evaluated, Reason.DEFAULT,
                                                               ErrorCode.FLAG_NOT_FOUND)
            return SplitProvider.construct_flag_resolution(evaluated, evaluated)
        except OpenFeatureError:
            raise
        except Exception:
            raise GeneralError("Error getting boolean evaluation")

    def resolve_integer_details(self, flag_key: str, default_value: int,
                                evaluation_context: EvaluationContext = EvaluationContext()):
        try:
            evaluated = self.evaluate_treatment(flag_key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_flag_resolution(default_value, evaluated, Reason.DEFAULT,
                                                               ErrorCode.FLAG_NOT_FOUND)
            try:
                value = int(evaluated)
            except ValueError:
                raise ParseError("Could not convert treatment to integer")
            return SplitProvider.construct_flag_resolution(value, evaluated)
        except OpenFeatureError:
            raise
        except Exception:
            raise GeneralError("Error getting boolean evaluation")

    def resolve_float_details(self, flag_key: str, default_value: float,
                              evaluation_context: EvaluationContext = EvaluationContext()):
        try:
            evaluated = self.evaluate_treatment(flag_key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_flag_resolution(default_value, evaluated, Reason.DEFAULT,
                                                               ErrorCode.FLAG_NOT_FOUND)
            try:
                value = float(evaluated)
            except ValueError:
                raise ParseError("Could not convert treatment to float")
            return SplitProvider.construct_flag_resolution(value, evaluated)
        except OpenFeatureError:
            raise
        except Exception:
            raise GeneralError("Error getting boolean evaluation")

    def resolve_object_details(self, flag_key: str, default_value: dict,
                               evaluation_context: EvaluationContext = EvaluationContext()):
        try:
            evaluated = self.evaluate_treatment(flag_key, evaluation_context)
            if SplitProvider.no_treatment(evaluated):
                return SplitProvider.construct_flag_resolution(default_value, evaluated, Reason.DEFAULT,
                                                               ErrorCode.FLAG_NOT_FOUND)
            value = json.loads(evaluated)
            return SplitProvider.construct_flag_resolution(value, evaluated)
        except JSONDecodeError:
            raise ParseError("Could not convert treatment to dict")
        except OpenFeatureError:
            raise
        except Exception:
            raise GeneralError("Error getting boolean evaluation")

    # *** --- Helpers --- ***

    def evaluate_treatment(self, key: str, evaluation_context: EvaluationContext):
        if evaluation_context is None:
            raise GeneralError("Evaluation Context must be provided for the Split Provider")

        targeting_key = evaluation_context.targeting_key
        if not targeting_key:
            raise TargetingKeyMissingError("Missing targeting key")

        attributes = SplitProvider.transform_context(evaluation_context)
        return self.split_client.get_treatment(targeting_key, key, attributes)

    @staticmethod
    def transform_context(evaluation_context: EvaluationContext):
        return evaluation_context.attributes

    @staticmethod
    def no_treatment(treatment: str):
        return not treatment or treatment == "control"

    @staticmethod
    def construct_flag_resolution(value, variant: str, reason: Reason = Reason.TARGETING_MATCH,
                                  error_code: ErrorCode = None):
        return FlagResolutionDetails(value=value, error_code=error_code, reason=reason, variant=variant)
