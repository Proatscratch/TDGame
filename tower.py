import glm, render, fighters
def create_tower(segments=16, radius=0.5, height=1.0, brick_height=0.2):
    """
    Generates vertex and index data for a cylindrical tower, a top cap, 
    and battlement merlons.
    
    Vertex format: [x, y, z, r, g, b, u, v]
    """
    Tower_vertices = []
    Tower_indices = []
    pi = 3.14159

    # ==========================================
    # 1. TOWER CYLINDER BODY
    # ==========================================
    for z in range(segments):
        angle = z * 2 * pi / segments
        cos_a = glm.cos(angle)
        sin_a = glm.sin(angle)

        # Bottom vertex (y = 0)
        Tower_vertices += [
            cos_a * radius, 0, sin_a * radius,  # Position
            1, 1, 1,                            # Color
            cos_a * radius + 0.5, 1             # UV
        ]
        # Top vertex (y = height)
        Tower_vertices += [
            cos_a * radius, height, sin_a * radius,  # Position
            1, 1, 1,                                 # Color
            cos_a * radius + 0.5, 0                  # UV
        ]

        # Wall quads (2 triangles per segment)
        b_curr = z * 2
        t_curr = z * 2 + 1
        b_next = ((z + 1) % segments) * 2
        t_next = ((z + 1) % segments) * 2 + 1

        Tower_indices += [b_curr, t_curr, b_next]
        Tower_indices += [t_curr, t_next, b_next]

    # ==========================================
    # 2. TOP CAP (ROOF)
    # ==========================================
    # Add a center vertex at the top
    cap_center_idx = len(Tower_vertices) // 8
    Tower_vertices += [
        0, height, 0,  # Position
        1, 1, 1,       # Color
        0.5, 0.5       # UV Center
    ]

    # Create triangle fan connecting center to all top edge vertices
    for z in range(segments):
        t_curr = z * 2 + 1
        t_next = ((z + 1) % segments) * 2 + 1
        
        # Winding order set facing upward
        Tower_indices += [cap_center_idx, t_next, t_curr]

    # ==========================================
    # 3. TOP BATTLEMENT BRICKS (MERLONS)
    # ==========================================
    base_vertex_offset = len(Tower_vertices) // 8  # 8 floats per vertex

    brick_count = 0
    uv_scale = brick_height / height

    for z in range(segments):
        if z % 2 == 0:  # Create a brick on even-numbered segments
            angle1 = z * 2 * pi / segments
            angle2 = (z + 1) * 2 * pi / segments

            c1, s1 = glm.cos(angle1), glm.sin(angle1)
            c2, s2 = glm.cos(angle2), glm.sin(angle2)

            # 4 vertices for the front face of the brick
            Tower_vertices += [
                c1 * radius, height, s1 * radius,                1, 1, 1, 0, -1 * uv_scale,         # V0: Bottom-Left
                c2 * radius, height, s2 * radius,                1, 1, 1, 1 * uv_scale, -1 * uv_scale, # V1: Bottom-Right
                c1 * radius, height + brick_height, s1 * radius, 1, 1, 1, 0, 0,                     # V2: Top-Left
                c2 * radius, height + brick_height, s2 * radius, 1, 1, 1, 1 * uv_scale, 0          # V3: Top-Right
            ]

            idx = base_vertex_offset + (brick_count * 4)

            # Front face triangles for the brick
            Tower_indices += [idx + 0, idx + 2, idx + 1]
            Tower_indices += [idx + 2, idx + 3, idx + 1]

            brick_count += 1

    return Tower_vertices, Tower_indices
def init(ctx, renderer):
    global rend
    global context
    rend = renderer
    context = ctx
def New_Tower(segments=16, radius=0.5, height=1.0, brick_height=0.2):
    Tower_vertices, Tower_indices = create_tower(segments, radius, height, brick_height)

    Enemy_Tower = rend.create_object(Tower_vertices, Tower_indices)
    Enemy_Tower.spritesheet = render.SpriteSheet(context, "assets/tower.png", 1, 1)
    return Enemy_Tower

def Tower_As_Fighter(position, enemy, segments=16, radius=0.5, height=1.0, brick_height=0.2):
    fight = fighters.Fighter(position, [render.SpriteSheet(context, "assets/tower.png", 1, 1),render.SpriteSheet(context, "assets/tower.png", 1, 1),render.SpriteSheet(context, "assets/tower.png", 1, 1),render.SpriteSheet(context, "assets/tower.png", 1, 1)], enemy)
    rend.scene_objects.remove(fight.renderObject)
    
    fight.renderObject = New_Tower(segments, radius, height, brick_height)
 #   rend.scene_objects.append(fight.renderObject)
    fight.renderObject.clippable = 1
    fight.update(0, [], [])
    fight.HP = 1000
    fight.plots = ((0, 0, 0),)
    fight.frr = list(fight.plots)
    fight.speed = 0
    fight.idle = 321098321
    fight.standing_range = 0
    fight.animation = fighters.IDLE
    return fight