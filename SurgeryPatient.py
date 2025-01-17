class Patient:
    """
    A class representing patients referred to Neurosurgery

    The patient's RTT clock tends to stop on admission for surgery
    """
    def __init__(self, p_id):

        self.id = p_id
        self.needs_surgery = False

        self.time_entered_pathway = 0

        self.clinic_queue_time = 0
        self.theatre_queue_time = 0
        self.overall_queue_time = 0

        # Attribute for patients who are pre-filled into queues
        self.from_prefills = False

        # Attributes to help with pre filling queues
        self.already_seen_clinic = False

        # Attribute for whether a patient is added to the waiting list before or after
        # the end of the simulation.
        # The simulation continues to run after the 'end time' of the simulation - the
        # requested simulation time just controls how long we keep adding patients into the
        # simulation who we want to keep track of
        self.before_end_sim = True
