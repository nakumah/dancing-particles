import numpy as np
from OpenGL.GL import *
from OpenGL.GLUT import (GLUT_BITMAP_HELVETICA_18)
from OpenGL.GL.shaders import compileProgram, compileShader
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

from core.app_colors import appColors
from models.camera import Camera
from models.structures import WaveDecay, RenderMode

VERTEX_SHADER = """
#version 330 core

layout(location = 0) in vec3 position;

// MVP matrix
uniform mat4 u_mvp;

// wave parameters
uniform int u_waveDecayMode;          // 1 = exponential, else inverse
uniform vec3 u_waveOrigin;            // wave center
uniform float u_waveFrequency;        // scalar radial frequency
uniform float u_waveAmplitude;        // initial amplitude
uniform float u_waveTimeStep;         // evolving time parameter
uniform float u_wavePhase;            // phase shift
uniform float u_waveDecayConstant;    // decay constant

// compute the decay factor over a distance
float decayAmplitude(float waveAmplitude, float distance, float decayConstant, int decayMode)
{
    if (decayMode == 1) {
        // exponential decay
        return waveAmplitude * exp(-decayConstant * distance);
    } else {
        // inverse decay
        return waveAmplitude / (1.0 + decayConstant * distance);
    }
}

void main()
{   
    // radial distance vector
    vec3 r_vec = position - u_waveOrigin;
    float r = length(r_vec);

    // normalize to direction
    vec3 r_hat = (r > 0.0) ? (r_vec / r) : vec3(0.0);

    // decayed amplitude
    float amp = decayAmplitude(u_waveAmplitude, r, u_waveDecayConstant, u_waveDecayMode);

    // oscillation
    float theta = r * u_waveFrequency - u_waveTimeStep + u_wavePhase;
    float wave = amp * sin(theta);

    // displace along radial direction
    vec3 displaced = position + wave * r_hat;

    gl_Position = u_mvp * vec4(displaced, 1.0);
}
"""

FRAGMENT_SHADER = """
#version 330 core

out vec4 FragColor;

uniform vec4 u_faceColor;
uniform vec4 u_edgeColor;
uniform int u_renderMode; // 0 = face, 1 = edge

void main()
{
     if (u_renderMode == 0) {
        FragColor = u_faceColor;
    } else {
        FragColor = u_edgeColor;
    }
}

"""


class Landscape(QObject):
    ready = Signal()

    def __init__(self, parent=None):
        super(Landscape, self).__init__(parent)

        self.__noiseAmplitude: float = 1.0
        self.__faceColor = QColor(appColors.dark_tint_rbg)
        self.__edgeColor = QColor(appColors.dark_rbg)
        self.__landscapeSize = 50
        self.__landscapeScale = 50
        self.__vertices: np.ndarray = self.__createLandscapeVertices(self.__landscapeSize, self.__landscapeScale)
        self.__faces: np.ndarray = self.__createLandscapeFaces(self.__vertices)
        self.__landscapeUpdateIndex = 0

        self.__slotGridIndex = self.__deriveSubGridIndices(40, 40)
        self.__slots = np.zeros((self.__slotGridIndex.shape[0], self.__slotGridIndex.shape[1]))
        self.__currentSlot = (0, 0)

        self.__waves = [
            # Longitudinal wave traveling along +Z, displacing along k (ripple)
            {'A': 0.3, 'k': [0, 0, 2 * np.pi / 8], 'omega': 5.0, 'phi': 0.0, 'dir': None, "decay": 0.2},
            # Transverse wave traveling along +X, displacing along +Y (flag-like)
            {'A': 0.8, 'k': [2 * np.pi / 12, 0, 0], 'omega': 8.0, 'phi': 0.5, 'dir': [0, 1, 0], "decay": 0.2},
        ]

        self.__timeStep = 1.0

        self.u_waveDecayMode = WaveDecay.INVERSE
        self.u_waveFrequency = 8.0
        self.u_waveOrigin = np.zeros(3)
        self.u_waveAmplitude = 3
        self.u_waveTimeStep = 1.0
        self.u_wavePhase = 0.0
        self.u_waveDecayConstant = 0.2

        self.shader = None
        self.VAO = None
        self.VBO = None
        self.EBO = None

    # region OpenGL

    def initializeGL(self):

        self.shader = compileProgram(
            compileShader(VERTEX_SHADER, GL_VERTEX_SHADER),
            compileShader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
        )

        vertices = self.glVertices()
        faces = self.glFaces()

        # VAO/VBO/EBO
        self.VAO = glGenVertexArrays(1)
        glBindVertexArray(self.VAO)

        self.VBO = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.VBO)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        self.EBO = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.EBO)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, faces.nbytes, faces, GL_STATIC_DRAW)

        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def draw(self, camera: Camera):
        glUseProgram(self.shader)

        # bind uniforms
        u_waveDecayMode = glGetUniformLocation(self.shader, "u_waveDecayMode")
        glUniform1i(u_waveDecayMode, self.u_waveDecayMode)

        u_waveFrequency = glGetUniformLocation(self.shader, "u_waveFrequency")
        glUniform1f(u_waveFrequency, self.u_waveFrequency + self.__noiseAmplitude)

        u_waveOrigin = glGetUniformLocation(self.shader, "u_waveOrigin")
        glUniform3f(u_waveOrigin, *self.u_waveOrigin)

        u_waveAmplitude = glGetUniformLocation(self.shader, "u_waveAmplitude")
        glUniform1f(u_waveAmplitude, self.u_waveAmplitude)

        u_waveTimeStep = glGetUniformLocation(self.shader, "u_waveTimeStep")
        glUniform1f(u_waveTimeStep, self.u_waveTimeStep)

        u_wavePhase = glGetUniformLocation(self.shader, "u_wavePhase")
        glUniform1f(u_wavePhase, self.u_wavePhase)

        u_waveDecayConstant = glGetUniformLocation(self.shader, "u_waveDecayConstant")
        glUniform1f(u_waveDecayConstant, self.u_waveDecayConstant)

        # camera
        mvp = camera.MVP_matrix().data()
        u_mvp = glGetUniformLocation(self.shader, "u_mvp")
        glUniformMatrix4fv(u_mvp, 1, GL_FALSE, mvp)

        # bind buffers
        glBindVertexArray(self.VAO)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.EBO)

        # Draw Faces
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glUniform1i(glGetUniformLocation(self.shader, "u_renderMode"), RenderMode.FACES)
        glUniform4f(glGetUniformLocation(self.shader, "u_faceColor"), *self.glFaceColor())
        glDrawElements(GL_TRIANGLES, self.__faces.size, GL_UNSIGNED_INT, None)

        # Wireframe mode
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glUniform1i(glGetUniformLocation(self.shader, "u_renderMode"), RenderMode.EDGES)
        glUniform4f(glGetUniformLocation(self.shader, "u_edgeColor"), *self.glEdgeColor())
        glDrawElements(GL_TRIANGLES, self.__faces.size, GL_UNSIGNED_INT, None)

        glBindVertexArray(0)

        # Reset polygon mode
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    # endregion

    # region workers

    def __deriveSubGridIndices(self, row: int, col: int) -> np.ndarray:
        size = self.__landscapeSize

        start = int(.5 * (size - row))
        _x = np.arange(start, start + row)

        start = int(.5 * (size - col))
        _y = np.arange(start, start + col)
        return np.dstack(np.meshgrid(_x, _y))

    def __createLandscapeFaces(self, vertices: np.ndarray) -> np.ndarray:
        assert vertices.ndim == 3
        assert vertices.shape[2] == 3

        arr = []
        rows, cols, _ = self.__vertices.shape

        for i in range(rows - 1):
            for j in range(cols - 1):
                v1 = i * rows + j
                v2 = v1 + 1
                v3 = (i + 1) * rows + j
                v4 = v3 + 1

                # Face 1: (i,j), (i+1,j), (i+1,j+1)
                # Face 2: (i,j), (i+1,j+1), (i,j+1)
                arr.append([v1, v2, v3])
                arr.append([v3, v2, v4])

        faces = np.array(arr, dtype=np.float32)
        return faces

    @staticmethod
    def __createLandscapeVertices(size: int, scale: float) -> np.ndarray:
        f = 1 * np.pi
        x = np.linspace(-scale, scale, size)
        z = np.linspace(-scale, scale, size)
        xx, zz = np.meshgrid(x, z)
        curve = 2 * np.log1p(np.linspace(1, scale, size))
        y = np.cos(f * z)
        yy = np.full(xx.shape, y).T * curve

        stack = np.dstack([xx, yy, zz])

        return stack  # shape (N, N, 3)

    def flagSlot(self, slot: tuple[int, int]) -> bool:
        try:
            self.__slots[slot[0], slot[1]] = 1
            return True
        except IndexError:
            return False

    def unflagSlot(self, slot: tuple[int, int]) -> bool:
        try:
            self.__slots[slot[0], slot[1]] = 0
            return True
        except IndexError:
            return False

    # endregion

    # region getters

    def getEmptySlot(self) -> tuple[int, int] | None:
        emptySlots = np.where(self.__slots == 0)
        rows, cols = emptySlots[0], emptySlots[1]
        if len(rows) == 0 or len(cols) == 0:
            return None

        rI = np.random.choice(len(rows))
        rJ = np.random.choice(len(cols))
        i, j = int(rows[rI]), int(cols[rJ])

        return i, j

    def getVertexAtSlot(self, slot: tuple[int, int]) -> np.ndarray:
        try:
            idx = self.__slotGridIndex[slot[0], slot[1]]
            vert = self.__vertices[idx[0], idx[1]]
        except IndexError:
            # if error, return midpoint
            i = j = int(self.__landscapeSize / 2)
            vert = self.__vertices[i, j]
        except Exception:
            # otherwise resolve center
            vert = np.zeros(3)

        return vert

    def vertices(self) -> np.ndarray:
        return self.__vertices

    def glVertices(self) -> np.ndarray:
        return self.__vertices.reshape(-1, 3).flatten().astype(np.float32)

    def glFaces(self) -> np.ndarray:
        return self.__faces.flatten().astype(np.uint32)

    def glFaceColor(self) -> np.ndarray:
        return np.array([
            self.__faceColor.redF(),
            self.__faceColor.greenF(),
            self.__faceColor.blueF(),
            self.__faceColor.alphaF(),
        ])

    def glEdgeColor(self) -> np.ndarray:
        return np.array([
            self.__edgeColor.redF(),
            self.__edgeColor.greenF(),
            self.__edgeColor.blueF(),
            self.__edgeColor.alphaF(),
        ])

    # endregion

    # region setters

    def setTimeStep(self, timeStep: float) -> None:
        self.__timeStep = timeStep
        self.u_waveTimeStep = timeStep

    def setNoiseAmplitude(self, amp: float) -> None:
        self.__noiseAmplitude = amp

    def setCurrentSlot(self, slot: tuple[int, int]) -> None:
        self.__currentSlot = slot
        self.u_waveOrigin = self.getVertexAtSlot(slot)
    # endregion
