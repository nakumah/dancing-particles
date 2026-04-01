import freetype
import numpy as np
from OpenGL.GL import *

class FontRenderer:
    def __init__(self, font_path: str, font_size: int = 48):
        self.face = freetype.Face(font_path)
        self.face.set_pixel_sizes(0, font_size)
        self.chars = {}

    def loadCharacters(self):
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)  # disable byte-alignment restriction

        for c in range(128):  # ASCII
            self.face.load_char(chr(c))
            bitmap = self.face.glyph.bitmap
            width, height = bitmap.width, bitmap.rows
            data = bitmap.buffer

            tex_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RED,
                         width, height, 0,
                         GL_RED, GL_UNSIGNED_BYTE, data)

            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            self.chars[chr(c)] = {
                "tex": tex_id,
                "size": (width, height),
                "bearing": (self.face.glyph.bitmap_left, self.face.glyph.bitmap_top),
                "advance": self.face.glyph.advance.x
            }

        glBindTexture(GL_TEXTURE_2D, 0)


class TextRenderer:
    def __init__(self, font: FontRenderer, shader: int = None):
        self.font = font
        self.shader = shader

        self.vao = None
        self.vbo = None

    def primeGL(self):
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, 6 * 4 * 4, None, GL_DYNAMIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(0))

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def renderText(self, text, pos, scale, color, mvp):
        if self.shader is None:
            return

        glUseProgram(self.shader)

        # uniforms
        glUniform3f(glGetUniformLocation(self.shader, "textColor"), *color)
        glUniformMatrix4fv(glGetUniformLocation(self.shader, "u_mvp"), 1, GL_FALSE, mvp)

        glActiveTexture(GL_TEXTURE0)
        glBindVertexArray(self.vao)

        x, y, z = pos
        for c in text:
            ch = self.font.chars[c]

            xpos = x + ch["bearing"][0] * scale
            ypos = y - (ch["size"][1] - ch["bearing"][1]) * scale
            w = ch["size"][0] * scale
            h = ch["size"][1] * scale

            vertices = np.array([
                [xpos,     ypos + h, z, 0.0],
                [xpos,     ypos,     z, 1.0],
                [xpos + w, ypos,     z, 1.0],

                [xpos,     ypos + h, z, 0.0],
                [xpos + w, ypos,     z, 1.0],
                [xpos + w, ypos + h, z, 0.0]
            ], dtype=np.float32)

            glBindTexture(GL_TEXTURE_2D, ch["tex"])
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
            glBufferSubData(GL_ARRAY_BUFFER, 0, vertices.nbytes, vertices)

            glDrawArrays(GL_TRIANGLES, 0, 6)

            x += (ch["advance"] >> 6) * scale  # advance.x in 1/64 pixels

        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)

    def setShader(self, s: int):
        self.shader = s
