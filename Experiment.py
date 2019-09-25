'''
Created on Sep 17, 2019

@author: Chris Fritz
Initial Function Definitions for Psychophysics Experiments
See README for more information.
'''

import socket
import numpy as np
import keyboard 
from OpenGL.GL import * #@UnusedWildImport   #stop annoying warning
from OpenGL.GLUT import * #@UnusedWildImport   
from OpenGL.GLU import * #@UnusedWildImport
import openvr
import subprocess
import cv2
import psutil
import pygame
import SpoutSDK


class PositionSender(object):
    '''
    The PositionSender object transmits head position and rotation information to 
    the Unity Game engine. 
    First, attach the script "PythonCaller.cs" to a camera representing the subject's 
    viewport into the environment.  Then instantiate a PositionSender. To send data,
    call [object].send(head_rotation, head_position) at the beginning of every frame.
    head_rotation and head_position can be obtained from the VR Interface. 
    ''' 
    def __init__(self):
        '''
        Initializes a  TCP socket connection with Unity.
        In its current state, you need to restart the Unity scene (stop and press play)
        in order to reconnect the PositionSender to Unity.  
        #TODO: Implement Proper error handling and open/close communication b/t this script
        and PythonCaller.cs in Unity
        '''
        
        self._HOST = "localhost"
        self._PORT = 9999
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
                self._sock.connect((self._HOST, self._PORT))
        except:
            print("Could not connect to Unity Server")
                
    def send(self,head_rot, head_pos):
        ''' Send Position & Rotation Data as an array of 7 doubles,
 
        the first 4 elements are the quaternion, and the remaining
        3 are the head position in 3d space
        input: head_rot: a numpy array of 4 doubles representing head rotation
               head_pos: a numpy array of 4 doubles representing head position
        '''
        try:
            self._sock.sendall(np.array(np.hstack((head_rot,head_pos)),dtype=np.float32))
        except:
            print('Could not send position to Unity, make sure receiver is running')     
            
    def _del(self):
        try:
            self._sock.close()
        except:
            print("Could not successfully close TCP socket.")           
    
class VRInterface(object):
    '''
    This class instantiates an interface object for the HTC Vive. It controls
    all I/O to and from the HMD, including head position tracking and video writing. 
    To use, initialize class by instantiating, head position can then be accessed using
    the get_head_pos() method. To upload a frame to the HMD, update the self._view_wnd display
    with the desired frame. (This is done once on every call to update()
    '''
    
    def __init__(self):
        ''' '''
        #1440 x 1600 pixels per eye
        self._width = 2880
        self._height = 1600
        
        try:
            openvr.init(openvr.VRApplication_Scene)
        except: Exception("Could Not Initialize VR Headset")         
        self._poses = []
        print("VR Interface Initialized Successfully.")
        
        # setup capture device for debugging
        # (video does not loop so script terminates with error when video finishes)
        self._cap = cv2.VideoCapture("sample_vid.mp4")
        self._view_wnd = "VR Display"
        
        # setup vr eye display 
        cv2.namedWindow(self._view_wnd)
        cv2.moveWindow(self._view_wnd,2*1920,-300)  #Using VR with DirectDisplay disabled, 
                                                    #Position the window in the HMD display
        cv2.setWindowProperty(self._view_wnd,cv2.WND_PROP_FULLSCREEN,  cv2.WINDOW_FULLSCREEN )
        
        
        #setup image processor 
        self._img_processor = ImageProcessor(self._width, self._height)

        #update to grab first data from VR Headset
        self.update()

    def update(self):
        ''' 
        Update the tracking data by retreiving from HMD. Because this method captures tracking
        data relevant to the rendering scene, update should be called at the start of each frame.
        '''
        self._poses = openvr.IVRSystem().getDeviceToAbsoluteTrackingPose(
            openvr.TrackingUniverseStanding,
            0.001,
            openvr.TrackedDevicePose_t()
        )
        
        frame = self._img_processor.get_processed_image()
        cv2.imshow(self._view_wnd,frame)
        cv2.waitKey(1)  #need waitkey(1) for Imshow to display videos properly.
           
    def get_head_position(self):
        ''' Return the position of the head in a numpy vector '''
        x = self._poses[openvr.k_unTrackedDeviceIndex_Hmd].mDeviceToAbsoluteTracking[0][3]
        y = self._poses[openvr.k_unTrackedDeviceIndex_Hmd].mDeviceToAbsoluteTracking[1][3]
        z = self._poses[openvr.k_unTrackedDeviceIndex_Hmd].mDeviceToAbsoluteTracking[2][3]
         # The -z is so that the movement in physical space matches movement in virtual space
        return np.asarray([x,y,-z])
    
    def get_head_rotation(self):
        ''' Return the head rotation data as a quaternion object.The data is converted from the rotation
        matrix to a quaternion object
        a quaternion representation See http://www.allenchou.net/2014/04/game-math-quaternion-basics/
        for detials on quaternion matricies and operations
        ''' 
        matrix = self._poses[openvr.k_unTrackedDeviceIndex_Hmd].mDeviceToAbsoluteTracking
        w = np.sqrt(np.fmax(0,1 + matrix[0][0]+matrix[1][1]+matrix[2][2])) / 2
        x = np.sqrt(np.fmax(0,1 + matrix[0][0]-matrix[1][1]-matrix[2][2])) / 2
        y = np.sqrt(np.fmax(0,1 - matrix[0][0]+matrix[1][1]-matrix[2][2])) / 2
        z = np.sqrt(np.fmax(0,1 - matrix[0][0]-matrix[1][1]+matrix[2][2])) / 2
        
        x = np.copysign(x, matrix[2][1]- matrix[1][2])
        y = np.copysign(y, matrix[0][2]- matrix[2][0])
        z = np.copysign(z, matrix[1][0]- matrix[0][1])
        # flip sign of w and z so that physical and virtual coordinate systems match
        return np.array((-w,x,y,-z))
    
    def __del__(self):
        try:
            openvr.shutdown()
            print('VR Interface Closed Successfully.')
        except:
            print("Could not close VR Interface. Restart the HMD")
            
class EyeTracker(object):
    '''
    The eye tracker class interfaces and grabs pupil position data from the Pupil-labs
    eye tracker integrated into the HTC Vive Headset. Communication is via a TCP socket
    Make sure pupil_capture folder is in same directory (or update _pupil_handle with its path)
    Further, make sure that the transmitting plugin transmit_gaze.py is in the Pupil Catpure plugins
    foler and is enabled. Initialization will halt until it receives input from Pupil Gaze Data
    '''

    def __init__(self):
        '''
        Initialize the interface to the Pupil Eye Tracker.
        The transmit_gaze.py script must be in the pupil_capture_settings\plugins
        folder (or pupil capture plugin directory) in order to initialize
        '''        
        self._HOST = '127.0.0.1'
        self._PORT = 8888
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self._HOST, self._PORT))
        self._socket.listen()
        self._pupil_handle = subprocess.Popen("pupil_capture\\pupil_capture.exe")
        self._conn, self._addr = self._socket.accept()
        self._eye_pos = (0,0,0,0)
        
    def get_gaze_pos(self):
        '''
        Return the gaze position in normalized screen coordinates
        bottom left is (0,0), top right is (1,1)
        '''
        while True:
            pos = np.frombuffer(self._conn.recv(8),dtype=np.float32)
            if pos is not None:
                return (pos[0], pos[1])
        
    def __del__(self):
        self._socket.close()
    
        process = psutil.Process(self._pupil_handle.pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()

#vr_int = VRInterface()
#sender = PositionSender()

# running = True
#   
# while running:
#     vr_int.update()
#     if keyboard.is_pressed('enter'):
#         break
#     pos = vr_int.get_head_position()
#     rot = vr_int.get_head_rotation()
#     sender.send(rot, pos)

class ImageProcessor(object):
    '''
    The image processor receives the image from the Unity-rendered environment,
    the eye position from the eye tracker and processes that image accordingly.
    To receive the processed image, call get_processed_image(). 
    '''

    def __init__(self, width, height):
        ''' 
        Initialize the Image Processor
        '''
        self._eye_tracker = EyeTracker()
        
        # width and height here are to the Viewport in Unity; from the transmitting camera
        self._width = width
        self._height = height 
        self._spout_name = "UnitySender"
        self._spout_size = (width,height)
        self.calibrate()
        self._init_Spout()
        self._init_GL()
        self._processed_img = np.zeros(self._spout_size,dtype=np.ubyte)
  
  
    def _init_Spout(self):
        '''
        Initalize a Spout receiver using Python Bindings for Spout C++ SDK. 
        Source code from: https://github.com/spiraltechnica/Spout-for-Python
        '''
        # create spout receiver
        self._spout_receiver = SpoutSDK.SpoutReceiver()
    
        # Its signature in c++ looks like this: bool pyCreateReceiver(const char* theName, unsigned int theWidth, unsigned int theHeight, bool bUseActive);
        self._spout_receiver.pyCreateReceiver(self._spout_name,
                                              self._spout_size[0],
                                              self._spout_size[1],
                                              False
        )
        
    def _init_GL(self):
        ''' 
        Initializes an OpenGL context via PyGame module. The window must exist for OpenGL
        to function, but is automatically minimized via iconify to avoid cluttering screenspace.
        ''' 
        # OpenGL init
        
        # window setup
        pygame.init() 
        pygame.display.set_caption('Spout Receiver')
        pygame.display.set_mode((self._width,self._height),pygame.DOUBLEBUF| pygame.OPENGL)
        pygame.display.iconify()
        
        # OpenGL init
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0,self._width,self._height,0,1,-1)
        glMatrixMode(GL_MODELVIEW)
        glDisable(GL_DEPTH_TEST)
        glClearColor(0.0,0.0,0.0,0.0)
        glEnable(GL_TEXTURE_2D)
        
    
    
        # create texture for spout receiver
        self._tex_id = glGenTextures(1).item()    
        
        # initalise receiver texture
        glBindTexture(GL_TEXTURE_2D, self._tex_id)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    
        # copy data into texture
        glTexImage2D(GL_TEXTURE_2D, 0, GL_LUMINANCE, self._spout_size[0], self._spout_size[1], 0, GL_LUMINANCE, GL_UNSIGNED_BYTE, None ) 
        glBindTexture(GL_TEXTURE_2D, 0)

    def calibrate(self):
        '''
        Calibrate the eye tracker by mapping pupil gaze position to screen position in the given image.
        The coordinate space for images is (0,0) at bottom left, and (1,1) at top right
        FUNCTION IS BUGGED AND NOT FULLY IMPLEMENTED: CALIBRATION NEEDS FURTHER WORK        
        '''
        NUM_LOOPS = 2
        CALIBRATION_POINTS = [
            (.5, .5), # center of screen
            ( 0,  0), # bottom left
            ( 1,  0), # bottom right
            ( 0,  1), # top left
            ( 1,  1)  # top right 
            ]
        DX = 25  
        DY = DX
        
        #collect data matrix
        num_data_points = NUM_LOOPS * len(CALIBRATION_POINTS)
        eye_pos_data = np.zeros((2, num_data_points))
        screen_data  = np.zeros((2, num_data_points))
        data_idx = 0
        cv2.namedWindow('calibration')
        cv2.resizeWindow('calibration',(500,100))
        # position window on VR display. 
        cv2.moveWindow('calibration',int(2*1920)+int(1920/2)-100,-300)
        #for num loops     
        for i in np.arange(NUM_LOOPS):
            # loop through each calibration point:
            for cp in CALIBRATION_POINTS:
                # plot the calibration point
                img = np.ones((self._height, self._width, 3))
                x = int(cp[0]*self._width)
                y = int(cp[1]*self._height)
                
                if cp == (.5, .5):
                    img[ y-int(DY/2) : y+int(DY/2),  x-int(DX/2) : x+int(DX/2), 1:2] = 0
                
                elif cp == (0 , 0):
                    img[ self._height - DY : self._height, 0 : DX, 1:2] = 0
                      
                elif cp == (1, 0):
                     img[ self._height-DY : self._height,  x-DX : x, 1:2] = 0
                     
                elif cp == (0, 1):
                    img[ 0 : DY,  0 : DX, 1:2] = 0
                 
                elif cp == (1, 1):
                    img[0 : DY,  self._width-DX : self._width, 1:2] = 0
                cv2.imshow('calibration', img)
                # wait for user to fixate and press key when ready
                cv2.waitKey(0)
                # record the pupil position, and screen position
                eye_pos_data[: , data_idx] = self._eye_tracker.get_gaze_pos()
                screen_data[:, data_idx] = cp
                data_idx += 1
        # calculate least squares fit from pupil position to screen position
        eye_to_screen_transform = np.linalg.lstsq(eye_pos_data.T , screen_data.T, rcond = None)[0]
        
        # set pupil transformation matrix  
        self._eye_to_screen_transform = eye_to_screen_transform

    def get_processed_image(self):
        '''
        The get_processed_image function retreives the uncalibrated gaze position from the 
        eye tracker, then transforms it according to the calibrated eye_to_screen_transform,
        and finally processed that image according to eye position. 
        In this implementation, it is simply a black square of width 500pixels
        centered around the eye position. The processed image is returned.
        '''
        (rx, ry) = (self._eye_tracker.get_gaze_pos())

        # calibrate rx, ry to screen 
        rx,ry = self._eye_to_screen_transform.T@np.array([ry,rx])
        r_x_coord = int(rx)
        r_y_coord = int(ry) 
         
        print(r_x_coord,r_y_coord)
        
        # Width/Height of Black Window
        dx = 500 
        dy = 500
        self._processed_img = self._get_unity_img()
        self._processed_img[r_x_coord:r_x_coord+dx,r_y_coord:r_y_coord+dy] = 0
        print('xbounds zeroed:', r_x_coord,r_x_coord+dx)
        print('ybounds zeroed:', r_y_coord,r_y_coord+dy)
        return self._processed_img
        
    def _get_unity_img(self):
        ''' 
        Using OpenGL and Spout, capture the image data from the Unity Engine being transmitted
        by the spout_sender camera.  Return this data as a numpy aray containing luminance data. 
        (Can change GL_LUMINANCE to GL_RGB/RGBA to capture color images)
        
        '''
        glBindTexture(GL_TEXTURE_2D, self._tex_id)
        self._spout_receiver.pyReceiveTexture(self._spout_name, 
                                              self._spout_size[0],
                                              self._spout_size[1],
                                              self._tex_id,
                                               GL_TEXTURE_2D, False, 0)
       

          
        data = glGetTexImage(GL_TEXTURE_2D, 0, GL_LUMINANCE, GL_UNSIGNED_BYTE, outputType=None) 
        return(np.reshape(np.frombuffer(data,dtype=np.ubyte),(self._spout_size[1],self._spout_size[0]))).T
        
    def __del__(self):
        self._spout_receiver.ReleaseReceiver()      
