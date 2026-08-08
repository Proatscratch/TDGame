import glm
import render

def init(ctx, renderer):
    global QUAD
    global rend
    rend = renderer
    quad_verts = [
        -0.2, -0.0, 0.0,  0.8, 0.8, 0.8,  0.0, 0.0,
        0.2, -0.0, 0.0,  0.8, 0.8, 0.8,  1.0, 0.0,
        -0.2, 0.4, 0.0,  0.8, 0.8, 0.8,  0.0, 1.0,
        0.2, 0.4, 0.0,  0.8, 0.8, 0.8,  1.0, 1.0,
    ]
    quad_indices = [0, 1, 2, 2, 1, 3]
    tx = render.SpriteSheet(ctx, "assets/hi.png", 2, 1)
    QUAD = renderer.create_object(quad_verts, quad_indices, spritesheet=tx)
    
    renderer.scene_objects.pop()

IDLE = 0
WALK = 1
ATTACK = 2
TOWER = 1

def GenerateSpriteSheets(ctx, folder_path, IdleFrames = 2, WalkFrames = 2, AttackFrames = 2, gfunc=None, **kwargs):
    return [
        render.SpriteSheet(ctx, folder_path + "idle.png", IdleFrames, 1, gfunc,  **kwargs), 
        render.SpriteSheet(ctx, folder_path + "walk.png", WalkFrames, 1, gfunc, **kwargs), 
        render.SpriteSheet(ctx, folder_path + "attack.png", AttackFrames, 1, gfunc, **kwargs), 
        render.SpriteSheet(ctx, folder_path + "spawner.png", 1, 1, gfunc, **kwargs)
    ]

class Fighter: 
    def __init__(self, position, spriteSheet, enemy = 0):
        self.position = position
        self.renderObject = QUAD.duplicate()
        self.animation = WALK
        self.spriteSheets = [z.duplicate() for z in spriteSheet]
        rend.scene_objects.append(self.renderObject)
        self.target = position
        self.enemy = enemy
        self.speed = 1
        self.standing_range = 1
        self.idle = 1
        self.idle_t = 0
        self.HP = 100
        self.plots = ((6, 1, 8),)
        self.frr = list(self.plots)
        self.knockback = glm.vec3(0, 0, 0)
        self.money = 0
        self.mode = 0
        self.evade_target = None
        self.evade_timer = 0.5  

    def apply_knockback(self, knockback):
        self.knockback += knockback

    def free(self):
        self.renderObject.y = -3321
        rend.scene_objects.remove(self.renderObject)

    def update(self, dt, enemies, avoid):
        self.renderObject.spritesheet = self.spriteSheets[self.animation]
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
          
        self.knockback = glm.mix(self.knockback, glm.vec3(0, 0, 0), dt * 5)
        self.position += self.knockback * dt

        
        if self.animation != ATTACK and self.idle_t > 0:
            self.idle_t -= dt
            if self.idle_t < 0:
                self.idle_t = 0

        
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

        
        if (self.animation == ATTACK and self.animation != IDLE) and self.frr and target:
            if glm.distance(self.position, target.position) < self.frr[0][1] and self.spriteSheets[self.animation].current_frame in [pp[0] for pp in self.frr]:
                target.HP -= self.frr[0][2]
                self.frr = self.frr[1:]
        T = glm.vec3(self.target)
        
        for obs in avoid:
            if (self.animation == WALK):
                pass
            obs_model = obs.get_model_matrix()
            
            
            target_dir = glm.normalize(self.target - self.position)
            next_pos = self.position + target_dir * self.speed * dt * 30

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

                
                if moving_toward:
                    collision_radius = min(0.5, self.standing_range)  
                else:
                    collision_radius = 0.01 

                
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

        if can_attack:
            if self.animation != ATTACK:
                self.animation = ATTACK
                self.spriteSheets[self.animation].reset()
                self.frr = list(self.plots)
        else:
            
            distance_to_target = glm.distance(self.position, T)
            
            if distance_to_target > self.standing_range and self.target != glm.vec3(3121321, 1323232, 132123123):
                
                if self.animation != WALK:
                    self.animation = WALK
                    self.spriteSheets[self.animation].reset()
                
                
              
                P = glm.normalize(self.target - self.position) * dt * self.speed
                self.position = glm.normalize(self.target - self.position) * dt * self.speed + self.position
              
                if glm.distance(self.position, self.target) < dt * self.speed:
                    self.position = self.target
                
               
            else:
                
                if self.animation != IDLE:
                    self.animation = IDLE
                    self.spriteSheets[self.animation].reset()

        
        if self.animation == ATTACK and self.spriteSheets[self.animation].is_finished:
            self.animation = IDLE
            self.idle_t = self.idle
            self.spriteSheets[self.animation].reset()

        move_dest = self.target if self.target != glm.vec3(3121321, 1323232, 132123123) else self.position
        self.renderObject.position = self.position
        self.renderObject.flipX = 1 if move_dest.x < self.position.x else -1

import json

def LoadFightersFromJSON(name):
    with open("fighters.json", "r") as r:
        data = json.load(r)
    return data[name]

def FighterData(fighter, position, enemy):
    QW = Fighter(position, GenerateSpriteSheets(rend.ctx, "assets/" + fighter["texture"] + "/", fighter["IdleFrames"], fighter["WalkFrames"], fighter["AttackFrames"]), enemy)
    QW.speed = fighter["speed"]
    QW.standing_range = fighter["standing_range"]
    QW.idle = fighter["idle"]
    QW.plots = [(z["frame"], z["range"], z["damage"]) for z in fighter["plots"]]
    QW.frr = list(fighter["plots"])
    QW.HP = fighter["health"]
    QW.money = fighter["Cost"]
    return QW

def GenerateFighter(name, position, enemy):
    fighter = LoadFightersFromJSON(name)
    return FighterData(fighter, position, enemy)