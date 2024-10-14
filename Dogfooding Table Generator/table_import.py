import numpy as np
import pandas as pd
import logging
import grpc
import subprocess
from datetime import datetime
import datetime as dt
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.json_format import MessageToDict
from google.oauth2 import service_account
from pandas_gbq import to_gbq, read_gbq
import schedule
import time
import os
from ml_util.query.microservices import (
    PisonGrpc,
    ResponseConverter,
    get_users,
    get_reaction_tests,
    get_plan_data,
    get_all_metadata,
)
from ml_util.pison_ready.readiness import get_score as get_readiness_score
from ml_util.pison_ready.agility import get_score as get_agility_score
from ml_util.pison_ready.focus import get_score as get_focus_score
from pison_cloud.pison.common.cloud.v1 import common_pb2
from typing import List, Dict, Tuple
from ml_util.query.utils import Env

import grpc
import subprocess
import json

from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.json_format import MessageToDict
import pandas as pd

from pison_cloud.pison.session.cloud.v2 import session_pb2_grpc
from pison_cloud.pison.session.cloud.v2.session_pb2 import ReadSessionRequest

from pison_cloud.pison.common.cloud.v1.common_pb2 import ListFilterParams, IdType, DateRange, ListPaginationParams, ListSortParams, ApplicationMetadata



from pison_cloud.pison.session.cloud.v2 import session_pb2_grpc
from pison_cloud.pison.session.cloud.v2.session_pb2 import ReadSessionRequest

from pison_cloud.pison.common.cloud.v1.common_pb2 import ListFilterParams, IdType, DateRange, ListPaginationParams, ListSortParams, ApplicationMetadata

# IES normalization table for agility score calculation
IES_NORM_TABLE = {
    900.0: 1, 885.49: 2, 871.21: 3, 857.16: 4, 843.34: 5,
    829.74: 6, 816.36: 7, 803.19: 8, 790.24: 9, 777.5: 10,
    764.96: 11, 752.63: 12, 740.49: 13, 728.55: 14, 716.8: 15,
    705.24: 16, 693.87: 17, 682.68: 18, 671.67: 19, 660.84: 20,
    650.18: 21, 639.7: 22, 629.38: 23, 619.24: 24, 609.25: 25,
    599.43: 26, 589.76: 27, 580.25: 28, 570.89: 29, 561.69: 30,
    552.63: 31, 543.72: 32, 534.95: 33, 526.32: 34, 517.84: 35,
    509.49: 36, 501.27: 37, 493.19: 38, 485.23: 39, 477.41: 40,
    469.71: 41, 462.14: 42, 454.68: 43, 447.35: 44, 440.14: 45,
    433.04: 46, 426.06: 47, 419.19: 48, 412.43: 49, 405.78: 50,
    399.23: 51, 392.8: 52, 386.46: 53, 380.23: 54, 374.1: 55,
    368.07: 56, 362.13: 57, 356.29: 58, 350.55: 59, 344.89: 60,
    339.33: 61, 333.86: 62, 328.48: 63, 323.18: 64, 317.97: 65,
    312.84: 66, 307.8: 67, 302.83: 68, 297.95: 69, 293.14: 70,
    288.42: 71, 283.77: 72, 279.19: 73, 274.69: 74, 270.26: 75,
    265.9: 76, 261.61: 77, 257.39: 78, 253.24: 79, 249.16: 80,
    245.14: 81, 241.19: 82, 237.3: 83, 233.47: 84, 229.71: 85,
    226.0: 86, 222.36: 87, 218.77: 88, 215.25: 89, 211.78: 90,
    208.36: 91, 205.0: 92, 201.69: 93, 198.44: 94, 195.24: 95,
    192.09: 96, 189.0: 97, 185.95: 98, 182.95: 99, 180: 100,
}

# Converter classes for different types of gRPC responses
class ReactionConverter(ResponseConverter):
    def __call__(self, response):
        response_dict = MessageToDict(response)
        if "tests" in response_dict:
            return pd.json_normalize(response_dict['tests'])
        else:
            data_f = super().__call__(response)
            return data_f

class UsersConverter(ResponseConverter):
    def __call__(self, response):
        response_dict = MessageToDict(response)
        if "users" in response_dict:
            data_f = pd.json_normalize(response_dict["users"])
        else:
            data_f = super().__call__(response)
        return data_f

class SessionConverter(ResponseConverter):
    def __call__(self, response):
        response_dict = MessageToDict(response)
        if "sessions" in response_dict:
            data_f = pd.json_normalize(response_dict["sessions"])
        else:
            data_f = super().__call__(response)
        return data_f

class ReadinessConverter(ResponseConverter):
    def __call__(self, readiness_res):
        response_dict = MessageToDict(readiness_res)
        if "scores" in response_dict:
            data_f = pd.json_normalize(response_dict["scores"])
            if "onsetMoments" in data_f:
                data_f = data_f.explode("onsetMoments")
        else:
            data_f = super().__call__(readiness_res)
        return data_f

class PlanConverter(ResponseConverter):
    def __call__(self, plan_res):
        data = MessageToDict(plan_res)
        if data and "plan" in data and "stimuli" in data["plan"]:
            flat_data = {
                "timeInSeconds": [],
                "configuration_color_red": [],
                "configuration_color_green": [],
                "configuration_color_blue": [],
                "configuration_durationInSeconds": [],
            }

            for stimulus in data["plan"]["stimuli"]:
                flat_data["timeInSeconds"].append(stimulus["timeInSeconds"])
                config = stimulus["configuration"]

                for color in ["red", "green", "blue"]:
                    val = config["color"].get(color, 0.0)
                    flat_data[f"configuration_color_{color}"].append(val)

                flat_data["configuration_durationInSeconds"].append(config["durationInSeconds"])

            data_f = pd.DataFrame(flat_data)
        else:
            data_f = super().__call__(plan_res)
        return data_f

# Function to calculate onset times
def extract_onset_times(onset_df):
    onset_df['onset_moment'] = pd.to_datetime(onset_df['onset_moment'], format='mixed')
    onset_df['created_at'] = pd.to_datetime(onset_df['created_at'], format='mixed')
    onset_times = (onset_df['onset_moment'] - onset_df['created_at']).dt.total_seconds().values
    return sorted(onset_times)

# Function to generate onset dataframe
def generate_onset_df(score_df):
    all_onset_rows = []
    for test_index, test_row in score_df.iterrows():
        onset_list = test_row['onset_moments']
        if not isinstance(onset_list, list):
            continue
        for onset in onset_list:
            row = {
                'onset_moment': onset,
                'created_at': test_row['created_at'],
                'uid': test_row['uid']
            }
            all_onset_rows.append(row)
    return pd.DataFrame(all_onset_rows)

# Function to normalize IES scores
def normalize_ies(ies_score: float):
    prev_val = 1
    for key, value in IES_NORM_TABLE.items():
        if ies_score < key:
            prev_val = value
            continue
        return prev_val
    return 100

# Function to calculate trial results
def get_trial_results(stimulus_times: List[float], onset_times: List[float], config: Dict) -> pd.DataFrame:
    trial_results = []
    for i, led_time in enumerate(stimulus_times):
        last_led_time = stimulus_times[i - 1] if i > 0 else -1 * config["detection_window"][1] + config["countdown"]
        relevant_onset_times = [
            x for x in onset_times
            if last_led_time + config["detection_window"][1] < x < led_time + config["detection_window"][1]
        ]

        trial_result = {
            "miss": len(relevant_onset_times) == 0,
            "false_start": False,
            "valid_reaction_time": False,
            "reaction_time": None
        }

        if relevant_onset_times:
            reaction_time = relevant_onset_times[0] - led_time
            trial_result["reaction_time"] = reaction_time
            if reaction_time <= config["detection_window"][0]:
                trial_result["false_start"] = True
            elif reaction_time < config["detection_window"][1]:
                trial_result["valid_reaction_time"] = True

        trial_results.append(trial_result)
    return pd.DataFrame(trial_results)

# Function to process reaction test data and calculate parity
def score_parity_test(uid, test, score_uid_df, plan_uid_df, config, baseline_df=None, verbose=False):
    report = {
        'uid': uid,
        'createdAt': score_uid_df['createdAt'].iloc[0],
        'has_ms_precision': '.' in str(score_uid_df['createdAt'].iloc[0]),
        'has_onset_moments': not score_uid_df['onsetMoments'].isna().any(),
        'has_plan_data': len(plan_uid_df) > 0,
        'has_stimuli_times': (len(plan_uid_df) > 0) and (not plan_uid_df['timeInSeconds'].isna().any()),
    }

    if pd.isnull(report['createdAt']) or not all([report['has_ms_precision'], report['has_onset_moments'], 
                                                  report['has_plan_data'], report['has_stimuli_times']]):
        return report, None

    stimulus_times = plan_uid_df['timeInSeconds'].values
    onset_times = extract_onset_times(score_uid_df)

    if test == 'readiness':
        score, info = get_readiness_score(stimulus_times, onset_times, config)
        firmware_score = score_uid_df['reactionTimeInMilliseconds'].fillna(0).iloc[0]
        match = abs(score - firmware_score) <= 1.0

    elif test == 'agility':
        nogo_trials = (plan_uid_df['configuration_color_blue'] == 0).values
        if np.sum(nogo_trials) == 0:
            report['nonstandard_nogo_lighting'] = True
            return report, None

        score, info = get_agility_score(stimulus_times, nogo_trials, onset_times, config)
        firmware_score = score_uid_df['agilityScoreValue'].fillna(0).iloc[0]
        match = (score - firmware_score) == 0

    elif test == 'focus':
        user_id = score_uid_df['userId'].iloc[0]
        baseline_uid_df = baseline_df[baseline_df['userId'] == user_id]

        if baseline_uid_df.empty:
            report['empty_baseline'] = True
            return report, None

        baseline_reaction_time = baseline_uid_df['reactionTimeInMilliseconds'].iloc[0] / 1000
        firmware_score = score_uid_df['focusScoreValue'].fillna(0).iloc[0]
        score, info = get_focus_score(stimulus_times, onset_times, config, baseline_reaction_time)
        match = (score - firmware_score) == 0

    if not match and verbose:
        print(info)

    return report, match

# Function to calculate all scores for parity testing
def score_parity_test_all(score_df, plan_df, test, config, baseline_df=None, verbose=False, subset=None):
    report_rows = []
    score_df = score_df.copy()
    plan_df = plan_df.copy()

    if subset is not None:
        unique_uids = score_df.uid.unique()
        rand_uids = np.random.choice(unique_uids, size=subset, replace=False)
        score_df = score_df[score_df.uid.isin(rand_uids)]

    score_df.sort_values(by='createdAt', inplace=True)
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

# Simplified PisonGrpc class
class PisonGrpc:
    def __init__(self, env):
        self.env = env
        self._target = "cloud.pison.io" if env == 'production' else f"{env}.cloud.pison.io"
        self._audience = f"pison-{env}"
        self._id_token = None
        self._channel = None

    def create_channel(self):
        service_account = f"dashboard-service-account@pison-{self.env}.iam.gserviceaccount.com"
        audience = self._audience
        result = subprocess.run(
            [
                f'gcloud auth print-identity-token --impersonate-service-account="{service_account}" --audiences="{audience}"'
            ],
            stdout=subprocess.PIPE,
            shell=True,
            check=True,
        )
        self._id_token = result.stdout.decode("utf-8").strip()
        self._channel = grpc.secure_channel(self._target, grpc.ssl_channel_credentials())

    def __call__(self, service_stub, rpc_name, request, res_converter=None):
        stub = service_stub(self._channel)
        rpc = getattr(stub, rpc_name)
        response = rpc(request, metadata=[("authorization", f"Bearer {self._id_token}")])
        ret = {"response": response}
        if res_converter:
            data_frame = res_converter(response)
            ret["dataframe"] = data_frame
        return ret

# Function to preprocess test data
def preprocess_test_data(test_df):
    test_df = test_df.copy()
    test_df["createdAt"] = pd.to_datetime(test_df["createdAt"], format='ISO8601', utc=True)
    test_df["onsetMoments"] = pd.to_datetime(test_df["onsetMoments"], format='ISO8601', utc=True)
    test_df.sort_values(by="createdAt", inplace=True)
    return test_df

# Function to get readiness data
def get_readiness_data(env, user_ids, start_date, end_date, max_rec=None):
    with PisonGrpc(env=env) as rpc:
        query_parameters = common_pb2.ListQueryParameters(
            user_ids=user_ids,
            date_range=get_pb_date_range(start_date, end_date),
        )

        request = readiness_pb2.ListReadinessRequest(
            query_parameters=query_parameters,
            sort=readiness_pb2.ListSortParams(key="createdAt", ascending=False),
            pagination=readiness_pb2.ListPaginationParams(limit=max_rec, offset=0),
        )

        readiness_res = rpc(
            readiness_pb2_grpc.ReadinessServiceStub, "ListReadiness", request, BulkyReadinessConverter()
        )
        readiness_df = preprocess_test_data(readiness_res["dataframe"])

    return readiness_df

# Function to get plan data
def get_plan_data(env, uids, keep_silent=True):
    plans = []

    with PisonGrpc(env=env) as rpc:
        for uid in tqdm(uids):
            try:
                plan_res = rpc(
                    readiness_pb2_grpc.ReadinessServiceStub,
                    "ReadPlan",
                    readiness_pb2.ReadPlanRequest(uid=uid),
                    PlanConverter(),
                )
                this_df = plan_res["dataframe"]
                this_df["uid"] = uid

                plans.append(this_df)
            except Exception as ex:
                if not keep_silent:
                    logging.error(ex, exc_info=True)

    plan_df = pd.concat(plans)
    return plan_df

# Function to convert date range to protobuf format
def get_pb_date_range(start, end):
    return common_pb2.DateRange(start=to_pb_timestamp(start), end=to_pb_timestamp(end))

# Function to convert datetime to protobuf timestamp
def to_pb_timestamp(datetime):
    timestamp = Timestamp()
    timestamp.FromDatetime(datetime)
    return timestamp

def get_specific_users(test_df, user_df):
    # Create a list of unique, trimmed emails from the user_df
    email_list = user_df['email'].str.split(',').explode().str.strip().unique().tolist()
    # Filter the test_df to include only rows where the email is in the email_list
    filtered_df = test_df[test_df['email'].isin(email_list)].reset_index(drop=True)
    return filtered_df
