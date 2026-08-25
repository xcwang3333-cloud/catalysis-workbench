"""Explicit retained NEB image/path state and discrete barrier arithmetic."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from math import isfinite

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from .structure import AtomicStructure


class NEBError(ValueError):
    """Raised when retained NEB state is scientifically ambiguous or inconsistent."""


_REACTION_COORDINATE_MODES = {"ordinal", "explicit"}
_ENERGY_MODES = {"absolute", "reference_relative"}
_DISCRETE_BARRIER_SEMANTICS = "discrete_retained_image"


def _required_text(value: object, *, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise NEBError(f"{name} must not be blank")
    return text


def _optional_text(value: object | None, *, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name=name)


def _finite_real(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be a real numeric value")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a real numeric value") from exc
    if not isfinite(number):
        raise NEBError(f"{name} must be finite")
    return number


def _index(value: object, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    result = int(value)
    if result < 0:
        raise NEBError(f"{name} must be non-negative")
    return result


def _frozen_1d(values: Sequence[float], *, name: str) -> NDArray[np.float64]:
    try:
        source = np.asarray(values)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a one-dimensional real numeric sequence") from exc
    if source.ndim != 1 or np.iscomplexobj(source) or source.dtype.kind not in "biuf":
        raise TypeError(f"{name} must be a one-dimensional real numeric sequence")
    normalized = np.ascontiguousarray(source, dtype=np.float64)
    if normalized.size == 0 or not np.isfinite(normalized).all():
        raise NEBError(f"{name} must contain finite values")
    frozen = np.frombuffer(normalized.tobytes(order="C"), dtype=np.float64)
    frozen.setflags(write=False)
    return frozen


def _digest_text(digest: object, value: str | None) -> None:
    if value is None:
        digest.update(b"none\0")
        return
    encoded = value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "little", signed=False))
    digest.update(encoded)


def _digest_float(digest: object, value: float) -> None:
    digest.update(np.float64(value).tobytes())


@dataclass(frozen=True, slots=True, eq=False)
class NEBImageState:
    """One retained NEB image energy with explicit source provenance."""

    key: str
    energy_ev: float
    source_key: str
    source_type: str
    source_digest: str
    structure: AtomicStructure | None = None
    label: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="image key")
        energy = _finite_real(self.energy_ev, name="energy_ev")
        source_key = _required_text(self.source_key, name="source_key")
        source_type = _required_text(self.source_type, name="source_type")
        source_digest = _required_text(self.source_digest, name="source_digest")
        label = _optional_text(self.label, name="label")
        structure = self.structure
        if structure is not None and not isinstance(structure, AtomicStructure):
            raise TypeError("structure must be an AtomicStructure or None")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.NEBImageState.v1\0")
        for text in (key, source_key, source_type, source_digest):
            _digest_text(digest, text)
        _digest_float(digest, energy)
        _digest_text(digest, None if structure is None else structure.digest)

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "energy_ev", energy)
        object.__setattr__(self, "source_key", source_key)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "source_digest", source_digest)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def structure_digest(self) -> str | None:
        """Return the attached immutable structure digest when one is retained."""
        return None if self.structure is None else self.structure.digest

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, NEBImageState)
            and self.digest == other.digest
            and self.label == other.label
        )


@dataclass(frozen=True, slots=True, eq=False)
class NEBPath:
    """Exact caller/source-ordered NEB image energies prepared for passive plotting."""

    key: str
    images: Sequence[NEBImageState]
    reaction_coordinate_mode: str
    reaction_coordinates: Sequence[float]
    energy_mode: str
    plotted_energy_ev: Sequence[float]
    reference_image_key: str | None = None
    label: str | None = None
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        key = _required_text(self.key, name="path key")
        images = tuple(self.images)
        if len(images) < 2 or not all(isinstance(item, NEBImageState) for item in images):
            raise NEBError("images must contain at least two NEBImageState values")
        image_keys = tuple(item.key for item in images)
        if len(image_keys) != len(set(image_keys)):
            raise NEBError("image keys must be unique within an NEB path")

        coordinate_mode = _required_text(
            self.reaction_coordinate_mode,
            name="reaction_coordinate_mode",
        ).lower()
        if coordinate_mode not in _REACTION_COORDINATE_MODES:
            raise NEBError("reaction_coordinate_mode must be 'ordinal' or 'explicit'")
        coordinates = _frozen_1d(
            self.reaction_coordinates,
            name="reaction_coordinates",
        )
        if coordinates.size != len(images):
            raise NEBError("reaction_coordinates must contain one value per retained image")
        if coordinate_mode == "ordinal":
            expected_coordinates = np.arange(len(images), dtype=np.float64)
            if not np.array_equal(coordinates, expected_coordinates):
                raise NEBError(
                    "ordinal reaction coordinates must equal exact retained image indices"
                )

        energy_mode = _required_text(self.energy_mode, name="energy_mode").lower()
        if energy_mode not in _ENERGY_MODES:
            raise NEBError("energy_mode must be 'absolute' or 'reference_relative'")
        plotted = _frozen_1d(self.plotted_energy_ev, name="plotted_energy_ev")
        if plotted.size != len(images):
            raise NEBError("plotted_energy_ev must contain one value per retained image")
        reference_key = _optional_text(
            self.reference_image_key,
            name="reference_image_key",
        )
        absolute = np.array([item.energy_ev for item in images], dtype=np.float64)
        if energy_mode == "absolute":
            if reference_key is not None:
                raise NEBError("absolute energy_mode must not define reference_image_key")
            expected_plotted = absolute
        else:
            if reference_key is None:
                raise NEBError(
                    "reference_relative energy_mode requires explicit reference_image_key"
                )
            if reference_key not in image_keys:
                raise NEBError("reference_image_key must identify one retained image")
            reference_energy = images[image_keys.index(reference_key)].energy_ev
            expected_plotted = absolute - reference_energy
        if not np.array_equal(plotted, expected_plotted):
            raise NEBError(
                "plotted_energy_ev must exactly match retained absolute/reference arithmetic"
            )
        label = _optional_text(self.label, name="label")

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.NEBPath.v1\0")
        for text in (key, coordinate_mode, energy_mode, reference_key):
            _digest_text(digest, text)
        for image in images:
            _digest_text(digest, image.digest)
        digest.update(coordinates.tobytes(order="C"))
        digest.update(plotted.tobytes(order="C"))

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "images", images)
        object.__setattr__(self, "reaction_coordinate_mode", coordinate_mode)
        object.__setattr__(self, "reaction_coordinates", coordinates)
        object.__setattr__(self, "energy_mode", energy_mode)
        object.__setattr__(self, "plotted_energy_ev", plotted)
        object.__setattr__(self, "reference_image_key", reference_key)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "digest", digest.hexdigest())

    @property
    def image_keys(self) -> tuple[str, ...]:
        """Return exact retained source image keys in source order."""
        return tuple(item.key for item in self.images)

    @property
    def absolute_energy_ev(self) -> NDArray[np.float64]:
        """Return a detached read-only copy of exact retained absolute image energies."""
        array = np.asarray([item.energy_ev for item in self.images], dtype=np.float64)
        frozen = np.frombuffer(np.ascontiguousarray(array).tobytes(), dtype=np.float64)
        frozen.setflags(write=False)
        return frozen

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, NEBPath)
            and self.digest == other.digest
            and self.label == other.label
        )


def build_neb_path(
    images: Sequence[NEBImageState],
    *,
    key: str,
    reaction_coordinates: Sequence[float] | None = None,
    reference_image_key: str | None = None,
    label: str | None = None,
) -> NEBPath:
    """Build an exact ordered NEB path without geometric or saddle inference."""
    retained = tuple(images)
    if reaction_coordinates is None:
        coordinate_mode = "ordinal"
        coordinates = np.arange(len(retained), dtype=np.float64)
    else:
        coordinate_mode = "explicit"
        coordinates = reaction_coordinates

    absolute = np.array([item.energy_ev for item in retained], dtype=np.float64)
    if reference_image_key is None:
        energy_mode = "absolute"
        plotted = absolute
    else:
        reference = _required_text(reference_image_key, name="reference_image_key")
        image_keys = tuple(item.key for item in retained)
        if reference not in image_keys:
            raise NEBError("reference_image_key must identify one retained image")
        energy_mode = "reference_relative"
        reference_energy = retained[image_keys.index(reference)].energy_ev
        plotted = absolute - reference_energy

    return NEBPath(
        key=key,
        images=retained,
        reaction_coordinate_mode=coordinate_mode,
        reaction_coordinates=coordinates,
        energy_mode=energy_mode,
        plotted_energy_ev=plotted,
        reference_image_key=reference_image_key,
        label=label,
    )


@dataclass(frozen=True, slots=True, eq=False)
class NEBBarrierResult:
    """Explicit forward/reverse barrier from one retained discrete saddle image."""

    path_digest: str
    initial_image_key: str
    saddle_image_key: str
    final_image_key: str
    initial_image_index: int
    saddle_image_index: int
    final_image_index: int
    initial_image_digest: str
    saddle_image_digest: str
    final_image_digest: str
    initial_energy_ev: float
    saddle_energy_ev: float
    final_energy_ev: float
    forward_barrier_ev: float
    reverse_barrier_ev: float
    barrier_semantics: str = _DISCRETE_BARRIER_SEMANTICS
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        path_digest = _required_text(self.path_digest, name="path_digest")
        initial_key = _required_text(self.initial_image_key, name="initial_image_key")
        saddle_key = _required_text(self.saddle_image_key, name="saddle_image_key")
        final_key = _required_text(self.final_image_key, name="final_image_key")
        if len({initial_key, saddle_key, final_key}) != 3:
            raise NEBError("initial, saddle, and final image keys must be distinct")

        initial_index = _index(self.initial_image_index, name="initial_image_index")
        saddle_index = _index(self.saddle_image_index, name="saddle_image_index")
        final_index = _index(self.final_image_index, name="final_image_index")
        if not initial_index < saddle_index < final_index:
            raise NEBError(
                "retained image order must satisfy initial before saddle before final"
            )

        initial_digest = _required_text(self.initial_image_digest, name="initial_image_digest")
        saddle_digest = _required_text(self.saddle_image_digest, name="saddle_image_digest")
        final_digest = _required_text(self.final_image_digest, name="final_image_digest")
        initial_energy = _finite_real(self.initial_energy_ev, name="initial_energy_ev")
        saddle_energy = _finite_real(self.saddle_energy_ev, name="saddle_energy_ev")
        final_energy = _finite_real(self.final_energy_ev, name="final_energy_ev")
        forward = _finite_real(self.forward_barrier_ev, name="forward_barrier_ev")
        reverse = _finite_real(self.reverse_barrier_ev, name="reverse_barrier_ev")
        expected_forward = saddle_energy - initial_energy
        expected_reverse = saddle_energy - final_energy
        if not np.isclose(forward, expected_forward, rtol=0.0, atol=1e-14):
            raise NEBError("forward_barrier_ev must equal E_saddle - E_initial")
        if not np.isclose(reverse, expected_reverse, rtol=0.0, atol=1e-14):
            raise NEBError("reverse_barrier_ev must equal E_saddle - E_final")

        semantics = _required_text(self.barrier_semantics, name="barrier_semantics")
        if semantics != _DISCRETE_BARRIER_SEMANTICS:
            raise NEBError(
                f"barrier_semantics must be {_DISCRETE_BARRIER_SEMANTICS!r}"
            )

        digest = hashlib.sha256()
        digest.update(b"CatalysisWorkbench.NEBBarrierResult.v1\0")
        for text in (
            path_digest,
            initial_key,
            saddle_key,
            final_key,
            initial_digest,
            saddle_digest,
            final_digest,
            semantics,
        ):
            _digest_text(digest, text)
        for index in (initial_index, saddle_index, final_index):
            digest.update(index.to_bytes(8, "little", signed=False))
        for value in (
            initial_energy,
            saddle_energy,
            final_energy,
            forward,
            reverse,
        ):
            _digest_float(digest, value)

        object.__setattr__(self, "path_digest", path_digest)
        object.__setattr__(self, "initial_image_key", initial_key)
        object.__setattr__(self, "saddle_image_key", saddle_key)
        object.__setattr__(self, "final_image_key", final_key)
        object.__setattr__(self, "initial_image_index", initial_index)
        object.__setattr__(self, "saddle_image_index", saddle_index)
        object.__setattr__(self, "final_image_index", final_index)
        object.__setattr__(self, "initial_image_digest", initial_digest)
        object.__setattr__(self, "saddle_image_digest", saddle_digest)
        object.__setattr__(self, "final_image_digest", final_digest)
        object.__setattr__(self, "initial_energy_ev", initial_energy)
        object.__setattr__(self, "saddle_energy_ev", saddle_energy)
        object.__setattr__(self, "final_energy_ev", final_energy)
        object.__setattr__(self, "forward_barrier_ev", forward)
        object.__setattr__(self, "reverse_barrier_ev", reverse)
        object.__setattr__(self, "barrier_semantics", semantics)
        object.__setattr__(self, "digest", digest.hexdigest())

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NEBBarrierResult) and self.digest == other.digest


def calculate_neb_barrier(
    path: NEBPath,
    *,
    initial_image_key: str,
    saddle_image_key: str,
    final_image_key: str,
) -> NEBBarrierResult:
    """Calculate a discrete retained-image barrier from three explicit image keys."""
    if not isinstance(path, NEBPath):
        raise TypeError("path must be an NEBPath")
    initial_key = _required_text(initial_image_key, name="initial_image_key")
    saddle_key = _required_text(saddle_image_key, name="saddle_image_key")
    final_key = _required_text(final_image_key, name="final_image_key")
    if len({initial_key, saddle_key, final_key}) != 3:
        raise NEBError("initial, saddle, and final image keys must be distinct")

    keys = path.image_keys
    missing = [key for key in (initial_key, saddle_key, final_key) if key not in keys]
    if missing:
        raise NEBError(f"barrier image keys are not retained in path: {missing!r}")
    initial_index = keys.index(initial_key)
    saddle_index = keys.index(saddle_key)
    final_index = keys.index(final_key)
    if not initial_index < saddle_index < final_index:
        raise NEBError("retained image order must satisfy initial before saddle before final")

    initial = path.images[initial_index]
    saddle = path.images[saddle_index]
    final = path.images[final_index]
    forward = saddle.energy_ev - initial.energy_ev
    reverse = saddle.energy_ev - final.energy_ev
    return NEBBarrierResult(
        path_digest=path.digest,
        initial_image_key=initial.key,
        saddle_image_key=saddle.key,
        final_image_key=final.key,
        initial_image_index=initial_index,
        saddle_image_index=saddle_index,
        final_image_index=final_index,
        initial_image_digest=initial.digest,
        saddle_image_digest=saddle.digest,
        final_image_digest=final.digest,
        initial_energy_ev=initial.energy_ev,
        saddle_energy_ev=saddle.energy_ev,
        final_energy_ev=final.energy_ev,
        forward_barrier_ev=forward,
        reverse_barrier_ev=reverse,
    )


def validate_neb_barrier_path(
    path: NEBPath,
    barrier: NEBBarrierResult,
) -> NEBBarrierResult:
    """Fail closed unless one barrier exactly identifies retained path images."""
    if not isinstance(path, NEBPath):
        raise TypeError("path must be an NEBPath")
    if not isinstance(barrier, NEBBarrierResult):
        raise TypeError("barrier must be an NEBBarrierResult")
    if barrier.path_digest != path.digest:
        raise NEBError("barrier path_digest does not match the retained NEB path")

    triplets = (
        (
            barrier.initial_image_index,
            barrier.initial_image_key,
            barrier.initial_image_digest,
            barrier.initial_energy_ev,
        ),
        (
            barrier.saddle_image_index,
            barrier.saddle_image_key,
            barrier.saddle_image_digest,
            barrier.saddle_energy_ev,
        ),
        (
            barrier.final_image_index,
            barrier.final_image_key,
            barrier.final_image_digest,
            barrier.final_energy_ev,
        ),
    )
    for index, key, image_digest, energy in triplets:
        if index >= len(path.images):
            raise NEBError("barrier image index is outside the retained NEB path")
        image = path.images[index]
        if image.key != key or image.digest != image_digest or image.energy_ev != energy:
            raise NEBError("barrier image identity does not match the retained NEB path")
    return barrier


def neb_path_frame(path: NEBPath) -> pd.DataFrame:
    """Return a detached table of retained NEB path state without recomputation."""
    if not isinstance(path, NEBPath):
        raise TypeError("path must be an NEBPath")
    rows: list[dict[str, object]] = []
    for index, image in enumerate(path.images):
        rows.append(
            {
                "path_key": path.key,
                "path_digest": path.digest,
                "image_index": index,
                "image_key": image.key,
                "label": image.label,
                "reaction_coordinate": float(path.reaction_coordinates[index]),
                "reaction_coordinate_mode": path.reaction_coordinate_mode,
                "absolute_energy_ev": image.energy_ev,
                "plotted_energy_ev": float(path.plotted_energy_ev[index]),
                "energy_mode": path.energy_mode,
                "reference_image_key": path.reference_image_key,
                "source_type": image.source_type,
                "source_key": image.source_key,
                "source_digest": image.source_digest,
                "image_digest": image.digest,
                "structure_digest": image.structure_digest,
            }
        )
    return pd.DataFrame(rows)


def neb_barrier_frame(result: NEBBarrierResult) -> pd.DataFrame:
    """Return a one-row detached table of retained discrete barrier state."""
    if not isinstance(result, NEBBarrierResult):
        raise TypeError("result must be an NEBBarrierResult")
    return pd.DataFrame(
        [
            {
                "path_digest": result.path_digest,
                "barrier_semantics": result.barrier_semantics,
                "initial_image_key": result.initial_image_key,
                "saddle_image_key": result.saddle_image_key,
                "final_image_key": result.final_image_key,
                "initial_image_index": result.initial_image_index,
                "saddle_image_index": result.saddle_image_index,
                "final_image_index": result.final_image_index,
                "initial_energy_ev": result.initial_energy_ev,
                "saddle_energy_ev": result.saddle_energy_ev,
                "final_energy_ev": result.final_energy_ev,
                "forward_barrier_ev": result.forward_barrier_ev,
                "reverse_barrier_ev": result.reverse_barrier_ev,
                "result_digest": result.digest,
            }
        ]
    )


__all__ = [
    "NEBBarrierResult",
    "NEBError",
    "NEBImageState",
    "NEBPath",
    "build_neb_path",
    "calculate_neb_barrier",
    "neb_barrier_frame",
    "neb_path_frame",
    "validate_neb_barrier_path",
]
