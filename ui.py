import numpy as np
import moderngl
import pygame
import glm


class GUIButton:
    """Renders a 2D UI text or color button using ModernGL."""

    def __init__(self, ctx, text=None, font=None, rect=None, bg_color=(50, 50, 50, 200), fg_color=(255, 255, 255)):
        self.ctx = ctx
        self.rect = pygame.Rect(rect) if rect else None
        self.texture = None

        if text and font:
            text_surf = font.render(text, True, fg_color)
            tw, th = text_surf.get_size()
            padding = 20
            surf = pygame.Surface((tw + padding * 2, th + padding * 2), pygame.SRCALPHA)
            surf.fill(bg_color)
            surf.blit(text_surf, (padding, padding))

            self.width, self.height = surf.get_size()
            data = pygame.image.tobytes(surf, "RGBA", True)
            self.texture = self.ctx.texture((self.width, self.height), 4, data)

        vshader = """
        #version 330
        in vec2 in_vert;
        in vec2 in_uv;
        out vec2 v_uv;
        uniform mat4 u_proj;
        uniform float scale;
        uniform vec2 offset;
        void main() {
            gl_Position = u_proj * vec4(in_vert * scale + offset, 0.0, 1.0);
            v_uv = in_uv;
        }
        """

        fshader = """
        #version 330
        in vec2 v_uv;
        uniform sampler2D Texture;
        uniform float percent;
        out vec4 f_color;
        void main() {
            f_color = texture(Texture, v_uv);
            if (1.0 - v_uv.x < percent) f_color *= 0.5;
        }
        """

        vertices = np.array([
            -0.75, -0.5, 0.0, 0.0,
             0.75, -0.5, 1.0, 0.0,
            -0.75,  0.5, 0.0, 1.0,
             0.75,  0.5, 1.0, 1.0
        ], dtype=np.float32)

        indices = np.array([0, 1, 2, 3], dtype=np.int32)

        self.shader = ctx.program(vertex_shader=vshader, fragment_shader=fshader)
        self.vbo = ctx.buffer(vertices.tobytes())
        self.ibo = ctx.buffer(indices.tobytes())
        self.vao = ctx.vertex_array(self.shader, [(self.vbo, "2f 2f", "in_vert", "in_uv")], index_buffer=self.ibo)

    def render(self, offset=(0, 0), scale=0.2, percent=0.0, texture_unit=7):
        if self.texture:
            self.texture.use(texture_unit)
            self.shader["Texture"].value = texture_unit

        self.shader["u_proj"].write(glm.ortho(-1.5, 1.5, -1, 1, -1, 1).to_bytes())
        self.shader["scale"].value = scale
        self.shader["percent"].value = percent
        self.shader["offset"].value = offset
        self.vao.render(moderngl.TRIANGLE_STRIP)

    def is_hovered(self, ortho_x, ortho_y, offset, scale=0.2):
        half_w = 0.75 * scale
        half_h = 0.5 * scale
        return (offset[0] - half_w <= ortho_x <= offset[0] + half_w) and \
               (offset[1] - half_h <= ortho_y <= offset[1] + half_h)

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos) if self.rect else False


class GUIImage:
    """Renders a standalone 2D image texture in screen space."""

    def __init__(self, ctx, screen_width, screen_height, rect, image_path):
        self.ctx = ctx
        self.rect = pygame.Rect(rect)

        x1 = (self.rect.left / screen_width) * 2 - 1
        y1 = 1 - (self.rect.top / screen_height) * 2
        x2 = (self.rect.right / screen_width) * 2 - 1
        y2 = 1 - (self.rect.bottom / screen_height) * 2

        vertices = np.array([
            x1, y1, 0.0, 0.0,
            x2, y1, 1.0, 0.0,
            x1, y2, 0.0, 1.0,
            x2, y2, 1.0, 1.0,
        ], dtype=np.float32)

        vshader = """
        #version 330
        in vec2 in_position;
        in vec2 in_uv;
        out vec2 uv;
        void main() {
            uv = in_uv;
            gl_Position = vec4(in_position, 0.0, 1.0);
        }
        """

        fshader = """
        #version 330
        in vec2 uv;
        out vec4 fragColor;
        uniform sampler2D u_texture;
        void main() {
            fragColor = texture(u_texture, uv);
        }
        """

        self.prog = self.ctx.program(vertex_shader=vshader, fragment_shader=fshader)
        self.vbo = self.ctx.buffer(vertices.tobytes())
        self.vao = self.ctx.vertex_array(self.prog, [(self.vbo, "2f 2f", "in_position", "in_uv")])

        img = pygame.image.load(image_path).convert_alpha()
        img_data = pygame.image.tobytes(img, "RGBA", True)
        self.texture = self.ctx.texture(img.get_size(), 4, img_data)

    def render(self):
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        self.texture.use(0)
        self.prog["u_texture"] = 0
        self.vao.render(moderngl.TRIANGLE_STRIP)

        self.ctx.enable(moderngl.DEPTH_TEST)