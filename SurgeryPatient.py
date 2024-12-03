# A class representing patients referred to Neurosurgery
# The patient's RTT clock tends to stop on admission for surgery

import random

class Patient:
    def __init__(self, p_id, 
                 already_seen_clinic=False,
                 needs_surgery=False, 
                 before_end_sim=True, 
                 from_prefills=False
                 ):
        
        self.id = p_id
        self.needs_surgery = False

        self.time_entered_pathway = 0
        
        self.clinic_queue_time = 0
        self.theatre_queue_time = 0
        self.overall_queue_time = 0

 
        #attributes to help with pre filling queues
        self.already_seen_clinic = False

        #attribute for before/after end of sim
        self.before_end_sim = True

        #attribute for patients who are pre-filled into queues
        self.from_prefills = False


