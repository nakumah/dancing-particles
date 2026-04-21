import numpy as np
import matplotlib.pyplot as plt

# Parameters
L = 10.0      # Domain length
T = 5.0       # Total time
nx = 100      # Number of spatial points
v = 1.0       # Wave speed
dx = L / (nx - 1)
dt = 0.05     # Time step (must satisfy CFL condition: v * dt / dx <= 1)

# Stability check (CFL condition)
cfl = v * dt / dx
print(f"CFL Number: {cfl}")

# Grid and Initial Conditions
x = np.linspace(0, L, nx)
u = np.zeros(nx)      # current time step (n)
u_old = np.zeros(nx)  # previous time step (n-1)
u_new = np.zeros(nx)  # next time step (n+1)

# Initial pulse (Gaussian)
u = np.exp(-0.5 * ((x - 5.0) / 0.5)**2)
u_old = np.copy(u) # Assume zero initial velocity for simplicity

# Time-stepping loop
steps = int(T / dt)
for n in range(steps):
    # Finite Difference Approximation (Central Difference)
    for i in range(1, nx - 1):
        u_new[i] = 2*u[i] - u_old[i] + (cfl**2) * (u[i+1] - 2*u[i] + u[i-1])

    # Boundary Conditions (Dirichlet: u=0 at ends)
    u_new[0] = 0
    u_new[-1] = 0

    # Update buffers
    u_old = np.copy(u)
    u = np.copy(u_new)

# Result visualization logic (internal)
plt.plot(x, u)
plt.title("1D Wave Propagation (Finite Difference)")
plt.xlabel("Position")
plt.ylabel("Amplitude")
plt.show()
