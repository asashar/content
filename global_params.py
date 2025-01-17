

class g:
    """
    Class to store global level parameters for the model.
    """
    # -------------------- #
    # Model Parameters     #
    # -------------------- #

    # number of referrals per week
    referrals_per_week = 350
    referral_interval = 7 / referrals_per_week

    # number of clinics per week and capacity
    surg_clinic_per_week = 2
    surg_clinic_appts = 6

    # theatre lists and cases per list
    theatre_list_per_week = 5
    theatre_list_capacity = 2

    # numbers to add to queues before simulation starts
    fill_non_admitted_queue = 4163
    fill_admitted_queue = 1143

    # proportion of patients requiring surgical admission
    prob_needs_surgery = 0.80

    trauma_list_per_week = 2
    weekly_extra_patients = 0

    # --------------------- #
    # Simulation Parameters #
    # --------------------- #

    # length of simulation (weeks)
    sim_duration = 100

    # number of times to run simulation
    number_of_runs = 5

    # --------------------- #
    # Historical Figures    #
    # --------------------- #

    # average waiting times for surgical admission (weeks)
    surgery_wait = 10

    # outpatient attendances per week
    surg_clinic_attendances = 937
