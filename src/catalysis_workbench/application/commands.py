"""Typed GUI-neutral application commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from catalysis_workbench.workflow import RecipeStep, WorkflowRecipe
from catalysis_workbench.workspace.composition import (
    insert_recipe_step,
    move_recipe_step,
    remove_recipe_step,
    replace_recipe_step,
)


def _command_step_id(value: object) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(
            "recipe command step_id must be a non-empty string without surrounding whitespace"
        )
    return value


@dataclass(frozen=True, slots=True)
class InsertRecipeStepCommand:
    """Insert one explicit recipe step at a literal position."""

    index: int
    step: RecipeStep

    def __post_init__(self) -> None:
        if type(self.index) is not int or self.index < 0:
            raise ValueError("insert command index must be a non-negative integer")
        if not isinstance(self.step, RecipeStep):
            raise TypeError("insert command step must be a RecipeStep")


@dataclass(frozen=True, slots=True)
class ReplaceRecipeStepCommand:
    """Replace one explicitly identified recipe step in place."""

    step_id: str
    replacement: RecipeStep

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _command_step_id(self.step_id))
        if not isinstance(self.replacement, RecipeStep):
            raise TypeError("replacement must be a RecipeStep")


@dataclass(frozen=True, slots=True)
class RemoveRecipeStepCommand:
    """Remove one explicitly identified recipe step."""

    step_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _command_step_id(self.step_id))


@dataclass(frozen=True, slots=True)
class MoveRecipeStepCommand:
    """Move one explicitly identified recipe step to a literal index."""

    step_id: str
    new_index: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _command_step_id(self.step_id))
        if type(self.new_index) is not int or self.new_index < 0:
            raise ValueError("move command new_index must be a non-negative integer")


RecipeEditCommand: TypeAlias = (
    InsertRecipeStepCommand
    | ReplaceRecipeStepCommand
    | RemoveRecipeStepCommand
    | MoveRecipeStepCommand
)


def apply_recipe_edit(
    recipe: WorkflowRecipe,
    command: RecipeEditCommand,
) -> WorkflowRecipe:
    """Apply one closed-set recipe edit without execution or operation discovery."""

    if not isinstance(recipe, WorkflowRecipe):
        raise TypeError("recipe must be a WorkflowRecipe")
    if isinstance(command, InsertRecipeStepCommand):
        return insert_recipe_step(recipe, command.index, command.step)
    if isinstance(command, ReplaceRecipeStepCommand):
        return replace_recipe_step(recipe, command.step_id, command.replacement)
    if isinstance(command, RemoveRecipeStepCommand):
        return remove_recipe_step(recipe, command.step_id)
    if isinstance(command, MoveRecipeStepCommand):
        return move_recipe_step(recipe, command.step_id, command.new_index)
    raise TypeError("command must be a supported recipe edit command")
