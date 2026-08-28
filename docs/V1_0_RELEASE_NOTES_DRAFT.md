# CatalysisWorkbench v1.0 Release Notes — Draft

These notes describe the current `1.0.0.dev0` release candidate scope. They are preparatory material only. Stable `1.0.0`, a `v1.0.0` tag, GitHub Release, and package-registry publication remain separately gated.

## Overview

CatalysisWorkbench v1.0 turns the reviewed catalysis post-processing library into a reproducible local workbench while preserving explicit scientific semantics. The release line combines the v0.8 operando/time-resolved analysis milestone, the v0.9 reproducible workflow foundation, and the six-block v1.0 workspace/application/desktop implementation.

## Scientific analysis carried into v1.0

The frozen scientific surface includes the reviewed capabilities developed through v0.8, including:

- quantitative electrochemistry and activity normalization;
- characterization workflows for diffraction, spectroscopy, thermal analysis, sorption, composition, XPS and XAS/EXAFS;
- product calibration and quantification;
- atomistic/DFT post-processing for structures, energetics, DOS/PDOS, bonding, CHE/free-energy analysis, volumetric fields, band/PROCAR/LOCPOT and NEB data;
- static publication visualization, including optional volumetric 3-D rendering;
- immutable operando/time-resolved stacks, measured-grid operations, descriptor trajectories and explicit cross-modal comparison.

Scientific transformations remain explicit and fail closed on incompatible state. The v1.0 workbench layers do not add hidden chemistry, parser guessing or automatic scientific correction.

## Reproducible workflows

The v0.9 foundation carried into v1.0 provides:

- explicit schema-versioned workflow recipes;
- literal ordered execution rather than DAG inference;
- deterministic workflow-run records and content identities;
- explicit batching and QA aggregation;
- source-controlled publication preset assets and reproducible serialization contracts.

Serialized recipes do not execute arbitrary callables or dynamically import operations.

## Local workspace

v1.0 adds a strict file-backed local workspace with:

- deterministic `WorkspaceManifest` identity;
- caller-selected asset IDs/types and explicit `copy` versus external `reference` policy;
- confined workspace-owned paths with fail-closed traversal/symlink rules;
- content SHA-256 retention;
- a persistent evidence ledger that associates existing reviewed recipe/run/batch/QA/content identities without recomputing scientific provenance;
- reproducible recipe and FigureSpec composition state with explicit asset associations and pinned identities.

## GUI-neutral application layer

The `catalysis_workbench.application` package provides transaction-safe session state and user-action orchestration for:

- workspace creation/opening/refresh and explicit asset selection/import;
- ordered recipe inspection/editing/saving;
- reviewed workflow execution with explicit inputs and identities;
- explicit QA aggregation;
- FigureSpec selection/editing/saving;
- fail-closed behavior when workspace state changes concurrently.

The application layer remains headless-testable and does not import a GUI toolkit.

## Optional desktop shell

The optional `[desktop]` extra provides a local Qt Widgets presentation shell backed by `PySide6-Essentials>=6.11.2,<6.12`.

The desktop includes workspace creation/opening, asset navigation/import, recipe inspection/editing, run/evidence/QA inspection, FigureSpec presentation controls, and an integration hook to the existing Matplotlib FigureSpec editor.

Qt remains optional and lazy-loaded. Base package imports do not require or load PySide6. Desktop presentation delegates mutations to the reviewed application/workspace APIs and does not become a second scientific execution engine.

## Reliability and release hardening

The Stable 1.0 Gate-A process adds:

- a unified installed-wheel public-API audit for the frozen v1.0 surface;
- retained historical scientific installed-wheel regression audits;
- isolated base-package checks for optional backend laziness;
- Linux/Windows/macOS exact-wheel installation checks on Python 3.11 and 3.14;
- isolated `[desktop]` installation/import validation on the same matrix;
- wheel + sdist metadata validation and sdist-to-wheel rebuild checks;
- release-oriented package metadata and explicit release procedure documentation.

## Intentional non-goals

v1.0 does not introduce:

- automatic parser selection as scientific authority;
- recursive project crawling or implicit file discovery;
- DAG/topological workflow scheduling;
- arbitrary callable execution or dynamic operation discovery;
- automatic QA strategy selection;
- silent unit/scientific correction;
- database, server, cloud or background-service architecture;
- GUI-side scientific transformations outside reviewed APIs.

## Release status

This document remains a draft while Stable 1.0 maturity gates are open. The project license, final `1.0.0` version candidate, exact tag target, GitHub Release publication, and PyPI/package-registry publication each require their defined review/authorization gate.
