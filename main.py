import jetson.inference
import jetson.utils
import cv2
import sys
import time
import os
import datetime
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime as dt
from utils import utils, classes, info, backend
from trackers.bboxssd import BBox
from trackers.bboxssdtracker import BBoxTracker
from trackers.datatracker import DataTracker
#import curses

isdaemon = "DAEMONIZE_ME" in os.environ and os.environ["DAEMONIZE_ME"] in ["on", "1", "true"]

if isdaemon:
  import systemd.daemon

# do "touch /home/username/Desktop/StreetQR/gimmeit" to get snapshots from both cameras
saveFilesOnDemand = isdaemon
saveFileThisTime  = False


if __name__ == "__main__":
        
        # ---------------------------------------
        #
        #      PARAMETER INITIALIZATION
        #
        # ---------------------------------------
        
        # Show live results
        # when production set this to False as it consume resources
        SHOW = True
        VIDEO = False

        firebase_project_id = "streetqr"
        firebase_private_key_path = os.path.abspath("streetqrm.json")
        cred = credentials.Certificate(firebase_private_key_path)
        firebase_admin.initialize_app(cred, {
          'projectId': firebase_project_id,
        })

        fb = firestore.client()

        doc_ref = fb.collection('log').document("streetqr_start")
        start_log = {}
        start_log["name"] = "streetqr"
        start_log["date"] = "test"
        print(start_log)
        doc_ref.set(start_log)
        
        # load the object detection network
        arch = "ssd-mobilenet-v2"
        overlay = "box,labels,conf"
        threshold = 0.7
        W, H = (640, 480)
        net = jetson.inference.detectNet(arch, sys.argv+["--log-level=error"], threshold)
        
        # Start printing console
        #console = curses.initscr()
        consoleConfig = info.ConsoleParams()
        
        # Get array of classes detected by the net
        classes = classes.classesDict
        # List to filter detections
        pedestrian_classes = [
                "person"
        ]
        
        # Initialize Trackers
        ped_tracker = BBoxTracker(50)
        data_tracker = DataTracker(ped_tracker)
        data_counter = info.DataCounter()

        # Track actual minute day
        actual_min = dt.now().minute
        actual_day = dt.now().day
        # whether people are crossing through the camera field
        people_crossing = False

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
        if isdaemon:
          systemd.daemon.notify('READY=1')
          timestart = datetime.datetime.now()
          minute_count = -1
        
        while True:
                
                start_time = time.time()  # start time of the loop

                if saveFilesOnDemand and os.path.isfile('gimmeit'):
                   try:
                     os.remove('gimmeit')
                   except:
                     pass
                   saveFileThisTime = True


                
                # ---------------------------------------
                #
                #              DETECTION
                #
                # ---------------------------------------
                
                # if we are on Jetson use jetson inference
                if is_jetson:
                        
                        # get frame from crosswalk and detect
                        #print("BEFORE GETTING SNAPSHOT")
                        crosswalkMalloc, _, _ = Cam.CaptureRGBA(zeroCopy=saveFileThisTime)
                        if saveFileThisTime:
                          crosswalk_numpy_img = jetson.utils.cudaToNumpy(crosswalkMalloc, W, H, 4)
                        #print("BEFORE DETECTING WITH DEEP LEARNING")
                        pedestrianDetections = net.Detect(crosswalkMalloc, W, H, overlay)
                        #print("AFTER DETECTING WITH DEEP LEARNING")

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
                        #people_crossing = True
                        #data_counter.add_left()
                        #data_counter.add_left()
                        #data_counter.add_right()
                        if people_crossing:
                                # if so, send new data to server
                                data_minute = data_counter.get_minute_data()
                                data_daily = data_counter.get_daily_data()
                                backend.post_minute_data(data_minute, fb)
                                backend.post_daily_data(data_daily, fb)
                                people_crossing = False

                        # Reset Minute Counters
                        data_counter.reset_minute_counters()

                        # Every day
                        if actual_day != dt.now().day:
                                actual_day = dt.now().day
                                # Reset Local Counters
                                data_counter.reset()
                                # Update Server Counters
                                data_daily = data_counter.get_daily_data()
                                backend.post_daily_data(data_daily, fb)
                                data_counter.reset_daily_counters()

                # ---------------------------------------
                #
                #           SHOWING PROGRAM INFO
                #
                # ---------------------------------------
                
                # Transform CUDA MALLOC to NUMPY frame is
                # highly computationally expensive for Jetson Platforms
                if isdaemon:
                  time_delta = datetime.datetime.now() - timestart
                  #print(time_delta)
                  systemd.daemon.notify('WATCHDOG=1')
                  delta_minutes = time_delta.seconds // 60
                  if delta_minutes!=minute_count:
                    # Configure Console Data
                    consoleConfig.detected_people = people_crossing
                    consoleConfig.total_minute_left = data_counter.total_minute_left
                    consoleConfig.total_minute_right = data_counter.total_minute_right
                    consoleConfig.total_minute = data_counter.total_minute
                    consoleConfig.total_today_left = data_counter.total_today_left
                    consoleConfig.total_today_right = data_counter.total_today_right
                    consoleConfig.total_today = data_counter.total_today
                    consoleConfig.fps = 1.0 / (time.time() - start_time)
                    info.print_console(consoleConfig)
                    minute_count = delta_minutes
                  if saveFileThisTime:
                    saveFileThisTime = False
                    crosswalk_numpy_img = info.print_items_to_frame(crosswalk_numpy_img, pedestrians)
                    stamp = datetime.datetime.now().strftime("%Y.%m.%d.%H.%M")
                    cv2.imwrite('crosswalk.%s.jpg' % stamp, crosswalk_numpy_img)
                    del crosswalk_numpy_img
                elif SHOW:
                        # Configure Console Data
                        consoleConfig.detected_people = people_crossing
                        consoleConfig.total_minute_left = data_counter.total_minute_left
                        consoleConfig.total_minute_right = data_counter.total_minute_right
                        consoleConfig.total_minute = data_counter.total_minute
                        consoleConfig.total_today_left = data_counter.total_today_left
                        consoleConfig.total_today_right = data_counter.total_today_right
                        consoleConfig.total_today = data_counter.total_today
                        consoleConfig.fps = 1.0 / (time.time() - start_time)
                        
                        # SHOW DATA IN CONSOLE
                        #info.print_console(console, consoleConfig)
                        info.print_console(consoleConfig)
                        
                        # If not in Jetson Platform show Camera Frames and Detections
                        if False:# not is_jetson:

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
                if not isdaemon:
                  key = cv2.waitKey(1) & 0xFF
                  if key == ord("q"):

                        # close any open windows
                        #curses.endwin()
                        cv2.destroyAllWindows()
                        break
