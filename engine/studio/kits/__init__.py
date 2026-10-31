"""Domain kits add object types and ops (e.g. `physics.road`, `race`). Load by name from spec.kits."""
import importlib

from ..spec import SpecError


def load(names: list[str]) -> None:
    for n in names:
        try:
            importlib.import_module(f"studio.kits.{n}")
        except ModuleNotFoundError as e:
            raise SpecError([f"unknown kit '{n}'"]) from e
