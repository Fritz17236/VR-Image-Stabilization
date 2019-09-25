'''
This is Testbed code. It is an attempt to interface with the HTC Vive without resorting
to Direct display mode.  To do so, the displayer class instantiates an OpenGL context from
scrath and draws the texture as a fullscreen quad using a render-to-texture approach outlined
here: http://www.opengl-tutorial.org/intermediate-tutorials/tutorial-14-render-to-texture/


The textures upload and display to the screen properly, however there is difficulty in 
interfacing correctly with OpenVR's IVROverlay interface via Python. While the desired
image shows up in the Overlay Viewer when code is running, it is completely invisible to
the HMD.  Using IVRCompositor().submit() correctly submits the texture but it is not fixed
to the user's viewport as desired.  Two approaches to fixing this are to:

    a) Update the Vertex coordinates of the rendered texture based on the VR headset position

    b) Submit bug report/ ask for assistance in getting the overlay texture to properly display.

(Using setoverlayfromfile works perfectly and has the desired effect of image fixed to viewport)

This approach is much more robust and less inclined to focus-errors during an experiment than the
current approach of using the VR HMD as a monitor and manually moving windows into the Subject view.
'''


import pygame
from OpenGL.GL import * #@UnusedWildImport squelch warning
from OpenGL import * #@UnusedWildImport
import numpy as np
import cv2
import openvr

class Displayer():
    def __init__(self):
        self._width = 1920
        self._height = 1080
        self._init_vr()
        self._cap = cv2.VideoCapture("sample_vid.mp4")
        self._init_window_context()
        self._init_vertex_objects()
        glUseProgram(self._load_shaders())
        self._init_tex_coord_buffer()
        self._init_texture()
        self._init_framebuffer()
        self.update()
        self._position_vr_overlay   

    def _init_vr(self):
        # initialize vr interface
        openvr.init(openvr.VRApplication_Scene)
        self._width, self._height =(2048, 1280)#openvr.IVRSystem().getRecommendedRenderTargetSize()
        print("VR Interace Open")
        self._overlay = openvr.IVROverlay().createOverlay("VR_Overlay", "VROverlay")
        
        openvr.IVROverlay().setOverlayFromFile(self._overlay, 'PATH TO FILE HERE' )
        self._position_vr_overlay()
 
    def _load_shaders(self):
        '''
         define and do all the work to load & compile 
        vertex and fragment shaders in OpenGL
        '''
        vtx_shader = glCreateShader(GL_VERTEX_SHADER)
        frg_shader = glCreateShader(GL_FRAGMENT_SHADER)
        
        VERTEX_SHADER_CODE =""\
        "#version 330 core\n"\
        "layout(location = 0) in vec3 vtx_pos;\n"\
        "layout(location = 1) in vec2 vtx_uv;\n"\
        "out vec2 uv;\n"\
        "void main() {\n"\
            "gl_Position =  vec4(vtx_pos,1);\n"\
            "uv = vtx_uv;\n"\
        "}\n"
        
        
        FRAGMENT_SHADER_CODE = ""\
        "#version 330 core\n"\
        "in vec2 uv;\n"\
        "out layout(location = 0) vec3 color;\n"\
        "uniform sampler2D tex_sampler;\n"\
        "void main() {\n"\
            "color = texture(tex_sampler, uv).rgb;\n"\
        "}\n"
        
        print("Compiling Vertex Shader")
        glShaderSource(vtx_shader, VERTEX_SHADER_CODE)
        glCompileShader(vtx_shader)
        if glGetShaderiv(vtx_shader, GL_INFO_LOG_LENGTH) > 0:
            print("Could not compile vertex shader")
            return None
    
        print("Compiling Fragment Shader")
        glShaderSource(frg_shader, FRAGMENT_SHADER_CODE)
        glCompileShader(frg_shader)
        if glGetShaderiv(frg_shader, GL_INFO_LOG_LENGTH) > 0:
            print("Could not compile fragment shader")
            return None
    
       
        
        print("Linking shader program")
        pid = glCreateProgram()
        glAttachShader(pid, vtx_shader)
        glAttachShader(pid, frg_shader)
        glLinkProgram(pid)
        if glGetProgramiv(pid, GL_INFO_LOG_LENGTH) > 0:
            print("Could not link shaders into program")
            return None
       
            
        #cleanup    
        glDetachShader(pid, vtx_shader)
        glDetachShader(pid, frg_shader)
        glDeleteShader(vtx_shader)
        glDeleteShader(frg_shader)
        print("Shader Program Complete")
        self._pid = pid
        return pid
        
    # set up context & window
    
    def _init_window_context(self):
        pygame.init()
        pygame.display.set_mode((self._width, self._height), pygame.OPENGL | pygame.DOUBLEBUF )
        pygame.display.set_caption("Window Title Here")
        pygame.display.iconify()
 
    # intialize vertex buffer
    
    def _draw(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # draw vertices
        glBindTexture(GL_TEXTURE_2D, self._tex_id)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        
    def _init_tex_coord_buffer(self):
        TexCoordBufferDataType = ctypes.c_float*12
        tex_coord_data = TexCoordBufferDataType(
            0.0, 0.0,      
            1.0, 0.0,
            0.0, 1.0, 
            0.0, 1.0,
            1.0, 0.0,
            1.0, 1.0
            )
        self._tcbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._tcbo)
        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(tex_coord_data), tex_coord_data, GL_STATIC_DRAW)
        
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0))
        return self._tcbo
    
    def _init_texture(self):
        self._tex_id = int(glGenTextures(1))
        glBindTexture(GL_TEXTURE_2D, self._tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, self._width, self._height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)

    def update(self):
        self._update_texture()
        glBindFramebuffer(GL_FRAMEBUFFER, self._fbo)
        glViewport(0, 0, self._width, self._height)
        self._draw()
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        glBindTexture(GL_TEXTURE_2D, self._view_tex)
#         openvr.IVROverlay().setOverlayFlag(
#             self._overlay,
#             openvr.VROverlayFlags_SortWithNonSceneOverlays,
#             True)
        openvr.IVROverlay().showOverlay(self._overlay)
        self._overlay_tex = openvr.Texture_t()
        self._overlay_tex.handle = self._view_tex
        self._overlay_tex.eType = openvr.TextureType_OpenGL
        self._overlay_tex.eColorSpace = openvr.ColorSpace_Auto    
#         openvr.IVROverlay().setOverlayColor(self._overlay, 1.0, 1.0, 1.0)
        openvr.IVROverlay().setOverlayTexture(self._overlay, self._overlay_tex)
        openvr.IVRCompositor().submit(openvr.Eye_Right,self._overlay_tex)
#         openvr.IVROverlay().setOverlayAlpha(self._overlay, 1.0)
#         t_bounds = openvr.VRTextureBounds_t()
#         t_bounds.uMin = 0.0
#         t_bounds.uMax = 1.0
#         t_bounds.vMin = 0.0
#         t_bounds.vMax = 1.0
         
         
#         openvr.IVROverlay().setOverlayTextureBounds(
#             self._overlay,
#             t_bounds)   
        
#         openvr.IVROverlay().setOverlayFlag(
#             self._overlay,
#             openvr.VROverlayFlags_VisibleInDashboard,
#             True)
#         openvr.IVROverlay().setOverlayFlag(
#             self._overlay,
#             openvr.VROverlayFlags_SortWithNonSceneOverlays,
#             True)
#         print(openvr.IVROverlay().setHighQualityOverlay(self._overlay))
#         openvr.IVROverlay().setOverlayFlag(
#             self._overlay,
#             openvr.VROverlayFlags_Panorama,
#             True)        

    def _init_vertex_objects(self):
        # vertex array object
        self._vao = glGenVertexArrays(1)
        glBindVertexArray(self._vao)
        
        #vertex buffer object
        VertexArrayType = ctypes.c_float*18
        vbo_data = VertexArrayType( 
            -1.0, -1.0,  0.0,
             1.0, -1.0,  0.0,
            -1.0,  1.0,  0.0,
            -1.0,  1.0,  0.0,
             1.0, -1.0,  0.0,
             1.0,  1.0,  0.0
             )
        
        self._vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo)
        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(vbo_data), vbo_data, GL_STATIC_DRAW)
        
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(
                0,
                3,
                GL_FLOAT,
                GL_FALSE,
                0,
                ctypes.c_voidp(0)
            )
     
    def _update_texture(self):
#         _, img = self._cap.read()
        img = cv2.imread("PATH TO FILE HERE")
        img = cv2.cvtColor(img, cv2.COLOR_RGB2RGBA)
        img = cv2.resize(img,(self._width,self._height))

        
        img = np.asarray(img,dtype=np.uint8)
        glBindTexture(GL_TEXTURE_2D, self._tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0 , GL_RGBA8, self._width, self._height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img.tobytes())
    
    def _position_vr_overlay(self):        # initialize overlay & setup transform to fix overlay to display viewport
        Transform_Type= (ctypes.c_float * 4) * 3
        transform = Transform_Type()
        transform[0][0]  = 1
        transform[0][1]  = 0
        transform[0][2]  = 0
        transform[0][3]  = 0
        
        transform[1][0] = 0
        transform[1][1] = 1
        transform[1][2] = 0
        transform[1][3] = 0
        
        transform[2][0] = 0
        transform[2][1] = 0
        transform[2][2] = 1
        transform[2][3] = -1
        self._hmd_transform = openvr.HmdMatrix34_t()
        self._hmd_transform.m = transform
        
    #set overlay to be fixed to hmd viewport
        openvr.IVROverlay().setOverlayTransformTrackedDeviceRelative(
              self._overlay,
              0,
              self._hmd_transform)
      
    def __del__(self):
        glBindFramebuffer( GL_FRAMEBUFFER, 0)
        glDeleteFramebuffers(1, self._fb)
        try:
            openvr.shutdown()
            print('VR Interface Closed Successfully.')
        except: Exception("Could not properly close VR")
      
    def _init_framebuffer(self):
    
        self._fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self._fbo)
        
        self._dbo = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, self._dbo)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, self._width, self._height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, self._dbo)
        
        self._view_tex = int(glGenTextures(1))
        glBindTexture(GL_TEXTURE_2D, self._view_tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, self._width, self._height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self._view_tex, 0)
        
        glDrawBuffers(1, GL_COLOR_ATTACHMENT0)
        glBindFramebuffer(GL_FRAMEBUFFER, 0) 
        
        
        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
        if status != GL_FRAMEBUFFER_COMPLETE:
            glBindFramebuffer(GL_FRAMEBUFFER, 0)
            raise Exception("Incomplete framebuffer")
        
        glBindTexture(GL_TEXTURE_2D, self._view_tex)
        self._overlay_tex = openvr.Texture_t()
        self._overlay_tex.handle = self._view_tex
        self._overlay_tex.eType = openvr.TextureType_OpenGL
        self._overlay_tex.eColorSpace = openvr.ColorSpace_Auto
        
disp = Displayer() 
disp.update()
 
