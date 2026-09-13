import glm
import render
import math
import json
from combat import FighterUpdate, GenerateSpriteSheets, Projectile, set_renderer_reference

QUAD = None
rend = None
context = None

IDLE = 0
WALK = 1
ATTACK = 2
TOWER = 1

def init(ctx, renderer):
    global QUAD, rend, context
    context = ctx
    rend = renderer
    set_renderer_reference(renderer)
    
    quad_verts = [
        -0.2, -0.0, 0.0,  0.8, 0.8, 0.8,  0.0, 0.0,
        0.2, -0.0, 0.0,  0.8, 0.8, 0.8,  1.0, 0.0,
        -0.2, 0.4, 0.0,  0.8, 0.8, 0.8,  0.0, 1.0,
        0.2, 0.4, 0.0,  0.8, 0.8, 0.8,  1.0, 1.0,
    ]
    quad_indices = [0, 1, 2, 2, 1, 3]
    tx = render.SpriteSheet(ctx, "assets/hi.png", 2, 1)
    QUAD = renderer.create_object(quad_verts, quad_indices, spritesheet=tx)
    render.QUAD = QUAD
    renderer.scene_objects.pop()

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

    def update(self, dt, enemies, avoid, projectiles):
        
        self.knockback = glm.mix(self.knockback, glm.vec3(0, 0, 0), dt * 5)
        self.position += self.knockback * dt

        if self.animation != ATTACK and self.idle_t > 0:
            self.idle_t -= dt
            if self.idle_t < 0:
                self.idle_t = 0

        
        distance_to_target = glm.distance(self.position, self.target)
        if distance_to_target > self.standing_range and self.target != glm.vec3(3121321, 1323232, 132123123):
            if self.animation != ATTACK:
                if self.animation != WALK:
                    self.animation = WALK
                    self.spriteSheets[self.animation].reset()
                
                self.position = glm.normalize(self.target - self.position) * dt * self.speed + self.position
                if glm.distance(self.position, self.target) < dt * self.speed:
                    self.position = self.target
        else:
            if self.animation != ATTACK:
                if self.animation != IDLE:
                    self.animation = IDLE
                    self.spriteSheets[self.animation].reset()

        if self.animation == ATTACK and self.spriteSheets[self.animation].is_finished:
            self.animation = IDLE
            self.idle_t = self.idle
            self.spriteSheets[self.animation].reset()

        
        self.renderObject.spritesheet = self.spriteSheets[self.animation]
        self.renderObject.position = self.position

        move_dest = self.target if self.target != glm.vec3(3121321, 1323232, 132123123) else self.position
        if self.renderObject.vertices is QUAD.vertices:
            self.renderObject.flipX = 1 if move_dest.x < self.position.x else -1
        else:
            self.renderObject.rotation.y = glm.mix(
                self.renderObject.rotation.y, 
                -math.atan2(self.target.z - self.position.z, self.target.x - self.position.x) - 3.14/2, 
                dt * 1
            )

def LoadFightersFromJSON(name):
    with open("fighters.json", "r") as r:
        data = json.load(r)
    return data[name]

def FighterData(fighter, position, enemy):
    mesh = 0
    if fighter["texture"][:5] == 'Mesh.':
        mesh = 1
        fighter["texture"] = fighter["texture"][5:]
    QW = Fighter(position, GenerateSpriteSheets(rend.ctx, "assets/" + fighter["texture"] + "/", fighter["IdleFrames"], fighter["WalkFrames"], fighter["AttackFrames"]), enemy)
    QW.speed = fighter["speed"]
    if mesh:
        rend.scene_objects.remove(QW.renderObject)
    QW.standing_range = fighter["standing_range"]
    QW.idle = fighter["idle"]
    QW.plots = [(z["frame"], z["range"], z["damage"]) if "range" in z else (z["frame"], z["yvelocity"], z["G"], z["damage"], z["HIT_CONDITION"], z["sphere_size"], render.SpriteSheet(context, "assets/" + fighter["texture"] + f"/projectile{I}.png", z["Pframe"], )) for I, z in enumerate(fighter["plots"])]
    
    QW.frr = list(fighter["plots"])
    QW.HP = fighter["health"]
    QW.money = fighter["Cost"]

    return QW

def GenerateFighter(name, position, enemy):
    fighter = LoadFightersFromJSON(name)
    return FighterData(fighter, position, enemy)