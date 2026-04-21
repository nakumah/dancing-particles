import numpy as np
import matplotlib.pyplot as plt

# ======================
# 1. Domain parameters
# ======================
Nx = Ny = Nz = 60
L = 1.0  # meters
dx = L / Nx

c = 343.0  # speed of sound (m/s)
dt = 0.4 * dx / c  # CFL-safe timestep

# ======================
# 2. Fields
# ======================
p = np.zeros((Nx, Ny, Nz))
p_prev = np.zeros_like(p)

# ======================
# 3. Source (speaker)
# ======================
src = np.array([Nx//4, Ny//2, Nz//2])  # position

# Direction speaker is facing (unit vector)
direction = np.array([1.0, 0.0, 0.0])
direction = direction / np.linalg.norm(direction)

frequency = 800  # Hz

# ======================
# 4. Precompute direction mask
# ======================
dir_mask = np.zeros_like(p)

for i in range(Nx):
    for j in range(Ny):
        for k in range(Nz):
            r = np.array([i, j, k]) - src
            norm = np.linalg.norm(r)
            if norm > 0:
                r_hat = r / norm
                # directional emission (cosine lobe)
                dir_mask[i,j,k] = max(0, np.dot(r_hat, direction))

# ======================
# 5. Absorbing boundary (damping layer)
# ======================
damping = np.ones_like(p)

layer = 10  # thickness of absorbing region

for i in range(Nx):
    for j in range(Ny):
        for k in range(Nz):
            dist_to_edge = min(i, j, k, Nx-1-i, Ny-1-j, Nz-1-k)
            if dist_to_edge < layer:
                damping[i,j,k] = dist_to_edge / layer

# ======================
# 6. Laplacian
# ======================
def laplacian(p):
    return (
        np.roll(p, 1, 0) + np.roll(p, -1, 0) +
        np.roll(p, 1, 1) + np.roll(p, -1, 1) +
        np.roll(p, 1, 2) + np.roll(p, -1, 2) -
        6*p
    ) / dx**2

# ======================
# 7. Simulation loop
# ======================
steps = 400
slice_z = Nz // 2

for step in range(steps):
    t = step * dt

    # Source injection (directional speaker)
    amp = np.sin(2 * np.pi * frequency * t)
    p[src[0], src[1], src[2]] += amp

    # Wave update
    p_next = (
        2*p - p_prev +
        (c**2)*(dt**2)*laplacian(p)
    )

    # Apply directional spreading
    p_next *= dir_mask + 0.2  # keep some baseline energy

    # Apply damping (absorbing boundaries + dissipation)
    p_next *= damping
    p_next *= 0.999  # global dissipation

    # Step forward
    p_prev, p = p, p_next

    # ======================
    # Visualization
    # ======================
    if step % 10 == 0:
        plt.clf()
        plt.imshow(p[:, :, slice_z], cmap='seismic', vmin=-0.01, vmax=0.01)
        plt.title(f"Step {step}")
        plt.colorbar(label="Pressure")
        plt.pause(0.01)

plt.show()