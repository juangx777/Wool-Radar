from __future__ import annotations
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class WatchConfig:
    origin: str
    destination: str
    date_mode: str  # "single" or "range"
    start_date: str
    end_date: Optional[str]
    sources: list[str]
    cabin: str  # "Y","W","J","F"
    filters: Dict[str, Any]
    notification: Dict[str, Any]

@dataclass(frozen=True)
class Settings:
    api_key_present: bool
    api_key: str 
    watch_path: Path
    state_path: Path
    watch: WatchConfig
    state: Dict[str, Any]

def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing config file: {path}\n"
            f"Create it with:\n"
            f"  cp config/watch.example.yaml config/watch.yaml"
        )
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML structure in {path}. Expected a mapping/object at top level.")
    return data

def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        # For MVP: auto-create empty state if missing
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        return {}
    txt = path.read_text(encoding="utf-8").strip()
    if not txt:
        return {}
    try:
        data = json.loads(txt)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON in state file: {path}\n"
            f"Fix the JSON or reset it with:\n"
            f"  echo '{{}}' > {path}"
        ) from e
    if not isinstance(data, dict):
        raise ValueError(f"Invalid JSON structure in {path}. Expected an object/dict at top level.")
    return data

def _parse_watch(data: Dict[str, Any], watch_path: Path) -> WatchConfig:
    required = ["origin", "destination", "date_mode", "start_date", "sources", "cabin", "filters", "notification"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Missing required fields in {watch_path}: {missing}")

    date_mode = str(data["date_mode"]).strip()
    if date_mode not in {"single", "range"}:
        raise ValueError(f"date_mode must be 'single' or 'range' in {watch_path}, got: {date_mode}")

    end_date = data.get("end_date")
    if date_mode == "range" and not end_date:
        raise ValueError(f"date_mode is 'range' but end_date is missing in {watch_path}")

    sources = data["sources"]
    if not isinstance(sources, list) or not all(isinstance(x, str) for x in sources) or len(sources) == 0:
        raise ValueError(f"'sources' must be a non-empty list of strings in {watch_path}")

    cabin = str(data["cabin"]).strip().upper()
    if cabin not in {"Y", "W", "J", "F"}:
        raise ValueError(f"'cabin' must be one of Y/W/J/F in {watch_path}, got: {cabin}")

    filters_ = data.get("filters") or {}
    notif_ = data.get("notification") or {}
    if not isinstance(filters_, dict) or not isinstance(notif_, dict):
        raise ValueError(f"'filters' and 'notification' must be objects (YAML mappings) in {watch_path}")

    return WatchConfig(
        origin=str(data["origin"]).strip().upper(),
        destination=str(data["destination"]).strip().upper(),
        date_mode=date_mode,
        start_date=str(data["start_date"]).strip(),
        end_date=str(end_date).strip() if end_date else None,
        sources=[str(x).strip() for x in sources],
        cabin=cabin,
        filters=filters_,
        notification=notif_,
    )

def load_settings(
    watch_rel_path: str = "config/watch.yaml",
    state_rel_path: str = "state/state.json",
) -> Settings:
    # Load env vars from .env if present (no error if absent)
    load_dotenv(dotenv_path=REPO_ROOT / ".env", override=False)

    api_key = (os.getenv("SEATS_AERO_API_KEY") or "").strip()
    api_key_present = bool(api_key)

    watch_path = REPO_ROOT / watch_rel_path
    state_path = REPO_ROOT / state_rel_path

    watch_raw = _read_yaml(watch_path)
    watch = _parse_watch(watch_raw, watch_path)

    state = _read_json(state_path)

    return Settings(
        api_key_present=api_key_present,
        api_key=api_key, 
        watch_path=watch_path,
        state_path=state_path,
        watch=watch,
        state=state,
    )