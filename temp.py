import numpy as np

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

Nx, Ny = 200, 200
dx = 0.01
dt = 0.00002
c = 343
damping = 0.001
frequency = 1000  # Hz

# Stability condition
assert c * dt / dx < 1 / np.sqrt(2), "Unstable starting conditions"

p = np.zeros((Nx, Ny))
p_prev = np.zeros_like(p)

# Initial pulse (center)
cx, cy = Nx // 2, Ny // 2
p[cx, cy] = 1.0


def laplacian(pressure: np.ndarray):
    return (
            np.roll(pressure, 1, axis=0) + np.roll(pressure, -1, axis=0) +
            np.roll(pressure, 1, axis=1) + np.roll(pressure, -1, axis=1) -
            4 * pressure
    ) / dx ** 2


# for step in range(300):
#     p_next = 2*p - p_prev + (c**2)*(dt**2)*laplacian(p)
#
#     p_prev, p = p, p_next
#
#     if step % 20 == 0:
#         plt.imshow(p, cmap='seismic')
#         plt.title(f"Step {step}")
#         plt.colorbar()
#         plt.show()


app = pg.mkQApp("ImageItem Example")

## Create window with GraphicsView widget
win = pg.GraphicsLayoutWidget()
win.show()  ## show widget alone in its own window
win.setWindowTitle('pyqtgraph example: ImageItem')
view = win.addViewBox()

## lock the aspect ratio so pixels are always square
view.setAspectLocked(True)

## Create image item
img = pg.ImageItem(border='w')
img.setColorMap("viridis")
view.addItem(img)

## Create random image
i = 0

src1 = (Nx//3, Ny//2)
src2 = (2*Nx//3, Ny//2)

mask = np.zeros((Nx, Ny), dtype=bool)
mask[80:120, 100] = True  # vertical wall

def updateData():
    global i, p, p_prev

    # if i == 300:
    #     p[cx, cy] = 1.0
    #     i = 0

    t = i * dt
    # source
    p[src1] += np.sin(2 * np.pi * frequency * t)
    # p[src2] += np.sin(2 * np.pi * frequency * t)

    # p_next = 2 * p - p_prev + (c ** 2) * (dt ** 2) * laplacian(p)
    p_next = (2 - damping) * p - (1 - damping) * p_prev + (c ** 2) * (dt ** 2) * laplacian(p)
    p_prev, p = p, p_next

    # a reflective boundary
    # p_next[mask] = 0

    ## Display the data
    img.setImage(p)
    i = i + 1


timer = QtCore.QTimer()
timer.setSingleShot(False)
timer.timeout.connect(updateData)
timer.start(16)

if __name__ == '__main__':
    pg.exec()
