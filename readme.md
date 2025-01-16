# My readme

This is a readme file for my hsma project. This explains how it works.

The project attempts to predict how many weeks patients will be waiting at
the end of the Neurosurgery RTT pathay.

There are various python files that are used to create the model.

- global_params.py: this sets the global parameters for the project.

- SurgeryPatient.py: this is the patient class.

- SurgeryPathway.py: this is the 'Pathway' class, setting up the environment,
setting up values, resources, methods to determine parts of the pathway,
the method to generate referral etc.

- SurgeryResultsCalculator.py: creates the class Trial_Results_Calculator, which
tries to capture the waiting times for each project during the project.

- model2.py: this is the model for the project, and includes the Streamlit
commands to create the app.

This produces various csv files that record thewaiting times.

STREAMLIT
For Streamlit, a config.toml file is saved in the .streamlit folder. This is
the theme for the streamlit app.

The cascading style sheet (css) specifies the font for the streamlit app.
It uses the font "Istok Web" which is closet to Google fonts.