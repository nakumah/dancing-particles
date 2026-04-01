
"""

Given a 3d world, and a  surface, the goal is ato apply  purtubations to the surface such that it
oscilliates.

Similar to what can be observed at sea.
"""

import numba as nb
import numpy as np

# ================================
# Utilities
# ================================

def wrap_periodic(pos, L):
    """Wrap positions to [0, L) per component."""
    return pos - L * np.floor(pos / L)

def minimum_image(dr, L):
    """Minimum image displacement for periodic boundaries."""
    return dr - L * np.round(dr / L)

def norm_rows(v):
    return np.sqrt((v * v).sum(axis=1))

# ================================
# Mixing rules
# ================================

def mix_sigma(sigma_i, sigma_j, rule="lorentz"):
    if rule == "lorentz":  # arithmetic mean
        return 0.5 * (sigma_i + sigma_j)
    elif rule == "geometric":
        return np.sqrt(sigma_i * sigma_j)
    else:
        raise ValueError("Unknown sigma mixing rule")

def mix_epsilon(eps_i, eps_j, rule="berthelot"):
    if rule == "berthelot":  # geometric mean
        return np.sqrt(eps_i * eps_j)
    elif rule == "arithmetic":
        return 0.5 * (eps_i + eps_j)
    else:
        raise ValueError("Unknown epsilon mixing rule")

# ================================
# Pair potentials (radial)
# ================================

def lj_force_mag(r, eps, sigma):
    """LJ 12-6 magnitude: F = 24*eps*(2*(sigma/r)^12 - (sigma/r)^6)/r"""
    invr = 1.0 / r
    sr = sigma * invr
    sr6 = sr**6
    sr12 = sr6 * sr6
    return 24.0 * eps * (2.0 * sr12 - sr6) * invr

def spring_coulomb_force_mag(r, k, r0, alpha):
    """F(r) = -k*(r - r0) + alpha/r^2"""
    return (-k * (r - r0)) + (alpha / (r * r))

# Optional soft wall (9-3) for LJ-like walls
def lj93_wall_force(z, eps_w, sigma_w):
    """Magnitude of 9-3 LJ wall force along +z (repels from wall at z=0).
       Force on particle points +z when z is small.
       U(z) = (2/15)*eps_w*((sigma/z)^9 - (sigma/z)^3)  (up to constants)
    """
    if z <= 0:
        return np.inf  # prevent penetration
    sz = sigma_w / z
    sz3 = sz**3
    sz9 = sz3**3
    # dU/dz -> F = -dU/dz ~ eps_w*(3*sz10 - sz4)  (scaled). We'll use a common heuristic:
    return eps_w * ( (3.0 * (sigma_w**9) / (z**10)) - ((sigma_w**3) / (z**4)) )

# ================================
# Neighbor list via cell lists with skin
# ================================

class NeighborList:
    def __init__(self, L, cutoff, skin=0.3):
        self.L = np.array(L, dtype=float)
        self.cutoff = float(cutoff)
        self.skin = float(skin)
        self.rc_list = self.cutoff + self.skin
        self.initialized = False
        self.last_pos = None
        self.cells = None
        self.ncell = None
        self.head = None
        self.nextp = None

    def _setup_cells(self, cell_size):
        # Ensure at least one cell per direction
        ncell = np.maximum(1, (self.L / cell_size).astype(int))
        self.ncell = ncell

    def _cell_id(self, ix, iy, iz):
        nx, ny, nz = self.ncell
        ix %= nx; iy %= ny; iz %= nz
        return ix + nx * (iy + ny * iz)

    def build(self, pos):
        N = pos.shape[0]
        cell_size = self.rc_list
        self._setup_cells(cell_size)
        nx, ny, nz = self.ncell
        self.head = -np.ones(nx * ny * nz, dtype=int)
        self.nextp = -np.ones(N, dtype=int)

        # Compute integer cell indices
        cs = self.L / self.ncell  # cell size vector
        idx = np.floor(pos / cs).astype(int)
        idx = np.mod(idx, self.ncell)
        flat = idx[:,0] + nx * (idx[:,1] + ny * idx[:,2])

        # Build linked lists
        for i in range(N):
            c = flat[i]
            self.nextp[i] = self.head[c]
            self.head[c] = i

        self.last_pos = pos.copy()
        self.initialized = True

    def needs_rebuild(self, pos):
        if not self.initialized:
            return True
        # Rebuild if any particle moved more than skin/2 since last build
        disp = minimum_image(pos - self.last_pos, self.L)
        max_disp = np.max(norm_rows(disp))
        return max_disp > (0.5 * self.skin)

    def pairs(self, pos):
        """Yield (i, j, rij, r) for i<j within rc_list (broad list); the caller should apply true cutoff."""
        assert self.initialized
        nx, ny, nz = self.ncell
        N = pos.shape[0]
        L = self.L

        def iter_cell_particles(c):
            i = self.head[c]
            while i != -1:
                yield i
                i = self.nextp[i]

        for iz in range(nz):
            for iy in range(ny):
                for ix in range(nx):
                    c = self._cell_id(ix, iy, iz)
                    # Get particles in this cell
                    for i in iter_cell_particles(c):
                        # Examine 27 neighbor cells (including current)
                        for dz in (-1, 0, 1):
                            for dy in (-1, 0, 1):
                                for dx in (-1, 0, 1):
                                    c2 = self._cell_id(ix+dx, iy+dy, iz+dz)
                                    for j in iter_cell_particles(c2):
                                        if j <= i:
                                            continue
                                        rij = minimum_image(pos[j] - pos[i], L)
                                        r = np.linalg.norm(rij)
                                        if r < self.rc_list:
                                            yield i, j, rij, r

# ================================
# Main simulator
# ================================

class SuspensionSim:
    """
    Many-particle Langevin MD with extras:
      - Mixtures (species), polydispersity, per-particle gamma & kT
      - Pair LJ or Spring+Coulomb with mixing; override matrices optional
      - Periodic / Reflective / Lees-Edwards shear boundaries
      - Background flow u = gamma_dot * y * ex (Couette); hydrodynamic drag to u
      - Gravity & buoyancy using species density and sigma -> volume
    Units are arbitrary/reduced unless you calibrate parameters.
    """
    def __init__(
        self,
        positions, velocities,
        species,                                 # (N,) ints
        species_params,                           # dict of species_id -> dict(params)
        box_lengths,                              # (3,)
        dt=1e-3,
        cutoff=2.5,
        skin=0.3,
        pair_model="LJ",                          # "LJ" or "spring_coulomb"
        mixing_rules=("lorentz","berthelot"),     # (sigma_rule, epsilon_rule)
        epsilon_matrix=None,                      # optional (S,S) overrides
        sigma_matrix=None,                        # optional (S,S) overrides
        boundary="periodic",                      # "periodic", "reflective", "lees_edwards"
        shear_rate=0.0,                           # for background flow / LE
        gravity=(0.0, 0.0, 0.0),                  # external g vector
        fluid_density=0.0,                        # for buoyancy
        seed=None
    ):
        self.rng = np.random.default_rng(seed)
        self.pos = np.array(positions, dtype=float)
        self.vel = np.array(velocities, dtype=float)
        self.species = np.asarray(species, dtype=int)
        self.N = self.pos.shape[0]
        assert self.vel.shape == self.pos.shape
        assert self.species.shape[0] == self.N

        self.S = len(species_params)
        self.sp = species_params
        self.dt = float(dt)
        self.L = np.array(box_lengths, dtype=float)
        self.cutoff = float(cutoff)
        self.skin = float(skin)

        self.boundary = boundary
        self.shear_rate = float(shear_rate)
        self.strain = 0.0  # accumulated strain for Lees–Edwards
        self.g = np.array(gravity, dtype=float)
        self.rho_f = float(fluid_density)

        self.pair_model = pair_model
        self.mix_sigma_rule, self.mix_eps_rule = mixing_rules

        # Gather per-particle params
        self.mass = np.array([self.sp[s]["mass"] for s in self.species], dtype=float)
        self.gamma = np.array([self.sp[s].get("gamma", 1.0) for s in self.species], dtype=float)
        self.kT    = np.array([self.sp[s].get("kT", 0.0)    for s in self.species], dtype=float)
        self.sigma_p = np.array([self.sp[s].get("sigma", 1.0) for s in self.species], dtype=float)
        # Per-particle sigma scale (polydispersity factor), default 1.0
        self.sigma_scale = np.array([self.sp[s].get("sigma_scale", 1.0) for s in self.species], dtype=float)
        self.sigma_p *= self.sigma_scale

        # Species densities (for buoyancy)
        self.rho_p = np.array([self.sp[s].get("density", 1.0) for s in self.species], dtype=float)

        # Pair parameter override matrices
        self.eps_mat_override = epsilon_matrix
        self.sig_mat_override = sigma_matrix

        # Neighbor list
        self.nl = NeighborList(self.L, cutoff=self.cutoff, skin=self.skin)
        self.nl.build(self.pos)

        # Precompute noise prefactor (per-particle, per-component)
        self.update_noise_scale()

    def update_noise_scale(self):
        # For BBK-like scheme we use noise ~ sqrt(2*gamma*kT/dt)
        # We'll draw N(0,1) and multiply by sqrt(dt) later to get correct variance.
        self.noise_scale = np.sqrt(2.0 * self.gamma * self.kT / np.maximum(self.dt, 1e-30))

    # ------- Boundary helpers -------

    def apply_reflective(self):
        """Reflective walls at 0 and L for each axis; simple elastic reflection."""
        for d in range(3):
            low = self.pos[:, d] < 0.0
            self.pos[low, d] *= -1.0
            self.vel[low, d] *= -1.0

            high = self.pos[:, d] >= self.L[d]
            self.pos[high, d] = 2.0*self.L[d] - self.pos[high, d]
            self.vel[high, d] *= -1.0

    def apply_periodic(self):
        self.pos = wrap_periodic(self.pos, self.L)

    def apply_lees_edwards_wrap(self):
        """Lees–Edwards shear periodicity with shear along x, gradient along y.
           We wrap y to [0,Ly) and shift x by +/- strain*Ly when crossing.
        """
        Ly = self.L[1]
        gamma_t = self.strain  # accumulated strain = gamma_dot * t
        # First wrap y
        y = self.pos[:,1]
        # Number of box crossings in y (could be multiple)
        ny = np.floor(y / Ly)
        # Adjust positions
        self.pos[:,1] = y - ny * Ly
        # Shift x according to crossings
        self.pos[:,0] += ny * gamma_t * Ly
        # Finally wrap x,z normally
        self.pos[:,0] = self.pos[:,0] - self.L[0]*np.floor(self.pos[:,0]/self.L[0])
        self.pos[:,2] = self.pos[:,2] - self.L[2]*np.floor(self.pos[:,2]/self.L[2])

    def lees_edwards_minimum_image(self, rij):
        """Minimum image considering shear offset between periodic images in y."""
        # Standard minimum image
        rij = rij - self.L * np.round(rij / self.L)
        # Apply shear correction for x when crossing y images
        Ly = self.L[1]
        gamma_t = self.strain
        # Compute how many y-boxes the vector crosses after min-image rounding
        ny = np.round(rij[1] / Ly)
        rij[0] -= ny * gamma_t * Ly
        return rij

    # ------- Pair mixing -------

    def pair_sigma_eps(self, i, j):
        si = self.species[i]; sj = self.species[j]
        # Base per-particle sigma (already polydisperse)
        sig_i = self.sigma_p[i]; sig_j = self.sigma_p[j]
        # Species-level epsilon (interaction strength)
        eps_i = self.sp[si].get("epsilon", 1.0)
        eps_j = self.sp[sj].get("epsilon", 1.0)

        if self.sig_mat_override is not None:
            sigma_ij = self.sig_mat_override[si, sj]
        else:
            sigma_ij = mix_sigma(sig_i, sig_j, self.mix_sigma_rule)

        if self.eps_mat_override is not None:
            eps_ij = self.eps_mat_override[si, sj]
        else:
            eps_ij = mix_epsilon(eps_i, eps_j, self.mix_eps_rule)
        return sigma_ij, eps_ij

    # ------- Forces -------

    @nb.njit(parallel=True, fastmath=True)
    def compute_forces_numba(self, positions, forces, box, cutoff, skin, cell_size, head, linked_list, num_cells,
                             pair_params):
        N, dim = positions.shape
        forces[:] = 0.0

        # loop over cells
        for cx in range(num_cells[0]):
            for cy in range(num_cells[1]):
                for cz in range(num_cells[2]):
                    cell_index = cx + num_cells[0] * (cy + num_cells[1] * cz)
                    i = head[cell_index]

                    while i != -1:
                        xi = positions[i]

                        # check neighbors in this + adjacent cells
                        for dx in (-1, 0, 1):
                            for dy in (-1, 0, 1):
                                for dz in (-1, 0, 1):
                                    nx = (cx + dx + num_cells[0]) % num_cells[0]
                                    ny = (cy + dy + num_cells[1]) % num_cells[1]
                                    nz = (cz + dz + num_cells[2]) % num_cells[2]
                                    ncell = nx + num_cells[0] * (ny + num_cells[1] * nz)

                                    j = head[ncell]
                                    while j != -1:
                                        if j > i:
                                            rij = positions[j] - xi

                                            # minimum image convention
                                            for d in range(dim):
                                                if rij[d] > 0.5 * box[d]:
                                                    rij[d] -= box[d]
                                                elif rij[d] < -0.5 * box[d]:
                                                    rij[d] += box[d]

                                            r2 = rij[0] ** 2 + rij[1] ** 2 + rij[2] ** 2
                                            if r2 < cutoff ** 2:
                                                r = np.sqrt(r2)
                                                sigma, epsilon = pair_params
                                                fmag = 48 * epsilon * (
                                                            (sigma ** 12 / r ** 13) - 0.5 * (sigma ** 6 / r ** 7))
                                                fij = fmag * rij / r
                                                forces[i] += fij
                                                forces[j] -= fij
                                        j = linked_list[j]
                        i = linked_list[i]

    def compute_forces(self):
        F = np.zeros_like(self.pos)

        # Pair interactions
        if self.nl.needs_rebuild(self.pos):
            self.nl.build(self.pos)

        for i, j, rij, r in self.nl.pairs(self.pos):
            # Cutoff check
            if r >= self.cutoff or r < 1e-12:
                continue

            # Lees–Edwards correction for displacement if needed
            if self.boundary == "lees_edwards":
                rij = self.lees_edwards_minimum_image(rij)
                r = np.linalg.norm(rij)

            sigma_ij, eps_ij = self.pair_sigma_eps(i, j)

            if self.pair_model == "LJ":
                fm = lj_force_mag(r, eps_ij, sigma_ij)
            elif self.pair_model == "spring_coulomb":
                # Species-pair overrides for k, r0, alpha (optional), else defaults
                si = self.species[i]; sj = self.species[j]
                k_ij = np.sqrt(self.sp[si].get("k",10.0) * self.sp[sj].get("k",10.0))
                r0_ij = mix_sigma(self.sp[si].get("r0",1.0), self.sp[sj].get("r0",1.0))
                alpha_ij = np.sqrt(self.sp[si].get("alpha",1.0) * self.sp[sj].get("alpha",1.0))
                fm = spring_coulomb_force_mag(r, k_ij, r0_ij, alpha_ij)
            else:
                raise ValueError("Unknown pair_model")

            fij = (fm / r) * rij
            F[i] -= fij
            F[j] += fij

        # Gravity and buoyancy
        if np.linalg.norm(self.g) > 0:
            # Estimate particle volume from sigma: interpret sigma as "diameter"
            radius = 0.5 * self.sigma_p
            volume = (4.0/3.0) * np.pi * radius**3
            # Effective force = (rho_p - rho_f) * V * g
            rho_p_local = np.array([self.sp[s].get("density", 1.0) for s in self.species])
            buoy = ((rho_p_local - self.rho_f) * volume)[:, None] * self.g[None, :]
            F += buoy

        return F

    # ------- Integrator (Langevin + background flow) -------

    def step(self):
        dt = self.dt
        # background Couette flow u = gamma_dot * y * ex
        u_bg = np.zeros_like(self.pos)
        if self.shear_rate != 0.0:
            u_bg[:,0] = self.shear_rate * self.pos[:,1]

        # Draw noises (per component)
        noise1 = self.noise_scale[:, None] * self.rng.normal(size=self.pos.shape) * np.sqrt(dt)
        noise2 = self.noise_scale[:, None] * self.rng.normal(size=self.pos.shape) * np.sqrt(dt)

        # Forces at t
        F = self.compute_forces()

        # Half-kick with drag to background + noise
        # dv = (F/m - gamma*(v - u_bg)) * dt/2 + noise/m * 1/2
        invm = 1.0 / self.mass[:, None]
        self.vel = ( self.vel * (1.0 - 0.5 * self.gamma[:,None] * dt)
                    + 0.5 * dt * (F * invm)
                    + 0.5 * (noise1 * invm)
                    + 0.5 * self.gamma[:,None] * dt * u_bg )

        # Drift
        self.pos += dt * self.vel

        # Boundaries
        if self.boundary == "periodic":
            self.apply_periodic()
        elif self.boundary == "reflective":
            self.apply_reflective()
        elif self.boundary == "lees_edwards":
            # advance accumulated strain
            self.strain += self.shear_rate * dt
            self.apply_lees_edwards_wrap()
        else:
            raise ValueError("Unknown boundary type")

        # Recompute forces
        F_new = self.compute_forces()

        # Second half-kick
        self.vel = ( self.vel * (1.0 - 0.5 * self.gamma[:,None] * dt)
                    + 0.5 * dt * (F_new * invm)
                    + 0.5 * (noise2 * invm)
                    + 0.5 * self.gamma[:,None] * dt * u_bg )

    def run(self, steps, sample_every=None):
        samples = []
        for k in range(steps):
            self.step()
            if sample_every and (k % sample_every == 0):
                samples.append(self.pos.copy())
        return np.array(samples) if samples else None

# ================================
# Example usage
# ================================

def demo():
    rng = np.random.default_rng(4)
    N = 600
    L = np.array([20.0, 12.0, 12.0])

    # Two-species mixture with polydispersity
    species = np.zeros(N, dtype=int)
    species[N//2:] = 1

    # Base positions/velocities
    pos = rng.random((N,3)) * L
    vel = rng.normal(0, 0.05, size=(N,3))

    # Species parameters
    # Interpret sigma as particle diameter (for cutoff + buoyancy volume)
    species_params = {
        0: dict(
            mass=1.0, gamma=1.0, kT=1.0,
            sigma=1.0, sigma_scale=1.0,
            epsilon=1.0,  # for LJ
            density=1.2,  # particle density for buoyancy
            # spring-coulomb (if used)
            k=10.0, r0=1.0, alpha=1.5,
        ),
        1: dict(
            mass=2.0, gamma=1.5, kT=0.5,
            sigma=1.2, sigma_scale=1.0,
            epsilon=0.8,
            density=0.8,
            k=8.0, r0=1.1, alpha=1.0,
        )
    }

    # Optional override matrices (species-by-species); here we leave None to use mixing rules
    epsilon_matrix = None
    sigma_matrix = None

    sim = SuspensionSim(
        positions=pos,
        velocities=vel,
        species=species,
        species_params=species_params,
        box_lengths=L,
        dt=0.002,
        cutoff=2.5,              # LJ cutoff ~ 2.5*sigma (using mixed sigma in practice)
        skin=0.4,
        pair_model="LJ",         # or "spring_coulomb"
        mixing_rules=("lorentz","berthelot"),
        epsilon_matrix=epsilon_matrix,
        sigma_matrix=sigma_matrix,
        boundary="lees_edwards", # "periodic", "reflective", "lees_edwards"
        shear_rate=0.2,          # background flow rate & LE
        gravity=(0.0, 0.0, -0.5),
        fluid_density=1.0,
        seed=42
    )

    # Run and sample
    samples = sim.run(steps=1, sample_every=None)
    # Return final state and a few snapshots for visualization elsewhere
    return sim.pos, sim.vel, samples

if __name__ == "__main__":
    p, vel, samp = demo()
    print("Final COM:", np.mean(p, axis=0))
    print("Vel stats: mean |v| =", np.mean(np.linalg.norm(vel, axis=1)))
