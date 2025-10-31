import typing
import logging

from openfeature.hook import Hook
from openfeature.evaluation_context import EvaluationContext
from openfeature.exception import ErrorCode, GeneralError, ParseError, OpenFeatureError, TargetingKeyMissingError
from openfeature.flag_evaluation import Reason, FlagResolutionDetails
from openfeature.provider import AbstractProvider, Metadata
from split_openfeature.split_client_wrapper import SplitClientWrapper
import json

_LOGGER = logging.getLogger(__name__)

class SplitProvider(AbstractProvider):

    def __init__(self, initial_context):
        self._split_client_wrapper = SplitClientWrapper(initial_context)

    def get_metadata(self) -> Metadata:
        return Metadata("Split")

    def get_provider_hooks(self) -> typing.List[Hook]:
        return []

    def resolve_boolean_details(self, flag_key: str, default_value: bool,
                                evaluation_context: EvaluationContext = EvaluationContext()):
        return self._evaluate_treatment(flag_key, evaluation_context, default_value)

    def resolve_string_details(self, flag_key: str, default_value: str,
                               evaluation_context: EvaluationContext = EvaluationContext()):
        return self._evaluate_treatment(flag_key, evaluation_context, default_value)

    def resolve_integer_details(self, flag_key: str, default_value: int,
                                evaluation_context: EvaluationContext = EvaluationContext()):
        return self._evaluate_treatment(flag_key, evaluation_context, default_value)

    def resolve_float_details(self, flag_key: str, default_value: float,
                              evaluation_context: EvaluationContext = EvaluationContext()):
        return self._evaluate_treatment(flag_key, evaluation_context, default_value)

    def resolve_object_details(self, flag_key: str, default_value: dict,
                               evaluation_context: EvaluationContext = EvaluationContext()):
        return self._evaluate_treatment(flag_key, evaluation_context, default_value)

    def _evaluate_treatment(self, key: str, evaluation_context: EvaluationContext, default_value):
        if evaluation_context is None:
            raise GeneralError("Evaluation Context must be provided for the Split Provider")

        if not self._split_client_wrapper.is_sdk_ready():
            return SplitProvider.construct_flag_resolution(default_value, None, None, Reason.ERROR,
                                                               ErrorCode.PROVIDER_NOT_READY)
        
        targeting_key = evaluation_context.targeting_key
        if not targeting_key:
            raise TargetingKeyMissingError("Missing targeting key")

        try:
            attributes = SplitProvider.transform_context(evaluation_context)
            evaluated = self._split_client_wrapper.split_client.get_treatment_with_config(targeting_key, key, attributes)
            treatment = None
            config = None
            if evaluated != None:
                treatment = evaluated[0]
                config = evaluated[1]
                
            if SplitProvider.no_treatment(treatment) or treatment == "control":
                return SplitProvider.construct_flag_resolution(default_value, treatment, None, Reason.DEFAULT,
                                                               ErrorCode.FLAG_NOT_FOUND)
            value = treatment
            try: 
                if type(default_value) is int:
                    value = int(treatment)
                elif isinstance(default_value, float):
                    value = float(treatment)
                elif isinstance(default_value, bool):
                    evaluated_lower = treatment.lower()
                    if evaluated_lower in ["true", "on"]:
                        value = True
                    elif evaluated_lower in ["false", "off"]:
                        value = False
                    else:
                        raise ParseError
                elif isinstance(default_value, dict):
                    value = json.loads(treatment)
                    
            except Exception:
                raise ParseError
            
            return SplitProvider.construct_flag_resolution(value, treatment, config)
        
        except ParseError as ex:
            _LOGGER.error("Evaluation Parse error")
            _LOGGER.debug(ex)
            raise ParseError("Could not convert treatment")            

        except OpenFeatureError as ex:
            _LOGGER.error("Evaluation OpenFeature Exception")
            _LOGGER.debug(ex)
            raise
        
        except Exception as ex:
            _LOGGER.error("Evaluation Exception")
            _LOGGER.debug(ex)
            raise GeneralError("Failed to evaluate treatment")

    @staticmethod
    def transform_context(evaluation_context: EvaluationContext):
        return evaluation_context.attributes

    @staticmethod
    def no_treatment(treatment: str):
        return not treatment or treatment == "control"

    @staticmethod
    def construct_flag_resolution(value, variant, config, reason: Reason = Reason.TARGETING_MATCH,
                                  error_code: ErrorCode = None):
        return FlagResolutionDetails(value=value, error_code=error_code, reason=reason, variant=variant, 
                                     flag_metadata={"config": config})
