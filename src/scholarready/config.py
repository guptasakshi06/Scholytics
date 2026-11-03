"""Validated fictional checklist configuration and explicit conditional applicability."""
import json
from pathlib import Path
from typing import Literal, Self

from pydantic import model_validator

from .schemas import ApplicantProfile, Contract, ExplicitTrue, RequirementDefinition, Text


class ScholarshipConfig(Contract):
    config_version: Text
    profile_id: Text
    display_name: Text
    fictional: ExplicitTrue
    scope: Literal["document_readiness_only"]
    description: Text
    requirements: list[RequirementDefinition]

    @model_validator(mode="after")
    def unique_requirements(self) -> Self:
        ids = [r.requirement_id for r in self.requirements]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate requirement ID")
        types = [r.document_type for r in self.requirements]
        if len(set(types)) != len(types):
            raise ValueError("one requirement item per document type in v1")
        return self


def load_config(path: str | Path) -> ScholarshipConfig:
    """Raise OSError, JSONDecodeError or ValidationError with actionable details."""
    return ScholarshipConfig.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def condition_applicability(requirement: RequirementDefinition, profile: ApplicantProfile) -> bool | None:
    """Resolve only explicit profile attributes; unknown stays unknown."""
    if requirement.condition is None:
        return True
    value = profile.category_certificate_required
    return None if value is None else value is requirement.condition.equals
