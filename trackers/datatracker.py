from collections import OrderedDict
import copy

class DataTracker:
        
        def __init__(self, bboxtracker):
                
                self._updated_objects = bboxtracker.objects
                self._objects = self._updated_objects.copy()
                self.tracked_ids = []
        
        def get_deregistered_bboxes_ids(self):
                updated_tracked_ids = list(self._updated_objects.keys())
                are_equal = (updated_tracked_ids == self.tracked_ids)
                deregistered_bboxes_ids = []
                if not are_equal:
                        for actual_id in self.tracked_ids:
                                if actual_id not in updated_tracked_ids:
                                        deregistered_bboxes_ids.append(actual_id)
                
                return deregistered_bboxes_ids
        
        def get_deregistered_bboxes_directions(self):
                
                deregistered_ids = self.get_deregistered_bboxes_ids()
                directions = []
                for i in deregistered_ids:
                        direction = self.get_bbox_direction(i)
                        directions.append(direction)
                return directions
        
        def get_bbox_direction(self, ids):
                bbox = self._objects.get(ids)
                direction = bbox.mov[0]
                return direction
        
        def update(self):
                
                directions = self.get_deregistered_bboxes_directions()
                self._objects = self._updated_objects.copy()
                self.tracked_ids = list(self._updated_objects.keys())
                return directions
#
#
# if __name__ == '__main__':
