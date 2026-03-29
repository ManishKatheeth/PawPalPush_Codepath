"""
PawPal+ local JSON persistence layer.
Saves and loads all owner/pet/task data to data/pawpal_data.json.
"""

import json
import uuid
from datetime import date
from pathlib import Path

from pawpal_system import Owner, Pet, Task

DATA_FILE = Path(__file__).parent / "data" / "pawpal_data.json"


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


def save(owner: Owner) -> None:
    """Persist the owner and all nested data to disk."""
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(_owner_to_dict(owner), indent=2))


def load() -> Owner:
    """Load persisted data, or return a fresh Owner if none exists."""
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text())
            return _owner_from_dict(data)
        except Exception:
            pass
    return Owner(owner_id=str(uuid.uuid4()), name="Sarah")
