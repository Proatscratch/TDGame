import pygame
import moderngl
import glm
import render
import game
pygame.init()
WIDTH, HEIGHT = 960, 640
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
ctx = moderngl.get_context()
# Initialize the renderer engine pipeline
renderer = render.Renderer(ctx, WIDTH, HEIGHT)

game.init(ctx, renderer)
# 1. Movable Triangle Object
tri_verts = [
    -0.5, -0.5, -0.0,  1.0, 0.2, 0.2,  0.0, 0.0,
     0.5, -0.5, -0.0,  0.2, 1.0, 0.2,  1.0, 0.0,
     0.0,  0.5, -0.0,  0.2, 0.2, 1.0,  0.5, 1.0,
]
tri_indices = [0, 1, 2]
# 2. Floor Object
floor_verts = [
    -10.0, -0.0, -8.0,  0.8, 0.8, 0.8,  0.0, 0.0,
     10.0, -0.0, -8.0,  0.8, 0.8, 0.8,  10.0, 0.0,
    -4.0, -0.0,  8.0,  0.8, 0.8, 0.8,  3.0, 16.0,
     4.0, -0.0,  8.0,  0.8, 0.8, 0.8,  7.0, 16.0,
]
import glm, tower
game.fighters.init(ctx, renderer)
tower.init(ctx, renderer)

# Example Usage:
floor_indices = [0, 1, 2, 2, 1, 3]
Z = renderer.create_object(floor_verts, floor_indices)
Z.spritesheet = render.SpriteSheet(ctx, "assets/grass.png", 1, 1)

Enemy_Tower = tower.Tower_As_Fighter(glm.vec3(0, 0, -3.5), 1)
game.peoples.append(Enemy_Tower)
Player_Tower = tower.Tower_As_Fighter(glm.vec3(0, 0, 3.5), 0)

game.peoples.append(Player_Tower)
clock = pygame.time.Clock()
t_acc = 0.0


#game.peoples.append(game.fighters.GenerateFighter("Debug Unit", glm.vec3(1, 0, 4), 0))
lineup  = ["Debug Unit", "", "", "", "", "", "", ""]
game.levels.init(ctx, renderer)
game.levels.LoadLevelsFromJSON("Dummy_Test", game.peoples, Z, game.avoid)
game.commitLineup(lineup)
while True:
    dt = clock.tick(60) / 1000.0
    t_acc += dt
    
    # Update game logic cleanly without touching ModernGL context or uniforms here
    game.off = 0
    for event in pygame.event.get():
        if event.type == pygame.MOUSEBUTTONUP:
            game.off = 1
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit

    # Delegate all rendering and pipeline updates entirely to the render module
    renderer.update(dt)
    game.update(dt)
    pygame.display.flip()