'''
Created on Sep 15, 2019

@author: chich
'''




import socket
import matplotlib.pyplot as plt 
import numpy as np
import keyboard
import subprocess
import psutil
class EyeTracker(object):
    '''
    The eye tracker class interfaces and grabs pupil position data from the Pupil-labs
    eye tracker integrated into the HTC Vive Headset. Communication is via a TCP socket
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


eye_tracker = EyeTracker()

# plt.figure()
# plt.ion()

# ax = plt.scatter(0,0)
# plt.show()
while True:
    if keyboard.is_pressed("enter"):
        break
    else:
        pos = eye_tracker.get_gaze_pos()
        print(pos)
#         plt.cla()
#         plt.scatter(pos[0],pos[1])
#         plt.xlim([0,1])
#         plt.ylim([0,1])
#         plt.pause(0.01)

