import pygame
import moderngl
import glm
import numpy as np
import render
import game
import tower


class GUIButton:
    """Renders a 2D interactive screen-space green button with procedural play icon."""
    def __init__(self, ctx, screen_width, screen_height, rect):
        self.ctx = ctx
        self.rect = pygame.Rect(rect)
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Convert screen pixel coordinates to Normalized Device Coordinates (-1..1)
        x1 = (self.rect.left / screen_width) * 2 - 1
        y1 = 1 - (self.rect.top / screen_height) * 2
        x2 = (self.rect.right / screen_width) * 2 - 1
        y2 = 1 - (self.rect.bottom / screen_height) * 2

        vertices = np.array([
            x1, y1, 0.0, 0.0,
            x2, y1, 1.0, 0.0,
            x1, y2, 0.0, 1.0,
            x2, y2, 1.0, 1.0,
        ], dtype='f4')

        vertex_shader = """
        #version 330
        in vec2 in_position;
        in vec2 in_uv;
        out vec2 uv;
        void main() {
            uv = in_uv;
            gl_Position = vec4(in_position, 0.0, 1.0);
        }
        """

        fragment_shader = """
        #version 330
        in vec2 uv;
        out vec4 fragColor;
        uniform vec4 u_color;

        void main() {
            vec4 col = u_color;
            vec2 p = (uv - vec2(0.6, 0.4)) * vec2(-2.2, 1.33);
            if (p.x > 0.0 && p.y > -p.x * 0.8 && p.y < p.x * 0.8 && p.x < 0.5) {
                col = vec4(1.0, 1.0, 1.0, 1.0);
            }
            fragColor = col;
        }
        """

        self.prog = self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader
        )

        self.vbo = self.ctx.buffer(vertices.tobytes())
        self.vao = self.ctx.vertex_array(
            self.prog,
            [(self.vbo, '2f 2f', 'in_position', 'in_uv')]
        )

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

    def render(self, is_hovered=False):
        self.ctx.disable(moderngl.DEPTH_TEST)
        color = (0.2, 0.8, 0.3, 1.0) if is_hovered else (0.1, 0.5, 0.2, 1.0)
        self.prog['u_color'] = color
        self.vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.enable(moderngl.DEPTH_TEST)


class GUIImage:
    """Renders a standalone 2D image texture anywhere on the screen in screen space."""
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
        ], dtype='f4')

        vertex_shader = """
        #version 330
        in vec2 in_position;
        in vec2 in_uv;
        out vec2 uv;
        void main() {
            uv = in_uv;
            gl_Position = vec4(in_position, 0.0, 1.0);
        }
        """

        fragment_shader = """
        #version 330
        in vec2 uv;
        out vec4 fragColor;
        uniform sampler2D u_texture;

        void main() {
            fragColor = texture(u_texture, uv);
        }
        """

        self.prog = self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader
        )

        self.vbo = self.ctx.buffer(vertices.tobytes())
        self.vao = self.ctx.vertex_array(
            self.prog,
            [(self.vbo, '2f 2f', 'in_position', 'in_uv')]
        )

        img = pygame.image.load(image_path).convert_alpha()
        img_data = pygame.image.tobytes(img, 'RGBA', True)
        self.texture = self.ctx.texture(img.get_size(), 4, img_data)

    def render(self):
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        self.texture.use(0)
        self.prog['u_texture'] = 0
        self.vao.render(moderngl.TRIANGLE_STRIP)

        self.ctx.enable(moderngl.DEPTH_TEST)


# Initialize Pygame & ModernGL
pygame.init()
WIDTH, HEIGHT = 960, 640
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
ctx = moderngl.get_context()

# Engine Pipelines
renderer = render.Renderer(ctx, WIDTH, HEIGHT)
game.init(ctx, renderer)

# Floor Geometry Setup
floor_verts = [
    -10.0, -0.0, -8.0,  0.8, 0.8, 0.8,  0.0, 0.0,
     10.0, -0.0, -8.0,  0.8, 0.8, 0.8,  10.0, 0.0,
    -4.0, -0.0,  8.0,  0.8, 0.8, 0.8,  3.0, 16.0,
     4.0, -0.0,  8.0,  0.8, 0.8, 0.8,  7.0, 16.0,
]
floor_indices = [0, 1, 2, 2, 1, 3]

game.fighters.init(ctx, renderer)
tower.init(ctx, renderer)

Z = renderer.create_object(floor_verts, floor_indices)
Z.spritesheet = render.SpriteSheet(ctx, "assets/grass.png", 1, 1)

# Tower Units
Enemy_Tower = tower.Tower_As_Fighter(glm.vec3(0, 0, -3.5), 1)
game.peoples.append(Enemy_Tower)
Player_Tower = tower.Tower_As_Fighter(glm.vec3(0, 0, 3.5), 0)
game.peoples.append(Player_Tower)

Enemy_tower_renderobject_copy = Enemy_Tower.renderObject.duplicate()
Player_tower_renderobject_copy = Player_Tower.renderObject.duplicate()
peeps = game.peoples.copy()
clock = pygame.time.Clock()
t_acc = 0.0

lineup = ["Debug Unit", "Cannon", "", "", "", "", "", ""]
game.levels.init(ctx, renderer)

# Lowered Button Placement
play_button_rect = ((WIDTH - 220) // 2, HEIGHT - 160, 220, 90)
play_button = GUIButton(ctx, WIDTH, HEIGHT, play_button_rect)

popart_rect = ((WIDTH - 400) // 2, HEIGHT - 420, 400, 200)
popart_banner = GUIImage(ctx, WIDTH, HEIGHT, popart_rect, "assets/popart.png")

state = "MENU"

def LoadLevel(name, lineup):
    global state
    for z in game.peoples:
        if z not in peeps:
            z.free()
    game.peoples = peeps.copy()
    game.avoid = []
    
    game.levels.LoadLevelsFromJSON(name, game.peoples, Z, game.avoid)
    game.commitLineup(lineup)
    game.paused = False
    state = "PLAYING"

game.commitLineup(["Play"])
renderer.ambient = render.SpriteSheet(ctx, "assets/sky.png")

# Main Loop
while True:
    
    dt = clock.tick(60) / 1000.0
    t_acc += dt
    game.off = 0

    mouse_pos = pygame.mouse.get_pos()
    is_hovered = play_button.is_clicked(mouse_pos)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if state == "MENU" and is_hovered:
                
                LoadLevel("Dummy_Test", lineup)

        if event.type == pygame.MOUSEBUTTONUP:
            game.off = 1

    # Render World
    renderer.update(dt)
    # Render UI & State Updates
    if state == "PLAYING":
        
        result = game.update(dt)
        
        if result == "MENU":
            state = "MENU"
            for z in game.peoples:
                z.free()
            game.peoples = []
            
            game.peoples.insert(0, Enemy_Tower)
            Enemy_Tower.renderObject = Enemy_tower_renderobject_copy.duplicate()
            game.peoples.insert(0, Player_Tower)
            Player_Tower.renderObject = Player_tower_renderobject_copy.duplicate()
            Player_Tower.HP = 1000
            Enemy_Tower.HP = 1000
            renderer.scene_objects.append(Player_Tower.renderObject)
            renderer.scene_objects.append(Enemy_Tower.renderObject)
            game.victory = 0
    elif state == "MENU":
        popart_banner.render()
        play_button.render(is_hovered=is_hovered)

    pygame.display.flip()