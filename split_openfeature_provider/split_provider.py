import typing
import logging
import json

from openfeature.hook import Hook
from openfeature.evaluation_context import EvaluationContext
from openfeature.exception import ErrorCode, GeneralError, ParseError, OpenFeatureError, TargetingKeyMissingError
from openfeature.flag_evaluation import Reason, FlagResolutionDetails
from openfeature.provider import AbstractProvider, Metadata
from openfeature.event import ProviderEventDetails
from split_openfeature_provider.split_client_wrapper import SplitClientWrapper, SPLIT_EVENT_BUR_TIMEOUT

_LOGGER = logging.getLogger(__name__)

try:
    from splitio.models.events import SdkEvent
except ImportError:
    SdkEvent = None  # type: ignore


def _flags_changed_from_sdk_update(event_metadata):
    """
    Extract list of updated flag/split names from Split SDK_UPDATE event metadata.
    OpenFeature expects flags_changed: list[str] for PROVIDER_CONFIGURATION_CHANGED.
    Handles: dict with "names", object with .metadata, or object with get_names() (Split EventsMetadata).
    """
    if event_metadata is None:
        return None
    if hasattr(event_metadata, "metadata") and getattr(event_metadata, "metadata", None) is not None:
        event_metadata = getattr(event_metadata, "metadata")
    if isinstance(event_metadata, dict):
        val = event_metadata.get("names")
        if isinstance(val, list):
            return [str(x) for x in val if x is not None]
        return None
    if hasattr(event_metadata, "get_names"):
        names = event_metadata.get_names()
        if names is not None:
            return [str(x) for x in names if x is not None]
    return None


def _metadata_from_split(split_event, event_metadata):
    """Build OpenFeature event metadata dict from Split event (and optional Split metadata)."""
    meta = {"split_event": getattr(split_event, "value", str(split_event))}
    if event_metadata is not None and isinstance(event_metadata, dict):
        for k, v in event_metadata.items():
            if isinstance(v, (bool, str, int, float)):
                meta["split_%s" % k] = v
    # Split may pass an object with get_type/get_names (e.g. EventsMetadata)
    if event_metadata is not None and hasattr(event_metadata, "get_type"):
        t = event_metadata.get_type()
        meta["split_type"] = getattr(t, "value", str(t))
    if event_metadata is not None and hasattr(event_metadata, "get_names"):
        names = event_metadata.get_names()
        meta["split_names"] = list(names) if names is not None else []
    return meta


class SplitProviderBase(AbstractProvider):

    def get_metadata(self) -> Metadata:
        return Metadata("Split")

    def attach(self, on_emit):
        super().attach(on_emit)
        self._split_client_wrapper.set_event_receiver(self)
        self._split_client_wrapper.register_for_split_events()

    def detach(self):
        self._split_client_wrapper.unregister_for_split_events()
        super().detach()

    def _on_split_event(self, split_event, event_metadata):
        """Map Split SDK events to OpenFeature provider events with OpenFeature-friendly details."""
        _LOGGER.debug("SplitProvider: _on_split_event received %s", split_event)
        if split_event == SPLIT_EVENT_BUR_TIMEOUT:
            self.emit_provider_error(ProviderEventDetails(
                message="Block until ready timed out",
                error_code=ErrorCode.PROVIDER_NOT_READY,
                metadata=_metadata_from_split(split_event, event_metadata),
            ))
            return
        if SdkEvent is None:
            return
        if split_event == SdkEvent.SDK_READY:
            self.emit_provider_ready(ProviderEventDetails(
                metadata=_metadata_from_split(split_event, event_metadata),
            ))
        elif split_event == SdkEvent.SDK_UPDATE:
            flags_changed = _flags_changed_from_sdk_update(event_metadata)
            details = ProviderEventDetails(
                flags_changed=flags_changed,
                metadata=_metadata_from_split(split_event, event_metadata),
            )
            _LOGGER.info("SplitProvider: emitting PROVIDER_CONFIGURATION_CHANGED flags_changed=%s", flags_changed)
            self.emit_provider_configuration_changed(details)

    async def _on_split_event_async(self, split_event, event_metadata):
        """Async version for asyncio path; same logic as _on_split_event (emit_* are sync)."""
        _LOGGER.debug("SplitProvider: _on_split_event_async received %s", split_event)
        if split_event == SPLIT_EVENT_BUR_TIMEOUT:
            self.emit_provider_error(ProviderEventDetails(
                message="Block until ready timed out",
                error_code=ErrorCode.PROVIDER_NOT_READY,
                metadata=_metadata_from_split(split_event, event_metadata),
            ))
            return
        if SdkEvent is None:
            return
        if split_event == SdkEvent.SDK_READY:
            self.emit_provider_ready(ProviderEventDetails(
                metadata=_metadata_from_split(split_event, event_metadata),
            ))
        elif split_event == SdkEvent.SDK_UPDATE:
            flags_changed = _flags_changed_from_sdk_update(event_metadata)
            details = ProviderEventDetails(
                flags_changed=flags_changed,
                metadata=_metadata_from_split(split_event, event_metadata),
            )
            _LOGGER.info("SplitProvider: emitting PROVIDER_CONFIGURATION_CHANGED flags_changed=%s", flags_changed)
            self.emit_provider_configuration_changed(details)

    def get_provider_hooks(self) -> typing.List[Hook]:
        return []

    def _evaluate_treatment(self, key: str, evaluation_context: EvaluationContext, default_value):
        if evaluation_context is None:
            raise GeneralError("Evaluation Context must be provided for the Split Provider")

        if not self._split_client_wrapper.is_sdk_ready():
            return SplitProvider.construct_flag_resolution(default_value, None, None, Reason.ERROR,
                                                               ErrorCode.PROVIDER_NOT_READY)

        targeting_key = evaluation_context.targeting_key
        if not targeting_key:
            raise TargetingKeyMissingError("Missing targeting key")

        attributes = SplitProvider.transform_context(evaluation_context)
        evaluated = self._split_client_wrapper.split_client.get_treatment_with_config(targeting_key, key, attributes)
        return self._process_treatment(evaluated, default_value)

    def _process_treatment(self, evaluated, default_value):
        try:
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

    def resolve_boolean_details(self, flag_key: str, default_value: bool,
                                evaluation_context: EvaluationContext = EvaluationContext()):
        pass

    def resolve_string_details(self, flag_key: str, default_value: str,
                               evaluation_context: EvaluationContext = EvaluationContext()):
        pass

    def resolve_integer_details(self, flag_key: str, default_value: int,
                                evaluation_context: EvaluationContext = EvaluationContext()):
        pass

    def resolve_float_details(self, flag_key: str, default_value: float,
                              evaluation_context: EvaluationContext = EvaluationContext()):
        pass

    def resolve_object_details(self, flag_key: str, default_value: dict,
                               evaluation_context: EvaluationContext = EvaluationContext()):
        pass

    async def resolve_boolean_details_async(self, flag_key: str, default_value: bool,
                                evaluation_context: EvaluationContext = EvaluationContext()):
        pass

    async def resolve_string_details_async(self, flag_key: str, default_value: str,
                               evaluation_context: EvaluationContext = EvaluationContext()):
        pass
    async def resolve_integer_details_async(self, flag_key: str, default_value: int,
                                evaluation_context: EvaluationContext = EvaluationContext()):
        pass

    async def resolve_float_details_async(self, flag_key: str, default_value: float,
                              evaluation_context: EvaluationContext = EvaluationContext()):
        pass

    async def resolve_object_details_async(self, flag_key: str, default_value: dict,
                               evaluation_context: EvaluationContext = EvaluationContext()):
        pass

class SplitProvider(SplitProviderBase):
    def __init__(self, initial_context):
        self._split_client_wrapper = SplitClientWrapper(initial_context)

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

class SplitProviderAsync(SplitProviderBase):
    def __init__(self, initial_context):
        if isinstance(initial_context, dict):
            initial_context["ThreadingMode"] = "asyncio"
        self._split_client_wrapper = SplitClientWrapper(initial_context)

    async def create(self):
        await self._split_client_wrapper.create()

    async def resolve_boolean_details_async(self, flag_key: str, default_value: bool,
                                evaluation_context: EvaluationContext = EvaluationContext()):
        return await self._evaluate_treatment_async(flag_key, evaluation_context, default_value)

    async def resolve_string_details_async(self, flag_key: str, default_value: str,
                               evaluation_context: EvaluationContext = EvaluationContext()):
        return await self._evaluate_treatment_async(flag_key, evaluation_context, default_value)

    async def resolve_integer_details_async(self, flag_key: str, default_value: int,
                                evaluation_context: EvaluationContext = EvaluationContext()):
        return await self._evaluate_treatment_async(flag_key, evaluation_context, default_value)

    async def resolve_float_details_async(self, flag_key: str, default_value: float,
                              evaluation_context: EvaluationContext = EvaluationContext()):
        return await self._evaluate_treatment_async(flag_key, evaluation_context, default_value)

    async def resolve_object_details_async(self, flag_key: str, default_value: dict,
                               evaluation_context: EvaluationContext = EvaluationContext()):
        return await self._evaluate_treatment_async(flag_key, evaluation_context, default_value)

    async def _evaluate_treatment_async(self, key: str, evaluation_context: EvaluationContext, default_value):
        if evaluation_context is None:
            raise GeneralError("Evaluation Context must be provided for the Split Provider")

        if not await self._split_client_wrapper.is_sdk_ready_async():
            return SplitProvider.construct_flag_resolution(default_value, None, None, Reason.ERROR,
                                                               ErrorCode.PROVIDER_NOT_READY)

        targeting_key = evaluation_context.targeting_key
        if not targeting_key:
            raise TargetingKeyMissingError("Missing targeting key")

        attributes = SplitProvider.transform_context(evaluation_context)
        evaluated = await self._split_client_wrapper.split_client.get_treatment_with_config(targeting_key, key, attributes)
        return self._process_treatment(evaluated, default_value)
