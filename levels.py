import render, glm, fighters
ObstacleData = {}
def init(ctx, renderer):
    global context
    context = ctx
    global rend
    rend = renderer
    with open("levels.json", "r") as r:
        data = json.load(r)
    for n in data["Meshs"]:
        ObstacleData[n] = renderer.create_object(data["Meshs"][n]["Verts"], data["Meshs"][n]["Index"])
        renderer.scene_objects.pop()
    

import json
import fighters
current_Json = None
def LoadLevelsFromJSON(name, peoples, Z, avoid):

    global current_Json
    global Limit
    peoples[2:] = []
    with open("levels.json", "r") as r:
        data = json.load(r)
    S = data["Stages"][name]
    current_Json = [peoples, S, 0, 0, 0, ]
    rend.ambient = render.SpriteSheet(context, "assets/"+S['sky'])
    rend.light_color = glm.vec3(S['light_color'])
    rend.light_pos = glm.vec3(S['lightPos'])
    Z.spritesheet = render.SpriteSheet(context, f"assets/{S['stage']}", 1, 1)
    peoples[0].HP = S["BaseHP"]
    current_Json[2] = S["Limit"]
    current_Json[3] = S["SpawnDist"]
    for k in avoid:
        rend.scene_objects.remove(k)
    for z in S["Obstacles"]:
        avoid.append(ObstacleData[z["mesh"]])
        rend.scene_objects.append(avoid[-1])
        rend.scene_objects[-1].spriteSheet = render.SpriteSheet(context, "assets/"+z["spritesheet"])
        rend.scene_objects[-1].scale = glm.vec3(z['scale'])
        rend.scene_objects[-1].position = glm.vec3(z['pos'])
queue = []
time = 0
def update(dt):
    global time
    time += dt
    js = current_Json[1]["Spawns"]
    current_Json[4] -= dt
    for x in js:
        if (time > x["Time"] and (time + x["Time"]) % x["Respawn"] < (time - dt + x["Time"]) % x["Respawn"]) and x["Amount"] > 1 and x["HP_Needed"] > current_Json[0][0].HP:
            x["Amount"]-=1
            queue.append(x)
   # print(current_Json[4], len(current_Json[0]), current_Json[2], len(queue), int(time))
    if current_Json[4] < 0 and len(current_Json[0])<= current_Json[2] and len(queue) > 0:
        current_Json[4] = current_Json[3]
        current_Json[0].append(fighters.GenerateFighter(queue[-1]["Spawn"], glm.vec3(0, 0, -3), 1))
        current_Json[0][-1].update(dt, [], [])
        queue.pop()


        