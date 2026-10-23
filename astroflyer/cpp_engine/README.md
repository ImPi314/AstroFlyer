# Retired C++ kernel

The propagator no longer loads `astro_physics_kernel.dll`. The kernel implemented the
earlier simplified physics (zonal J2–J4 only, circular Sun/Moon, exponential drag), and
the current force model in `backend/forces.py` (EGM2008, DE440, conical-shadow SRP,
NRLMSISE-00) runs a full day of Molniya or GTO propagation in about 1 s with Numba,
with most of the time spent in SciPy's integrator loop rather than in the forces.

These sources are kept for reference. Porting the full model to C++ would mean
re-implementing the DE440 reader, NRLMSISE-00 and the IERS Earth-orientation chain,
for a speed-up on a step that is already about a second.
