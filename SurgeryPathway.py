# A class containing functions to model the Neurosurgery RTT pathway

import simpy
import random
import numpy as np
import pandas as pd
import csv

from SurgeryPatient import Patient
from global_params import g

class Neurosurgery_Pathway:

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

        #setup values from defaults and calculate
        self.referrals_per_week = referrals_per_week
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

        self.prob_needs_surgery = prob_needs_surgery

        self.sim_duration = sim_duration

        self.fill_non_admitted_queue = fill_non_admitted_queue
        self.fill_admitted_queue = fill_admitted_queue

        self.total_fill_queues = fill_non_admitted_queue + fill_admitted_queue

        #create 'end of simulation' Event
        self.end_of_sim = self.env.event()

        #setup resources
        self.surg_clinic = simpy.PriorityResource(self.env, capacity=1)
        self.theatres = simpy.PriorityResource(self.env, capacity=1)

        self.run_number = run_number

        #variables to keep track of numbers in queues
        self.clinic_queue_time = 0
        self.theatre_queue_time = 0

        #create dataframe with queue times
        data = {'time_entered_pathway': [],
                'overall_queue_time': []}
        self.queue_times_df = pd.DataFrame(data)

    #method to determine if patient needs surgery
    def determine_surgery(self, patient):
        if random.uniform(0,1) < self.prob_needs_surgery:
            patient.needs_surgery = True

    # method to determine before end sim
    def determine_end_sim(self, patient):
        if self.env.now >= self.sim_duration:
            patient.before_end_sim = False

    # method to pre fill queues with set numbers
    def prefill_queues(self):

        # fill non-admitted queue
        for i in range(self.fill_non_admitted_queue):

            #increment patient counter by 1
            self.patient_counter += 1
            self.active_entities += 1

            #create new patient
            pt = Patient(self.patient_counter)
            pt.from_prefills = True

            #get simpy env to run enter_pathway method with this patient
            self.env.process(self.enter_pathway(pt))

            # need to have yield statement so code works - timeout for zero time
            yield self.env.timeout(0)

        # fill admitted queue
        for i in range(self.fill_admitted_queue):

            # increment patient counter by 1
            self.patient_counter += 1
            self.active_entities += 1

            # create new patient
            pt = Patient(self.patient_counter)
            pt.already_seen_clinic = True
            pt.from_prefills = True

            # get simpy env to run enter_pathway method with this patient
            self.env.process(self.enter_pathway(pt))

            # need to have yield statement so code works - timeout for zero time
            yield self.env.timeout(0)

    #method to generate patient referrals
    def generate_referrals(self):
        
        #keep generating indefinitely (until simulation ends)
        while True:
            
            #increment patient counter by 1
            self.patient_counter += 1
            
            #create new patient
            pt = Patient(self.patient_counter)
            
            #decide if needs surgery and end sim
            self.determine_surgery(pt)
            self.determine_end_sim(pt)

            #if before end sim, increment counter
            if pt.before_end_sim == True:
                self.active_entities += 1
                
            #get simpy env to run enter_pathway method with this patient
            self.env.process(self.enter_pathway(pt))
            #print(f'Patient {pt.id} has been generated and entered the clinic queue')

            #randomly sample time to next referral
            sampled_interref_time = random.expovariate(1.0/self.referral_interval)
            
            #freeze until time has elapsed
            yield self.env.timeout(sampled_interref_time)

    #method to enter pathway
    def enter_pathway(self, patient):

        if not patient.already_seen_clinic:
            # record start of queue time and add to tracker
            start_q_clinic = self.env.now
            self.fill_non_admitted_queue += 1
            #print(f'Patient {patient.id} is waiting for clinic')

            # request clinic resource
            with self.surg_clinic.request() as req:
                yield req

                # record end of queue time and add to tracker
                end_q_clinic = self.env.now
                self.fill_non_admitted_queue -= 1

                # record total queue time
                patient.clinic_q_time = end_q_clinic - start_q_clinic

                # freeze for clinic appointment duration
                yield self.env.timeout(self.surg_clinic_duration)
                #print(f'Patient {patient.id} has left the clinic queue')

        # enter queue for theatres
        # record start of queue time and add to tracker
        start_q_theatres = self.env.now
        self.fill_admitted_queue += 1

        # request theatres resource
        with self.theatres.request() as req:
            yield req

            # record end of queue time and add to tracker
            end_q_theatres = self.env.now
            self.fill_admitted_queue -= 1

            # record theatre queue time and overall queue time
            if not patient.from_prefills:
                patient.theatre_q_time = end_q_theatres - start_q_theatres
                patient.overall_q_time = end_q_theatres - start_q_clinic
                patient.time_entered_pathway = start_q_clinic

            # freeze for theatre case duration
            yield self.env.timeout(self.theatre_case_duration)
            
            # decrement counter if before end sim patient
            if patient.before_end_sim == True:
                self.active_entities -= 1

        # add patient to queue times dataframe
        if not patient.from_prefills and patient.before_end_sim == True:
            self.store_queue_times(patient)


    # method to model interval between clinic appointments
    def clinic_unavail(self):

        while True:
        
            #freeze clinic_unavail function for duration of clinic
            yield self.env.timeout(1)
            
            #request clinic with max priority and hold until next clinic
            with self.surg_clinic.request(priority=-1) as req:
                # Freeze the function until the request can be met (this
                # ensures that the last patient in clinic will be seen)
                yield req

                yield self.env.timeout(self.surg_clinic_interval)


     # method to model interval between theatre lists
    def theatres_unavail(self):

        while True:
        
            #freeze theatres_unavail function for duration of list
            yield self.env.timeout(1)
            
            #request resource with max priority and hold until next list
            with self.theatres.request(priority=-1) as req:
                # Freeze the function until the request can be met (this
                # ensures that the last theatre case will be completed)
                yield req
                
                yield self.env.timeout(self.theatre_list_interval)

    # method to check if simulation should continue
    def monitor(self, env, active_entities, end_point, end_of_sim):
        while True:
            # check conditions every 1 time unit
            yield self.env.timeout(1)
            if self.env.now >= self.sim_duration and self.active_entities <= 0:
                # trigger end of simulation event
                self.end_of_sim.succeed()
                break
            #else:
                #print(self.active_entities)

    #method to store queue times
    def store_queue_times(self, patient):

        # create temporary dataframe with queue times
        df_to_add = pd.DataFrame({'time_entered_pathway': [patient.time_entered_pathway],
                                  'overall_q_time': [patient.overall_q_time]})

        # add to main dataframe
        self.queue_times_df = pd.concat([self.queue_times_df, df_to_add])

    # A method to save the wait times from this run to a csv file
    def write_queue_times(self):
        print(self.queue_times_df.head())
        self.queue_times_df.to_csv(f'wait_times_run_{self.run_number}.csv')

    # A method to write the queue numbers to a csv file
    def write_queue_numbers(self):
        with open('queue_numbers.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow([self.run_number, self.fill_non_admitted_queue,
                             self.fill_admitted_queue])
            
    # A method to run the simulation
    def run(self):
        # fill queues
        self.env.process(self.prefill_queues())

        # start entity generators
        self.env.process(self.generate_referrals())

        #simulate interval between clinics and lists
        self.env.process(self.clinic_unavail())
        self.env.process(self.theatres_unavail())

        #use monitor() to check if sim should end
        self.env.process(self.monitor(self.env, self.active_entities,
                                      self.sim_duration, self.end_of_sim))

        #run simulation
        self.env.run(until=self.end_of_sim)

        #write results to csv
        self.write_queue_times()
        self.write_queue_numbers()