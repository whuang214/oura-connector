"""Pure source-field selection, unit labels, and duration display."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy

from .models import Collection, Format, JsonObject
from .resources import FIELD_LABELS, get_resource

IDENTITY_FIELDS = (
    "id",
    "day",
    "type",
    "timestamp",
    "timestamp_unix",
    "bedtime_start",
    "bedtime_end",
    "start_datetime",
    "end_datetime",
    "start_day",
    "end_day",
    "start_time",
    "end_time",
)
SLEEP_TYPES = {"long_sleep", "sleep", "late_nap", "rest", "deleted"}


def duration_display(seconds: object) -> str | None:
    if seconds is None:
        return None
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or seconds < 0:
        return None
    hours, remaining = divmod(int(seconds), 3600)
    minutes, secs = divmod(remaining, 60)
    return f"{hours}h {minutes}m" + (f" {secs}s" if secs else "")


def format_record(
    resource: str, record: JsonObject, format: Format, fields: tuple[str, ...] | None = None
) -> JsonObject:
    if format == "source":
        return deepcopy(record)
    selected = set((*IDENTITY_FIELDS, *(fields if fields is not None else get_resource(resource).fields)))
    output: JsonObject = {}
    units: dict[str, str] = {}
    for name, value in record.items():
        if name not in selected:
            continue
        label, unit = FIELD_LABELS.get(name, (name, ""))
        output[label] = deepcopy(value)
        if unit:
            units[label] = unit
        if name == "total_sleep_duration":
            output["total_sleep_display"] = duration_display(value)
    if units:
        output["units"] = units
    omitted = sorted(set(record) - selected)
    if omitted:
        output["omitted_fields"] = omitted
    return output


def format_collection(collection: Collection, format: Format, fields: tuple[str, ...] | None = None) -> Collection:
    output = collection.model_copy(deep=True)
    retained = collection.records
    if collection.resource == "sleep" and format == "compact":
        omitted = Counter(str(row.get("type")) for row in retained if row.get("type") in ("rest", "deleted"))
        retained = [row for row in retained if row.get("type") not in ("rest", "deleted")]
        output.omitted_records = dict(omitted)
        if any(not isinstance(row.get("type"), str) or row["type"] not in SLEEP_TYPES for row in retained):
            output.warnings.append("Unrecognized sleep type retained; no classification was inferred")
    output.records = [format_record(collection.resource, row, format, fields) for row in retained]
    if output.complete:
        output.status = "ok" if output.records else "empty"
    return output
