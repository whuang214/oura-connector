"""One registry owns upstream names, filters, compact fields, and units.

Verified against Oura's openapi-1.41.json. Unknown source fields remain available
through source format; compact field overrides select source field names.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

FilterKind = Literal["date", "datetime", "none", "singleton"]


@dataclass(frozen=True)
class Resource:
    name: str
    filters: FilterKind
    fields: tuple[str, ...]
    scopes: tuple[str, ...] = ()
    lookup: bool = True
    day_field: str | None = "day"
    exclusive_end: bool = False


def resource(name: str, fields: str, scopes: str = "", *, filters: FilterKind = "date",
             lookup: bool = True, day_field: str | None = "day") -> Resource:
    return Resource(name, filters, tuple(fields.split()), tuple(scopes.split()), lookup, day_field,
                    name in {"daily_activity", "sleep", "workout", "session"})


RESOURCES = MappingProxyType({r.name: r for r in (
    resource("daily_sleep", "score contributors timestamp", "daily"),
    resource("sleep", "type period bedtime_start bedtime_end total_sleep_duration time_in_bed "
             "deep_sleep_duration rem_sleep_duration light_sleep_duration awake_time latency efficiency "
             "average_hrv average_heart_rate lowest_heart_rate average_breath low_battery_alert", "daily"),
    resource("daily_readiness", "score contributors temperature_deviation temperature_trend_deviation timestamp", "daily"),
    resource("daily_activity", "score steps active_calories total_calories target_calories contributors "
             "high_activity_time medium_activity_time low_activity_time sedentary_time resting_time "
             "non_wear_time equivalent_walking_distance timestamp", "daily"),
    resource("daily_stress", "day_summary stress_high recovery_high"),
    resource("daily_spo2", "spo2_percentage breathing_disturbance_index", "spo2"),
    resource("workout", "activity calories distance intensity label source start_datetime end_datetime", "workout"),
    resource("session", "type mood start_datetime end_datetime", "session"),
    resource("daily_cardiovascular_age", "vascular_age pulse_wave_velocity"),
    resource("vO2_max", "vo2_max timestamp"),
    resource("daily_resilience", "level contributors"),
    resource("sleep_time", "optimal_bedtime recommendation status", "daily"),
    resource("enhanced_tag", "tag_type_code custom_name start_time end_time start_day end_day comment", "tag",
             day_field=None),
    resource("tag", "tags text timestamp", "tag"),
    resource("rest_mode_period", "start_day end_day start_time end_time episodes", day_field=None),
    resource("heartrate", "timestamp timestamp_unix bpm source", "heartrate", filters="datetime",
             lookup=False, day_field=None),
    resource("ring_battery_level", "timestamp timestamp_unix level charging in_charger", filters="datetime",
             lookup=False, day_field=None),
    resource("ring_configuration", "color design firmware_version hardware_type set_up_at size", filters="none",
             day_field=None),
    resource("personal_info", "age weight height biological_sex email", "personal email", filters="singleton",
             lookup=False, day_field=None),
)})

SECTIONS = MappingProxyType({
    "sleep": {"daily": "daily_sleep", "periods": "sleep"},
    "readiness": {"daily": "daily_readiness"},
    "activity": {"daily": "daily_activity"},
    "stress": {"daily": "daily_stress"},
    "spo2": {"daily": "daily_spo2"},
    "workouts": {"records": "workout"},
    "sessions": {"records": "session"},
    "heart_health": {"cardiovascular_age": "daily_cardiovascular_age", "vo2_max": "vO2_max"},
    "resilience": {"daily": "daily_resilience"},
})

# Only formatting/units, never new physiological calculations.
FIELD_LABELS = {
    "total_sleep_duration": ("total_sleep_seconds", "seconds"),
    "time_in_bed": ("time_in_bed_seconds", "seconds"),
    "deep_sleep_duration": ("deep_sleep_seconds", "seconds"),
    "rem_sleep_duration": ("rem_sleep_seconds", "seconds"),
    "light_sleep_duration": ("light_sleep_seconds", "seconds"),
    "awake_time": ("awake_seconds", "seconds"),
    "latency": ("latency_seconds", "seconds"),
    "average_hrv": ("average_hrv_ms", "milliseconds"),
    "average_heart_rate": ("average_heart_rate_bpm", "beats/minute"),
    "lowest_heart_rate": ("lowest_heart_rate_bpm", "beats/minute"),
    "average_breath": ("average_breath_per_minute", "breaths/minute"),
    "bpm": ("bpm", "beats/minute"),
    "efficiency": ("efficiency", "percent"),
    "temperature_deviation": ("temperature_deviation", "degrees Celsius"),
    "temperature_trend_deviation": ("temperature_trend_deviation", "degrees Celsius"),
    "spo2_percentage": ("spo2_percentage", "percent"),
    "stress_high": ("stress_high_seconds", "seconds"),
    "recovery_high": ("recovery_high_seconds", "seconds"),
    "vascular_age": ("vascular_age", "years"),
    "pulse_wave_velocity": ("pulse_wave_velocity", "meters/second"),
    "vo2_max": ("vo2_max", "ml/kg/min"),
    "distance": ("distance", "meters"),
    "equivalent_walking_distance": ("equivalent_walking_distance", "meters"),
    "weight": ("weight", "kg"),
    "height": ("height", "meters"),
    **{name: (name, "kcal") for name in ("calories", "active_calories", "total_calories", "target_calories")},
    **{name: (name.removesuffix("_time") + "_seconds", "seconds") for name in (
        "high_activity_time", "medium_activity_time", "low_activity_time", "sedentary_time",
        "resting_time", "non_wear_time")},
}


def get_resource(name: str) -> Resource:
    if name not in RESOURCES:
        raise ValueError("Unknown resource; use oura_resources to list supported names")
    return RESOURCES[name]
