"""Video spec and batch plan schemas (pydantic), with readable error messages."""
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class SpecError(ValueError):
    def __init__(self, messages: list[str]):
        super().__init__("\n".join(messages))
        self.messages = messages


class Loose(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Obj(Loose):
    id: str
    type: str


class Op(Loose):
    op: str
    at: float = 0.0
    for_: float | None = Field(None, alias="for")


class Beat(BaseModel):
    say: str
    caption: str | None = None
    chapter: str | None = None
    do: list[Op] = []


class Short(BaseModel):
    hook: list[str]
    beats: list[int]
    cta: str = ""


class Thumb(BaseModel):
    lines: list[str]
    badge: str = ""
    formula: str = ""


class Stage(BaseModel):
    width: float = 10
    height: float = 6


class Spec(BaseModel):
    id: str
    template: str = "concept-explainer"
    title: str
    subtitle: str = ""
    kits: list[str] = []
    thumbnail: Thumb | None = None
    params: dict[str, float] = {}
    stage: Stage = Stage()
    objects: list[Obj] = []
    beats: list[Beat]
    short: Short | None = None


Output = Literal["long", "short", "thumb"]


class PlanItem(BaseModel):
    id: str
    title: str
    template: str
    outputs: list[Output]
    target_seconds: int = 240
    research: Literal["off", "vet", "deep"] = "vet"
    source_refs: list[str] = []
    notes: str = ""


class Plan(BaseModel):
    request: str = ""
    items: list[PlanItem]


def _load(model, path):
    try:
        return model.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
    except json.JSONDecodeError as e:
        raise SpecError([f"invalid JSON at line {e.lineno}: {e.msg}"]) from e
    except ValidationError as e:
        raise SpecError([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()]) from e


def load(path) -> Spec:
    return _load(Spec, path)


def load_plan(path) -> Plan:
    return _load(Plan, path)
