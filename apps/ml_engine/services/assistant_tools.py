"""Reviewed local read tools. Document/model text cannot register or execute tools."""
from copy import deepcopy
from dataclasses import dataclass
import json
import logging
from math import isfinite
import re
import time

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .canonical_evidence import KINDS, DOCUMENT_LIMIT
from .persistent_memory import _owner

logger = logging.getLogger(__name__)
TIMEOUT_SECONDS = 5
MAX_RESULT_BYTES = 128 * 1024
MAX_ID = 2**63 - 1
SOURCE_URL = (r'^/(?:career/|mobility/|ai/financial-records/(?:expense|budget|loan|investment|baseline)/[1-9][0-9]*/|'
              r'documents/(?:loan-closures/[1-9][0-9]*/|statements/[1-9][0-9]*/transactions/[1-9][0-9]*/|'
              r'(?:loans|investments)/[1-9][0-9]*/records/[1-9][0-9]*/))$')


class ToolInputError(ValueError):
    pass


class ToolResultError(ValueError):
    pass


class ToolDeadlineExceeded(TimeoutError):
    pass


class StrictInput(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError('Use only declared tool inputs.')
        for name, value in data.items():
            field = self.fields[name]
            if ((isinstance(field, serializers.IntegerField) and type(value) is not int)
                    or (isinstance(field, (serializers.CharField, serializers.ChoiceField)) and not isinstance(value, str))):
                raise serializers.ValidationError('Use the declared input types.')
        return super().to_internal_value(data)


class SourceSelection(StrictInput):
    id = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    revision = serializers.RegexField(r'\A[a-f0-9]{64}\Z', trim_whitespace=False, max_length=64)


class ToolInputs(StrictInput):
    document_id = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    transaction_id = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    record_id = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    record_type = serializers.ChoiceField(KINDS)
    selected_documents = SourceSelection(many=True, min_length=1, max_length=DOCUMENT_LIMIT)
    selected_records = SourceSelection(many=True, min_length=1, max_length=3)
    source_catalog = serializers.CharField(max_length=4096, trim_whitespace=False)

    def get_fields(self):
        spec = self.context['tool']
        fields = {name: field for name, field in super().get_fields().items() if name in spec.parameters}
        for name, field in fields.items():
            field.required = name in spec.required
        if spec.scope == 'financial_document':
            fields['record_type'].choices = ('expense', 'loan', 'investment')
        return fields


def _schema(field):
    if isinstance(field, serializers.Serializer):
        return _object_schema(field.fields)
    if isinstance(field, serializers.ListSerializer):
        return dict(type='array', minItems=field.min_length, maxItems=field.max_length, items=_schema(field.child))
    if isinstance(field, serializers.IntegerField):
        return dict(type='integer', minimum=field.min_value, maximum=field.max_value)
    if isinstance(field, serializers.ChoiceField):
        return dict(type='string', enum=list(field.choices))
    result = dict(type='string', minLength=1, maxLength=field.max_length)
    if isinstance(field, serializers.RegexField):
        result['pattern'] = r'^[a-f0-9]{64}$'
    return result


def _object_schema(fields):
    return dict(type='object', additionalProperties=False,
                properties={name: _schema(field) for name, field in fields.items()},
                required=[name for name, field in fields.items() if field.required])


OUTPUT_SCHEMA = dict(type='array', maxItems=3, items=dict(type='object', required=['ref', 'classification', 'url', 'data'],
    properties=dict(ref=dict(type='string', minLength=1, maxLength=160),
                    classification=dict(type='string', minLength=1, maxLength=100),
                    url=dict(type='string', maxLength=2048, pattern=SOURCE_URL), data=dict(type='object')),
    additionalProperties=True))


@dataclass(frozen=True)
class Tool:
    name: str
    scope: str
    title: str
    parameters: tuple = ()
    required: tuple = ()

    def describe(self):
        return dict(name=self.name, scope=self.scope, title=self.title,
            input_schema=_object_schema(ToolInputs(context={'tool': self}).fields), output_schema=deepcopy(OUTPUT_SCHEMA),
            owner_scope='authenticated_owner_only; family sharing does not delegate access',
            authentication='active persisted owner from an authenticated session caller',
            authorization='existing owner-scoped domain services and current source revisions',
            required_consent='explicit source selection for this question or owned citation request',
            data_sensitivity='private', network_usage='no provider, model or MCP calls; configured database/storage access only',
            max_result_bytes=MAX_RESULT_BYTES,
            timeout_seconds=TIMEOUT_SECONDS,
            timeout_behavior='reject late results; synchronous database/file reads are not forcibly interrupted',
            cache_policy='fresh source read; no additional tool cache', side_effects='redacted audit log only; no record changes',
            audit_behavior='tool name, outcome and elapsed time; no owner IDs, arguments, results or exception text')


TOOLS = (
    Tool('finance.baseline', 'finance', 'Financial snapshot'),
    Tool('finance.record', 'financial_records', 'Financial record',
         ('record_type', 'record_id', 'selected_documents', 'source_catalog'), ('record_type', 'record_id')),
    Tool('finance.statement', 'bank_statements', 'Reviewed bank transaction', ('transaction_id',), ('transaction_id',)),
    Tool('documents.financial_records', 'financial_document', 'Reviewed document records',
         ('record_type', 'document_id', 'selected_records', 'source_catalog'),
         ('record_type', 'document_id', 'selected_records', 'source_catalog')),
    Tool('documents.loan_closure', 'documents', 'Verified loan closure', ('document_id',), ('document_id',)),
    Tool('travel.preferences', 'travel', 'Saved travel preferences'),
    Tool('career.applications', 'career', 'Recorded Career application progress'),
)


def tool_catalog():
    return [tool.describe() for tool in TOOLS]


def tool_for_scope(scope):
    for tool in TOOLS:
        if tool.scope == scope:
            return tool
    raise ToolInputError('Choose a registered local source tool.')


def _validate_result(result):
    if not isinstance(result, list) or len(result) > 3:
        raise ToolResultError('Local tool result failed validation.')
    for source in result:
        if (not isinstance(source, dict) or not isinstance(source.get('data'), dict)
                or any(not isinstance(source.get(key), str) or not 1 <= len(source[key]) <= limit
                       for key, limit in (('ref', 160), ('classification', 100), ('url', 2048)))
                or not re.fullmatch(SOURCE_URL, source['url'])):
            raise ToolResultError('Local tool result failed validation.')
    try:
        if len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode()) > MAX_RESULT_BYTES:
            raise ValueError()
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ToolResultError('Local tool result exceeds its safe JSON boundary.') from None


def execute_tool(user, name, arguments, *, consent=False, deadline=None):
    tool = next((tool for tool in TOOLS if tool.name == name), None)
    if tool is None:
        raise ToolInputError('Choose a registered local source tool.')
    started = time.monotonic()
    outcome = 'error'
    try:
        if deadline is not None and (type(deadline) not in (int, float) or not isfinite(deadline)):
            raise ToolInputError('Use a finite server-owned deadline.')
        expires = min(started + TIMEOUT_SECONDS, deadline) if deadline is not None else started + TIMEOUT_SECONDS
        _owner(user)
        if (consent is not True or not isinstance(user, get_user_model())
                or not get_user_model().objects.filter(pk=user.pk, created_at=user.created_at, is_active=True).exists()):
            raise PermissionError('This local read requires its active owner and explicit source selection.')
        inputs = ToolInputs(data=arguments, context={'tool': tool})
        if not inputs.is_valid():
            raise ToolInputError('Use valid inputs declared for this local tool.')
        if time.monotonic() >= expires:
            raise ToolDeadlineExceeded('Local source read deadline exceeded.')
        from .hybrid_intelligence import _read_source_context
        result = _read_source_context(user, tool.scope, **inputs.validated_data)
        _validate_result(result)
        if time.monotonic() >= expires:
            raise ToolDeadlineExceeded('Local source read deadline exceeded.')
        outcome = 'ok'
        return result
    finally:
        logger.info('Local read tool: name=%s outcome=%s elapsed_ms=%d', tool.name, outcome,
                    int(max(0, time.monotonic()-started) * 1000))
