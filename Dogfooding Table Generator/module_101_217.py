# Import necessary libraries
import schedule
import time
import datetime as dt
import pandas as pd
from pandas_gbq import to_gbq
from google.oauth2 import service_account
import os
import glob
import logging



# pylint:disable=import-error, arguments-differ, ungrouped-imports
from abc import ABC
import logging
from enum import Enum
import subprocess

import grpc
import pandas as pd
from tqdm import tqdm

from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.json_format import MessageToDict

from pison_cloud.pison.readiness.cloud.v1 import readiness_pb2, readiness_pb2_grpc
from pison_cloud.pison.agility_score.cloud.v1 import agility_score_pb2, agility_score_pb2_grpc
from pison_cloud.pison.focus_score.cloud.v1 import focus_score_pb2, focus_score_pb2_grpc
from pison_cloud.pison.session.cloud.v1 import session_pb2, session_pb2_grpc
from pison_cloud.pison.common.cloud.v1.common_pb2 import DateRange, ListQueryParameters

from query.microservices import get_users

from query.utils import Env

env = Env.STAGING



class Env(Enum):
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "ops"


class ResponseConverter(ABC):
    """
    Base class of reponse converters
    """

    def __call__(self, response):
        """
        Convert a reponse object to pandas dataframe

        :param reponse: a reponse object
        :type response: grpc response
        :return: a dataframe object
        :rtype: pandas.DataFrame
        """
        return pd.DataFrame()


class UsersConverter(ResponseConverter):
    """
    Converter for the `ListUsersRequest()` RPC call
    """

    def __call__(self, response):
        """
        Convert a reponse object to pandas dataframe

        :param reponse: a reponse object
        :type response: grpc response
        :return: a dataframe object
        :rtype: pandas.DataFrame
        """
        response_dict = MessageToDict(response)
        if "users" in response_dict:
            data_f = pd.json_normalize(response_dict["users"])
        else:
            data_f = super().__call__(response)
        return data_f


class SessionConverter(ResponseConverter):
    def __call__(self, response):
        """
        Convert a reponse object to pandas dataframe

        :param reponse: a reponse object
        :type response: grpc response
        :return: a dataframe object
        :rtype: pandas.DataFrame
        """
        response_dict = MessageToDict(response)
        if "sessions" in response_dict:
            data_f = pd.json_normalize(response_dict["sessions"])
        else:
            data_f = super().__call__(response)
        return data_f


class ReadinessConverter(ResponseConverter):
    """
    Converter for the `ListReadiness()` RPC call
    """

    def __call__(self, readiness_res):
        """
        Convert a reponse object to pandas dataframe

        :param reponse: a reponse object
        :type response: grpc response
        :return: a dataframe object
        :rtype: pandas.DataFrame
        """
        response_dict = MessageToDict(readiness_res)
        if "scores" in response_dict:
            data_f = pd.json_normalize(response_dict["scores"])
            if "onsetMoments" in data_f:
                data_f = data_f.explode("onsetMoments")
        else:
            data_f = super().__call__(readiness_res)
        return data_f


class BulkyReadinessConverter(ResponseConverter):
    """
    Converter for the `ListReadiness()` RPC call, assuming a
    response that includes bulk user data.
    """

    def __call__(self, readiness_res):
        """
        Convert a reponse object to pandas dataframe

        :param reponse: a reponse object
        :type response: grpc response
        :return: a dataframe object
        :rtype: pandas.DataFrame
        """
        dfs = []
        for _, user_scores in readiness_res.scores_by_user.items():
            for score in user_scores.scores:
                flat_score = pd.json_normalize(MessageToDict(score))
                if "onsetMoments" in flat_score:
                    flat_score = flat_score.explode("onsetMoments")
                dfs.append(flat_score)
        data_f = pd.concat(dfs)
        return data_f


class AgilityConverter(ReadinessConverter):
    """
    Converter for the `ListAgilityScore()` RPC call
    """


class BulkyAgilityConverter(BulkyReadinessConverter):
    """
    Converter for the `ListAgilityScore()` RPC call, assuming a
    response that includes bulk user data.
    """


class FocusConverter(ReadinessConverter):
    """
    Converter for the `ListFocusScore()` RPC call
    """


class BulkyFocusConverter(BulkyReadinessConverter):
    """
    Converter for the `ListFocusScore()` RPC call, assuming a
    response that includes bulk user data.
    """


class BaselineConverter(ResponseConverter):
    """
    Converter for the `ReadBaselineById()` RPC call
    """

    def __call__(self, baseline_res):
        """
        Convert a reponse object to pandas dataframe

        :param reponse: a reponse object
        :type response: grpc response
        :return: a dataframe object
        :rtype: pandas.DataFrame
        """
        response_dict = MessageToDict(baseline_res)
        data_f = pd.DataFrame(response_dict).T
        return data_f


class PlanConverter(ResponseConverter):
    """
    Converter for the `ReadPlan()` RPC call
    """

    def __call__(self, plan_res):
        """
        Convert a reponse object to pandas dataframe

        :param reponse: a reponse object
        :type response: grpc response
        :return: a dataframe object
        :rtype: pandas.DataFrame
        """
        data = MessageToDict(plan_res)
        if data and data["plan"] and data["plan"]["stimuli"]:
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
                    val = config["color"][color] if color in config["color"] else 0.0
                    flat_data[f"configuration_color_{color}"].append(val)

                flat_data["configuration_durationInSeconds"].append(config["durationInSeconds"])

            # Create DataFrame
            data_f = pd.DataFrame(flat_data)
        else:
            data_f = super().__call__(plan_res)
        return data_f


class PisonGrpc:
    """
    A gRPC utility class for reading Pison Ready data from the cloud
    """

    def __init__(self, env=Env.STAGING):
        """
        Constructor

        :param env: environment Enum which dictates which environment to use
        :type env: Env
        """
        self.env = env
        if env.value == Env.PRODUCTION.value:
            self._target = "cloud.pison.io"
        else:
            self._target = f"{env.value}.cloud.pison.io"
        self._audience = f"pison-{env.value}"
        self._id_token = None
        self._channel = None

    def __enter__(self):
        """
        Overloaded context manager entry call
        """
        self.create_channel()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Overloaded context manager exit call
        """
        if self._channel is not None:
            self._channel.close()

    def create_channel(self):
        """
        Creates a gRPC channel using the new authenticaion framework
        """
        service_account = f"dashboard-service-account@pison-{self.env.value}.iam.gserviceaccount.com"
        audience = self._audience
        result = subprocess.run(
            [
                f'gcloud auth print-identity-token --impersonate-service-account="{service_account}" --audiences="{audience}"'
            ],
            stdout=subprocess.PIPE,
            shell=True,
            check=True,
        )
        self._id_token = result.stdout.decode("utf-8")[:-1]  # remove trailing newline
        self._channel = grpc.secure_channel(self._target, grpc.ssl_channel_credentials())

    def __call__(self, service_stub, rpc_name, request, res_converter=None):
        """
        Handles gRPC calls

        :param service_stub: gRPC service stub
        :type service_stub: str
        :param rpc_name: gRPC call name
        :type rpc_name: str
        :param request: gRPC request
        :type request: gRPC request object compatible with the corresponding service call
        :param res_converter: a response converter
        :type res_converter: ResponseConverter
        :return: a dict containing the response as a dataframe
        :rtype: dict
        """
        stub = service_stub(self._channel)
        rpc = getattr(stub, rpc_name)

        response = rpc(request, metadata=[("authorization", f"Bearer {self._id_token}")])

        ret = {"response": response}

        if res_converter:
            data_frame = res_converter(response)
            ret["dataframe"] = data_frame

        return ret


def preprocess_test_data(test_df):
    """
    Perporms common preprocessing of test (readiness, agility, focus) data after it's pulled and before it's returned.

    :param test_df: readiness, agility or focus score dataframe
    :type datetime: datetime.datetime
    :return: processesd test data dataframe
    :rtype: pandas.DataFrame
    """
    test_df = test_df.copy()
    test_df["createdAt"] = pd.to_datetime(test_df["createdAt"], format= 'ISO8601')
    test_df["onsetMoments"] = pd.to_datetime(test_df["onsetMoments"], format= 'ISO8601')
    test_df = test_df.sort_values(by="createdAt")
    return test_df

def to_pb_timestamp(datetime):
    """
    Convert a datetime object to a Google pb timestamp

    :param datetime: the datetime object
    :type datetime: datetime.datetime
    :return: Google pb timestamp
    :rtype: datetime
    """
    timestamp = Timestamp()
    timestamp.FromDatetime(datetime)
    return timestamp


def get_pb_date_range(start, end):
    return DateRange(start=to_pb_timestamp(start), end=to_pb_timestamp(end))


def get_readiness_data(env, user_ids, start_date, end_date, max_rec=10000):

    with PisonGrpc(env=env) as rpc:

        query_parameters = ListQueryParameters(
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


def get_agility_data(env, user_ids, start_date, end_date, max_rec=10000):

    with PisonGrpc(env=env) as rpc:
        query_parameters = ListQueryParameters(
            user_ids=user_ids,
            date_range=get_pb_date_range(start_date, end_date),
        )

        request = agility_score_pb2.ListAgilityScoreRequest(
            query_parameters=query_parameters,
            sort=agility_score_pb2.ListSortParams(key="createdAt", ascending=False),
            pagination=agility_score_pb2.ListPaginationParams(limit=max_rec, offset=0),
        )

        agility_res = rpc(
            agility_score_pb2_grpc.AgilityScoreServiceStub, "ListAgilityScore", request, BulkyAgilityConverter()
        )
        agility_df = preprocess_test_data(agility_res["dataframe"])

    return agility_df


def get_focus_data(env, user_ids, start_date, end_date, max_rec=10000):
    with PisonGrpc(env=env) as rpc:
        query_parameters = ListQueryParameters(
            user_ids=user_ids,
            date_range=get_pb_date_range(start_date, end_date),
        )

        request = focus_score_pb2.ListFocusScoreRequest(
            query_parameters=query_parameters,
            sort=focus_score_pb2.ListSortParams(key="createdAt", ascending=False),
            pagination=focus_score_pb2.ListPaginationParams(limit=max_rec, offset=0),
        )

        focus_res = rpc(focus_score_pb2_grpc.FocusScoreServiceStub, "ListFocusScore", request, BulkyFocusConverter())
        focus_df = preprocess_test_data(focus_res["dataframe"])

    return focus_df


# def get_plan_data(env, score_df, keep_silent=True):
def get_plan_data(env, uids, keep_silent=True):
    """
    Downloads plan data for users in the passed-in score dataframe

    :param env: cloud environment enum
    :type env: Env
    :param score_df: score dataframe
    :type score_df: pandas.DataFrame
    :param keep_silent: whether to log errors
    :type keep_silent: bool
    :return: plan dataframe
    :rtype: pandas.DataFrame
    """
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


def get_baseline_data(env, baseline_ids, keep_silent=True):
    """
    Downloads baseline data for users in the passed-in score dataframe

    :param env: cloud environment enum
    :type env: Env
    :param score_df: score dataframe
    :type score_df: pandas.DataFrame
    :param keep_silent: whether to log errors
    :type keep_silent: bool
    :return: baseline dataframe
    :rtype: pandas.DataFrame
    """
    baselines = []

    with PisonGrpc(env=env) as rpc:
        for baseline_id in tqdm(baseline_ids):
            try:
                baseline_res = rpc(
                    readiness_pb2_grpc.ReadinessServiceStub,
                    "ReadBaselineById",
                    readiness_pb2.ReadBaselineByIdRequest(id=baseline_id),
                    BaselineConverter(),
                )
                baselines.append(baseline_res["dataframe"])
            except Exception as ex:
                if not keep_silent:
                    logging.error(ex, exc_info=True)

    baseline_df = pd.concat(baselines)
    return baseline_df


def get_session_data(env, user_ids, keep_silent=True):

    sessions = []

    with PisonGrpc(env=env) as rpc:
        for user_id in tqdm(user_ids):
            try:
                session_res = rpc(
                    session_pb2_grpc.SessionServiceStub,
                    "ReadSession",
                    session_pb2.ReadSessionRequest(user_id=user_id),
                    SessionConverter(),
                )
                sessions.append(session_res["dataframe"])
            except Exception as ex:
                if not keep_silent:
                    logging.error(ex, exc_info=True)

    session_df = pd.concat(sessions)
    return session_df

# pylint:disable=import-error, arguments-differ, ungrouped-imports
from typing import List, Tuple

import pandas as pd

#from pison_ready.onset_detection import get_emg_activations
from pison_ready.utils import activations_to_onset_times
from pison_ready import readiness, agility, focus


# def get_onset_times(session_df: pd.DataFrame, channels: List[str], detector_configuration: dict):
#     """
#     Get onset times given an IDF with specified channels.

#     :param session_df: Processed session data in IDF format
#     :type session_df: pd.DataFrame
#     :param channels: List of column names in session_df corresponding to EMG data channels
#     :type channels: List[str]
#     :param detector_configuration: onset detector config
#     :type detector_configuration: dict
#     :return: A tuple containing array of actdivation and the corresponding onset times
#     :rtype: tuple
#     """
#     emg_data = session_df[channels].values
#     activations = get_emg_activations(emg_data, detector_configuration)
#     timestamps = session_df["timestamp"].values
#     onset_times = activations_to_onset_times(activations, timestamps)
#     onset_times = list(onset_times)

#     return activations, onset_times


def generate_test_score(
    session_df: pd.DataFrame, channels: List[str], test_info: dict, sampling_rate: int = 800
) -> Tuple:
    """
    High level function that takes raw data and test information in dict format and returns the expected score

    :param session_df: test dataframe (IDF format) containing the EMG data
    :type session_df: pd.DataFrame
    :param channels: list of EMG channels
    :type channels: List[str]
    :param test_info: Overloade dictionary acting as all the parameters for this test
    :type test_info: dict
    :param sampling_rate: (Optional) Sampling rate of the EMG data
    :type sampling_rate: int
    :return: A tuple containing the test score, additional test information (for developmenet), and onset times
    :rtype: Tuple[float, dict, List[float]]
    """
    _, onset_times = get_onset_times(session_df, channels, test_info["detector_config"])

    test_type = test_info["test_type"]
    stimulus_times = test_info["stimulus_times"]
    test_config = test_info["test_config"]

    if test_type == "readiness":
        score, info = readiness.get_score(stimulus_times, onset_times, test_config)
    if test_type == "agility":
        score, info = agility.get_score(stimulus_times, test_info["nogo_trials"], onset_times, test_config)
    if test_type == "focus":
        score, info = focus.get_score(stimulus_times, onset_times, test_config, test_info["user_baseline"])

    return score, info, onset_times


def preprocess_test_data(test_df):
    """
    Perporms common preprocessing of test (readiness, agility, focus) data after it's pulled and before it's returned.

    :param test_df: readiness, agility or focus score dataframe
    :type datetime: datetime.datetime
    :return: processesd test data dataframe
    :rtype: pandas.DataFrame
    """
    test_df = test_df.copy()
    test_df["createdAt"] = pd.to_datetime(test_df["createdAt"], format='ISO8601', utc=True)
    test_df["onsetMoments"] = pd.to_datetime(test_df["onsetMoments"], format='ISO8601', utc=True)
    test_df = test_df.sort_values(by="createdAt")
    return test_df
    
def get_readiness_data(env, user_ids, start_date, end_date, max_rec=10000):

    with PisonGrpc(env=env) as rpc:

        query_parameters = ListQueryParameters(
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

def get_plan_data(env, uids, keep_silent=True):
    """
    Downloads plan data for users in the passed-in score dataframe

    :param env: cloud environment enum
    :type env: Env
    :param score_df: score dataframe
    :type score_df: pandas.DataFrame
    :param keep_silent: whether to log errors
    :type keep_silent: bool
    :return: plan dataframe
    :rtype: pandas.DataFrame
    """
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


from pison_ready.readiness import get_score as get_readiness_score
from pison_ready.agility import get_score as get_agility_score
from pison_ready.focus import get_score as get_focus_score
from query.microservices import get_reaction_tests

import pprint

# pylint:disable=import-error, arguments-differ, ungrouped-imports
from typing import List
import logging

import numpy as np

from pison_utils.utils import pison_assert
from pison_ready.utils import get_trial_results


def get_readiness_score(stimulus_times: List[float], onset_times: List[float], config: dict) -> tuple:
    """
    Calculates SRT readiness score from data per specifications.
    Specifications: https://docs.google.com/spreadsheets/d/1t7bg14730FJphSW4fZNg8aDwwd8Q2yzBXhbp8j5WsHI/edit#gid=955054747

    :param stimulus_times: List of stimulus times in seconds
    :type stimulus_times: List[float]
    :param onset_times: List of onset times in seconds
    :type onset_times: List[float]
    :param config: Configuration dictionary specifying business logic parameters
    :type config: dict
    :return: A tuple containing the SRT readiness score and a dictionary with additional scoring information
    :rtype: tuple
    """
    pison_assert(
        len(stimulus_times) > 0,
        exception=ValueError(f"Length of stimulus times ({len(stimulus_times)}) can't be empty"),
    )
    logger = logging.getLogger(__name__)

    trial_results_df = get_trial_results(stimulus_times, onset_times, config)

    active_trials_df = trial_results_df[(~trial_results_df["miss"]) & (~trial_results_df["false_start"])]
    active_trials_df = active_trials_df.sort_values(by="reaction_time")

    remove_last = len(stimulus_times) - config["retained_reaction_time_count"][1]
    retained_trials_df = active_trials_df.iloc[
        config["retained_reaction_time_count"][0] : len(active_trials_df) - remove_last
    ]

    is_valid_score = len(retained_trials_df) >= config["minimum_reaction_time_count"]

    if is_valid_score:
        score = np.mean(retained_trials_df["reaction_time"]) * 1000  # convert to ms
    else:
        score = 0.0

    logger.debug("is valid: %s, score: %s", is_valid_score, score)
    info = {"is_valid_score": is_valid_score, "trial_results_df": trial_results_df}

    return score, info

def get_focus_score(stimulus_times: List[float], onset_times: List[float], config: dict) -> tuple:
    pison_assert(
        len(stimulus_times) > 0,
        exception=ValueError(f"Length of stimulus times ({len(stimulus_times)}) can't be empty"),
    )
    logger = logging.getLogger(__name__)

    trial_results_df = get_trial_results(stimulus_times, onset_times, config)

    active_trials_df = trial_results_df[(~trial_results_df["miss"]) & (~trial_results_df["false_start"])]
    active_trials_df = active_trials_df.sort_values(by="reaction_time")

    remove_last = len(stimulus_times) - config["retained_reaction_time_count"][1]
    retained_trials_df = active_trials_df.iloc[
        config["retained_reaction_time_count"][0] : len(active_trials_df) - remove_last
    ]

    is_valid_score = len(retained_trials_df) >= config["minimum_reaction_time_count"]

    if is_valid_score:
        score = np.mean(retained_trials_df["reaction_time"]) * 1000  # convert to ms
    else:
        score = 0.0

    logger.debug("is valid: %s, score: %s", is_valid_score, score)
    info = {"is_valid_score": is_valid_score, "trial_results_df": trial_results_df}

    return score, info



def get_onset_times(score_df):
    onset_times = score_df['onsetMoments'] - score_df['createdAt']
    onset_times = onset_times.dt.total_seconds().values
    onset_times = sorted(onset_times)
    return onset_times


def parity_test(score_df, plan_df, test, config, baseline_df = None, verbose = False, subset = -1):
    common_uids = list(set(score_df.uid) & set(plan_df.uid))
    score_matches = 0
    tested_uids = 0
    
    print("Checking parity...")
    for uid in common_uids[0:subset]:
        score_uid_df = score_df[score_df['uid'] == uid]
        plan_uid_df = plan_df[plan_df['uid'] == uid]

        if score_uid_df['onsetMoments'].isna().any() or score_uid_df['createdAt'].isna().any() or plan_uid_df['timeInSeconds'].isna().any():
            print(f'skipping {uid}, insufficient datetime info')
            continue

        stimulus_times = plan_uid_df['timeInSeconds'].values
        onset_times = get_onset_times(score_uid_df)
        
        if test == 'readiness':
            score, info = get_readiness_score(stimulus_times, onset_times, config)
            firmware_score = score_uid_df['reactionTimeInMilliseconds'].fillna(0).iloc[0]
            
            match = abs(score - firmware_score) <= 1.0

            
        elif test == 'agility':
            nogo_trials = (plan_uid_df.configuration_color_blue == 0).values
            score, info = get_agility_score(stimulus_times, nogo_trials, onset_times, config)
            
            firmware_score = score_uid_df['agilityScoreValue'].fillna(0).iloc[0]
            
            match = (score - firmware_score) == 0
            
        elif test == 'focus':
            user_id = score_uid_df['userId'].iloc[0]
            baseline_uid_df = baseline_df[baseline_df['uid'] == user_id]
            if baseline_uid_df.empty:
                print(f'skipping {uid}, no baseline found')
                continue
                
            baseline_reaction_time = baseline_uid_df['reactionTimeInMilliseconds'].iloc[0] / 1000
            
            firmware_score = score_uid_df['focusScoreValue'].fillna(0).iloc[0]
            score, info = get_focus_score(stimulus_times, onset_times, config, baseline_reaction_time)
            
            match = (score - firmware_score) == 0
            
        if match:
            #print('score', score, 'firmware_score', firmware_score)
            score_matches += 1
            
        else:
            if verbose:
                print('uid', uid)
                print('stimulus_times', stimulus_times)
                print('onset_times', onset_times)
                print('score', score)
                print('firmware_score', firmware_score)
                #print(info['trial_results'])
                #display(info['trial_results_df'])
                pprint.pprint(info)
                
                #"proportion": proportion,
                #"mean_time": mean_time,
                #"ies_score": ies_score,
                print('date', score_uid_df.createdAt.iloc[0])
                print()
                print()
        
        tested_uids += 1
    
    score_parity = score_matches / tested_uids
    print(f"Score Parity: {score_parity * 100:.1f}%")

    return score, info


# Define the function with the requested additional columns
def score_pvt_results(df):
    results_list = []

    # Group by both user and test UID
    grouped = df.groupby(['email', 'uid'])

    for (user_id, test_uid), df_user in grouped:
        # Initialize variables to avoid UnboundLocalError
        mean_rt = None
        std_dev_rt = None
        fastest_10 = None
        slowest_10 = None
        percent_lapses = None
        percent_false_starts = None
        cv = None
        throughput = None
        
        df_user['reaction_time_ms'] = df_user['reaction_time'] * 1000
        df_user['is_false_start'] = df_user['reaction_time_ms'] < 80
        false_starts = df_user['is_false_start'].sum()
        total_responses = len(df_user)
        valid_reactions = df_user[~df_user['is_false_start']]
        
        # Check if there are no valid reactions
        if valid_reactions.empty:
            continue
        
        mean_rt = valid_reactions['reaction_time_ms'].mean()
        std_dev_rt = valid_reactions['reaction_time_ms'].std()
        fastest_10 = valid_reactions['reaction_time_ms'].quantile(0.1)
        slowest_10 = valid_reactions['reaction_time_ms'].quantile(0.9)
        lapses = valid_reactions['reaction_time_ms'][valid_reactions['reaction_time_ms'] > 295].count()
        date = df_user['createdAt'].iloc[0]
        
        results = {
            'email': user_id,
            'test_uid': test_uid,
            'date': date,
            'total_trials': total_responses,
            'total_lapses': lapses,
            'total_fs': false_starts,
            'mean_reaction_time': mean_rt,
            'standard_deviation': std_dev_rt,
            'fastest_10': fastest_10, 
            'slowest_10': slowest_10
        }

        # Convert results to DataFrame with a single row and append to results list
        results_df = pd.DataFrame([results])
        results_list.append(results_df)

    # Concatenate all results into a single DataFrame
    final_results_df = pd.concat(results_list, ignore_index=True)

    return final_results_df

def format_df(users_df, config, start_date, end_date, test_type='readiness'):
    # email_list = pd.read_csv('101_users.csv')['email'].str.split(',').explode().str.strip().unique().tolist()
    # users_df = pd.DataFrame()
    # filtered_df = [user_df[user_df['email'] == email] for email in email_list]
    # users_df = pd.concat(filtered_df, ignore_index=True)
    # users_df = user_df[user_df['email'].isin(email_list)].reset_index(drop=True)
    if test_type == 'readiness':
        tests_df = get_readiness_data(env, users_df.uid.unique(), start_date, end_date, max_rec=10000).dropna(subset=['sessionId'])
    elif test_type == 'agility':
        tests_df = get_agility_data(env, users_df.uid.unique(), start_date, end_date, max_rec=10000).dropna(subset=['sessionId'])
    else:
        tests_df = get_focus_data(env, users_df.uid.unique(), start_date, end_date, max_rec=10000)#.dropna(subset=['sessionId'])
        

    # plan_df = get_plan_data(env, tests_df.uid.unique(), keep_silent=True)

    plan_df = get_reaction_tests(env, start_date, end_date, uids= tests_df.uid.unique())

    
    results = get_verbose_scoring_output(tests_df, plan_df, test_type, config, verbose = False)
    merged_df = pd.merge(results, users_df[['uid', 'email']], left_on='userId', right_on='uid', how='left')
    merged_df.drop(columns=['uid_y'], inplace=True)
    merged_df.rename(columns={'uid_x': 'uid'}, inplace=True)
    return merged_df

def get_verbose_scoring_output(score_df, plan_df, test, config, baseline_df=None, verbose=False, subset=-1):
    # Initialize a list to store result dictionaries
    results_list = []
    
    common_uids = list(set(score_df.uid) & set(plan_df.id))
    print("Checking parity...")
    for uid in common_uids:#[0:subset]:
        score_uid_df = score_df[score_df['uid'] == uid]
        # plan_uid_df = plan_df[plan_df['uid'] == uid]
        plan_uid_df = plan_df[plan_df['id'] == uid]['plan.stimuli'].iloc[0]

        import math
        if isinstance(plan_uid_df, float) and math.isnan(plan_uid_df):
            continue
        else:

    
            times_in_seconds = [item['timeInSeconds'] for item in plan_uid_df]
            # print(times_in_seconds)
                
            # if score_uid_df['onsetMoments'].isna().any() or score_uid_df['createdAt'].isna().any() or plan_uid_df['timeInSeconds'].isna().any():
            if score_uid_df['onsetMoments'].isna().any() or score_uid_df['createdAt'].isna().any() or not len(times_in_seconds):
                print(f'skipping {uid}, insufficient datetime info')
                continue
    
            # stimulus_times = plan_uid_df['timeInSeconds'].values
            stimulus_times = times_in_seconds
            onset_times = get_onset_times(score_uid_df)
            
            # Initialize score to None, it will be updated based on the test type
            score = None
            
            if test == 'readiness':
                score, info = get_readiness_score(stimulus_times, onset_times, config)
            elif test == 'agility':
                nogo_trials = (plan_uid_df.configuration_color_blue == 0).values
                

                print(nogo_trials)

                score, info = get_agility_score(stimulus_times, nogo_trials, onset_times, config)                
            elif test == 'focus':
                user_id = score_uid_df['userId'].iloc[0]
                score, info = get_focus_score(stimulus_times, onset_times, config)
    
            user_id = score_uid_df['userId'].iloc[0]  # Extract userId for inclusion in results
            
            trial_results_df = info['trial_results_df']
    
    
            if test == 'readiness':
            # Iterate over each row in the trial_results_df DataFrame
                for index, row in trial_results_df.iterrows():
                    results_list.append({
                        'uid': uid,
                        'userId': user_id,  # Include userId in each row
                        'test': test,
                        'trial': index,
                        'miss': row['miss'],
                        'false_start': row['false_start'],
                        'reaction_time': row['reaction_time'],
                        'score': score,  # Include the overall score for this user/test
                        'createdAt': score_uid_df['createdAt'].iloc[0],
                        'fw_reaction_time': score_uid_df['reactionTimeInMilliseconds'].iloc[0]
                    })
    
            
    
            else: 
                for index, row in trial_results_df.iterrows():
                    results_list.append({
                        'uid': uid,
                        'userId': user_id,  # Include userId in each row
                        'test': test,
                        'trial': index,
                        'miss': row['miss'],
                        'false_start': row['false_start'],
                        'reaction_time': row['reaction_time'],
                        'score': score,  # Include the overall score for this user/test
                        'createdAt': score_uid_df['createdAt'].iloc[0]
                    })
                
        
        # Create a DataFrame from the collected result dictionaries
        results_df = pd.DataFrame(results_list)
    
    return results_df



# Import your existing functions and classes here
# from your_notebook_code import *

# Ensure your notebook code (functions, classes, etc.) is imported or included in this script

# def main():
#     try:
#         env = Env.PRODUCTION
#         user_df = get_users(env)

#         teams = ['project101', 'project217']
#         tables = ['-101', 'pvt-217']

#         for team, table in zip(teams, tables):
#             try:
#                 print(f"Processing team: {team}, table: {table}")

#                 # Filter user_df for the current team
#                 merged_user_df = user_df[user_df['email'].str.contains(team)].copy()
                

#                 # Define date range and focus configuration
#                 start_date = dt.datetime(2024, 3, 1, 0, 0, 0)
#                 end_date = dt.datetime(2024, 9, 25, 0, 0, 0)
#                 focus_config = {
#                     'detection_window': (0.01, 1.0),
#                     'countdown': 5,
#                     'retained_reaction_time_count': (0, 90),
#                     'minimum_reaction_time_count': 2
#                 }

#                 # Format and score PVT results
#                 pvt_df = format_df(merged_user_df, focus_config, start_date, end_date, test_type='focus')
#                 PVT_results = score_pvt_results(pvt_df)
                
#                 PVT_results['total_users'] = merged_user_df['email'].nunique()
                
#                 print(PVT_results)

#                 # Set project ID, dataset name, and table name
#                 project_id = 'core-aca65d38'
#                 dataset_name = 'dogfooding'
#                 destination_table = f'{project_id}.{dataset_name}.{table}'

#                 # Set the path to the service account key file and the environment variable
#                 cred_path = "key.json"
#                 os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path

#                 # Create credentials using the service account key file
#                 credentials = service_account.Credentials.from_service_account_file(cred_path)

#                 # Write DataFrame to BigQuery
#                 to_gbq(
#                     PVT_results,
#                     destination_table,
#                     project_id=project_id,
#                     if_exists='replace',
#                     credentials=credentials
#                 )
#                 print(f"Successfully uploaded data for team: {team}, table: {table}")

#             except Exception as e:
#                 print(f"Error processing team: {team}, table: {table} - {str(e)}")

#     except Exception as e:
#         print(f"Error in main process - {str(e)}")


# schedule.every(10).minutes.do(main)

# if __name__ == "__main__":
#     main()  # Run the main function once initially
#     while True:
#         schedule.run_pending()
#         time.sleep(1)
