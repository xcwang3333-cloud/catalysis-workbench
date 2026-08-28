"""Closed-set task descriptors for v1.1 analysis documents."""

from __future__ import annotations

from dataclasses import dataclass


class AnalysisTaskError(ValueError):
    """Raised when an analysis task identifier is invalid or unsupported."""


@dataclass(frozen=True, slots=True)
class AnalysisTaskDescriptor:
    """One user-facing analysis task with a stable serialized identifier."""

    task_id: str
    display_name: str
    description: str
    default_title: str


_TASKS = (
    AnalysisTaskDescriptor(
        task_id="lsv",
        display_name="LSV / Polarization",
        description="Analyze polarization curves and electrochemical LSV data.",
        default_title="Untitled LSV analysis",
    ),
    AnalysisTaskDescriptor(
        task_id="fe_partial_current",
        display_name="FE & Partial Current",
        description="Analyze Faradaic efficiency and product partial-current data.",
        default_title="Untitled FE & partial current analysis",
    ),
    AnalysisTaskDescriptor(
        task_id="generic_xy",
        display_name="Generic XY Plot",
        description="Start a general two-column or multi-series XY analysis.",
        default_title="Untitled XY analysis",
    ),
)
_TASKS_BY_ID = {task.task_id: task for task in _TASKS}


def analysis_task_catalog() -> tuple[AnalysisTaskDescriptor, ...]:
    """Return the stable v1.1 analysis-task catalog in presentation order."""

    return _TASKS


def get_analysis_task_descriptor(task_id: str) -> AnalysisTaskDescriptor:
    """Resolve one exact task identifier without guessing or discovery."""

    if type(task_id) is not str or not task_id:
        raise AnalysisTaskError("task_id must be a non-empty string")
    try:
        return _TASKS_BY_ID[task_id]
    except KeyError as exc:
        raise AnalysisTaskError(f"unknown analysis task_id: {task_id!r}") from exc


__all__ = [
    "AnalysisTaskDescriptor",
    "AnalysisTaskError",
    "analysis_task_catalog",
    "get_analysis_task_descriptor",
]
