import glm
import render

IDLE = 0
WALK = 1
ATTACK = 2

rend = None

def set_renderer_reference(renderer):
    global rend
    rend = renderer

def intersection(point, obs):
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
        v0_w = glm.vec3(obs_model * glm.vec4(obs.vertices[idx0], obs.vertices[idx0 + 1], obs.vertices[idx0 + 2], 1.0))
        v1_w = glm.vec3(obs_model * glm.vec4(obs.vertices[idx1], obs.vertices[idx1 + 1], obs.vertices[idx1 + 2], 1.0))
        v2_w = glm.vec3(obs_model * glm.vec4(obs.vertices[idx2], obs.vertices[idx2 + 1], obs.vertices[idx2 + 2], 1.0))

        p0 = glm.vec2(v0_w.x, v0_w.z)
        p1 = glm.vec2(v1_w.x, v1_w.z)
        p2 = glm.vec2(v2_w.x, v2_w.z)

        edges = [(p0, p1), (p1, p2), (p2, p0)]
        for edge in edges:
            if ray_intersect_segment(ray_origin, ray_end, edge[0], edge[1]):
                intersections += 1

    return intersections

def is_point_inside_shape(point, obs):
    return (intersection(point, obs) // 2 % 2) == 1

def ray_intersect_segment(p1, p2, p3, p4):
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

def GenerateSpriteSheets(ctx, folder_path, IdleFrames = 2, WalkFrames = 2, AttackFrames = 2, gfunc=None, **kwargs):
    return [
        render.SpriteSheet(ctx, folder_path + "idle.png", IdleFrames, 1, gfunc, **kwargs),
        render.SpriteSheet(ctx, folder_path + "walk.png", WalkFrames, 1, gfunc, **kwargs),
        render.SpriteSheet(ctx, folder_path + "attack.png", AttackFrames, 1, gfunc, **kwargs),
        render.SpriteSheet(ctx, folder_path + "spawner.png", 1, 1, gfunc, **kwargs)
    ]

class Projectile:
    def __init__(self, speed, renderObject, accel, dmg, HIT, radius, position, enemy):
        self.speed = glm.vec3(speed)
        self.renderObject = renderObject
        self.accel = accel
        self.damage = dmg
        self.HIT = HIT
        self.position = position
        self.radius = radius
        self.delME = 0
        self.enemy = enemy

    def update(self, avoid, unit, dt):
        if self.HIT != "":
            self.renderObject.position = self.position 
            self.position += self.speed * dt
            self.speed += self.accel * dt
            self.renderObject.spritesheet.current_frame = 0
            self.renderObject.animation_timer = -0.1
        if self.HIT == "GROUND":
            has_collide = 0
            for n in avoid:
                if is_point_inside_shape(self.position, n):
                    has_collide = 1
            if self.position.y < 0 or has_collide:
                self.HIT = ""
        if self.HIT == "":
            if self.renderObject.spritesheet.current_frame >= self.renderObject.spritesheet.cols * self.renderObject.spritesheet.rows - 1:
                for n in unit:
                    if (glm.distance(n.position, self.position) < self.radius) and not self.delME and n.enemy != self.enemy:
                        n.HP -= self.damage
                self.delME = 1

def FighterUpdate(self, dt, enemies, avoid, projectiles):
    self.target = glm.vec3(3121321, 1323232, 132123123)
    target = None
    
    evade_accumulated = glm.vec3(0, 0, 0)
    threat_count = 0
    
    for z in enemies:
        if z.enemy != self.enemy:
            dist = glm.distance(self.position, z.position)
            if dist <= z.standing_range and z.animation == ATTACK:
                away_vector = glm.normalize(self.position - z.position)
                weight = 1.0 / max(dist, 0.1)
                evade_accumulated += away_vector * weight
                threat_count += 1

            if dist < glm.distance(self.position, self.target):
                self.target = z.position     
                target = z

    if self.evade_timer > 0:
        self.evade_timer -= dt
    
    is_recovering = (self.idle_t > 0)
    if is_recovering and threat_count > 0 and glm.length(evade_accumulated) > 0:
        if self.evade_target is None or self.evade_timer <= 0:
            escape_direction = glm.normalize(evade_accumulated)
            self.evade_target = self.position + (escape_direction * (self.standing_range * 1.5))
            self.evade_timer = 0.3  
    elif self.evade_timer <= 0:
        self.evade_target = None

    if self.evade_target is not None and self.evade_timer > 0:
        self.target = self.evade_target
    elif target and self.idle_t <= 0:
        self.target = target.position

    
    if self.animation == ATTACK and self.frr and target:
        current_frame = self.spriteSheets[self.animation].current_frame
        
        
        if len(self.frr) > 0 and current_frame == self.frr[0][0]:
            action = self.frr[0]
            
            
            if len(action) == 3:
                if glm.distance(self.position, target.position) < action[1]:
                    target.HP -= action[2]
                self.frr = self.frr[1:]
                
            
            elif len(action) > 6 and action[6] is not None:
                TIME = (-2 * action[1]) / action[2]
                bvec = (self.target - self.position) / TIME
                bvec.y = action[1]
                accel = glm.vec3(0, action[2], 0)
                
                obj = render.QUAD.duplicate()
                obj.spritesheet = action[6].duplicate()
                
                if rend:
                    rend.scene_objects.append(obj)
                    
                projectiles.append(Projectile(
                    bvec, obj, accel, action[3], action[4], action[5], 
                    glm.vec3(self.position), self.enemy
                ))
                self.frr = self.frr[1:]
            else:
                
                self.frr = self.frr[1:]
          
    for obs in avoid:
        obs_model = obs.get_model_matrix()
        target_dir = glm.normalize(self.target - self.position)

        for i in range(0, len(obs.indices), 3):
            idx0, idx1, idx2 = obs.indices[i] * 8, obs.indices[i+1] * 8, obs.indices[i+2] * 8
            v0 = glm.vec3(obs_model * glm.vec4(obs.vertices[idx0], obs.vertices[idx0+1], obs.vertices[idx0+2], 1.0))
            v1 = glm.vec3(obs_model * glm.vec4(obs.vertices[idx1], obs.vertices[idx1+1], obs.vertices[idx1+2], 1.0))
            v2 = glm.vec3(obs_model * glm.vec4(obs.vertices[idx2], obs.vertices[idx2+1], obs.vertices[idx2+2], 1.0))
            
            tri_min = glm.min(glm.min(v0, v1), v2)
            tri_max = glm.max(glm.max(v0, v1), v2)
            K = glm.vec3(0, 0, -self.enemy)
            center = tri_max/2 + tri_min/2
            v0 += glm.vec3(2, 1, 2) * (v0 - center) + center + K
            v1 += glm.vec3(2, 1, 2) * (v1 - center) + center + K
            v2 += glm.vec3(2, 1, 2) * (v2 - center) + center + K

            p = self.position
            ab = v1 - v0
            ac = v2 - v0
            ap = p - v0

            d1 = glm.dot(ab, ap)
            d2 = glm.dot(ac, ap)
            if d1 <= 0.0 and d2 <= 0.0:
                closest_point = v0
            else:
                bp = p - v1
                d3 = glm.dot(ab, bp)
                d4 = glm.dot(ac, bp)
                if d3 >= 0.0 and d4 <= d3:
                    closest_point = v1
                else:
                    vc = d1 * d4 - d3 * d2
                    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
                        v = d1 / (d1 - d3)
                        closest_point = v0 + v * ab
                    else:
                        cp = p - v2
                        d5 = glm.dot(ab, cp)
                        d6 = glm.dot(ac, cp)
                        if d6 >= 0.0 and d5 <= d6:
                            closest_point = v2
                        else:
                            vb = d5 * d2 - d1 * d6
                            if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
                                w = d2 / (d2 - d6)
                                closest_point = v0 + w * ac
                            else:
                                va = d3 * d6 - d5 * d4
                                if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
                                    w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
                                    closest_point = v1 + w * (v2 - v1)
                                else:
                                    denom = 1.0 / (va + vb + vc)
                                    v = vb * denom
                                    w = vc * denom
                                    closest_point = v0 + ab * v + ac * w

            u_edge = v1 - v0
            v_edge = v2 - v0
            normal = glm.normalize(glm.cross(u_edge, v_edge))

            moving_toward = glm.dot(target_dir, normal) < 0.0
            collision_radius = min(0.5, self.standing_range) if moving_toward else 0.01 

            dist_vector = p - closest_point
            distance = glm.length(dist_vector)

            if distance < collision_radius and self.target != glm.vec3(3121321, 1323232, 132123123):
                slide_dir = glm.rotate(normal, 3.14/2, glm.vec3(0, 1, 0))
                slide_dir2 = glm.rotate(normal, -3.14/2, glm.vec3(0, 1, 0))
               
                if (glm.dot(10 * slide_dir, self.target-self.position) < glm.dot(10 * slide_dir2, self.target-self.position)):
                    slide_dir2 = slide_dir
                self.target = self.position + 10 * slide_dir 
                self.target.y = 0
                break

    can_attack = (target and glm.distance(self.position, target.position) <= self.standing_range and self.idle_t <= 0 and (self.evade_target is None or self.evade_timer <= 0))

    if can_attack and self.animation != ATTACK:
        self.animation = ATTACK
        self.spriteSheets[self.animation].reset()
        self.frr = list(self.plots)
