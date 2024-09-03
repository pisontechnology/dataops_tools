from ml_util.query.utils import Env
import schedule
import numpy as np
import pandas as pd
from pison_cloud.pison.reaction.cloud.v1 import reaction_pb2, reaction_pb2_grpc
from ml_util.query.microservices import PisonGrpc
from ml_util.query.microservices import ResponseConverter

class ReactionConverter(ResponseConverter):
    def __call__(self, response):
        response_dict = MessageToDict(response)
        
        if "tests" in response_dict:
            return pd.json_normalize(response_dict['tests'])
        else:
            data_f = super().__call__(response)
            return data_f


import logging
from datetime import datetime
from pison_cloud.pison.common.cloud.v1 import common_pb2
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.json_format import MessageToDict
from ml_util.pison_ready.readiness import get_score as get_readiness_score
from ml_util.pison_ready.agility import get_score as get_agility_score
from ml_util.pison_ready.focus import get_score as get_focus_score
import pprint
import time
from typing import List, Dict
import datetime as dt
from ml_util.query.microservices import get_users
from ml_util.query.microservices import get_reaction_tests, get_plan_data,get_all_metadata
import os
from google.oauth2 import service_account
from pandas_gbq import to_gbq, read_gbq
from module_101_217 import *

def extract_onset_times(onset_df):
    onset_df['onset_moment'] = pd.to_datetime(onset_df['onset_moment'],format ='mixed')
    onset_df['created_at'] = pd.to_datetime(onset_df['created_at'],format ='mixed')
    onset_times = onset_df['onset_moment'] - onset_df['created_at']
    onset_times = onset_times.dt.total_seconds().values
    onset_times = sorted(onset_times)
    return onset_times

def generate_onset_df(score_df):
    all_onset_rows = []  # To accumulate all onset rows from each test_row
    for test_index, test_row in score_df.iterrows():
        onset_list = test_row['onset_moments']
        if not isinstance(onset_list, list):
            continue  # Skip rows where onset_moments is not a valid list
        for onset in onset_list:
            row = {
                'onset_moment': onset,
                'created_at': test_row['created_at'],  # Accessing the created_at from the same dataframe
                'uid': test_row['uid']  # Accessing the UID from the same dataframe
            }
            all_onset_rows.append(row)  # Append the row to the all_onset_rows list
    return pd.DataFrame(all_onset_rows)

def score_parity_test(uid, test, score_uid_df, plan_uid_df, config, baseline_df = None, verbose = False):
    
    report = {
        'uid': uid,
        'createdAt': score_uid_df['createdAt'].iloc[0],
        'has_ms_precision': '.' in str(score_uid_df['createdAt'].iloc[0]),
        'has_onset_moments': not score_uid_df['onsetMoments'].isna().any(), # score but no onset moments is weird
        'has_plan_data': len(plan_uid_df) > 0,
        'has_stimuli_times': (len(plan_uid_df) > 0) and (not plan_uid_df['timeInSeconds'].isna().any()),
    }
    
    if pd.isnull(report['createdAt']) or (not report['has_ms_precision']) or (not report['has_onset_moments']) or not report['has_plan_data'] or not report['has_stimuli_times']:
        return report, None

    stimulus_times = plan_uid_df['timeInSeconds'].values
    onset_times = extract_onset_times(score_uid_df)

    if test == 'readiness':
        score, info = get_readiness_score(stimulus_times, onset_times, config)
        firmware_score = score_uid_df['reactionTimeInMilliseconds'].fillna(0).iloc[0]
        match = abs(score - firmware_score) <= 1.0

    elif test == 'agility':
        nogo_trials = (plan_uid_df.configuration_color_blue == 0).values

        # blue = 0 -> nogo
        # blue = 1 -> go
        # blue = 0.4 -> new nogo?
        if np.sum(nogo_trials) == 0:
            report['nonstandard_nogo_lighting'] = True
            #print(f"Skipping {uid}, no nogo trials found, possibly using a nonstandard lighting schema")
            return report, None

        score, info = get_agility_score(stimulus_times, nogo_trials, onset_times, config)
        firmware_score = score_uid_df['agilityScoreValue'].fillna(0).iloc[0]
        match = (score - firmware_score) == 0

    elif test == 'focus':
        user_id = score_uid_df['userId'].iloc[0]
        baseline_uid_df = baseline_df[baseline_df['userId'] == user_id]
        
        if baseline_uid_df.empty:
            report['empty_baseline'] = True
            #print(f'skipping {uid}, no baseline found')
            return report, None
        
        # ms to seconds
        baseline_reaction_time = baseline_uid_df['reactionTimeInMilliseconds'].iloc[0] / 1000
        firmware_score = score_uid_df['focusScoreValue'].fillna(0).iloc[0]
        score, info = get_focus_score(stimulus_times, onset_times, config, baseline_reaction_time)
        match = (score - firmware_score) == 0

    if not match and verbose:
        # print('uid', uid)
        # print('created at', score_uid_df['createdAt'].iloc[0])
        # print('stimulus_times', stimulus_times)
        # print('onset_times', onset_times)
        # if 'nogo_trials' in locals():
        #     print('nogo_trials', nogo_trials)
        # print('score', score)
        # print('firmware_score', firmware_score)
        # pprint.pprint(info
        print(info)

    return report, match


def score_parity_test_all(score_df, plan_df, test, config, baseline_df = None, verbose = False, subset = None):
    
    report_rows = []
    score_df = score_df.copy()
    plan_df = plan_df.copy()
    
    if subset is not None:
        unique_uids = score_df.uid.unique()
        rand_uids = np.random.choice(unique_uids, size = subset, replace = False)
        score_df = score_df[score_df.uid.isin(rand_uids)]
        
    score_df.sort_values(by='createdAt', inplace = True)
    print(f"Checking Score parity on {len(score_df.uid.unique())} {test} tests...")
    
    for uid, score_uid_df in score_df.groupby('uid', sort=False):
        score_uid_df = score_df[score_df['uid'] == uid]
        plan_uid_df = plan_df[plan_df['uid'] == uid]
        
        report_row, match = score_parity_test(uid, test, score_uid_df, plan_uid_df, config, baseline_df, verbose)
        report_row['match'] = match
        
        report_rows.append(report_row)
        
    report_df = pd.DataFrame(report_rows)
    
    valid_report_df = report_df[~report_df['match'].isna()]
    invalid_report_df = report_df[report_df['match'].isna()]
    print(f"{len(invalid_report_df)} invalid tests out of {len(report_df)} total; ({(len(invalid_report_df) / len(report_df))*100:.1f}%)")
    
    score_parity = (valid_report_df['match'] == True).sum() / len(valid_report_df)
    print(f"{(valid_report_df['match'] == True).sum()} tests with parity out of {len(valid_report_df)} valid tests; ({score_parity*100:.1f}%)")
    
    return report_df 

IES_NORM_TABLE = {
    900.0: 1,
    885.49: 2,
    871.21: 3,
    857.16: 4,
    843.34: 5,
    829.74: 6,
    816.36: 7,
    803.19: 8,
    790.24: 9,
    777.5: 10,
    764.96: 11,
    752.63: 12,
    740.49: 13,
    728.55: 14,
    716.8: 15,
    705.24: 16,
    693.87: 17,
    682.68: 18,
    671.67: 19,
    660.84: 20,
    650.18: 21,
    639.7: 22,
    629.38: 23,
    619.24: 24,
    609.25: 25,
    599.43: 26,
    589.76: 27,
    580.25: 28,
    570.89: 29,
    561.69: 30,
    552.63: 31,
    543.72: 32,
    534.95: 33,
    526.32: 34,
    517.84: 35,
    509.49: 36,
    501.27: 37,
    493.19: 38,
    485.23: 39,
    477.41: 40,
    469.71: 41,
    462.14: 42,
    454.68: 43,
    447.35: 44,
    440.14: 45,
    433.04: 46,
    426.06: 47,
    419.19: 48,
    412.43: 49,
    405.78: 50,
    399.23: 51,
    392.8: 52,
    386.46: 53,
    380.23: 54,
    374.1: 55,
    368.07: 56,
    362.13: 57,
    356.29: 58,
    350.55: 59,
    344.89: 60,
    339.33: 61,
    333.86: 62,
    328.48: 63,
    323.18: 64,
    317.97: 65,
    312.84: 66,
    307.8: 67,
    302.83: 68,
    297.95: 69,
    293.14: 70,
    288.42: 71,
    283.77: 72,
    279.19: 73,
    274.69: 74,
    270.26: 75,
    265.9: 76,
    261.61: 77,
    257.39: 78,
    253.24: 79,
    249.16: 80,
    245.14: 81,
    241.19: 82,
    237.3: 83,
    233.47: 84,
    229.71: 85,
    226.0: 86,
    222.36: 87,
    218.77: 88,
    215.25: 89,
    211.78: 90,
    208.36: 91,
    205.0: 92,
    201.69: 93,
    198.44: 94,
    195.24: 95,
    192.09: 96,
    189.0: 97,
    185.95: 98,
    182.95: 99,
    180: 100,
}


def normalize_ies(ies_score: float):
    """
    Normalizes IES scores using predefined table.

    :param ies_score: The IES score to normalize.
    :type ies_score: float
    :return: The normalized IES score (final agility score)
    :rtype: int
    """
    prev_val = 1
    for key, value in IES_NORM_TABLE.items():
        if ies_score < key:
            prev_val = value
            continue
        return prev_val
    return 100


def get_trial_results(stimulus_times: List[float], onset_times: List[float], config: Dict) -> pd.DataFrame:
    """
    Computes individual trial results based on stimulus and reaction times with test configuration.
    Common logic between all three Pison Ready tests

    :param stimulus_times: List of stimulus times in seconds
    :type stimulus_times: List[float]
    :param onset_times: List of onset times in seconds
    :type onset_times: List[float]
    :param config: test parameters (business logic)
    :type config: Dict
    :return: DataFrame that contains: miss, false start, and reaction time info for each trial
    :rtype: pd.DataFrame
    """
    logger = logging.getLogger(__name__)

    trial_results = []
    for i, led_time in enumerate(stimulus_times):

        if i == 0:
            last_led_time = -1 * config["detection_window"][1] + config["countdown"]
        else:
            last_led_time = stimulus_times[i - 1]

        # This trial is from last_led_time + detection window end to led_time + detection window end
        relevant_onset_times = [
            x
            for x in onset_times
            if x > last_led_time + config["detection_window"][1] and x < led_time + config["detection_window"][1]
        ]

        trial_result = {"miss": False, "false_start": False, "valid_reaction_time": False, "reaction_time": None}

        if len(relevant_onset_times) == 0:
            trial_result["miss"] = True
        else:
            reaction_time = relevant_onset_times[0] - led_time
            trial_result["reaction_time"] = reaction_time

            # These three are mutually exclusive
            if reaction_time <= config["detection_window"][0]:
                trial_result["false_start"] = True
            elif reaction_time >= config["detection_window"][1]:
                trial_result["miss"] = True
            else:
                trial_result["valid_reaction_time"] = True

        logger.debug("trial (%s) results: %s", i, trial_result)

        trial_results.append(trial_result)
    trial_results_df = pd.DataFrame(trial_results)
    trial_results_df.index.name = "trial"

    return trial_results_df

def modified_get_agility_score(stimulus_times: List[float], nogo_trials: List[bool], onset_times: List[float], config: dict) -> tuple:
    """
    Calculates GNG agility score from data per configuration.
    Specifications: https://docs.google.com/document/d/1p2WjJF6YwtrJBbaoMl0sO466jPIX2-cWUlRACBKEc2c/edit#heading=h.ebe2537u0xx5

    :param stimulus_times: List of stimulus times in seconds
    :type stimulus_times: List[float]
    :param nogo_trials: List indicating whether each trial is a no-go trial
    :type nogo_trials: List[bool]
    :param onset_times: List of onset times in seconds
    :type onset_times: List[float]
    :param config: Configuration specifying business logic parameters
    :type config: dict
    :return: A tuple containing the final score and a dictionary with additional scoring information
    :rtype: tuple
    """
    # logger = logging.getLogger(__name__)

    num_nogo_trials = np.sum(nogo_trials)
    num_go_trials = len(stimulus_times) - num_nogo_trials

    # pison_assert(
    logger = logging.getLogger(__name__)

    num_nogo_trials = np.sum(nogo_trials)
    num_go_trials = len(stimulus_times) - num_nogo_trials
    
    if num_nogo_trials == 0 or num_go_trials == 0:
        logger.debug("Number of nogo trials or go trials is zero, invalid score")
        return None, None, None, None, None, None
    
    trial_results_df = get_trial_results(stimulus_times, onset_times, config)

    # Add nogo_trials as a column to trial_results_df for easier access
    trial_results_df["go_trial"] = ~nogo_trials

    # Calculate correct go and nogo trials and their reaction times
    correct_go_trials = trial_results_df[trial_results_df["go_trial"] & trial_results_df["valid_reaction_time"]]
    correct_nogo_trials = trial_results_df[(~trial_results_df["go_trial"]) & trial_results_df["miss"]]
    correct_go = len(correct_go_trials)
    correct_nogo = len(correct_nogo_trials)

    if correct_go == 0:
        logger.debug("no correct go trials, invalid score")
        return None, None, None, None, None, None
        # return 0, {"is_valid_score": False, "trial_results_df": trial_results_df}

    # Must come after checking for correct_go = 0
    algo_data_mean_reaction_time = correct_go_trials["reaction_time"].sum() / correct_go
    algo_data_stdev_reaction_time = correct_go_trials["reaction_time"].std()
    

    # TPR/FPR for research reasons
    # proportion of actual positive cases that are correctly identified
    tpr = correct_go / num_go_trials
    # proportion of actual negative cases that are incorrectly identified as positive
    incorrect_nogo = num_nogo_trials - correct_nogo
    fpr = incorrect_nogo / num_nogo_trials
    

    if "proportion_correct_balanced" not in config:
        config["proportion_correct_balanced"] = True

    if config["proportion_correct_balanced"]:
        algo_data_accuracy = ((0.7) * (correct_nogo / num_nogo_trials)) + ((0.3) * (correct_go / num_go_trials))
    else:
        # here for backwards compatibility for older firmware versions
        algo_data_accuracy = (correct_go + correct_nogo) / len(stimulus_times)

    if algo_data_accuracy == 0:
        ies_score = 1
    else:
        ies_score = algo_data_mean_reaction_time / algo_data_accuracy
    normalized_score = normalize_ies(ies_score * 1000)

    logger.debug("proportion: %s", algo_data_accuracy)
    logger.debug("mean_time: %s, ies_score: %s", algo_data_mean_reaction_time, ies_score)
    logger.debug("normalized_score: %s", normalized_score)
    
    algo_data_number_of_trials = len(stimulus_times)
    algo_data_number_of_false_starts = len(trial_results_df[trial_results_df["false_start"] == True])
    algo_data_number_of_lapses = len(correct_go_trials[correct_go_trials["reaction_time"] > 0.295])    
    info = {
        "is_valid_score": True,
        "algo_data_accuracy": algo_data_accuracy,
        "algo_data_mean_reaction_time": algo_data_mean_reaction_time,
        "algo_data_stdev_reaction_time": algo_data_stdev_reaction_time,
        # "trial_results_df": trial_results_df,
        "TPR": tpr,
        "FPR": fpr,
    }

    # return normalized_score, info
    return algo_data_mean_reaction_time, algo_data_accuracy, algo_data_stdev_reaction_time, algo_data_number_of_trials, algo_data_number_of_false_starts, algo_data_number_of_lapses

def generate_plan_df(score_df):
    all_stim_rows = []  # To accumulate all stim_rows from each test_row
    for test_index, test_row in score_df.iterrows():
        plan_list = test_row['plan.stimuli'] #had to change back to period instead of underscore since we change to underscore later TUE

        if not isinstance(plan_list, list):
            continue  # Skip rows where plan_stimuli is not a valid list
        for stimuli in plan_list:
            row = { #i am using .get to deal with handling missing blue for agility 
                'timeInSeconds': stimuli['timeInSeconds'],
                'configuration_color_red': stimuli['configuration']['color']['red'],
                'configuration_color_green': stimuli['configuration']['color']['green'],
                'configuration_color_blue': stimuli.get('configuration', {}).get('color', {}).get('blue', None),
                'configuration_durationInSeconds': stimuli['configuration']['durationInSeconds'],
                'uid': test_row['uid'],
                'id': test_row['id']
            }
            if row['configuration_color_blue'] is None:
                logging.info(f"Missing 'configuration_color_blue' for UID: {row['uid']}")

            all_stim_rows.append(row)
    return pd.DataFrame(all_stim_rows)


def get_algo_calculations(test, test_df, users_df):
    score_df = test_df
        
    #for agility stuff temporarilty
    plan_df = generate_plan_df(test_df)
    
    def process_ready(score_df):
        pvt_df = format_df(users_df, readiness_config, start_date, end_date, test_type='readiness')
        PVT_results = score_pvt_results(pvt_df)
        
        return {
            'uid': PVT_results['test_uid'],
            'algo_enrichment_data_mean_reaction_time': PVT_results['mean_reaction_time'],
            'algo_enrichment_data_accuracy': None,  # Replace with the appropriate value if needed
            'algo_enrichment_data_stdev_reaction_time': PVT_results['standard_deviation'],
            'algo_enrichment_data_number_of_trials': PVT_results['total_trials'],
            'algo_enrichment_data_number_of_false_starts': PVT_results['total_fs'],
            'algo_enrichment_data_number_of_lapses': PVT_results['total_lapses'],
        }


    def process_agility(id, group, score_df, plan_df):
        # agility_df = format_df(users_df, agility_config, start_date, end_date, test_type='agility')

        score_uid_df = score_df[score_df['plan.id'] == id]
        onset_df = generate_onset_df(score_uid_df)
        plan_uid_df = plan_df[plan_df['id'] == id]

        if not onset_df.empty:
            nogo_trials = (plan_uid_df['configuration_color_blue'].isna() | (plan_uid_df['configuration_color_blue'] == 0)).values
            onset_times = extract_onset_times(onset_df)
            stimulus_times = plan_uid_df['timeInSeconds'].values

            algo_enrichment_data_mean_reaction_time, algo_enrichment_data_accuracy, algo_enrichment_data_stdev_reaction_time, algo_enrichment_data_number_of_trials, algo_enrichment_data_number_of_false_starts, algo_enrichment_data_number_of_lapses = modified_get_agility_score(stimulus_times, nogo_trials, onset_times, agility_config)

            return {
                'uid': id,
                'algo_enrichment_data_mean_reaction_time': algo_enrichment_data_mean_reaction_time,
                'algo_enrichment_data_accuracy': algo_enrichment_data_accuracy,
                'algo_enrichment_data_stdev_reaction_time': algo_enrichment_data_stdev_reaction_time,
                'algo_enrichment_data_number_of_trials': algo_enrichment_data_number_of_trials,
                'algo_enrichment_data_number_of_false_starts': algo_enrichment_data_number_of_false_starts,
                'algo_enrichment_data_number_of_lapses': algo_enrichment_data_number_of_lapses
            }
        else:
            print(f"Warning: Onset DataFrame is empty for id={id}. No data to process.")
            return None

    def process_focus(score_df):
        
        pvt_df = format_df(users_df, focus_config, start_date, end_date, test_type='focus')
        PVT_results = score_pvt_results(pvt_df)
            
        return {
            'uid': PVT_results['test_uid'],
            'algo_enrichment_data_mean_reaction_time': PVT_results['mean_reaction_time'],
            'algo_enrichment_data_accuracy': None,  # Replace with the appropriate value if needed
            'algo_enrichment_data_stdev_reaction_time': PVT_results['standard_deviation'],
            'algo_enrichment_data_number_of_trials': PVT_results['total_trials'],
            'algo_enrichment_data_number_of_false_starts': PVT_results['total_fs'],
            'algo_enrichment_data_number_of_lapses': PVT_results['total_lapses'],
            #make sure to exclude them for the big table
            # 'algo_enrichment_data_fastest_10': PVT_results['fastest_10'],
            # 'algo_enrichment_data_slowest_10': PVT_results['slowest_10']
        }

    
    results = []
    result = None

    if test == 'READY':
        result = process_ready(score_df)
        # result = None
    elif test == 'AGILITY':
        for id, group in test_df.groupby('id', sort=False):
            if test == 'AGILITY':
                result = process_agility(id, group, score_df, plan_df)
            if result:
                results.append(result)
                
        algo_calculations_df = pd.DataFrame(results)
        return algo_calculations_df
    
    elif test == 'FOCUS':
        result = process_focus(score_df)
    else:
        print(f"Unknown test type: {test}")

    algo_calculations_df = pd.DataFrame(result)

    return algo_calculations_df

def get_specific_users(test_df, user_df):
    # Create a list of unique, trimmed emails from the user_df
    email_list = user_df['email'].str.split(',').explode().str.strip().unique().tolist()
    # Filter the test_df to include only rows where the email is in the email_list
    filtered_df = test_df[test_df['email'].isin(email_list)].reset_index(drop=True)
    return filtered_df
    
def create_test_df(env, user_df, algo_calculations_df, test_type, start_date, end_date):
    tests_df = get_reaction_tests(env, start_date = start_date, end_date = end_date)
    tests_df = pd.merge(tests_df, user_df, left_on='user_id', right_on='uid', how='inner')
    
    metadata_df = get_all_metadata(env)
    metadata_df = metadata_df[['session_id','user_id','application_id','device_id','device_version']]    

    if test_type is None:
        test_df = tests_df
        test_types = ['AGILITY', 'FOCUS', 'READY']
        algo_calculations_df = pd.concat(
            [get_algo_calculations(test, tests_df[tests_df['reaction_test_type'] == test], user_df) for test in test_types],
            axis=0
        ).reset_index(drop=True)    
        #print (algo_calculations_df)
    else:
        test_df = tests_df[tests_df['reaction_test_type'] == test_type]
        algo_calculations_df = get_algo_calculations(test_type, test_df, user_df)
        
    
    # print(f"Printing Algorithm Columns: {algo_calculations_df.columns}")
    algo_test_df = pd.merge(test_df, algo_calculations_df, left_on='id', right_on='uid', how='left') # For agility algorithms
    the_final_df = pd.merge(algo_test_df, metadata_df, left_on='session_id', right_on ='session_id', how='left')

    the_final_df.columns = the_final_df.columns.str.replace('.', '_')
    col_to_drop =['uid_y','uid_x','onset_moments','plan_stimuli','user_id_y','enrichment_data_trial_results','custom_attributes_subscription','custom_attributes_claims','is_baseline','model_identifier','deletion_reason', 'is_deleted', 'sharing_mode','enrichment_data_number_of_hits', 'enrichment_data_trial_results_is_hit', 'enrichment_data_trial_results_onset_moment', 'enrichment_data_trial_results_reaction_time', 'enrichment_data_trial_results_is_false_start', 'enrichment_data_trial_results_is_lapse', 'plan_id', 'plan_user_id']
    #print (the_final_df['enrichment_data_trial_results_trial_number']
    ### Flatten out some columns to make it bigquery-able
    columns_to_convert = ['enrichment_data_mean_reaction_time','enrichment_data_accuracy', 'algo_enrichment_data_accuracy','score'] #'enrichment_data_trial_results_trial_number'
    
    for column in columns_to_convert:
        the_final_df[column] = pd.to_numeric(the_final_df[column], errors='coerce')
    
    the_final_df['is_failed'] = pd.to_numeric(the_final_df['is_failed'], errors='coerce').astype('boolean')
    the_final_df['is_failed'] = the_final_df['is_failed'].fillna(False).astype(bool)

    #the_final_df = the_final_df.drop(columns = col_to_drop, axis=1)
    the_final_df = the_final_df.drop(columns=[col for col in col_to_drop if col in the_final_df.columns])
    the_final_df = the_final_df.rename(columns={'user_id_x':'user_id'})
    
    # Rename columns with 'sw_' prefix
    the_final_df.rename(columns={
        'enrichment_data_number_of_trials': 'sw_enrichment_data_number_of_trials',
        'enrichment_data_number_of_false_starts': 'sw_enrichment_data_number_of_false_starts',
        'enrichment_data_number_of_lapses': 'sw_enrichment_data_number_of_lapses',
        'enrichment_data_mean_reaction_time': 'sw_enrichment_data_mean_reaction_time',
        'enrichment_data_stdev_reaction_time': 'sw_enrichment_data_stdev_reaction_time',
        'enrichment_data_accuracy': 'sw_enrichment_data_accuracy'
    }, inplace=True)

    return the_final_df

agility_config = {'detection_window': (0.07, 0.750), 'countdown': 5, 'proportion_correct_balanced': True}
readiness_config = {'detection_window': (0.1, 1.0), 'countdown': 5, 'retained_reaction_time_count': (1,5), 'minimum_reaction_time_count': 2}
focus_config= {'detection_window': (0.08, 1.0), 'countdown': 5, 'retained_reaction_time_count': (0,90), 'minimum_reaction_time_count': 2, 'lapse_multiplier':1}
start_date = dt.datetime(2024, 1, 1, 0, 0, 0)
end_date = dt.datetime(2024, 12, 30, 0, 0, 0)

def main():
    env = Env.STAGING
    user_df = get_users(env)
    user_df = user_df.drop(columns='created_at')
    pison_users_df = pd.read_csv('pison_users.csv')
    users_df = get_specific_users(user_df, pison_users_df)


    
    algo_calculations_df = []
    test_type = None

    big_df = create_test_df(env, users_df, algo_calculations_df, test_type, start_date, end_date)

    try:
        team_df = pd.read_csv('pison_users.csv')
        team_df = team_df[['email', 'Team']]
        team_df.rename(columns={'Team': 'pison_team'}, inplace=True)
        team_df['email'] = team_df['email'].astype(str).str.split(',')
        team_df_exploded = team_df.explode('email')
        team_df_exploded['email'] = team_df_exploded['email'].str.strip()
        email_to_team_map = team_df_exploded.set_index('email')['pison_team'].to_dict()
        big_df['pison_team'] = big_df['email'].map(email_to_team_map)
    except Exception as e:
        print(f"Error processing team data: {e}")
        return

    try:
        project_id = 'core-aca65d38'
        dataset_name = 'Big_Tables'
        super_table = 'Super_Table'
        CHOOSE_YOUR_DESTINATION_TABLE = super_table  
        destination_table = f'{project_id}.{dataset_name}.{CHOOSE_YOUR_DESTINATION_TABLE}'
        rel_cred_path = "key.json" 
        cred_path = os.path.abspath(rel_cred_path)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
        credentials = service_account.Credentials.from_service_account_file(cred_path)
        to_gbq(big_df, destination_table, project_id=project_id, if_exists='replace', credentials=credentials)
    except FileNotFoundError:
        print("Error: Google service account key file 'key.json' not found.")
        return
    except Exception as e:
        print(f"Error uploading data to BigQuery: {e}")
        return



schedule.every(1).hours.do(main)
if __name__ == "__main__":
    main()  # Run the main function once initially
    while True:
        schedule.run_pending()
        time.sleep(1)
