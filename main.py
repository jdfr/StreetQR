import jetson.inference
import jetson.utils
import cv2
import sys
import time
from utils import utils, classes, gpios, cameras, info, tracking, contour
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
        data_counter = info.DataCounter()
        ped_tracker = BBoxTracker(15)
        data_tracker = DataTracker(ped_tracker)
        
        # check if running on jetson
        is_jetson = utils.is_jetson_platform()
        # Activate Board
        if is_jetson: gpios.activate_jetson_board()
        
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
        
        elif is_jetson:
                # If in jetson platform initialize Cameras from CUDA (faster inferences)
                print('[*] Starting camera...')
                Cam = jetson.utils.gstCamera(W, H, "dev/video0")
        
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
                removed_pedestrians_directions = data_tracker.update()
                
                # ---------------------------------------
                #
                #           POST DATA TRACKING
                #
                # ---------------------------------------
                
                for direction in removed_pedestrians_directions:
                        if direction == 'left': data_counter.add_left()
                        if direction == 'right': data_counter.add_right()
                
                # ---------------------------------------
                #
                #           SHOWING PROGRAM INFO
                #
                # ---------------------------------------
                
                consoleConfig.fps = 1.0 / (time.time() - start_time)

                # Transform CUDA MALLOC to NUMPY frame is
                # highly computationally expensive for Jetson Platforms
                if SHOW and not is_jetson:

                        # Print square detections into frame
                        crosswalkFrame = info.print_items_to_frame(crosswalkFrame, pedestrians)
                        # Print fps to frame
                        crosswalkFrame = info.print_fps_on_frame(crosswalkFrame, consoleConfig.fps)
                        
                        # Show the frames
                        cv2.imshow("Crosswalk CAM", crosswalkFrame)

                # SHOW DATA IN CONSOLE
                # info.print_console(console, consoleConfig)
                
                # ----------------------------------
                #
                #           PROGRAM END
                #
                # ----------------------------------
                
                # Quit program pressing 'q'
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                        # free GPIOs before quit
                        if is_jetson:
                                gpios.warning_OFF()
                                gpios.deactivate_jetson_board()
                        # close any open windows
                        curses.endwin()
                        cv2.destroyAllWindows()
                        break
