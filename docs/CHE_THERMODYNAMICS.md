# CHE and free-energy thermodynamics

CatalysisWorkbench v0.6 block 7 adds explicit free-energy thermodynamics and Computational Hydrogen Electrode (CHE) arithmetic on top of the reviewed v0.5 DFT-energy ledger.

The implementation is intentionally narrow. It does not calculate vibrational frequencies, discover reactions, query gas/solvation databases, construct Pourbaix diagrams, solve microkinetics, or draw free-energy diagrams. Those tasks either remain caller responsibilities or belong to later blocks.

## Electronic-energy authority

`DFTEnergyLedger` remains the authority for electronic DFT energies. A `ThermodynamicEntry` stores `dft_entry_key` and corrections; it does not copy a second independent electronic-energy value.

Evaluation therefore begins by resolving that exact key from the supplied ledger. The referenced DFT entry must have an explicit `normalization_basis`; CatalysisWorkbench retains that basis and does not silently convert it.

## Thermodynamic entry

A `ThermodynamicEntry` retains, independently:

- stable thermodynamic key;
- exact `dft_entry_key`;
- optional ZPE, in eV;
- optional thermal enthalpy correction, in eV;
- optional entropy, in eV/K;
- temperature, in K, when thermal enthalpy or entropy is supplied;
- caller-supplied additional `FreeEnergyCorrection` objects;
- optional display label.

`None` means **not supplied**. It is distinct from `0.0`, which means the caller explicitly supplied a zero-valued term.

Every additional correction has a stable key, correction type, value in eV, and source ID. Corrections are canonicalized by stable key because additive correction order has no scientific meaning.

## Explicit evaluation recipe

A `FreeEnergyRecipe` explicitly selects which available terms enter the evaluated free energy:

```text
G = E_DFT
    + [ZPE]
    + [thermal enthalpy correction]
    - [T * S]
    + sum([selected additional corrections])
```

Square brackets mean that the term contributes only when the recipe explicitly requests it.

Rules:

- electronic DFT energy is always included from the resolved ledger entry;
- requested missing ZPE/thermal/entropy state fails closed;
- requesting an unknown additional correction fails closed;
- supplied but unselected state remains retained in `ThermodynamicEntry` but does not enter `FreeEnergyEvaluation`;
- the entropy contribution is exactly `-temperature_k * entropy_ev_per_k`;
- no hidden standard-state, vibrational, gas, solvent, field, or experimental correction is inserted.

`FreeEnergyEvaluation` retains every included contribution, its source identity/digest, the ledger digest, DFT entry key, normalization basis, recipe digest, temperature state, and reconstructible total in eV.

## Computational Hydrogen Electrode

For one proton-electron pair on the SHE scale, block 7 uses the frozen v0.6 convention

```text
mu(H+ + e-) = 1/2 G(H2) - U_SHE - k_B T ln(10) * pH
```

The one-electron `e * U` energy contribution is numerically equal to the potential in eV when `U` is supplied in volts. The API nevertheless retains potential and energy contributions as separate physical state rather than relying on an undocumented unit shortcut.

### Boltzmann constant

The implementation records

```text
BOLTZMANN_EV_PER_K = 8.617333262145e-5 eV/K
```

This is the eV/K value obtained from the exact post-2019 SI values of the Boltzmann constant and elementary charge. The exact value used in a `CHEState` is retained in the state and result provenance.

### SHE input

For `potential_reference="SHE"`:

```text
U_SHE = U_input
DeltaG_U = -U_SHE
DeltaG_pH = -k_B T ln(10) * pH
```

Thus

```text
mu = 1/2 G(H2) + DeltaG_U + DeltaG_pH
```

No reaction name or reduction/oxidation label changes these signs.

### RHE input

For `potential_reference="RHE"`, CatalysisWorkbench first performs the explicit one-electron conversion

```text
U_SHE = U_RHE - k_B T ln(10) * pH
```

and then evaluates the same SHE CHE equation. Substitution gives

```text
mu = 1/2 G(H2)
     - [U_RHE - k_B T ln(10) * pH]
     - k_B T ln(10) * pH
```

so the pH terms cancel naturally:

```text
mu = 1/2 G(H2) - U_RHE
```

The implementation does **not** use this simplified expression as a separate hidden RHE branch. `CHEProtonElectronResult` retains the input potential/reference, Nernst pH shift, converted `U_SHE`, potential contribution, pH contribution, half-H2 contribution, and final chemical potential.

If the evaluated H2 free energy carries a temperature, the CHE temperature must match it. A temperature-independent explicit H2 evaluation can still be used; its absent temperature remains visible rather than being invented.

## Reaction free-energy arithmetic

Reaction arithmetic uses explicit `ReactionFreeEnergyTerm` objects with the convention

```text
products:  positive coefficient
reactants: negative coefficient
```

and

```text
Delta G = sum_i coefficient_i * value_i
```

Minimum source types are:

- `thermodynamic_state` from a `FreeEnergyEvaluation`;
- `che_proton_electron_pair` from a `CHEProtonElectronResult`.

The coefficient, not a reaction name, controls the sign and multiplicity. A CHE pair with coefficient `-2` contributes exactly twice the one-pair chemical potential with the explicit reactant sign.

All thermodynamic-state terms in one reaction must share one explicit normalization basis. A CHE term carries the explicit basis `per proton-electron pair`; its stoichiometric coefficient controls pair count. CatalysisWorkbench does not parse formulas or infer whether caller-supplied states are atom-balanced.

## Reporting

Detached tables are provided for:

- supplied/not-supplied thermodynamic entry state;
- included free-energy contributions;
- retained CHE conversion/contribution state;
- reaction free-energy terms and contributions.

Editing a returned DataFrame does not mutate retained scientific state.

## Prior art and dependency decision

ASE thermochemistry is a scientific/API reference for explicit thermodynamic components, temperature, entropy, and free-energy units. ASE is LGPL-2.1-or-later. Frequency-to-ZPE/entropy helpers are not part of this block and ASE is not added as a dependency.

CatMAP electrochemistry is reference prior art for representing proton-electron state as a potential-dependent thermodynamic correction referenced to one-half H2. CatMAP is GPL-3.0 and is reference-only; no CatMAP code is copied or adapted.

No new runtime dependency is introduced.

## Explicitly out of scope

Block 7 does not provide:

- vibrational-frequency parsing or automatic ZPE/entropy calculation;
- ideal-gas/harmonic/hindered-rotor thermochemistry engines;
- automatic gas, pressure, standard-state, solvent, hydrogen-bond, field, or experimental corrections;
- automatic reaction/pathway discovery or formula balancing;
- Pourbaix construction;
- microkinetic or coverage solving;
- constant-potential DFT schemes or transfer coefficients;
- free-energy diagrams or plotting (block 8);
- charge-density-difference calculation (block 9).
