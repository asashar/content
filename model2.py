import simpy
import pyttsx3
import random
import numpy as np
import pandas as pd
import csv
from statistics import mean
import matplotlib.pyplot as plt
# import seaborn as sns
import os
import streamlit as st
import plotly.express as px

from SurgeryPatient import Patient
from SurgeryPathway import Neurosurgery_Pathway
from SurgeryResultsCalculator import Trial_Results_Calculator
from global_params import g
from PIL import Image


############ Page Config set to wide
# page config
# This must be the first Streamlit command used on an app page (after importing streamlit)!
st.set_page_config(layout='wide')

############ Streamlit theme - colours
# Streamlit page theme is saved as a config.toml file in the folder .streamlit

############ Fonts
# The css style sheet is saved as style.css in the content folder.
# The below points towards the css file and wrapss it in some HTML tags that will 
# ensure the css # is recognised by the web browser.
# This imports Google fonts.
# Istok Web is often cited as being the closest Google Font equivalent to the standard 
# NHS font Frutige
with open("style.css") as css:
 st.markdown(f'<style>{css.read()}</style>', unsafe_allow_html=True)

############ Title and introduction
# title text
st.title('Neurosurgery RTT Pathway Simulation')

st.subheader("An interactive Simulation")

# description text
st.markdown('This simulation models a simple RTT Neurosurgery pathway, based on the diagram below, using a computer modelling technique called Discrete Event Simulation.')
st.markdown('By adjusting the parameters in the :red[sidebar], you can see how allocating resources differently will affect the waiting lists and waiting times.')
st.markdown('In particular, it is possible to model the impact of adding extra elective patients onto lists - use the :green[green input box] in the :red[sidebar].')
# the below adds an information box, with an icon
st.info('To note, repeating the simulation more times will provide more reliable results, but will take longer to run.', icon=":material/thumb_up:")
st.markdown('Press \'Start Simulation\' to run the simulation, and the results will be displayed below.')

st.divider()


############ Sidebar
# The below adds a collapsible sidebar

st.markdown(
  """
<style>
    /* Expander */
    div[data-testid=stExpander] > details > summary > span > div > p
    {
        font-size: 30px;
    }
</style>
  """,
  unsafe_allow_html=True
)



# the below adds a sidebar title
# and various adjustable parameters the user can use
with st.sidebar:
  st.header("Adjustable parameters")

  REFS_PER_WEEK = st.number_input('Referrals Per Week',
                                         step=1,
                                         value = g.referrals_per_week)

# TODO: SR Note: Have commented this out for now as I can't see how this is meant to
# fit in - have asked for clarification
#   ATTENDANCES_PER_WEEK = st.number_input('Clinics Per Week',
#                                            step = 1,
#                                            value = g.surg_clinic_attendances)

  st.divider()

  CLINIC_QUEUE = st.number_input('Patients Waiting for Clinic Appointment at Start of Simulation',
                                    step = 1,
                                    value = g.fill_non_admitted_queue)

  THEATRE_QUEUE = st.number_input('Patients Waiting for Theatre at Start of Simulation',
                                    step = 1,
                                    value = g.fill_admitted_queue)

  st.divider()

  st.subheader("Clinic Parameters")

  CLINICS_PER_WEEK = st.number_input('Clinics Per Week',
                                            step = 1,
                                            value = g.surg_clinic_per_week)

  CLINIC_APPOINTMENTS_PER_CLINIC = st.number_input('Appointments per Clinic',
                                            step = 1,
                                            value = g.surg_clinic_appts)

  st.caption(f"*This gives you a total of {CLINICS_PER_WEEK*CLINIC_APPOINTMENTS_PER_CLINIC:.0f} clinic slots per week*")

  st.divider()

  st.subheader("Theatre Parameters")

  LISTS_PER_WEEK = st.number_input('Theatre Lists Per Week',
                                            step = 1,
                                            value = g.theatre_list_per_week)

  LIST_CAPACITY = st.number_input('Cases Per Theatre List',
                                            step = 1,
                                            value = g.theatre_list_capacity)

  st.caption(f"*This gives you a total of {LISTS_PER_WEEK*LIST_CAPACITY:.0f} theatre slots per week*")

  PROB_SURGERY = st.slider('Percentage of Patients requiring Surgery',
                                            step = 0.01,
                                            value = g.prob_needs_surgery)

  EXTRA_PATIENTS = st.number_input(':green[**Extra Patients Per List**]',
                                        step = 1,
                                        value = g.weekly_extra_patients)

  st.divider()

  st.subheader("Simulation Parameters")

  NUM_OF_RUNS = st.number_input('Number of Times to Run Simulation',
                                        step = 1,
                                        value = g.number_of_runs)

  sim_length_help_text = """The simulation length determines the number of weeks that new patients
  to monitor will be generated for.

  The simulation will continue to run until every patient who is waiting for a clinic appointment or
  theatre at the start of the simulation, or who gets added to the waiting list during the weeks
  specified in this input, completes their journey through the system.
  """

  LENGTH_OF_SIM = st.number_input('Length of Time to Simulate (weeks)',
                                   step = 1,
                                   value = g.sim_duration,
                                   help=sim_length_help_text)

############ The model itself

#calculate total in queues at start of simulation
TOTAL_QUEUE_START = CLINIC_QUEUE + THEATRE_QUEUE


#### This adds two tabs.
# The model is in tab 1
# Everything in tab 1 is indented
tab1, tab2 = st.tabs(["Simulation", "Pathway"])

with tab1:

# button to run simulation
    button_run_pressed = st.button("Start Simulation")

    if button_run_pressed:
    #if st.button('Start Simulation'):

    # spinner while loading
        with st.spinner('Running simulation...'):

        # create a file to store the numbers in queues
            with open('queue_numbers.csv', 'w') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow(['run','clinic_queue', 'theatres_queue'])

        # For the number of runs specified in the g class, create an instance of the
        # ED_Model class, and call its run method
            for run in range(NUM_OF_RUNS):
                print (f"Run {run+1} of {NUM_OF_RUNS}")
                demo_pathway_model = Neurosurgery_Pathway(run,
                                                      referrals_per_week=REFS_PER_WEEK,
                                                      surg_clinic_attendances=ATTENDANCES_PER_WEEK,
                                                      fill_non_admitted_queue=CLINIC_QUEUE,
                                                      prob_needs_surgery = PROB_SURGERY,
                                                      #fill_admitted_pathway = THEATRE_QUEUE,
                                                      fill_admitted_queue = THEATRE_QUEUE,
                                                      sim_duration=LENGTH_OF_SIM
                                                      )
                demo_pathway_model.run()

        # Once the trial is complete, we'll create an instance of the
        # Trial_Result_Calculator class and run the print_trial_results method
            demo_trial_results_calculator = Trial_Results_Calculator(
                                                                 number_of_runs=NUM_OF_RUNS,
                                                                 sim_duration=LENGTH_OF_SIM,
                                                                 fill_non_admitted_queue=CLINIC_QUEUE,
                                                                 fill_admitted_queue=THEATRE_QUEUE
                                                                )

            demo_trial_results_calculator.concatenate_wait_times()
            demo_trial_results_calculator.calculate_mean_queue_numbers()

        # calculate number of patients in queues at end of simulation
            TOTAL_QUEUE_END = demo_trial_results_calculator.readout_total_queue_numbers()

        # calculate number of patients waiting 52+ weeks at end of simulation
            TOTAL_52_plus = demo_trial_results_calculator.readout_total_52_plus()

        # calculate number of patients waiting 65+ weeks at end of simulation
            TOTAL_65_plus = demo_trial_results_calculator.readout_total_65_plus()

            TOTAL_65_plus_Sum = sum(demo_trial_results_calculator.readout_total_65_plus())

        # calculate average wait times at start and end of simulation
            MEAN_WAIT_START = demo_trial_results_calculator.readout_wait_time_start()
            MEAN_WAIT_END = demo_trial_results_calculator.readout_wait_time_end()


############ Showing the results and the charts

        # print results
            st.header('Results')
            st.subheader('Numbers on Waiting Lists')
            st.write(f'At the start of the simulation, the total number of patients on the waiting list was {TOTAL_QUEUE_START}.')
            st.write(f'After {LENGTH_OF_SIM} weeks, the total number of patients on the waiting list is predicted to be {round(TOTAL_QUEUE_END)}.')
            st.write(f'After {LENGTH_OF_SIM} weeks, the total number of patiens waiting >52 weeks is predicted to be **:red[{sum(TOTAL_52_plus)}]**.')
            st.write(f'After {LENGTH_OF_SIM} weeks, the total number of patiens waiting >65 weeks is predicted to be **:red[{sum(TOTAL_65_plus)}]**.')

            if TOTAL_65_plus_Sum == 0:
                st.success("Great! This model anticipates no 65+ waiters (possibly, hopefully)")
            else:
                st.error("Oh no. There may be long waits")

        # demo_trial_results_calculator.readout_wait_time_end()

        # plot the results
            st.subheader('Graphs of Waiting Times and Numbers on Waiting Lists')
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(demo_trial_results_calculator.plot_wait_times())
            with col2:
                st.plotly_chart(demo_trial_results_calculator.plot_queue_numbers())

# Creating the dataframe
    wait_times_df = pd.read_csv('all_wait_times.csv')

# Add new columns for the long waiters
    
    wait_times_df['Long Waiters 52+'] = [1 if x > 52 else 0 for x in wait_times_df['overall_q_time']]
    wait_times_df['Long Waiters 65+'] = [1 if x > 65 else 0 for x in wait_times_df['overall_q_time']]

    long_waiters_df = {'52+': wait_times_df[wait_times_df["Long Waiters 52+"] == 1]["Long Waiters 52+"].value_counts() ,
           '65+' : wait_times_df[wait_times_df["Long Waiters 65+"] == 1]["Long Waiters 65+"].value_counts()
           }

    # This creates a chart showing the total 52+ and 65+ waits
    # This is referenced in the columns below.
    # I added a 'if button_run_pressed: ' further below, because otherwise
    # the chart and score cards were showing before you run the simulation.
    fig = px.bar(long_waiters_df, barmode='group',
                title='Number of long waiters',
                labels={'value': 'Number of long waiters',
                        'name': 'Waiting Groups',
                       'variable': 'Wait Group Bands'
                        })


    fig.update_layout(
        xaxis = dict(
        tickmode = 'array',
        tickvals = [1],
        ticktext = ['Waiting Groups']
    )
    )

    if button_run_pressed:   

        # To print the DataFrame, uncomment the below.
        # st.dataframe(long_waiters_df)

        long_waiters_52 = long_waiters_df['52+']
        long_waiters_65 = long_waiters_df['65+']

        col1, col2, col3 = st.columns([3,1,1])

        with col1:
            st.plotly_chart(fig)
        with col2:
            st.metric(
            label="Number of 52+ waiters",
            value= long_waiters_52
            )
        with col3:
            st.metric(
            label="Number of 65+ waiters",
            value= long_waiters_65
            )    


#### This is the second tab.
# This is the pathway
# Everything in tab 2 is indented

with tab2:
    st.markdown('This is the very basic pathway used for the model.')
    st.markdown('This assumes patients are seen at clinic and added to an inpatient waiting list.')

    image = Image.open('pathway_diagram.jpg')