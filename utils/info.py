from tabulate import tabulate
from sys import stdout
from datetime import datetime as dt
from datetime import timedelta
from collections import defaultdict
import warnings
import cv2
import platform


class DataCounter:
        """
        Class that summarizes pedestrian info
        """

        def __init__(self):
                self.total_minute_left = 0
                self.total_minute_right = 0
                self.total_minute = 0
                self.total_today_left = 0
                self.total_today_right = 0
                self.total_today = 0

        def add_right(self):
                """
                Update right counter and save values
                """
                self.total_minute_right += 1
                self.total_today_right += 1
                self.total_minute += 1
                self.total_today += 1

        def add_left(self):
                """
                Checks Actual time
                Update left counter and save values
                """
                self.total_minute_left += 1
                self.total_today_left += 1
                self.total_minute += 1
                self.total_today += 1

        def reset_minute_counters(self):
                """
                Resets minute counters to zero
                """
                self.total_minute_left = 0
                self.total_minute_right = 0
                self.total_minute = 0

        def reset_daily_counters(self):
                """
                Resets daily counters to zero
                """
                self.total_today_left = 0
                self.total_today_right = 0
                self.total_today = 0

        def get_minute_data(self):
                """
                Get just minute counters values
                :param hour: int, 0..23, hour of the counter
                :param minute: int, 0..59, minute of the counter
                :return: dict, minute counter values
                """
                return {
                        'lm': self.total_minute_left,
                        'rm': self.total_minute_right,
                        "tm": self.total_minute,
                }

        def get_daily_data(self):
                """
                Get just daily counters values
                :return dict, daily counter values
                """
                return {
                        'ld': self.total_today_left,
                        'rd': self.total_today_right,
                        "td": self.total_today
                }

        def reset(self):
                self.reset_minute_counters()
                self.reset_daily_counters()


class ConsoleParams:
        """
        Class containing parameters to be presented
        on terminal
        """
        system: str = platform.system() + ' ' + platform.processor()
        fps: float
        detected_people: bool = False
        total_minute_left: int = 0
        total_minute_right: int = 0
        total_minute: int = 0
        total_today_left: int = 0
        total_today_right: int = 0
        total_today: int = 0



def print_console(params: ConsoleParams):
#def print_console(console, params: ConsoleParams):
        """
        Runs a Dynamic Terminal to present program info
        :param console: Terminal Object
        :param params: ConsoleParams object
        """
        fps = round(params.fps, 2)
        seconds = 59 - dt.now().second

        template = tabulate(
                [
                        ["FPS:", str(fps)],
                        ["Time", str(dt.now().hour) + ':' + str(dt.now().minute)],
                        ["Data sent in (sec)", seconds],
                        ["New Data", params.detected_people],
                        ["--------------", '------------'],
                        ["Minute Left/Right", str(params.total_minute_left) + '/' + str(params.total_minute_right)],
                        ["TOTAL MINUTE", params.total_minute],
                        ["Daily Left/Right", str(params.total_today_left) + '/' + str(params.total_today_right)],
                        ["TOTAL DAILY", params.total_today]
                ]
        )
        
        #console.clear()
        #console.addstr(params.system + '\n')
        #console.addstr(template + '\n')
        
        #console.refresh()
        print(params.system)
        print(template)


def print_fps_on_terminal(fps):
        """
        prints one line on terminal dynamically
        :param fps:
        :return:
        """
        stdout.write("\r{0} {1}>".format("[*] fps", fps))


def print_fps_on_frame(frame, fps):
        """
        takes a frame and returns same frame with fps on the upperleft corner
        :param frame: numpy array, image
        :param fps: float, fps value
        :return: printed frame
        """
        
        fr = frame
        cv2.putText(
                fr,
                "FPS: " + str(round(fps, 2)),
                # + str(bbox.dx) + ' ' + str(bbox.dy) ,
                # + ': ' + str(bbox.name),
                (30, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0),
                2
        )
        
        return fr


def print_items_to_frame(frame, items):
        """
        take bboxes items from dict and print them into frame
        :param frame: numpy array, image
        :param items: orderedDict with bboxes on values
        :return: numpy array, new frame
        """
        
        fr = frame
        
        for (k, v) in items.items():
                ids = k
                bbox = v
                
                text_over_bbox = str(ids) + ': ' + bbox.mov[1]
                
                fr = cv2.rectangle(
                        fr,
                        bbox.start_point,
                        bbox.end_point,
                        bbox.color,
                        2)
                
                cv2.putText(
                        fr,
                        text_over_bbox,
                        bbox.start_point,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        bbox.color,
                        2
                )
        
        return fr


def print_bboxes_to_frame(frame, bboxes):
        """
        take bboxes and print them into frame
        :param frame: numpy array, image
        :param bboxes: bboxssd objects
        :return: numpy array, new frame
        """
        
        fr = frame
        
        for bbox in bboxes:
                fr = cv2.rectangle(
                        frame,
                        bbox.start_point,
                        bbox.end_point,
                        bbox.color,
                        2)
                
                cv2.putText(
                        fr,
                        bbox.name,
                        # + ': ' + str(bbox.name),
                        bbox.start_point,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        bbox.color,
                        2
                )
        
        return fr
