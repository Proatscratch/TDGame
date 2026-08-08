import numpy
import pygame, moderngl, glm

import fighters
import render
import levels
peoples : list[fighters.Fighter]= []
vertex = numpy.array([-0.75, -0.5, 0.0, 0.0,
                      0.75, -0.5, 1.0, 0.0,
                      -0.75, 0.5, 0.0, 1.0,
                      0.75, 0.5, 1.0, 1.0], dtype=numpy.float32)

indices = numpy.array([0, 1, 2, 3], dtype=numpy.int32)
off = 0
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
import glm


def is_point_inside_shape(point, obs):
  """Determines if a 2D/3D point is inside a closed concave shape

  defined by triangles using the Ray Casting (Even-Odd) rule.
  """
  obs_model = obs.get_model_matrix()
  intersections = 0

  
  ray_origin = glm.vec2(point.x, point.z)
  
  ray_end = glm.vec2(point.x + 10000.0, point.z)

  
  for i in range(0, len(obs.indices), 3):
    idx0, idx1, idx2 = (
        obs.indices[i] * 8,
        obs.indices[i + 1] * 8,
        obs.indices[i + 2] * 8,
    )

    
    v0_w = glm.vec3(
        obs_model
        * glm.vec4(
            obs.vertices[idx0],
            obs.vertices[idx0 + 1],
            obs.vertices[idx0 + 2],
            1.0,
        )
    )
    v1_w = glm.vec3(
        obs_model
        * glm.vec4(
            obs.vertices[idx1],
            obs.vertices[idx1 + 1],
            obs.vertices[idx1 + 2],
            1.0,
        )
    )
    v2_w = glm.vec3(
        obs_model
        * glm.vec4(
            obs.vertices[idx2],
            obs.vertices[idx2 + 1],
            obs.vertices[idx2 + 2],
            1.0,
        )
    )

    
    p0 = glm.vec2(v0_w.x, v0_w.z)
    p1 = glm.vec2(v1_w.x, v1_w.z)
    p2 = glm.vec2(v2_w.x, v2_w.z)

    
    
    edges = [(p0, p1), (p1, p2), (p2, p0)]
    for edge in edges:
      if ray_intersect_segment(ray_origin, ray_end, edge[0], edge[1]):
        intersections += 1

  
  
  
 
  return (intersections//2 % 2) == 1


def ray_intersect_segment(p1, p2, p3, p4):
  """Helper: Checks if ray (p1->p2) intersects line segment (p3->p4)"""
  
  x1, y1 = p1.x, p1.y
  x2, y2 = p2.x, p2.y
  x3, y3 = p3.x, p3.y
  x4, y4 = p4.x, p4.y

  denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
  if denom == 0:
    return False

  ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
  ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom

  return 0.0 <= ua <= 1.0 and 0.0 <= ub <= 1.0
def init(ctxs, rend):
    global vbo
    global ibo
    global vao
    global ctx
    global shader
    global empty_texture
    global cache
    global renderer
    global Arial
    global avoid
    avoid = []

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
lineup = []
def SCALEBLIT(surf, cost):
    surf = pygame.transform.scale_by(surf, 5)
    surf.blit(Arial.render('$' + str(cost), 0, (0,0, 0)), (2, 2))
    return surf
def commitLineup(lineupS):
    global lineup
    json = [fighters.LoadFightersFromJSON(S) if S != "" else fighters.json.dumps({}) for S in lineupS ]
    i = -1
    for k in lineupS:
        i+=1
        if k not in cache:
            SpriteSHeet = fighters.GenerateSpriteSheets(ctx, f"assets/{json[i]["texture"]}/", gfunc=SCALEBLIT, cost=json[i]["Cost"])[3].frames[0]
                
            cache[k] = SpriteSHeet
    lineup = [[z, cache[z], 0.2, 0, fighters.LoadFightersFromJSON(z)["Recharge"] if z != "" else 0, fighters.LoadFightersFromJSON(z)["Cost"] if z != "" else ""] for z in lineupS]
money = 50
selected = None
R = 0
def update(dt):
    global money
    global R
    global selected
    if (dt > 0.1): dt = 0.1
    levels.update(dt)
    for p in peoples:
       
        p.update(dt, peoples, avoid)
     
        
        if p.speed == 0 and not hasattr(p, "initialized"):
            renderer.scene_objects.append(fighters.QUAD.duplicate())
            p.initialized = renderer.scene_objects[len(renderer.scene_objects)-1]
        elif p.speed == 0:
            p.initialized.spritesheet = render.SpriteSheet(ctx)
            p.initialized.spritesheet.SetSurface(ctx, Arial.render(f"{p.HP}", 0, (0, 0, 0)))
            
            p.initialized.position = glm.vec3(p.position)
            p.initialized.position.y += 1.5
            p.initialized.position.z -= 1
            p.initialized.clippable = 1
        if p.HP <= 0:
            if (p.enemy):
                money += p.money            
            p.free()
            
            if (p.speed == 0):
                renderer.scene_objects.remove(p.initialized)
            peoples.remove(p)
    
    
    
    mouse_x, mouse_y = pygame.mouse.get_pos()
    window_w, window_h = ctx.screen.size  

    
    ortho_x = (mouse_x / window_w) * 3.0 - 1.5
    
    ortho_y = 1.0 - (mouse_y / window_h) * 2.0

    
    scale = 0.2
    half_width = 0.75 * scale   
    half_height = 0.5 * scale   

    
    hovered_quad_index = -1

    ctx.screen.use()
    ctx.disable(moderngl.DEPTH_TEST)

    for z in range(8):
        lineup[z][3] -= dt
        offset_x = (z % 4 / 4 - 0.5 + 0.5 / 4) * 2
        offset_y = -0.5 - 0.25 * (z // 4)
        
        min_x = offset_x - half_width
        max_x = offset_x + half_width
        min_y = offset_y - half_height
        max_y = offset_y + half_height

        
        if min_x <= ortho_x <= max_x and min_y <= ortho_y <= max_y:
            hovered_quad_index = z
            lineup[z][2] = glm.mix(lineup[z][2], 0.23, dt*10)
            if (pygame.mouse.get_pressed()[0]) and lineup[z][0] != "" and lineup[z][3] < 0 and money >= lineup[z][5]:
                selected = lineup[z]
            if (pygame.mouse.get_pressed()[0]) :
                lineup[z][2] = 0.26
        else:
            lineup[z][2] = glm.mix(lineup[z][2], 0.2, dt*10)
            if (selected == lineup[z]):
                R = 1

            

        
        lineup[z][1].use(7)
        shader['Texture'].value = 7
        shader['u_proj'].write(glm.ortho(-1.5, 1.5, -1, 1, -1, 1).to_bytes())
        shader['scale'].value = lineup[z][2]
        
        if (lineup[z][4] != 0):
            shader['percent'].value = lineup[z][3]/lineup[z][4]
        else:
            shader['percent'].value = 1
        if selected == lineup[z]:
            mouse = pygame.mouse.get_pos()

            
            if mouse[1] > 639:
                mouse = (mouse[0], 639)

            
            mouse_vec = glm.vec2(mouse)
            screen_size = glm.vec2(960, 640)
            
            NDC = (mouse_vec / screen_size) * 2.0 - glm.vec2(1.0, 1.0)
            NDC.y = -NDC.y  

            
            DNDC = glm.vec2(glm.inverse(glm.ortho(-1.5, 1.5, -1, 1, -1, 1)) * glm.vec4(NDC, 1.0, 1.0))
            offset_x = DNDC.x
            offset_y = DNDC.y

            
            inv_VP = glm.inverse(renderer.projection_matrix * renderer.view_matrix)

            
            near_4d = inv_VP * glm.vec4(NDC, -1.0, 1.0)
            far_4d  = inv_VP * glm.vec4(NDC,  1.0, 1.0)

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
                if is_point_inside_shape(world_space_pos, obs ):
                    world_space_pos.z = -1
            if (world_space_pos.z) < 0:
                shader["percent"] = 1
            if (off and selected) and (world_space_pos.z) > 0:
                if not R:
                    world_space_pos = glm.vec3(0, 0, 4)
                R = 0
                peoples.append(fighters.GenerateFighter(selected[0], world_space_pos, 0))
                peoples[-1].update(dt, [], [])
                peoples[-1].animation = fighters.IDLE
                selected[3] = selected[4]
                money -= selected[5]
                selected = None
            elif off and selected:
                selected = None
                R = 0
        shader['offset'].value = (offset_x, offset_y)
        vao.render(moderngl.TRIANGLE_STRIP)
    
    surf =Arial.render("$" + str(money), 0, (0, 0, 0)).convert_alpha()
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