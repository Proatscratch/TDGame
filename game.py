import numpy
import pygame, moderngl, glm, combat
import fighters
import render
import levels
import json as JSON

peoples: list[fighters.Fighter] = []
projectiles: list[fighters.Projectile] = []

vertex = numpy.array([-0.75, -0.5, 0.0, 0.0,
                      0.75, -0.5, 1.0, 0.0,
                      -0.75, 0.5, 0.0, 1.0,
                      0.75, 0.5, 1.0, 1.0], dtype=numpy.float32)

indices = numpy.array([0, 1, 2, 3], dtype=numpy.int32)
off = 0
paused = False  # Pause state flag

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
out vec4 f_color;
uniform float percent;
void main() {
    f_color = texture(Texture, v_uv);
    if (1-v_uv.x < percent) f_color *= 0.5;
}
"""
#TODO: unify GUI BUTTON in one file.
class GUIButton:
    """Helper class to render simple 2D UI text buttons using Pygame fonts and ModernGL textures."""
    def __init__(self, ctx, text, font, bg_color=(50, 50, 50, 200), fg_color=(255, 255, 255)):
        self.ctx = ctx
        text_surf = font.render(text, True, fg_color)
        tw, th = text_surf.get_size()
        padding = 20
        
        # Draw background surface
        surf = pygame.Surface((tw + padding * 2, th + padding * 2), pygame.SRCALPHA)
        surf.fill(bg_color)
        surf.blit(text_surf, (padding, padding))
        
        w, h = surf.get_size()
        data = pygame.image.tobytes(surf, 'RGBA', True)
        self.texture = self.ctx.texture((w, h), 4, data)
        self.width = w
        self.height = h

    def render(self, shader, vao, offset, scale=0.2):
        self.texture.use(7)
        shader['Texture'].value = 7
        shader['u_proj'].write(glm.ortho(-1.5, 1.5, -1, 1, -1, 1).to_bytes())
        shader['scale'].value = scale
        shader['percent'].value = 0
        shader['offset'].value = offset
        vao.render(moderngl.TRIANGLE_STRIP)

    def is_hovered(self, ortho_x, ortho_y, offset, scale=0.2):
        half_w = 0.75 * scale
        half_h = 0.5 * scale
        min_x = offset[0] - half_w
        max_x = offset[0] + half_w
        min_y = offset[1] - half_h
        max_y = offset[1] + half_h
        return min_x <= ortho_x <= max_x and min_y <= ortho_y <= max_y


def init(ctxs, rend):
    global vbo, ibo, vao, ctx, shader, empty_texture, cache, renderer, Arial, avoid, paused
    global btn_pause, btn_resume, btn_leave, btn_defeat, btn_victory
    avoid = []
    paused = False

    renderer = rend
    ctx = ctxs
    vbo = ctx.buffer(data=vertex.tobytes())
    ibo = ctx.buffer(data=indices.tobytes())
    shader = ctx.program(vertex_shader=vshader, fragment_shader=fshader)
    vao = ctx.vertex_array(shader, [(vbo, '2f 2f', 'in_vert', 'in_uv')], index_buffer=ibo)
    
    surf = pygame.image.load("assets/spawner.png").convert_alpha()
    w, h = surf.get_size()
    data = pygame.image.tobytes(surf, 'RGBA', True)
    empty_texture = ctx.texture((w, h), 4, data)
    cache = {"": empty_texture}
    Arial = pygame.font.SysFont("Arial", 64, 1)

    # Initialize UI buttons
    btn_pause = GUIButton(ctx, " || ", Arial, bg_color=(40, 40, 40, 220), fg_color=(255, 255, 255))
    btn_resume = GUIButton(ctx, "Resume", Arial, bg_color=(30, 140, 30, 230), fg_color=(255, 255, 255))
    btn_leave = GUIButton(ctx, "Leave", Arial, bg_color=(160, 30, 30, 230), fg_color=(255, 255, 255))

    
    btn_victory = GUIButton(ctx, "Victory!", Arial, bg_color=(255, 255, 30, 230), fg_color=(255, 255, 255))
    btn_defeat = GUIButton(ctx, "Defeat...", Arial, bg_color=(30, 0, 30, 230), fg_color=(255, 255, 255))

lineup = []

def SCALEBLIT(surf, cost):
    surf = pygame.transform.scale_by(surf, 5)
    surf.blit(Arial.render('$' + str(cost), 0, (0, 0, 0)), (2, 2))
    return surf

def commitLineup(lineupS):
    global lineup
    json_data = [fighters.LoadFightersFromJSON(S) if S != "" else fighters.json.dumps({}) for S in lineupS]
    i = -1
    tshape = {}
    for k in lineupS:
        i += 1
        tshape[k] = fighters.QUAD
        if k == '':
            continue
        mesh = 0
        s = json_data[i]["texture"]
        if s[:5] == 'Mesh.':
            mesh = 1
            s = s[5:]
        if mesh:
            with open((f"assets/{s}/using.json")) as F:
                mem = JSON.load(F)
                tshape[k] = renderer.create_object(mem["Verts"], mem["Index"])
                if s == "Cannon":
                    tshape[k].scale /= 3
                    tshape[k].INNER.y += 0.125
                renderer.scene_objects.remove(tshape[k])

        if k not in cache:
            SpriteSheet = fighters.GenerateSpriteSheets(ctx, f"assets/{s}/", gfunc=SCALEBLIT, cost=json_data[i]["Cost"])[3].frames[0]
            cache[k] = SpriteSheet
            
    lineup = [[z, cache[z], 0.2, 0, fighters.LoadFightersFromJSON(z)["Recharge"] if z != "" else 0, fighters.LoadFightersFromJSON(z)["Cost"] if z != "" else "", tshape[z]] for z in lineupS]

money = 50
selected = None
R = 0

def get_mouse_pos():
    mouse_x, mouse_y = pygame.mouse.get_pos()
    window_w, window_h = ctx.screen.size
    ortho_x = (mouse_x / window_w) * 3.0 - 1.5
    ortho_y = 1.0 - (mouse_y / window_h) * 2.0
    return mouse_x, mouse_y, ortho_x, ortho_y

def can_place_unit(world_space_pos):
    for obs in avoid:
        if combat.is_point_inside_shape(world_space_pos, obs):
            return False
    return world_space_pos.z > 0

def place_selected_unit(dt, z):
    global selected, money, R
    mouse_x, mouse_y, _, _ = get_mouse_pos()
    if mouse_y > 639:
        mouse_y = 639

    mouse_vec = glm.vec2(mouse_x, mouse_y)
    screen_size = glm.vec2(960, 640)
    
    NDC = (mouse_vec / screen_size) * 2.0 - glm.vec2(1.0, 1.0)
    NDC.y = -NDC.y

    DNDC = glm.vec2(glm.inverse(glm.ortho(-1.5, 1.5, -1, 1, -1, 1)) * glm.vec4(NDC, 1.0, 1.0))
    offset_x = DNDC.x
    offset_y = DNDC.y

    inv_VP = glm.inverse(renderer.projection_matrix * renderer.view_matrix)
    near_4d = inv_VP * glm.vec4(NDC, -1.0, 1.0)
    far_4d  = inv_VP * glm.vec4(NDC, 1.0, 1.0)

    near_world = glm.vec3(near_4d) / near_4d.w
    far_world  = glm.vec3(far_4d)  / far_4d.w
    direction = far_world - near_world
    
    if abs(direction.y) > 0.0001:
        t = -near_world.y / direction.y
        world_space_pos = near_world + t * direction
    else:
        world_space_pos = near_world

    shader['scale'].value = 0.2 / (NDC.y * 2 + 2)
    
    for obs in avoid:
        if combat.is_point_inside_shape(world_space_pos, obs):
            world_space_pos.z = -1

    if world_space_pos.z < 0:
        shader["percent"] = 1

    if off and selected:
        if world_space_pos.z > 0:
            if not R:
                world_space_pos = glm.vec3(0, 0, 4)
            R = 0
            peoples.append(fighters.GenerateFighter(selected[0], world_space_pos, 0))
            peoples[-1].renderObject = lineup[z][6].duplicate()
            renderer.scene_objects.append(peoples[-1].renderObject)
            peoples[-1].update(dt, [], [], [])
            peoples[-1].animation = fighters.IDLE
            selected[3] = selected[4]
            money -= selected[5]
            selected = None
    elif off and selected:
        selected = None
        R = 0

    return offset_x, offset_y

def update_selected_unit(dt, z):
    return place_selected_unit(dt, z)

def update_tower_menu(dt):
    global selected, R
    _, _, ortho_x, ortho_y = get_mouse_pos()
    scale = 0.2
    half_width = 0.75 * scale
    half_height = 0.5 * scale

    ctx.screen.use()
    ctx.disable(moderngl.DEPTH_TEST)

    for z in range(min(8, len(lineup))):
        if not paused:
            lineup[z][3] -= dt
        offset_x = (z % 4 / 4 - 0.5 + 0.5 / 4) * 2
        offset_y = -0.5 - 0.25 * (z // 4)
        
        min_x = offset_x - half_width
        max_x = offset_x + half_width
        min_y = offset_y - half_height
        max_y = offset_y + half_height

        if min_x <= ortho_x <= max_x and min_y <= ortho_y <= max_y:
            lineup[z][2] = glm.mix(lineup[z][2], 0.23, dt * 10)
            if pygame.mouse.get_pressed()[0] and lineup[z][0] != "" and lineup[z][3] <= 0 and money >= lineup[z][5] and not paused:
                selected = lineup[z]
            if pygame.mouse.get_pressed()[0]:
                lineup[z][2] = 0.26
        else:
            lineup[z][2] = glm.mix(lineup[z][2], 0.2, dt * 10)
            if selected == lineup[z]:
                R = 1
        
        render_tower_menu(z, dt)

def render_tower_menu(z, dt):
    global selected
    lineup[z][1].use(7)
    shader['Texture'].value = 7
    shader['u_proj'].write(glm.ortho(-1.5, 1.5, -1, 1, -1, 1).to_bytes())
    shader['scale'].value = lineup[z][2]
    
    if lineup[z][4] != 0:
        shader['percent'].value = lineup[z][3] / lineup[z][4]
    else:
        shader['percent'].value = 1

    if selected == lineup[z]:
        offset_x, offset_y = update_selected_unit(dt, z)
        shader['offset'].value = (offset_x, offset_y)
    else:
        offset_x = (z % 4 / 4 - 0.5 + 0.5 / 4) * 2
        offset_y = -0.5 - 0.25 * (z // 4)
        shader['offset'].value = (offset_x, offset_y)
        
    vao.render(moderngl.TRIANGLE_STRIP)

def render_money():
    surf = Arial.render("$" + str(money), 0, (0, 0, 0)).convert_alpha()
    w, h = surf.get_size()
    data = pygame.image.tobytes(surf, 'RGBA', True)
    DCost = ctx.texture((w, h), 4, data)
    DCost.use(7)
    shader['Texture'].value = 7
    shader['u_proj'].write(glm.ortho(-1.5, 1.5, -1, 1, -1, 1).to_bytes())
    shader['scale'].value = 0.2
    shader['percent'].value = 0
    shader['offset'].value = (1.1, 0.9)
    vao.render(moderngl.TRIANGLE_STRIP)
    ctx.enable(moderngl.DEPTH_TEST)

def render_pause_menu():
    """Renders pause button and, if paused, the menu overlay buttons for Unpause and Leave."""
    global paused
    _, _, ortho_x, ortho_y = get_mouse_pos()
    mouse_clicked = pygame.mouse.get_pressed()[0] and not off
    ctx.disable(moderngl.DEPTH_TEST)
    pause_pos = (-1.3, 0.85)
    btn_pause.render(shader, vao, pause_pos, scale=0.15)

    if not paused:
        if mouse_clicked and btn_pause.is_hovered(ortho_x, ortho_y, pause_pos, scale=0.15):
            paused = True
        ctx.enable(moderngl.DEPTH_TEST)
        return None

    # Pause Overlay Active
    resume_pos = (0.0, 0.25)
    leave_pos = (0.0, -0.15)

    btn_resume.render(shader, vao, resume_pos, scale=0.3)
    btn_leave.render(shader, vao, leave_pos, scale=0.3)

    if mouse_clicked:
        if btn_resume.is_hovered(ortho_x, ortho_y, resume_pos, scale=0.3):
            paused = False
        elif btn_leave.is_hovered(ortho_x, ortho_y, leave_pos, scale=0.3):
            paused = False
            return "LEAVE"
    
    ctx.enable(moderngl.DEPTH_TEST)
    return None

def render_victory_menu(victory):
    """Renders victory button"""
    _, _, ortho_x, ortho_y = get_mouse_pos()
    mouse_clicked = pygame.mouse.get_pressed()[0] and not off
    ctx.disable(moderngl.DEPTH_TEST)
    pause_pos = (-1.3, 0.85)


    # Pause Overlay Active
    resume_pos = (0.0, 0.25)
    leave_pos = (0.0, -0.15)

    (btn_victory if victory > 0 else btn_defeat).render(shader, vao, resume_pos, scale=0.3)
    btn_leave.render(shader, vao, leave_pos, scale=0.3)

    if mouse_clicked:
        if btn_leave.is_hovered(ortho_x, ortho_y, leave_pos, scale=0.3):
            return "LEAVE"
    
    ctx.enable(moderngl.DEPTH_TEST)
    return None
victory = 0
def update_fighters(dt):
    global money
    global victory
    collect = []
    for p in peoples:
        combat.FighterUpdate(p, dt, peoples, avoid, projectiles)
        p.update(dt, peoples, avoid, projectiles)
      
        if p.speed == 0 and not hasattr(p, "initialized"):
            renderer.scene_objects.append(fighters.QUAD.duplicate())
            p.initialized = renderer.scene_objects[len(renderer.scene_objects) - 1]
        elif p.speed == 0:
            p.initialized.spritesheet = render.SpriteSheet(ctx)
            p.initialized.spritesheet.SetSurface(ctx, Arial.render(f"{p.HP}", 0, (0, 0, 0)))
            p.initialized.position = glm.vec3(p.position)
            p.initialized.position.y += 1
            p.initialized.position.z -= 2
            p.initialized.clippable = 1
        
        if p.HP <= 0:
            if (p.speed == 0 and p.enemy):
                for x in peoples:
                    if (x.enemy): x.HP = 0
                victory = 1
            elif (p.speed == 0):
                for x in peoples:
                    if (not x.enemy): x.HP = 0
                victory = -1
                
            if p.enemy:
                money += p.money            
            p.free()
            if p.speed == 0:
                renderer.scene_objects.remove(p.initialized)
            collect.append(p)
    for z in collect:
        
        peoples.remove(z)

def update_projectiles(dt):
    for z in projectiles:
        z.update(avoid, peoples, dt)
        if z.delME:
            renderer.scene_objects.remove(z.renderObject)
            projectiles.remove(z)

def update(dt):
    dt = min(dt, 0.1)
    
    # Handle pause overlay UI interaction
    pause_action = render_pause_menu()
    if pause_action == "LEAVE":
        return "MENU"
    if (victory):
        vic_action = render_victory_menu(victory)
        if (vic_action == "LEAVE"):
            return "MENU"
    # Freeze gameplay calculations if paused
    if not paused:
        levels.update(dt)
        update_fighters(dt)
        update_projectiles(dt)

    update_tower_menu(dt)
    render_money()
    render_pause_menu()
    return None