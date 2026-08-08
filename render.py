import pygame
import moderngl
import struct
import numpy as np
import glm

vshader = """
#version 430
layout(location = 0) in vec3 in_position;
layout(location = 1) in vec3 in_color;
layout(location = 2) in vec2 in_uv;
out vec3 v_color;
out vec2 v_uv;
out vec3 v_position_world; 

uniform mat4 u_proj;
uniform mat4 u_view;
uniform mat4 u_model;

uniform vec2 u_uvOffset;
uniform vec2 u_uvScale;

void main() {
    v_color = in_color;
    v_uv = (in_uv * u_uvScale) + u_uvOffset;
    vec4 worldPos = u_model * vec4(in_position, 1.0);
    gl_Position = u_proj * u_view * worldPos;
    v_position_world = worldPos.xyz;
}
"""

geom_shader_frag = """
#version 430
in vec3 v_color;
in vec2 v_uv;
in vec3 v_position_world;

uniform sampler2D u_Texture;
uniform int u_HasTexture;
uniform int clippable;

layout(location = 0) out vec4 gPosition;
layout(location = 1) out vec4 gNormal;
layout(location = 2) out vec4 gAlbedo;
uniform float time;
float rand(vec2 co) {
   return fract(sin(dot(co, vec2(12.9898 + time, 78.233 + time))) * 43758.5453);
}
uniform mat4 u_view;
void main() {
    vec4 texColor = (u_HasTexture == 1) ? texture(u_Texture, v_uv) : vec4(1.0);
    
    if (texColor.a < 0.1 || (clippable == 1 && (((u_view * vec4(v_position_world, 1.0))).z > -5 && rand(round(gl_FragCoord.xy /1)*1) > pow(0.5, (((u_view * vec4(v_position_world, 1.0))).z+5))))) {
        discard;
    }

    vec3 dx = dFdx(v_position_world);
    vec3 dy = dFdy(v_position_world);
    vec3 normal = normalize(cross(dx, dy));
    if (dot(normal, normalize(-v_position_world)) < 0.0) {
        normal = -normal;
    }
    
    vec3 finalAlbedo = v_color * texColor.rgb;
    float finalAlpha = texColor.a;
    
    gPosition = vec4(v_position_world, 1.0);
    gNormal = vec4(normal * 0.5 + 0.5, 1.0);
    gAlbedo = vec4(finalAlbedo, finalAlpha);
}
"""

rayTraceCS = """
#version 430 core
layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(binding = 0, r32f) uniform image2D u_ShadowMask;
uniform sampler2D u_GWorldPos;
uniform sampler2D u_GNormal;
uniform sampler2D u_Texture; 
uniform int u_HasTexture;    
uniform vec3 u_PrimaryLightPos;
uniform uint u_NumObjects;

struct Vertex {
    float x, y, z;
    float r, g, b;
    float u, v;
};

struct Triangle {
    uint i0, i1, i2;
};

struct BVHNode {
    vec3 minBounds;
    uint leftChildOrFirstTri;
    vec3 maxBounds;
    uint triCount;
};

struct ObjectData {
    uint bvhRootNode;
    uint hasTexture;
    uint pad0;
    uint pad1;
};

layout(std430, binding = 1) readonly buffer VertexBuffer { Vertex vertices[]; };
layout(std430, binding = 2) readonly buffer IndexBuffer  { Triangle triangles[]; };
layout(std430, binding = 3) readonly buffer ObjectBuffer { ObjectData objects[]; };
layout(std430, binding = 4) readonly buffer BVHBuffer    { BVHNode bvhNodes[]; };

bool RayIntersectsAABB(vec3 rayOrigin, vec3 rayDirInv, vec3 minB, vec3 maxB, float maxDist) {
    vec3 t1 = (minB - rayOrigin) * rayDirInv;
    vec3 t2 = (maxB - rayOrigin) * rayDirInv;
    vec3 tMin = min(t1, t2);
    vec3 tMax = max(t1, t2);
    float tNear = max(max(tMin.x, tMin.y), tMin.z);
    float tFar  = min(min(tMax.x, tMax.y), tMax.z);
    return (tFar >= max(0.0, tNear)) && (tNear < maxDist);
}

bool RayIntersectsTriangle(vec3 rayOrigin, vec3 rayDir, Vertex v0, Vertex v1, Vertex v2, float maxDist, out float outT, out float outU, out float outV) {
    vec3 p0 = vec3(v0.x, v0.y, v0.z);
    vec3 p1 = vec3(v1.x, v1.y, v1.z);
    vec3 p2 = vec3(v2.x, v2.y, v2.z);

    vec3 e1 = p1 - p0; vec3 e2 = p2 - p0;
    vec3 h = cross(rayDir, e2);
    float a = dot(e1, h);
    if (abs(a) < 0.000001) return false;

    float f = 1.0 / a;
    vec3 s = rayOrigin - p0;
    outU = f * dot(s, h);
    if (outU < 0.0 || outU > 1.0) return false;

    vec3 q = cross(s, e1);
    outV = f * dot(rayDir, q);
    if (outV < 0.0 || (outU + outV) > 1.0) return false;

    outT = f * dot(e2, q);
    return (outT > 0.001 && outT < (maxDist - 0.01));
}

void main() {
    ivec2 pixelCoords = ivec2(gl_GlobalInvocationID.xy);
    ivec2 screenSize = imageSize(u_ShadowMask);
    if (pixelCoords.x >= screenSize.x || pixelCoords.y >= screenSize.y) return;

    vec2 uv = (vec2(pixelCoords) + 0.5) / vec2(screenSize);
    vec4 worldPosData = texture(u_GWorldPos, uv);

    if (worldPosData.w < 0.5) {
        imageStore(u_ShadowMask, pixelCoords, vec4(1.0));
        return;
    }

    vec3 normal = normalize(texture(u_GNormal, uv).xyz * 2.0 - 1.0);
    vec3 biasedPos = worldPosData.xyz + normal * 0.02;
    vec3 lightToPixel = u_PrimaryLightPos - biasedPos;
    float dist = length(lightToPixel);

    if (dist <= 0.0001) {
        imageStore(u_ShadowMask, pixelCoords, vec4(1.0));
        return;
    }

    vec3 rayDir = lightToPixel / dist;
    float maxDist = dist;
    
    vec3 safeRayDir = max(abs(rayDir), 0.00001) * sign(rayDir);
    vec3 rayDirInv = 1.0 / safeRayDir;

    float shadowFactor = 1.0;

    for (uint o = 0u; o < u_NumObjects; ++o) {
        ObjectData obj = objects[o];

        uint stack[32];
        int stackPtr = 0;
        stack[stackPtr++] = obj.bvhRootNode;

        while (stackPtr > 0) {
            uint nodeIdx = stack[--stackPtr];
            BVHNode node = bvhNodes[nodeIdx];

            if (RayIntersectsAABB(biasedPos, rayDirInv, node.minBounds, node.maxBounds, maxDist)) {
                if (node.triCount > 0u) {
                    uint lastTri = node.leftChildOrFirstTri + node.triCount;
                    for (uint i = node.leftChildOrFirstTri; i < lastTri; ++i) {
                        Triangle tri = triangles[i];
                        Vertex v0 = vertices[tri.i0]; 
                        Vertex v1 = vertices[tri.i1]; 
                        Vertex v2 = vertices[tri.i2];
                        float t, u, v;
                        if (RayIntersectsTriangle(biasedPos, rayDir, v0, v1, v2, maxDist, t, u, v)) {
                            vec2 hitUV = (1.0 - u - v) * vec2(v0.u, v0.v) + u * vec2(v1.u, v1.v) + v * vec2(v2.u, v2.v);
                            
                            float alpha = 1.0;
                            if (obj.hasTexture == 1 && u_HasTexture == 1) {
                                alpha = texture(u_Texture, hitUV).a;
                            }

                            if (alpha >= 0.1) {
                                shadowFactor = 0.0; 
                                break;
                            }
                        }
                    }
                } else {
                    if (stackPtr < 30) {
                        stack[stackPtr++] = node.leftChildOrFirstTri;
                        stack[stackPtr++] = node.leftChildOrFirstTri + 1u;
                    }
                }
            }
            if (shadowFactor <= 0.001) break;
        }
        if (shadowFactor <= 0.001) break;
    }

    imageStore(u_ShadowMask, pixelCoords, vec4(shadowFactor));
}
"""

lighting_shader_frag = """
#version 430
in vec2 v_uv;
out vec4 fragcolor;

uniform sampler2D u_GWorldPos;
uniform sampler2D u_GNormal;
uniform sampler2D u_GAlbedo;
uniform sampler2D u_ShadowMask;

uniform sampler2D ambientS;
uniform vec3 light_color;
uniform vec3 lightPos;


void main() {
    vec2 uv = gl_FragCoord.xy / vec2(960, 640);
    vec4 worldPos = texture(u_GWorldPos, uv);
    vec4 albedoSample = texture(u_GAlbedo, uv);
    vec3 ambient = texture(ambientS, uv).xyz;
    if (worldPos.w < 0.5 || albedoSample.a < 0.1) {
        fragcolor = vec4(ambient, 1.0);
        return;
    }

    vec3 normal = normalize(texture(u_GNormal, uv).xyz * 2.0 - 1.0);
    vec3 albedo = pow(albedoSample.rgb, vec3(2.2));
    float shadow = texture(u_ShadowMask, uv).r;

    vec3 lightDir = normalize(lightPos - worldPos.xyz);
    float diff = max(dot(normal, lightDir), 0.0);

    vec3 viewDir = normalize(-worldPos.xyz);
    vec3 reflectDir = reflect(-lightDir, normal);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 10);

    vec3 result = (ambient + shadow * (diff + spec * 0.5) * light_color) * albedo;
    fragcolor = vec4(pow(result, vec3(1.0/2.2)), 1.0);
}
"""

fullscreen_vshader = """
#version 430
in vec2 in_position;
out vec2 v_uv;
void main() {
    v_uv = in_position * 0.5 + 0.5;
    gl_Position = vec4(in_position, 0.0, 1.0);
}
"""

class SpriteSheet:
    def __init__(self, ctx, image_source=None, cols=1, rows=1, gfunc=None, **kwargs):
        self.ctx = ctx
        self.frames = []
        self.is_grid = False
        self.cols = cols
        self.rows = rows
        self.current_frame = 0
        self.is_finished = 0
        self.framesC = self.cols * self.rows
        if isinstance(image_source, str):
            surf = pygame.image.load(image_source).convert_alpha()
            if gfunc:
                surf = gfunc(surf, **kwargs)
            w, h = surf.get_size()
            data = pygame.image.tobytes(surf, 'RGBA', True)
            tex = ctx.texture((w, h), 4, data)
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self.frames.append(tex)
            self.is_grid = True
        elif isinstance(image_source, list):
            for path in image_source:
                self.framesC = len(image_source)
                surf = pygame.image.load(path).convert_alpha()
                if gfunc:
                    surf = gfunc(surf, **kwargs)
                w, h = surf.get_size()
                data = pygame.image.tobytes(surf, 'RGBA', True)
                tex = ctx.texture((w, h), 4, data)
                tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
                self.frames.append(tex)
    def SetSurface(self, ctx, surf):
        self.frames = []
        self.framesC = 1
        w, h = surf.get_size()
        data = pygame.image.tobytes(surf, 'RGBA', True)
        tex = ctx.texture((w, h), 4, data)
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.frames.append(tex)
        self.is_grid = False

    def reset(self):
        self.current_frame = 0
        self.is_finished = 0
    def bind_frame(self, program, frame_index=0, texture_unit=0):
        if not self.frames:
            if "u_HasTexture" in program:
                program["u_HasTexture"] = 0
            return

        if self.is_grid:
            self.frames[0].use(texture_unit)
            if "u_Texture" in program:
                program["u_Texture"] = texture_unit
            if "u_HasTexture" in program:
                program["u_HasTexture"] = 1
            
            col = frame_index % self.cols
            row = frame_index // self.cols
            scale_x = 1.0 / self.cols
            scale_y = 1.0 / self.rows
            offset_x = col * scale_x
            offset_y = row * scale_y
            
            if "u_uvScale" in program:
                program["u_uvScale"] = (scale_x, scale_y)
            if "u_uvOffset" in program:
                program["u_uvOffset"] = (offset_x, offset_y)
        else:
            idx = frame_index % len(self.frames)
            self.frames[idx].use(texture_unit)
            if "u_Texture" in program:
                program["u_Texture"] = texture_unit
            if "u_HasTexture" in program:
                program["u_HasTexture"] = 1
            if "u_uvScale" in program:
                program["u_uvScale"] = (1.0, 1.0)
            if "u_uvOffset" in program:
                program["u_uvOffset"] = (0.0, 0.0)

    def duplicate(self, current_frame=0):
        dup = self.__class__.__new__(self.__class__)
        dup.ctx = self.ctx
        dup.frames = self.frames  
        dup.is_grid = self.is_grid
        dup.cols = self.cols
        dup.rows = self.rows
        dup.current_frame = current_frame
        dup.framesC = self.framesC
        dup.is_finished = self.is_finished
        return dup

class RenderObject:
    def __init__(self, ctx, program, vertices, indices, position=glm.vec3(0), scale=glm.vec3(1), spritesheet=None):
        self.ctx = ctx
        self.position = glm.vec3(position)
        self.scale = glm.vec3(scale)
        self.vertices = np.array(vertices, dtype='f4')
        self.indices = np.array(indices, dtype='i4')
        
        self.vbo = ctx.buffer(self.vertices.tobytes())
        self.ibo = ctx.buffer(self.indices.tobytes())
        self.vao = ctx.vertex_array(program, [(self.vbo, '3f 3f 2f', 0, 1, 2)], index_buffer=self.ibo, index_element_size=4)
        
        self.spritesheet = spritesheet
        self.animation_timer = 0.0
        self.frame_duration = 0.066
        self.flipX = 1
        self.clippable = 0
    def get_model_matrix(self):
        mat = glm.translate(glm.mat4(1.0), self.position)
        mat = glm.rotate(mat, glm.radians(90.0) * (self.flipX - 1), glm.vec3(0, 1, 0))
        mat = glm.scale(mat, self.scale)
        
        return mat

    def duplicate(self, position=None, scale=None, spritesheet=None):
        dup = self.__class__.__new__(self.__class__)
        dup.ctx = self.ctx
        dup.vertices = self.vertices
        dup.indices = self.indices
        dup.vbo = self.vbo
        dup.ibo = self.ibo
        dup.vao = self.vao
        dup.position = glm.vec3(position) if position is not None else glm.vec3(self.position)
        dup.scale = glm.vec3(scale) if scale is not None else glm.vec3(self.scale)
        dup.spritesheet = spritesheet.duplicate() if spritesheet is not None else (self.spritesheet.duplicate() if self.spritesheet else None)
        dup.animation_timer = 0.0
        dup.frame_duration = self.frame_duration
        dup.flipX = self.flipX
        dup.clippable = self.clippable
        return dup
TIME = 0
class Renderer:
    def __init__(self, ctx, width, height):
        self.ctx = ctx
        self.width = width
        self.height = height
        
        self.programs = [
            self.ctx.program(vertex_shader=vshader, fragment_shader=geom_shader_frag),
            self.ctx.program(vertex_shader=fullscreen_vshader, fragment_shader=lighting_shader_frag)
        ]
        
        self.scene_objects = []
        
        self.vertex_buffer_gpu = None
        self.index_buffer_gpu = None
        self.object_buffer_gpu = None
        self.bvh_buffer_gpu = None
        
        self.ray_trace_program = self.ctx.compute_shader(rayTraceCS)
        
        self.aspect_ratio = width / height
        self.projection_matrix = glm.perspective(glm.radians(45.0), self.aspect_ratio, 0.1, 100.0)
        
        self.programs[1]["u_GWorldPos"] = 0
        self.programs[1]["u_GNormal"] = 1
        self.programs[1]["u_GAlbedo"] = 2
        self.programs[1]["u_ShadowMask"] = 3

        self.ambient = SpriteSheet(ctx, "assets/tower.png")
        self.light_pos = glm.vec3(5.0, 5.0, 0.0)
        self.light_color = glm.vec3(1, 1, 1)

        self.ctx.enable(moderngl.DEPTH_TEST | moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.ctx.disable(moderngl.CULL_FACE)

        self.g_position = self.ctx.texture((width, height), 4, dtype='f4')
        self.g_normal = self.ctx.texture((width, height), 4, dtype='f4')
        self.g_albedo = self.ctx.texture((width, height), 4, dtype='f4')
        self.depth_buffer_texture = self.ctx.depth_texture((width, height))

        self.g_buffer_fbo = self.ctx.framebuffer(
            color_attachments=[self.g_position, self.g_normal, self.g_albedo],
            depth_attachment=self.depth_buffer_texture
        )

        self.shadow_mask_tex = self.ctx.texture((width, height), 1, dtype='f4')
        self.shadow_mask_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.shadow_mask_tex.bind_to_image(0, read=False, write=True)
        self.view_matrix = glm.lookAt(
            glm.vec3(0.0, 2.0, 6.0), 
            glm.vec3(0.0, 0.0, 1.0),  
            glm.vec3(0.0, 1.0, 0.0)  
        )

    def create_object(self, vertices, indices, position=glm.vec3(0), scale=glm.vec3(1), spritesheet=None):
        obj = RenderObject(self.ctx, self.programs[0], vertices, indices, position, scale, spritesheet)
        self.scene_objects.append(obj)
        self._update_scene_buffers()
        return obj

    def _update_scene_buffers(self):
        all_verts = bytearray()
        all_indices = bytearray()
        obj_data_list = []
        bvh_nodes = []
        
        v_offset = 0
        for i, obj in enumerate(self.scene_objects):
            num_tris = len(obj.indices) // 3
            model = obj.get_model_matrix()
            
            min_b = glm.vec3(float('inf'))
            max_b = glm.vec3(float('-inf'))
            
            obj_transformed_verts = bytearray()
            for v_idx in range(0, len(obj.vertices), 8):
                local_pos = glm.vec4(obj.vertices[v_idx], obj.vertices[v_idx+1], obj.vertices[v_idx+2], 1.0)
                world_pos = model * local_pos
                
                min_b = glm.min(min_b, glm.vec3(world_pos))
                max_b = glm.max(max_b, glm.vec3(world_pos))
                
                v_data = np.array([world_pos.x, world_pos.y, world_pos.z,
                                   obj.vertices[v_idx+3], obj.vertices[v_idx+4], obj.vertices[v_idx+5],
                                   obj.vertices[v_idx+6], obj.vertices[v_idx+7]], dtype='f4')
                obj_transformed_verts.extend(v_data.tobytes())

            bvh_nodes.append({
                'min': [min_b.x, min_b.y, min_b.z], 
                'max': [max_b.x, max_b.y, max_b.z],
                'first_tri': sum([len(o.indices)//3 for o in self.scene_objects[:i]]), 
                'count': num_tris
            })
            
            has_tex = 1 if (obj.spritesheet and obj.spritesheet.frames) else 0
            obj_data_list.append({
                'bvh_root': i,
                'has_texture': has_tex
            })
            
            all_verts.extend(obj_transformed_verts)
            all_indices.extend((obj.indices + v_offset).tobytes())
            v_offset += len(obj.vertices) // 8

        if self.vertex_buffer_gpu: self.vertex_buffer_gpu.release()
        if self.index_buffer_gpu: self.index_buffer_gpu.release()
        if self.object_buffer_gpu: self.object_buffer_gpu.release()
        if self.bvh_buffer_gpu: self.bvh_buffer_gpu.release()

        self.vertex_buffer_gpu = self.ctx.buffer(bytes(all_verts))
        self.index_buffer_gpu = self.ctx.buffer(bytes(all_indices))
        
        self.vertex_buffer_gpu.bind_to_storage_buffer(1)
        self.index_buffer_gpu.bind_to_storage_buffer(2)
        
        obj_bytes = bytearray()
        for item in obj_data_list:
            obj_bytes.extend(struct.pack('IIII', item['bvh_root'], item['has_texture'], 0, 0))
        
        self.object_buffer_gpu = self.ctx.buffer(bytes(obj_bytes))
        self.object_buffer_gpu.bind_to_storage_buffer(3)

        bvh_bytes = bytearray()
        for node in bvh_nodes:
            bvh_bytes.extend(struct.pack('fffI', node['min'][0], node['min'][1], node['min'][2], node['first_tri']))
            bvh_bytes.extend(struct.pack('fffI', node['max'][0], node['max'][1], node['max'][2], node['count']))
        
        self.bvh_buffer_gpu = self.ctx.buffer(bytes(bvh_bytes))
        self.bvh_buffer_gpu.bind_to_storage_buffer(4)

    def update(self, dt):
        global TIME
        TIME += dt
        self.programs[1]["light_color"].write(self.light_color.to_bytes())
        self.ambient.frames[0].use(16)
        self.programs[1]["ambientS"] = 16
        self.programs[1]["lightPos"].write(self.light_pos.to_bytes())
        self._update_scene_buffers()

        self.g_buffer_fbo.use()
        self.g_buffer_fbo.clear(0.0, 0.0, 0.0, 0.0)

        for obj in self.scene_objects:
            self.programs[0]["u_proj"].write(self.projection_matrix.to_bytes())
            self.programs[0]["u_view"].write(self.view_matrix.to_bytes())
            self.programs[0]["u_model"].write(obj.get_model_matrix().to_bytes())
            self.programs[0]["clippable"].write(struct.pack('i', obj.clippable))
            self.programs[0]["time"].write(struct.pack('f', TIME))
            
            if obj.spritesheet:
                obj.animation_timer += dt
                if obj.animation_timer >= obj.frame_duration:
                    obj.animation_timer = 0.0
                    obj.spritesheet.current_frame = (obj.spritesheet.current_frame + 1)
                    obj.spritesheet.is_finished = 0
                    if (obj.spritesheet.current_frame >= obj.spritesheet.framesC):
                        obj.spritesheet.current_frame = 0
                        obj.spritesheet.is_finished = 1
                obj.spritesheet.bind_frame(self.programs[0], obj.spritesheet.current_frame, texture_unit=0)
            else:
                if "u_HasTexture" in self.programs[0]:
                    self.programs[0]["u_HasTexture"] = 0
                
            obj.vao.render(moderngl.TRIANGLES)

        self.ray_trace_program['u_PrimaryLightPos'].value = tuple(self.light_pos)
        self.ray_trace_program['u_NumObjects'].value = len(self.scene_objects)
        
        self.g_position.use(0)
        self.g_normal.use(1)
        if "u_GWorldPos" in self.ray_trace_program:
            self.ray_trace_program['u_GWorldPos'] = 0
        if "u_GNormal" in self.ray_trace_program:
            self.ray_trace_program['u_GNormal'] = 1

        bound_texture = False
        for obj in self.scene_objects:
            if obj.spritesheet and obj.spritesheet.frames:
                obj.spritesheet.bind_frame(self.ray_trace_program, obj.spritesheet.current_frame, texture_unit=2)
                bound_texture = True
                break
        
        if not bound_texture:
            if "u_HasTexture" in self.ray_trace_program:
                self.ray_trace_program['u_HasTexture'] = 0

        self.ray_trace_program.run((self.width + 7) // 8, (self.height + 7) // 8, 1)

        self.ctx.screen.use()
        self.ctx.clear(0.0, 0.0, 0.0)
        
        self.g_position.use(0)
        self.g_normal.use(1)
        self.g_albedo.use(2)
        self.shadow_mask_tex.use(3)
        
        quad_vbo = self.ctx.buffer(np.array([-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0], dtype='f4').tobytes())
        quad_ibo = self.ctx.buffer(np.array([0, 1, 2, 2, 1, 3], dtype='i4').tobytes())
        vao_lighting_pass = self.ctx.vertex_array(self.programs[1], [(quad_vbo, '2f', 0)], index_buffer=quad_ibo, index_element_size=4)
        vao_lighting_pass.render(moderngl.TRIANGLES)