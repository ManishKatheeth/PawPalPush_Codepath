"""
PawPal+ persistence layer.

Backend selection (checked at import time):
  - If SUPABASE_URL and SUPABASE_KEY are set → Supabase (Postgres)
  - Otherwise → local JSON file (data/pawpal_data.json)

The public API is identical in both cases: save(owner) / load() -> Owner.
"""

import json
import logging
import os
import uuid
from datetime import date
from pathlib import Path

from pawpal_system import Owner, Pet, Task

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "data" / "pawpal_data.json"

_SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
_SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
_USE_SUPABASE = bool(_SUPABASE_URL and _SUPABASE_KEY)

# Lazy-initialised Supabase client
_supabase_client = None


def _get_supabase():
    """Return a cached Supabase client, creating it on first call."""
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(_SUPABASE_URL, _SUPABASE_KEY)
    return _supabase_client


# ---------------------------------------------------------------------------
# Serialisation helpers (shared by both backends)
# ---------------------------------------------------------------------------

def _task_to_dict(task: Task) -> dict:
    return {
        "task_id": task.task_id,
        "description": task.description,
        "time": task.time,
        "frequency": task.frequency,
        "due_date": task.due_date.isoformat(),
        "completed": task.completed,
    }


def _pet_to_dict(pet: Pet) -> dict:
    return {
        "pet_id": pet.pet_id,
        "name": pet.name,
        "species": pet.species,
        "tasks": [_task_to_dict(t) for t in pet.tasks],
    }


def _owner_to_dict(owner: Owner) -> dict:
    return {
        "owner_id": owner.owner_id,
        "name": owner.name,
        "pets": [_pet_to_dict(p) for p in owner.get_pets()],
    }


def _task_from_dict(d: dict) -> Task:
    return Task(
        task_id=d["task_id"],
        description=d["description"],
        time=d["time"],
        frequency=d["frequency"],
        due_date=date.fromisoformat(d["due_date"]),
        completed=d.get("completed", False),
    )


def _pet_from_dict(d: dict) -> Pet:
    pet = Pet(pet_id=d["pet_id"], name=d["name"], species=d["species"])
    for t in d.get("tasks", []):
        pet.add_task(_task_from_dict(t))
    return pet


def _owner_from_dict(d: dict) -> Owner:
    owner = Owner(owner_id=d["owner_id"], name=d["name"])
    for p in d.get("pets", []):
        owner.add_pet(_pet_from_dict(p))
    return owner


# ---------------------------------------------------------------------------
# JSON backend
# ---------------------------------------------------------------------------

def _save_json(owner: Owner) -> None:
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(_owner_to_dict(owner), indent=2))


def _load_json() -> Owner:
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text())
            return _owner_from_dict(data)
        except Exception as exc:
            logger.warning("JSON load failed, returning fresh owner: %s", exc)
    return Owner(owner_id=str(uuid.uuid4()), name="Sarah")


# ---------------------------------------------------------------------------
# Supabase backend
#
# Schema (run once in Supabase SQL editor):
#
#   create table owners (
#     owner_id text primary key,
#     name     text not null
#   );
#
#   create table pets (
#     pet_id   text primary key,
#     owner_id text references owners(owner_id) on delete cascade,
#     name     text not null,
#     species  text not null
#   );
#
#   create table tasks (
#     task_id     text primary key,
#     pet_id      text references pets(pet_id) on delete cascade,
#     description text not null,
#     time        text not null,
#     frequency   text not null,
#     due_date    date not null,
#     completed   boolean not null default false
#   );
# ---------------------------------------------------------------------------

def _save_supabase(owner: Owner) -> None:
    sb = _get_supabase()

    # Upsert owner
    sb.table("owners").upsert({"owner_id": owner.owner_id, "name": owner.name}).execute()

    # Collect current pet IDs in DB for this owner
    existing = sb.table("pets").select("pet_id").eq("owner_id", owner.owner_id).execute()
    db_pet_ids = {r["pet_id"] for r in (existing.data or [])}
    live_pet_ids = {p.pet_id for p in owner.get_pets()}

    # Delete removed pets (cascade deletes their tasks)
    for dead_id in db_pet_ids - live_pet_ids:
        sb.table("pets").delete().eq("pet_id", dead_id).execute()

    for pet in owner.get_pets():
        # Upsert pet
        sb.table("pets").upsert({
            "pet_id": pet.pet_id,
            "owner_id": owner.owner_id,
            "name": pet.name,
            "species": pet.species,
        }).execute()

        # Collect current task IDs in DB for this pet
        existing_tasks = sb.table("tasks").select("task_id").eq("pet_id", pet.pet_id).execute()
        db_task_ids = {r["task_id"] for r in (existing_tasks.data or [])}
        live_task_ids = {t.task_id for t in pet.get_tasks()}

        # Delete removed tasks
        for dead_tid in db_task_ids - live_task_ids:
            sb.table("tasks").delete().eq("task_id", dead_tid).execute()

        # Upsert all current tasks
        for task in pet.get_tasks():
            sb.table("tasks").upsert({
                "task_id": task.task_id,
                "pet_id": pet.pet_id,
                "description": task.description,
                "time": task.time,
                "frequency": task.frequency,
                "due_date": task.due_date.isoformat(),
                "completed": task.completed,
            }).execute()


def _load_supabase() -> Owner:
    sb = _get_supabase()

    # Load first owner in DB (single-user app)
    result = sb.table("owners").select("*").limit(1).execute()
    if not result.data:
        owner = Owner(owner_id=str(uuid.uuid4()), name="Sarah")
        _save_supabase(owner)
        return owner

    row = result.data[0]
    owner = Owner(owner_id=row["owner_id"], name=row["name"])

    pets_result = sb.table("pets").select("*").eq("owner_id", owner.owner_id).execute()
    for pet_row in (pets_result.data or []):
        pet = Pet(pet_id=pet_row["pet_id"], name=pet_row["name"], species=pet_row["species"])

        tasks_result = sb.table("tasks").select("*").eq("pet_id", pet.pet_id).execute()
        for task_row in (tasks_result.data or []):
            pet.add_task(Task(
                task_id=task_row["task_id"],
                description=task_row["description"],
                time=task_row["time"],
                frequency=task_row["frequency"],
                due_date=date.fromisoformat(str(task_row["due_date"])),
                completed=task_row["completed"],
            ))

        owner.add_pet(pet)

    return owner


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save(owner: Owner) -> None:
    """Persist the owner and all nested data (Supabase or JSON)."""
    if _USE_SUPABASE:
        try:
            _save_supabase(owner)
            return
        except Exception as exc:
            logger.error("Supabase save failed, falling back to JSON: %s", exc)
    _save_json(owner)


def load() -> Owner:
    """Load persisted data (Supabase or JSON), or return a fresh Owner."""
    if _USE_SUPABASE:
        try:
            return _load_supabase()
        except Exception as exc:
            logger.error("Supabase load failed, falling back to JSON: %s", exc)
    return _load_json()
