"""Field type registry and survey schema validation / answer evaluation."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from uuid import uuid4

from app.core.exceptions import AppError

# Extensible catalog — add entries without schema migrations.
FIELD_TYPES: dict[str, dict[str, Any]] = {
    "text": {"label": "Text", "category": "text", "aliases": []},
    "long_text": {"label": "Long text", "category": "text", "aliases": ["textarea"]},
    "rich_text": {"label": "Rich text", "category": "text", "aliases": []},
    "number": {"label": "Number", "category": "numeric", "aliases": ["integer"]},
    "decimal": {"label": "Decimal", "category": "numeric", "aliases": []},
    "currency": {"label": "Currency", "category": "numeric", "aliases": []},
    "date": {"label": "Date", "category": "datetime", "aliases": []},
    "time": {"label": "Time", "category": "datetime", "aliases": []},
    "datetime": {"label": "Date & time", "category": "datetime", "aliases": []},
    "email": {"label": "Email", "category": "text", "aliases": []},
    "phone": {"label": "Phone", "category": "text", "aliases": []},
    "url": {"label": "URL", "category": "text", "aliases": []},
    "boolean": {"label": "Yes / No", "category": "choice", "aliases": []},
    "checkbox": {"label": "Checkbox", "category": "choice", "aliases": []},
    "radio": {"label": "Radio", "category": "choice", "aliases": []},
    "dropdown": {"label": "Dropdown", "category": "choice", "aliases": ["select"]},
    "multi_select": {"label": "Multi select", "category": "choice", "aliases": []},
    "gps": {"label": "GPS", "category": "media", "aliases": ["geopoint"]},
    "image": {"label": "Image", "category": "media", "aliases": ["photo"]},
    "video": {"label": "Video", "category": "media", "aliases": []},
    "audio": {"label": "Audio", "category": "media", "aliases": []},
    "file": {"label": "File upload", "category": "media", "aliases": ["file_upload"]},
    "signature": {"label": "Signature", "category": "media", "aliases": []},
    "qr_code": {"label": "QR code", "category": "scan", "aliases": ["qr"]},
    "barcode": {"label": "Barcode", "category": "scan", "aliases": []},
    "matrix": {"label": "Matrix", "category": "advanced", "aliases": []},
    "rating": {"label": "Rating", "category": "advanced", "aliases": []},
    "slider": {"label": "Slider", "category": "advanced", "aliases": []},
    "repeat_group": {"label": "Repeat group", "category": "advanced", "aliases": ["repeat"]},
    "section_header": {"label": "Section header", "category": "layout", "aliases": ["header"]},
}

_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _code, _meta in FIELD_TYPES.items():
    _ALIAS_TO_CANONICAL[_code] = _code
    for _alias in _meta.get("aliases") or []:
        _ALIAS_TO_CANONICAL[str(_alias)] = _code

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_RE = re.compile(r"^https?://", re.I)

DEFAULT_SCHEMA_V2: dict[str, Any] = {
    "schema_version": 2,
    "settings": {
        "progress_bar": True,
        "allow_draft": True,
        "auto_save": True,
        "randomize_questions": False,
        "anonymous": False,
    },
    "pages": [
        {
            "id": "page_1",
            "title": "Page 1",
            "sections": [
                {
                    "id": "sec_1",
                    "title": "Questions",
                    "fields": [
                        {
                            "id": "q1",
                            "type": "text",
                            "label": "Full name",
                            "required": True,
                        },
                        {
                            "id": "q2",
                            "type": "dropdown",
                            "label": "Household status",
                            "required": False,
                            "options": [
                                {"value": "stable", "label": "Stable"},
                                {"value": "displaced", "label": "Displaced"},
                                {"value": "host", "label": "Host"},
                            ],
                        },
                        {
                            "id": "q3",
                            "type": "long_text",
                            "label": "Notes",
                            "required": False,
                        },
                    ],
                }
            ],
        }
    ],
}


def normalize_field_type(raw: str) -> str:
    key = (raw or "text").strip().lower()
    if key not in _ALIAS_TO_CANONICAL:
        raise AppError(f"Unsupported field type: {raw}", code="VALIDATION_ERROR", status_code=422)
    return _ALIAS_TO_CANONICAL[key]


def list_field_types() -> list[dict[str, Any]]:
    return [
        {"code": code, "label": meta["label"], "category": meta["category"]}
        for code, meta in FIELD_TYPES.items()
    ]


def _normalize_options(options: Any) -> list[dict[str, str]]:
    if not options:
        return []
    out: list[dict[str, str]] = []
    for opt in options:
        if isinstance(opt, str):
            out.append({"value": opt, "label": opt})
        elif isinstance(opt, dict):
            value = str(opt.get("value") or opt.get("label") or "")
            label = str(opt.get("label") or value)
            if value:
                out.append({"value": value, "label": label})
    return out


def normalize_schema(schema: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Upgrade v1 flat fields into v2 pages/sections; canonicalize types."""
    if not schema:
        return deepcopy(DEFAULT_SCHEMA_V2)

    data = deepcopy(schema)
    if "pages" not in data and "fields" in data:
        fields = []
        for raw in data.get("fields") or []:
            if not isinstance(raw, dict):
                continue
            field = dict(raw)
            field["id"] = str(field.get("id") or f"f_{uuid4().hex[:8]}")
            field["type"] = normalize_field_type(str(field.get("type") or "text"))
            if "options" in field:
                field["options"] = _normalize_options(field.get("options"))
            fields.append(field)
        data = {
            "schema_version": 2,
            "settings": {
                "progress_bar": True,
                "allow_draft": True,
                "auto_save": True,
                "randomize_questions": False,
                "anonymous": False,
                **(data.get("settings") or {}),
            },
            "pages": [
                {
                    "id": "page_1",
                    "title": data.get("title") or "Page 1",
                    "sections": [
                        {
                            "id": "sec_1",
                            "title": "Questions",
                            "fields": fields,
                        }
                    ],
                }
            ],
        }
    else:
        data["schema_version"] = int(data.get("schema_version") or 2)
        data.setdefault(
            "settings",
            {
                "progress_bar": True,
                "allow_draft": True,
                "auto_save": True,
                "randomize_questions": False,
                "anonymous": False,
            },
        )
        for page in data.get("pages") or []:
            page["id"] = str(page.get("id") or f"page_{uuid4().hex[:8]}")
            for section in page.get("sections") or []:
                section["id"] = str(section.get("id") or f"sec_{uuid4().hex[:8]}")
                for field in section.get("fields") or []:
                    field["id"] = str(field.get("id") or f"f_{uuid4().hex[:8]}")
                    field["type"] = normalize_field_type(str(field.get("type") or "text"))
                    if "options" in field:
                        field["options"] = _normalize_options(field.get("options"))
    return data


def iter_fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
    schema = normalize_schema(schema)
    fields: list[dict[str, Any]] = []
    for page in schema.get("pages") or []:
        for section in page.get("sections") or []:
            for field in section.get("fields") or []:
                fields.append(field)
    return fields


def flatten_fields_for_legacy(schema: dict[str, Any]) -> list[dict[str, Any]]:
    return iter_fields(schema)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _eval_condition(answers: dict[str, Any], logic: Optional[dict[str, Any]]) -> bool:
    if not logic:
        return True
    show_if = logic.get("show_if") if isinstance(logic, dict) else None
    if not show_if:
        return True
    field_id = show_if.get("field")
    op = show_if.get("op") or "eq"
    expected = show_if.get("value")
    actual = answers.get(field_id)
    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    if op == "in":
        return actual in (expected or [])
    if op == "not_in":
        return actual not in (expected or [])
    if op == "truthy":
        return bool(actual)
    if op == "falsy":
        return not bool(actual)
    return True


def _coerce_and_validate_value(field: dict[str, Any], value: Any) -> Any:
    ftype = normalize_field_type(str(field.get("type") or "text"))
    if ftype in {"section_header"}:
        return None
    if _is_empty(value):
        return None

    validation = field.get("validation") or {}

    if ftype in {"text", "long_text", "rich_text", "phone", "qr_code", "barcode", "signature"}:
        text = str(value)
        if validation.get("regex") and not re.search(str(validation["regex"]), text):
            raise AppError(
                f"Invalid value for {field.get('label') or field['id']}",
                code="VALIDATION_ERROR",
                status_code=422,
            )
        if validation.get("min_length") and len(text) < int(validation["min_length"]):
            raise AppError(
                f"{field.get('label') or field['id']} is too short",
                code="VALIDATION_ERROR",
                status_code=422,
            )
        if validation.get("max_length") and len(text) > int(validation["max_length"]):
            raise AppError(
                f"{field.get('label') or field['id']} is too long",
                code="VALIDATION_ERROR",
                status_code=422,
            )
        return text

    if ftype == "email":
        text = str(value).strip()
        if not EMAIL_RE.match(text):
            raise AppError("Invalid email", code="VALIDATION_ERROR", status_code=422)
        return text

    if ftype == "url":
        text = str(value).strip()
        if not URL_RE.match(text):
            raise AppError("Invalid URL", code="VALIDATION_ERROR", status_code=422)
        return text

    if ftype in {"number", "rating", "slider"}:
        try:
            num = int(value) if ftype == "number" else float(value)
        except (TypeError, ValueError) as exc:
            raise AppError(
                f"{field.get('label') or field['id']} must be a number",
                code="VALIDATION_ERROR",
                status_code=422,
            ) from exc
        if validation.get("min") is not None and num < float(validation["min"]):
            raise AppError(
                f"{field.get('label') or field['id']} below minimum",
                code="VALIDATION_ERROR",
                status_code=422,
            )
        if validation.get("max") is not None and num > float(validation["max"]):
            raise AppError(
                f"{field.get('label') or field['id']} above maximum",
                code="VALIDATION_ERROR",
                status_code=422,
            )
        return int(num) if ftype == "number" else num

    if ftype in {"decimal", "currency"}:
        try:
            dec = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise AppError(
                f"{field.get('label') or field['id']} must be a decimal",
                code="VALIDATION_ERROR",
                status_code=422,
            ) from exc
        return str(dec)

    if ftype == "date":
        try:
            return date.fromisoformat(str(value)[:10]).isoformat()
        except ValueError as exc:
            raise AppError("Invalid date", code="VALIDATION_ERROR", status_code=422) from exc

    if ftype == "time":
        try:
            return time.fromisoformat(str(value)).isoformat()
        except ValueError as exc:
            raise AppError("Invalid time", code="VALIDATION_ERROR", status_code=422) from exc

    if ftype == "datetime":
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
        except ValueError as exc:
            raise AppError("Invalid datetime", code="VALIDATION_ERROR", status_code=422) from exc

    if ftype in {"boolean", "checkbox"}:
        if isinstance(value, bool):
            return value
        if str(value).lower() in {"1", "true", "yes", "on"}:
            return True
        if str(value).lower() in {"0", "false", "no", "off"}:
            return False
        raise AppError("Invalid boolean", code="VALIDATION_ERROR", status_code=422)

    if ftype in {"radio", "dropdown"}:
        text = str(value)
        options = {o["value"] for o in _normalize_options(field.get("options"))}
        if options and text not in options:
            raise AppError(
                f"Invalid option for {field.get('label') or field['id']}",
                code="VALIDATION_ERROR",
                status_code=422,
            )
        return text

    if ftype == "multi_select":
        if not isinstance(value, list):
            raise AppError("Multi select expects a list", code="VALIDATION_ERROR", status_code=422)
        options = {o["value"] for o in _normalize_options(field.get("options"))}
        cleaned = [str(v) for v in value]
        if options and any(v not in options for v in cleaned):
            raise AppError("Invalid multi-select option", code="VALIDATION_ERROR", status_code=422)
        return cleaned

    if ftype == "gps":
        if isinstance(value, dict) and "lat" in value and "lng" in value:
            return {
                "lat": float(value["lat"]),
                "lng": float(value["lng"]),
                "accuracy": value.get("accuracy"),
            }
        raise AppError("GPS expects {lat, lng}", code="VALIDATION_ERROR", status_code=422)

    if ftype in {"image", "video", "audio", "file"}:
        if isinstance(value, dict):
            return value
        return {"uri": str(value)}

    if ftype == "matrix":
        if not isinstance(value, dict):
            raise AppError("Matrix expects an object", code="VALIDATION_ERROR", status_code=422)
        return value

    if ftype == "repeat_group":
        if not isinstance(value, list):
            raise AppError("Repeat group expects a list", code="VALIDATION_ERROR", status_code=422)
        return value

    return value


def apply_calculated_fields(fields: list[dict[str, Any]], answers: dict[str, Any]) -> dict[str, Any]:
    out = dict(answers)
    for field in fields:
        calc = field.get("calculate")
        if not calc:
            continue
        if isinstance(calc, dict) and calc.get("op") == "sum":
            total = 0.0
            for fid in calc.get("fields") or []:
                try:
                    total += float(out.get(fid) or 0)
                except (TypeError, ValueError):
                    continue
            out[field["id"]] = total
    return out


def validate_answers(
    schema: dict[str, Any],
    answers: dict[str, Any],
    *,
    partial: bool = False,
) -> dict[str, Any]:
    """Validate answers against schema. partial=True skips required checks (drafts)."""
    normalized = normalize_schema(schema)
    fields = iter_fields(normalized)
    working = apply_calculated_fields(fields, dict(answers or {}))
    cleaned: dict[str, Any] = {}
    field_ids = {f["id"] for f in fields}

    for field in fields:
        fid = field["id"]
        ftype = normalize_field_type(str(field.get("type") or "text"))
        if ftype == "section_header":
            continue
        if field.get("hidden") and not field.get("calculate"):
            if fid in working:
                cleaned[fid] = working[fid]
            continue
        if not _eval_condition(working, field.get("logic")):
            continue
        value = working.get(fid)
        if field.get("default") is not None and _is_empty(value):
            value = field.get("default")
        if field.get("required") and not partial and _is_empty(value):
            raise AppError(
                f"Missing required field: {field.get('label') or fid}",
                code="VALIDATION_ERROR",
                status_code=422,
            )
        if field.get("read_only") and not field.get("calculate"):
            value = field.get("default") if _is_empty(value) else field.get("default", value)
            if fid in answers and answers.get(fid) != field.get("default") and field.get("default") is not None:
                value = field.get("default")
        if _is_empty(value):
            continue
        cleaned[fid] = _coerce_and_validate_value(field, value)

    if partial:
        for key, value in working.items():
            if key not in cleaned and key not in field_ids:
                cleaned[key] = value

    return cleaned


def schema_with_flat_fields(schema: dict[str, Any]) -> dict[str, Any]:
    """Return normalized schema plus legacy `fields` array for older clients."""
    normalized = normalize_schema(schema)
    normalized["fields"] = flatten_fields_for_legacy(normalized)
    return normalized
