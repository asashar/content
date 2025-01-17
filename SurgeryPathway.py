# A class containing functions to model the Neurosurgery RTT pathway

import simpy
import random
import numpy as np
import pandas as pd
import csv

from SurgeryPatient import Patient
from global_params import g

import logging
# log = logging.getLogger(__name__)

from utils import setup_logger
log = setup_logger(level=logging.INFO)  # Configure global logging

class Neurosurgery_Pathway:
    """
    Defines a model that puts patients through a multi-step neurosurgery pathway.

    Parameters
    ------

    run_number: int
        Unique identifier for the simulation run.

    referrals_per_week: int, default is `g.referrals_per_week`
        Average number of new referrals received to this pathway per week.

    surg_clinic_per_week: int, default is `g.surg_clinic_per_week`
        Number of surgical clinics per week. Default is `g.surg_clinic_per_week`.

    surg_clinic_capacity: int, default is `g.surg_clinic_capacity`
        Capacity (number of people it is possible to see) of a surgical clinic.

    theatre_list_per_week: int, default is `g.theatre_list_per_week`
        Number of theatre lists per week. Default is `g.theatre_list_per_week`.

    theatre_list_capacity: int, default is `g.theatre_list_capacity`
        Capacity (number of people it is possible to operate on) of a single theatre list.

    trauma_list_per_week: int, default is `g.trauma_list_per_week`
        Number of trauma lists per week. Default is `g.trauma_list_per_week`.

    weekly_extra_patients: int, default is `g.weekly_extra_patients`
        Number of extra patients for trauma lists per week.

    prob_needs_surgery: float, default is `g.prob_needs_surgery`
        Probability a patient needs surgery post-clinic.

    fill_non_admitted_queue: int, default is `g.fill_non_admitted_queue`.
        Initial non-admitted queue size (patients who are waiting for clinic appointment and potentially surgery).

    fill_admitted_queue: int, default is `g.fill_admitted_queue`
        Initial admitted queue size (patients who have had clinic appointment but not surgery).

    sim_duration: int, default is `g.sim_duration`
        Duration of the simulation; interpreted as a number of weeks.
        Note that the simulation run may exceed this duration so that the full journey of all patients
        who enter the simulation prior to the point specified by sim_duration will complete their
        full journies.
    """

    def __init__(self, run_number,
                 referrals_per_week = g.referrals_per_week,
                 surg_clinic_per_week = g.surg_clinic_per_week,
                 surg_clinic_attendances = g.surg_clinic_attendances,
                 theatre_list_per_week = g.theatre_list_per_week,
                 theatre_list_capacity = g.theatre_list_capacity,
                 trauma_list_per_week = g.trauma_list_per_week,
                 weekly_extra_patients = g.weekly_extra_patients,     
                 prob_needs_surgery = g.prob_needs_surgery,
                 fill_non_admitted_queue = g.fill_non_admitted_queue,
                 fill_admitted_queue = g.fill_admitted_queue,
                 sim_duration = g.sim_duration
                 ):

        #setup environment
        self.env = simpy.Environment()
        self.active_entities = 0
        self.patient_counter = 0

        # Add an empty list to store our event logs in
        self.event_log = []

        #setup values from defaults and calculate
        self.referrals_per_week = referrals_per_week
        # Calculate the average inter-arrival time between referrals
        self.referral_interval = 7 / referrals_per_week
        
        self.surg_clinic_attendances = surg_clinic_attendances
 
        self.theatre_list_per_week = theatre_list_per_week
        self.theatre_list_capacity = theatre_list_capacity

        # calculate total extra patients added on to trauma lists per week
        self.weekly_extra_patients = weekly_extra_patients * trauma_list_per_week

        # calculate equivalent extra patients per non trauma list
        self.extra_patients_adjusted = self.weekly_extra_patients / theatre_list_per_week

        # calculate new theatre list capacity
        self.adjusted_theatre_capacity = theatre_list_capacity + self.extra_patients_adjusted

        self.surg_clinic_duration = 1 / surg_clinic_attendances
        self.surg_clinic_interval = 7 / surg_clinic_per_week


        # here use adjusted theatre capacity
        self.theatre_case_duration = 1 / self.adjusted_theatre_capacity
        self.theatre_list_interval = 7 / theatre_list_per_week

        # The probability that a patient, after going to the clinic, will progress to the
        # step of having surgery
        self.prob_needs_surgery = prob_needs_surgery

        self.sim_duration = sim_duration

        self.fill_non_admitted_queue = fill_non_admitted_queue
        self.fill_admitted_queue = fill_admitted_queue

        self.total_fill_queues = fill_non_admitted_queue + fill_admitted_queue

        #create 'end of simulation' Event
        self.end_of_sim = self.env.event()

        #setup resources

        # Set up a PriorityResource with a capacity of 1.
        # NOTE: At present their is no concept of priority within the clinic or theatre lists
        # However, the use of PriorityResource is so that a 'blocking' process with a higher
        # priority can come in to model the unavailability of the clinic and theatre
        self.surg_clinic = simpy.PriorityResource(self.env, capacity=1)
        self.theatres = simpy.PriorityResource(self.env, capacity=1)

        self.run_number = run_number

        #variables to keep track of numbers in queues
        # SR NOTE 18/1/25: These were originally named
        # self.clinic_queue_time = 0
        # self.theatre_queue_time = 0
        # I think they might have been an accidental duplicate of
        # attributes from the patient class
        # They didn't appear to be updated later in the code and the naming
        # of '_time' doesn't appear to match with the initial comment of
        # '#variables to keep track of numbers in queues'
        # I have updated these to have the name '_length' and used them
        # where seems appropriate for keeping track of queues
        self.clinic_queue_length = 0
        self.theatre_queue_length = 0

        # Create dataframe with queue times
        # NOTE: Later in the model, when writing data to this dataframe, it is only used
        # to store the patients who were
        # - not prefills
        # - not added to the simulation after the 'end time' of the simulation
        # so it only contains data for those patients who were added during those e.g. 100 weeks
        # that are being simulated
        #
        # TODO: Consider what impacts this may have on reported figures for waits, and how you
        # may want to explain this as part of the Streamlit app outputs or documentation.
        # I don't think this is necessarily a problem (as you would otherwise have to generate the
        # wait times for the existing patients) but it's something you will need to be able to
        # pass in.
        # As a future extension to the model, you could look at being able to upload a csv file
        # that just lists the wait times of the patients on the prefill list. You could then either
        # use these as-is, or use them to generate a distribution from which you sample wait times
        # at simulation start for the prefill patients.

        data = {'time_entered_pathway': [],
                'overall_queue_time': []}
        self.queue_times_df = pd.DataFrame(data)

    def determine_surgery(self, patient):
        """
        Method to determine if patient needs surgery

        If randomly generated number from the uniform distribution is below the globally defined
        probability of needing surgery, patient will be set as needing surgery
        """
        if random.uniform(0,1) < self.prob_needs_surgery:
            patient.needs_surgery = True

    def determine_end_sim(self, patient):
        """
        Method to determine if a patient is added to the simulation before the time we
        have set as the end of the simulation.

        Patients who are added to the simulation before the 'end' - whether this is via prefilling
        or via being generated as new patients - will count as active entities in the simulation.

        The simulation will continue to run until the number of patients
        who were entered and tracked as active entities reaches 0 (which may take some time!) -
        i.e. after the 'simulation end' we will continue to add patients to lists and put patients
        through their required steps of the pathway
        """
        if self.env.now >= self.sim_duration:
            patient.before_end_sim = False

    def prefill_queues(self):
        """
        Method to pre fill queues with set numbers that are defined in the model class
        """

        log.debug(f"Prefilling non-admitted queues with {self.fill_non_admitted_queue} patients")

        # Fill non-admitted queue
        for i in range(self.fill_non_admitted_queue):

            # Increment patient counter by 1
            self.patient_counter += 1
            self.active_entities += 1

            # Create new patient
            pt = Patient(self.patient_counter)
            pt.from_prefills = True
            self.event_log.append(
                {'patient': self.patient_counter, 'event_type': 'arrival_departure',
                 'event': 'arrival', 'time': self.env.now,
                 'prefill': pt.from_prefills, 'prefill_already_seen_clinic': pt.already_seen_clinic,
                 'before_end_sim': pt.before_end_sim, 'surgery_required': pt.needs_surgery
                 }
            )
            # NOTE: the default value for new patients is that they have not
            # already been seen by the clinic
            # So these patients in the non-admitted queue have
            # the sttribute *already_seen_clinic*=False

            # Get simpy env to run enter_pathway method with this patient
            self.env.process(self.enter_pathway(pt))

            # need to have yield statement so code works - timeout for zero time
            yield self.env.timeout(0)

        log.debug(f"Prefilling admitted queues with {self.fill_admitted_queue} patients")

        # Fill admitted queue
        for i in range(self.fill_admitted_queue):

            # Increment patient counter by 1
            self.patient_counter += 1
            self.active_entities += 1

            # Create new patient
            pt = Patient(self.patient_counter)

            # Note that unlike the patients in the 'non-admitted' queue,
            # these patients have a value of 'already_seen_clinic' of true,
            # so will begin at an earlier point in the pathway
            pt.already_seen_clinic = True
            pt.from_prefills = True

            self.event_log.append(
                {'patient': self.patient_counter, 'event_type': 'arrival_departure',
                 'event': 'arrival', 'time': self.env.now,
                 'prefill': pt.from_prefills, 'prefill_already_seen_clinic': pt.already_seen_clinic,
                 'before_end_sim': pt.before_end_sim, 'surgery_required': pt.needs_surgery
                 }
            )

            # Get simpy env to run enter_pathway method with this patient
            self.env.process(self.enter_pathway(pt))

            # Need to have yield statement so code works - timeout for zero time
            yield self.env.timeout(0)

    def generate_referrals(self):
        """
        Method to generate new patients for the neurosurgery simulation model.

        These are new patients who join the waiting list while the simulation is running.
        'Prefill' patients - those who were on the waiting list at the time the simulation
        commences - are handled in separate methods.
        """

        #keep generating indefinitely (until simulation ends)
        while True:

            # Increment patient counter by 1
            self.patient_counter += 1

            # Create a new patient, passing the counter to serve as the patient's ID
            pt = Patient(self.patient_counter)
            log.debug(f"Day {self.env.now:.3f}: Adding Patient {self.patient_counter} to the simulation")

            # Decide if the patient needs surgery
            self.determine_surgery(pt)
            # Determine if the patient was generated before the end of the simulation or not
            self.determine_end_sim(pt)

            # If before end sim, add to the count of active entities
            # Note that the simulation will not terminate until active entities reaches 0!
            if pt.before_end_sim == True:
                self.active_entities += 1
            self.event_log.append(
                {'patient': self.patient_counter, 'event_type': 'arrival_departure',
                 'event': 'arrival', 'time': self.env.now,
                 'prefill': pt.from_prefills, 'prefill_already_seen_clinic': pt.already_seen_clinic,
                 'before_end_sim': pt.before_end_sim, 'surgery_required': pt.needs_surgery
                 }
            )

            # Get simpy env to run enter_pathway method with this patient
            self.env.process(self.enter_pathway(pt))
            #print(f'Patient {pt.id} has been generated and entered the clinic queue')

            # Randomly sample time to next referral
            sampled_interref_time = random.expovariate(1.0/self.referral_interval)
            log.debug(f"Next patient arriving in {sampled_interref_time:.3f} weeks ({sampled_interref_time * 24 * 60:.2f} minutes)")

            # Freeze until time has elapsed
            yield self.env.timeout(sampled_interref_time)

    def enter_pathway(self, patient):
        """
        Method to put a single patient through the neurosurgery pathway.

        If patients have not already been seen in the clinic, they will first begin queueing
        for a surgery clinic, which uses the surg_clinic resource.

        Then, all patients who have been passed to this method will progress to entering the
        theatre queue.

        Finally, patients who were **not** a 'prefill' and who complete their journey before
        the simulation ends will be added to the queue times.
        """

        if not patient.already_seen_clinic:
            self.event_log.append(
                {'patient': patient.id, 'event_type': 'queue',
                 'event': 'queue_clinic', 'time': self.env.now,
                 'prefill': patient.from_prefills,
                 'prefill_already_seen_clinic': patient.already_seen_clinic,
                 'before_end_sim': patient.before_end_sim,
                 'surgery_required': patient.needs_surgery
                 }
            )
            # record start of queue time and add to tracker
            start_q_clinic = self.env.now
            # self.fill_non_admitted_queue += 1 # SR 16/1 have commented out as think incorrect attribute
            self.clinic_queue_length += 1
            #print(f'Patient {patient.id} is waiting for clinic')

            # request clinic resource
            with self.surg_clinic.request() as req:
                yield req
                self.event_log.append(
                    {'patient': patient.id, 'event_type': 'resource_use',
                    'event': 'surg_clinic_begins', 'time': self.env.now,
                    'resource_id': 1,
                    'prefill': patient.from_prefills,
                    'prefill_already_seen_clinic': patient.already_seen_clinic,
                    'before_end_sim': patient.before_end_sim,
                    'surgery_required': patient.needs_surgery
                    }
                )

                # record end of queue time and add to tracker
                end_q_clinic = self.env.now
                # self.fill_non_admitted_queue -= 1 # SR 16/1 have commented out as think incorrect attribute
                self.clinic_queue_length -= 1

                # record total queue time
                patient.clinic_q_time = end_q_clinic - start_q_clinic

                # freeze for clinic appointment duration
                yield self.env.timeout(self.surg_clinic_duration)

                self.event_log.append(
                    {'patient': patient.id, 'event_type': 'resource_use_end',
                    'event': 'surg_clinic_complete', 'time': self.env.now,
                    'resource_id': 1,
                    'prefill': patient.from_prefills,
                    'prefill_already_seen_clinic': patient.already_seen_clinic,
                    'before_end_sim': patient.before_end_sim,
                    'surgery_required': patient.needs_surgery
                    }
                )
                # log.debug(f'Patient {patient.id} has left the clinic queue at {self.env.now:.3f}')

        # Enter queue for theatres
        # Record start of queue time and add to tracker
        start_q_theatres = self.env.now
        self.event_log.append(
                {'patient': patient.id, 'event_type': 'queue',
                 'event': 'queue_theatre', 'time': self.env.now,
                 'prefill': patient.from_prefills,
                 'prefill_already_seen_clinic': patient.already_seen_clinic,
                 'before_end_sim': patient.before_end_sim,
                 'surgery_required': patient.needs_surgery
                 }
            )
        #self.fill_admitted_queue += 1 # SR 16/1 have commented out as think incorrect attribute
        self.theatre_queue_length += 1

        # Request theatres resource
        with self.theatres.request() as req:
            yield req
            self.event_log.append(
                    {'patient': patient.id, 'event_type': 'resource_use',
                    'event': 'theatre_begins', 'time': self.env.now, 'resource_id': 1,
                    'prefill': patient.from_prefills,
                    'prefill_already_seen_clinic': patient.already_seen_clinic,
                    'before_end_sim': patient.before_end_sim,
                    'surgery_required': patient.needs_surgery
                    }
                )

            # Record end of queue time and add to tracker
            end_q_theatres = self.env.now
            #self.fill_admitted_queue -= 1 # SR 16/1 have commented out as think incorrect attribute
            self.theatre_queue_length -= 1

            # Record theatre queue time and overall queue time
            # TODO: SR NOTE: For consistency with later results recording, should this also check
            # whether the simulation duration has elapsed?
            if not patient.from_prefills:
                patient.theatre_q_time = end_q_theatres - start_q_theatres
                patient.overall_q_time = end_q_theatres - start_q_clinic
                patient.time_entered_pathway = start_q_clinic

            # Freeze for theatre case duration
            yield self.env.timeout(self.theatre_case_duration)
            self.event_log.append(
                    {'patient': patient.id, 'event_type': 'resource_use_end',
                    'event': 'theatre_complete', 'time': self.env.now, 'resource_id': 1,
                    'prefill': patient.from_prefills,
                    'prefill_already_seen_clinic': patient.already_seen_clinic,
                    'before_end_sim': patient.before_end_sim,
                    'surgery_required': patient.needs_surgery
                    }
                )

            # Decrement counter if before end sim patient
            # Note that the number of active entities are tracked to determine when the
            # simulation should terminate. However, patients are only added to the count of
            # active entities if they were a prefill or generated during the initial simulation
            # runtime.
            if patient.before_end_sim == True:
                self.active_entities -= 1

        # Add patient to queue times dataframe
        # NOTE - only patients who were not prefills and who were not in the
        # TODO - though it will make your dataframe bigger, you may wish at some point to switch
        # to recording all patients in your dataframe, but add additional columns that log whether
        # they were prefill patients
        if not patient.from_prefills and patient.before_end_sim == True:
            self.store_queue_times(patient)

        # Make a note of the time the patient leaves the system having completed all of their
        # activities
        self.event_log.append(
                {'patient': patient.id, 'event_type': 'arrival_departure',
                 'event': 'depart', 'time': self.env.now,
                 'prefill': patient.from_prefills,
                 'prefill_already_seen_clinic': patient.already_seen_clinic,
                 'before_end_sim': patient.before_end_sim,
                 'surgery_required': patient.needs_surgery
                 }
            )

    def clinic_unavail(self):
        """
        Method to model interval between clinic appointments

        Sends in a high priority resource that will hog the clinic until
        the next case should be sent in (modelling unavailability e.g. overnight
        or otherwise)
        """

        while True:

            # Freeze clinic_unavail function for duration of clinic
            yield self.env.timeout(1)

            # Request clinic with max priority and hold until next clinic
            with self.surg_clinic.request(priority=-1) as req:
                # Freeze the function until the request can be met (this
                # ensures that the last patient in clinic will be seen)
                yield req

                yield self.env.timeout(self.surg_clinic_interval)


     # method to model interval between theatre lists
    def theatres_unavail(self):
        """
        Method to model interval between theatre lists

        Sends in a high priority resource that will hog the theatre until
        the next case should be sent in (modelling unavailability e.g. overnight
        or otherwise)
        """
        while True:

            # Freeze theatres_unavail function for duration of list
            yield self.env.timeout(1)

            # Request resource with max priority and hold until next list
            with self.theatres.request(priority=-1) as req:
                # Freeze the function until the request can be met (this
                # ensures that the last theatre case will be completed)
                yield req
                
                yield self.env.timeout(self.theatre_list_interval)

    def monitor(self):
        """
        Method to check if simulation should continue

        It should continue until both
        - the simulation time is later than the 'sim_duration' parameter
        - the number of active entities in the simulation is 0

        Active entities are those who
        - were prefills OR were added to the simulation during the period between 0 and sim_duration
        - have not yet completed their journey through the pathway

        Therefore, the number of active entities will not reach 0 until all prefill patients or
        patients generated during the initial sim runtime have had surgery or left the pathway
        at a different point.
        """
        while True:
            # check conditions every 1 time unit
            yield self.env.timeout(1)
            if self.env.now >= self.sim_duration and self.active_entities <= 0:
                # trigger end of simulation event
                self.end_of_sim.succeed()
                log.info(f"""Simulation terminated at week {self.env.now} after reaching 0 active
                         entities and exceeding the minimum number of weeks ({self.sim_duration})""")
                break
            elif self.env.now >= (self.sim_duration + (52 * 10) ):
                # trigger end of simulation event
                log.warning(f"""Simulation terminated at week {self.env.now} due to extreme long-running
                            behaviour. Number of active entities remaining was {self.active_entities}""")
                self.end_of_sim.succeed()
                break
            else:
                log.info(f"Simulation week {self.env.now}: {self.active_entities} active entities remaining")

    #method to store queue times
    def store_queue_times(self, patient):
        """
        Method to store queue times
        """

        # create temporary dataframe with queue times
        df_to_add = pd.DataFrame({'time_entered_pathway': [patient.time_entered_pathway],
                                  'overall_q_time': [patient.overall_q_time]})

        # Add to main dataframe

        # TODO: SR NOTE: At some point you may want to adjust this to speed up the model
        # Concatenating dataframes is relatively slow and memory-heavy compared to something
        # like concatenating a list of dictionaries and turning it into a dataframe at the end

        self.queue_times_df = pd.concat([self.queue_times_df, df_to_add])

    # A method to save the wait times from this run to a csv file
    def write_queue_times(self):
        """
        A method to save the wait times from this run to a csv file
        """
        # Preview the dataframe in the console
        print(self.queue_times_df.head())


    # A method to write the queue numbers to a csv file
    def write_queue_numbers(self):
        """
        A method to write the queue numbers to a csv file
        """
        with open('queue_numbers.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
    def write_event_log(self):
        """
        A method to write the full event log
        """
        # Write the entire dataframe to a csv file
        pd.DataFrame(self.event_log).sort_values(['patient', 'time']).to_csv(f'event_log_run_{self.run_number}.csv', index=False)

    def run(self):
        """
        A method to run the simulation
        """
        # Fill queues
        self.env.process(self.prefill_queues())

        # Start entity generators
        self.env.process(self.generate_referrals())

        # Simulate interval between clinics and lists
        self.env.process(self.clinic_unavail())
        self.env.process(self.theatres_unavail())

        # Use monitor() to check if sim should end
        self.env.process(self.monitor())

        # Run simulation
        self.env.run(until=self.end_of_sim)

        # Write results to csv
        self.write_queue_times()
        self.write_queue_numbers()
        self.write_event_log()
