# Structure geometry, coordination, and comparison

This v0.5 layer performs deterministic geometry on the reviewed immutable `AtomicStructure` model. Every periodic image is caller-visible; the library does not silently replace requested positions with a minimum-image convention.

## Exact periodic images

`PeriodicImage(a, b, c)` stores integer translations along the retained lattice row vectors. `SiteImage(site_key, image)` identifies one exact copy of one retained site.

For lattice matrix `L` with row vectors `a`, `b`, `c`, an image offset `n = (na, nb, nc)` is placed at

```text
r_image = r_site + n @ L
```

A nonzero offset is valid only on an axis whose PBC flag is true. No lattice image can be requested for a nonperiodic molecule.

## Distances and angles

`site_distance(structure, first, second)` returns the exact displacement

```text
Delta r = r_second - r_first
```

and its Euclidean norm in angstrom. It never applies a hidden minimum-image transform.

`site_angle(structure, first, vertex, third)` evaluates the caller-selected first–vertex–third angle in degrees. Zero-length vectors fail explicitly.

## Coordination by explicit cutoff and image bounds

`coordination_by_cutoff(structure, center_key, cutoff_angstrom, image_range=...)` searches only lattice images inside the caller-declared integer extents.

For example:

```python
result = coordination_by_cutoff(
    structure,
    "site-0000",
    2.5,
    image_range=(1, 1, 0),
)
```

searches a and b images from -1 through +1 and only the zero c image. Nonperiodic axes require an extent of zero.

The center site at image `(0, 0, 0)` is excluded. A periodic copy of the same site at a nonzero image remains a legitimate neighbor. Candidates at `distance <= cutoff` are retained and sorted deterministically by distance, original site order, then image tuple. The coordination number is exactly the neighbor count. No covalent-radius, bond-valence, Voronoi, CrystalNN, or element-name bond inference is applied.

## Explicit structure comparison

`compare_structures(reference, candidate, mappings)` compares only caller-supplied `SiteMapping` records. No site matching, symmetry matching, translation removal, rotation fit, or Kabsch alignment is performed.

For each mapping:

```text
Delta r_i = r_candidate,i - r_reference,i
```

The result retains all displacement vectors and per-mapping distances, plus

```text
RMSD = sqrt(mean(distance_i^2))
max_displacement = max(distance_i)
```

Reference and candidate site/image identities must each be unique within the mapping set.

## Guardrails

- geometry uses site keys rather than silently relying on positional index arguments;
- periodic images are explicit and validated against PBC;
- direct distance and angle operations do not infer chemical bonds;
- coordination searches only explicit image bounds;
- structure comparison never reorders or auto-aligns sites;
- result arrays are detached and read-only;
- no new runtime dependency is introduced.

## Explicit non-actions

This block does not implement automatic bonding, Voronoi/CrystalNN coordination, symmetry standardization, site mapping, rigid-body alignment, structure visualization, or VASP job management.
