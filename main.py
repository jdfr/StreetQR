import jetson.inference
import jetson.utils
import cv2
import sys
import time
from firebase import firebase

from datetime import datetime as dt
from utils import utils, classes, info, backend
from trackers.bboxssd import BBox
from trackers.bboxssdtracker import BBoxTracker
from trackers.datatracker import DataTracker
import platform
import curses


if __name__ == "__main__":
        
        # ---------------------------------------
        #
        #      PARAMETER INITIALIZATION
        #
        # ---------------------------------------
        
        # Show live results
        # when production set this to False as it consume resources
        SHOW = True
        VIDEO = True
        
        # load the object detection network
        arch = "ssd-mobilenet-v2"
        overlay = "box,labels,conf"
        threshold = 0.7
        W, H = (800, 480)
        net = jetson.inference.detectNet(arch, sys.argv, threshold)
        
        # Start printing console
        # console = curses.initscr()
        consoleConfig = info.ConsoleParams()
        consoleConfig.system = platform.system()
        
        # Get array of classes detected by the net
        classes = classes.classesDict
        # List to filter detections
        pedestrian_classes = [
                "person"
        ]
        
        # Initialize Trackers
        ped_tracker = BBoxTracker(15)
        data_tracker = DataTracker(ped_tracker)
        data_counter = info.DataCounter()

        actual_min = dt.now().minute
        actual_day = dt.now().day
        people_crossing = False

        fb = firebase.FirebaseApplication("https://smart-campus-uma.firebaseio.com/", None)
        # check if running on jetson
        is_jetson = utils.is_jetson_platform()

        # ---------------------------------------
        #
        #      VIDEO CAPTURE INITIALIZATION
        #
        # ---------------------------------------
        
        VIDEO_PATH = "video/crosswalk.mpg"
        
        # Get two Video Input Resources
        # Rather from VIDEO file (testing) or CAMERA file
        
        if VIDEO:
                print('[*] Starting video...')
                Cam = cv2.VideoCapture(VIDEO_PATH)
                
                # Override initial width and height
                W = int(Cam.get(3))  # float
                H = int(Cam.get(4))  # float
                
                if is_jetson:
                        raise Exception("Video Files are not supported on Jetson Inference, use camera instead")
                
        
        elif is_jetson:
                # If in jetson platform initialize Cameras from CUDA (faster inferences)
                print('[*] Starting camera...')
                Cam = jetson.utils.gstCamera(W, H, "/dev/video0")
        
        else:
                # If NOT in jetson platform initialize Cameras from cv2 (slower inferences)
                # Set video source from camera
                print('[*] Starting camera...')
                
                Cam = cv2.VideoCapture(0)
                
                # Override initial width and height
                W = int(Cam.get(3))  # float
                H = int(Cam.get(4))  # float
        
        # ---------------------------------------
        #
        #      VIDEO PROCESSING MAIN LOOP
        #
        # ---------------------------------------

        print('[*] Starting MAIN LOOP [*]')
        
        while True:
                
                start_time = time.time()  # start time of the loop
                
                # ---------------------------------------
                #
                #              DETECTION
                #
                # ---------------------------------------
                
                # if we are on Jetson use jetson inference
                if is_jetson:
                        
                        # get frame from crosswalk and detect
                        crosswalkMalloc, _, _ = Cam.CaptureRGBA()
                        pedestrianDetections = net.Detect(crosswalkMalloc, W, H, overlay)

                # If we are NOT on jetson use CV2
                else:
                        # Check if more frames are available
                        if Cam.grab():
                                # capture the image
                                _, crosswalkFrame = Cam.read()
                        else:
                                print("no more frames")
                                break
                        
                        # Synchronize system
                        jetson.utils.cudaDeviceSynchronize()
                        
                        # Get Cuda Malloc to be used by the net
                        # Get processes frame to fit Cuda Malloc Size
                        crosswalkFrame, crosswalkMalloc = utils.frameToCuda(crosswalkFrame, W, H)
                        
                        # Get detections Detectnet.Detection Object
                        pedestrianDetections = net.Detect(crosswalkMalloc, W, H, overlay)
                
                # ---------------------------------------
                #
                #               TRACKING
                #
                # ---------------------------------------
                
                # Initialize bounding boxes lists
                ped_bboxes = []
                
                # Convert Crosswalk Detections to Bbox object
                # filter detections if recognised as pedestrians
                # add to pedestrian list of bboxes
                for detection in pedestrianDetections:
                        bbox = BBox(detection)
                        if bbox.name in pedestrian_classes:
                                ped_bboxes.append(bbox)
                
                # Relate previous detections to new ones
                # updating trackers
                pedestrians = ped_tracker.update(ped_bboxes)
                # If a person exits from camera visual field
                # data_tracker will return his/her direction
                # ['left, 'right, ...]
                removed_pedestrians_directions = data_tracker.update()
                
                # ---------------------------------------
                #
                #           POST DATA TRACKING
                #
                # ---------------------------------------
                
                # add people walking directions to counter
                for direction in removed_pedestrians_directions:
                        if direction == 'left':
                                data_counter.add_left()
                        if direction == 'right':
                                data_counter.add_right()
                        # If anyone has crossed the camera field
                        # data can be sent to server
                        # otherwise no data is sent
                        people_crossing = True
                
                # Every minute
                if actual_min != dt.now().minute:
                        actual_min = dt.now().minute
                        # Check if people crossed during the last minute
                        if people_crossing:
                                # if so, send new data to server
                                data_minute = data_counter.get_minute_data()
                                data_daily = data_counter.get_daily_data()
                                backend.post_minute_data(data_minute, fb)
                                backend.post_daily_data(data_daily, fb)
                                people_crossing = False
                        
                        # Every day
                        if actual_day != dt.now().day:
                                actual_day = dt.now().day
                                # Reset Local Counters
                                data_counter.reset()
                                # Update Server Counters
                                data_daily = data_counter.get_daily_data()
                                backend.post_daily_data(data_daily, fb)

                # ---------------------------------------
                #
                #           SHOWING PROGRAM INFO
                #
                # ---------------------------------------
                
                # Transform CUDA MALLOC to NUMPY frame is
                # highly computationally expensive for Jetson Platforms
                if SHOW:
                        
                        consoleConfig.fps = 1.0 / (time.time() - start_time)
                        # SHOW DATA IN CONSOLE
                        # info.print_console(console, consoleConfig)
                        if not is_jetson:

                                # Print square detections into frame
                                crosswalkFrame = info.print_items_to_frame(crosswalkFrame, pedestrians)
                                # Print fps to frame
                                crosswalkFrame = info.print_fps_on_frame(crosswalkFrame, consoleConfig.fps)
                                
                                # Show the frames
                                cv2.imshow("Crosswalk CAM", crosswalkFrame)

                # ----------------------------------
                #
                #           PROGRAM END
                #
                # ----------------------------------

                # Quit program pressing 'q'
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):

                        # close any open windows
                        curses.endwin()
                        cv2.destroyAllWindows()
                        break
