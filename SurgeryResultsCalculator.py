# A class to calculate and display trial results

import simpy
import random
import numpy as np
import pandas as pd
import csv
from statistics import mean
import matplotlib.pyplot as plt
#import seaborn as sns
import os
import plotly.express as px

from global_params import g
from SurgeryPathway import Neurosurgery_Pathway
from SurgeryPatient import Patient


class Trial_Results_Calculator:
    def __init__(self,
                 number_of_runs = g.number_of_runs,
                 sim_duration = g.sim_duration,
                 fill_non_admitted_queue = g.fill_non_admitted_queue,
                 fill_admitted_queue = g.fill_admitted_queue):
        #self.trial_results_df = pd.DataFrame()

        self.number_of_runs = number_of_runs
        self.sim_duration = sim_duration
        self.fill_non_admitted_queue = fill_non_admitted_queue
        self.fill_admitted_queue = fill_admitted_queue

    def concatenate_wait_times(self):
        """
        A method to concatenate the multiple wait time CSVs
        """

        # create empty dataframe
        nodata = {'time_entered_pathway': [],
                    'overall_queue_time': [],
                    'run': []}
        all_wait_times_df = pd.DataFrame(nodata)

        for i in range(self.number_of_runs):
            wait_times_this_run = pd.read_csv(f'wait_times_run_{i}.csv')
             # Add column indicating the run these wait times come from
            wait_times_this_run['run'] = i+1
            all_wait_times_df = pd.concat([all_wait_times_df, wait_times_this_run])

        # save to csv
        # print(all_wait_times_df.head())
        all_wait_times_df['run'] = all_wait_times_df['run'].astype('int')
        all_wait_times_df.to_csv('all_wait_times.csv')

        # delete individual run files
        for i in range(self.number_of_runs):
            os.remove(f'wait_times_run_{i}.csv')

    def plot_wait_times(self):
        """
        A method to read in the run results csv file and print them for the user
        """
        trial_results_df = pd.read_csv('all_wait_times.csv')
        trial_results_df['run'] = trial_results_df['run'].astype('str')

        fig = px.scatter(trial_results_df, x='time_entered_pathway',
                            y='overall_queue_time', opacity=0.3, trendline='ols',
                            trendline_color_override='black',
                            trendline_scope = 'overall',
                            color="run",
                            title='Total wait time vs time of referral',
                            labels={'time_entered_pathway': 'Week of referral',
                                    'overall_queue_time': 'Total wait time (weeks)'})
        return fig

    def calculate_mean_queue_numbers(self):
        """
        A method to calculate average queue numbers over all runs
        """

        # read in queue numbers csv
        self.queue_numbers_df = pd.read_csv('queue_numbers.csv')

        # calculate mean queue numbers
        data = {
            'name': ['Clinic', 'Theatres'],
            'Before': [self.fill_non_admitted_queue, self.fill_admitted_queue],
            'After': [self.queue_numbers_df['clinic_queue'].mean(),
                        self.queue_numbers_df['theatres_queue'].mean()]
        }

        # create dataframe
        self.overall_q_numbers_df = pd.DataFrame(data)
        self.overall_q_numbers_df.set_index('name', inplace=True)

        #print(f'Number in clinic queue before: {self.fill_clinic_q}')
        #print(f'Number in clinic queue after: {self.overall_q_numbers_df["After"][0]}')
        #print(self.overall_q_numbers_df)

    def plot_queue_numbers(self):
        """
        Plot the average queue numbers as an interactive plot using the plotly express module
        """
        fig = px.bar(self.overall_q_numbers_df, barmode='group',
                     title='Numbers in waiting lists at start and end of simulation',
                     labels={'value': 'Patients waiting',
                             'name': 'Stage of pathway',
                             'variable': 'Before or after simulation'})
        return fig

    def readout_total_queue_numbers(self):
        """
        Method to calculate queue numbers at end of simulation

        Returns
        ---
        A single float representing the total number of people queueing
        """

        return self.overall_q_numbers_df['After'].sum()

    def readout_wait_time_start(self):
        """
        Method to calculate average wait time at start of simulation

        Returns
        ---
        A single float representing the average wait time for patients who entered
        the pathway on day 0

        This will also look at patients who are prefills.

        # TODO: SR NOTE: Consider whether the fact that prefills don't have a prior waiting time is
        # artificially reducing this figure

        """

        #read trial results csv
        trial_results_df = pd.read_csv('all_wait_times.csv')

        #return average wait time for patients who entered pathway on day 0
        return trial_results_df[trial_results_df['time_entered_pathway'] < 1]['overall_queue_time'].mean()

    def readout_wait_time_end(self):
        """
        Method to calculate average wait time at end of simulation

        Returns
        ---
        A single float representing the average wait time for entered the pathway on the final day
        of the simulation or later

        TODO: Check whether this will be an underestimate for the prefills
        """

        # read trial results csv
        trial_results_df = pd.read_csv('all_wait_times.csv')

        # return average wait time for patients who entered pathway on final day of simulation
        last_day = self.sim_duration - 1
        return trial_results_df[trial_results_df['time_entered_pathway'] > last_day]['overall_queue_time'].mean()


    def readout_total_52_plus(self):
        """
        Method to calculate number of patients waiting 52+ weeks at end of simulation

        Returns
        ---
        Float
        """

        # read trial results csv
        trial_results_df = pd.read_csv('all_wait_times.csv')

        # return number waiting over 52 weeks who entered pathway on final week of simulation
        last_week = self.sim_duration - 1
        entered_final_week = trial_results_df[trial_results_df['time_entered_pathway'] > last_week]
        long_wait = entered_final_week[entered_final_week['overall_queue_time'] >= 52]
        return int(long_wait.groupby('run').count()['overall_queue_time'].mean().round(0))


        # return trial_results_df[trial_results_df['time_entered_pathway'] > last_week]['overall_queue_time']>52
        #trial_results_df['Long Waiters'] = [1 if x >52 else 0 for x in trial_results_df['overall_queue_time']]

    def readout_total_65_plus(self):
        """
        Method to calculate number of patients waiting 65+ weeks at end of simulation

        Returns
        ---
        Float
        """

        # read trial results csv
        trial_results_df = pd.read_csv('all_wait_times.csv')

        # return number waiting over 65 weeks who entered pathway on final week of simulation
        last_week = self.sim_duration - 1
        entered_final_week = trial_results_df[trial_results_df['time_entered_pathway'] > last_week]
        long_wait = entered_final_week[entered_final_week['overall_queue_time'] >= 65]
        return int(long_wait.groupby('run').count()['overall_queue_time'].mean().round(0))
        # return trial_results_df[trial_results_df['time_entered_pathway'] > last_week]['overall_queue_time']>65
