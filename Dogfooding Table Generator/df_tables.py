from table_import import *

agility_config = {'detection_window': (0.07, 0.750), 'countdown': 5, 'proportion_correct_balanced': True}
readiness_config = {'detection_window': (0.1, 1.0), 'countdown': 5, 'retained_reaction_time_count': (1,5), 'minimum_reaction_time_count': 2}
focus_config= {'detection_window': (0.08, 1.0), 'countdown': 5, 'retained_reaction_time_count': (0,90), 'minimum_reaction_time_count': 2, 'lapse_multiplier':1}
start_date = dt.datetime(2024, 7, 1, 0, 0, 0)
end_date = dt.datetime(2024, 12, 30, 0, 0, 0)

def main():
    SERVICE_ACCOUNT = "dashboard-service-account@pison-staging.iam.gserviceaccount.com"
    local_audience = "pison-staging"
    result = subprocess.run(
        [f'gcloud auth print-identity-token --impersonate-service-account="{SERVICE_ACCOUNT}" --audiences="{local_audience}"'],
        stdout=subprocess.PIPE,
        shell=True,
        )
    token = result.stdout.decode("utf-8")[:-1]  # remove trailing newline


    POSTGRES_JSONB_MAX = 1024 * 1024 * 256
    PAGE_LIMIT = 1


    MAX_MESSAGE_LENGTH = PAGE_LIMIT * (POSTGRES_JSONB_MAX + 256)
    channel = grpc.secure_channel("staging.cloud.pison.io", grpc.ssl_channel_credentials(),
                              options=[
                                  ('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),
                                  ('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH),
                              ],
                              )
    stub = session_pb2_grpc.SessionServiceStub(channel)

    response = stub.ReadSession(
        ReadSessionRequest(
        ),
        metadata=[
            ("authorization", f"Bearer {token}")
            ]
        )
    response_dict = MessageToDict(response)
    df = pd.json_normalize(response_dict['sessions'])


    try:
        env = Env.STAGING
        user_df = get_users(env)
        user_df = user_df.drop(columns='created_at')
        pison_users_df = pd.read_csv('pison_users.csv')
        users_df = get_specific_users(user_df, pison_users_df)

    
        test_df = get_reaction_tests(env, start_date, end_date)
        test_df = pd.merge(test_df, users_df, left_on='user_id', right_on='uid', how='inner')
        metadata_df = get_all_metadata(env)
        metadata_df = metadata_df[['session_id','user_id','application_id','device_id','device_version','protocol_name']]
        the_final_df = pd.merge(test_df, metadata_df, left_on='session_id', right_on ='session_id', how='left')
        the_final_df.columns = the_final_df.columns.str.replace('.', '_')
        pt1_2024_df = pd.read_csv('2024_pt1.csv')
        the_final_df = pd.concat([pt1_2024_df, the_final_df], axis=0, ignore_index=True)
        col_to_drop =['uid_y','uid_x','user_id_y','enrichment_data_trial_results','onset_moments','custom_attributes_subscription','custom_attributes_claims','is_baseline','model_identifier','deletion_reason', 
        'is_deleted', 'sharing_mode','enrichment_data_number_of_hits', 'enrichment_data_trial_results_is_hit', 'enrichment_data_trial_results_onset_moment', 'enrichment_data_trial_results_reaction_time', 
        'enrichment_data_trial_results_is_false_start', 'enrichment_data_trial_results_is_lapse', 'plan_id', 'plan_user_id', 'demographics_date_of_birth', 'demographics_gender', 'demographics_height', 
        'demographics_weight']
        the_final_df = the_final_df.drop(columns=[col for col in col_to_drop if col in the_final_df.columns])

        the_final_df = the_final_df.rename(columns={'user_id_x':'user_id'})
        columns_to_convert = ['enrichment_data_mean_reaction_time','enrichment_data_accuracy','score']
    
        for column in columns_to_convert:
            the_final_df[column] = pd.to_numeric(the_final_df[column], errors='coerce')

        the_final_df.rename(columns={
        'enrichment_data_number_of_trials': 'sw_enrichment_data_number_of_trials',
        'enrichment_data_number_of_false_starts': 'sw_enrichment_data_number_of_false_starts',
        'enrichment_data_number_of_lapses': 'sw_enrichment_data_number_of_lapses',
        'enrichment_data_mean_reaction_time': 'sw_enrichment_data_mean_reaction_time',
        'enrichment_data_stdev_reaction_time': 'sw_enrichment_data_stdev_reaction_time',
        'enrichment_data_accuracy': 'sw_enrichment_data_accuracy',
        'plan_stimuli': 'plan_exists'
            }, inplace=True)
    
        the_final_df['is_failed'] = the_final_df['is_failed'].fillna(False).astype(bool)
        the_final_df['is_failed'] = pd.to_numeric(the_final_df['is_failed'], errors='coerce').astype('boolean')

        the_final_df['plan_exists'] = the_final_df['plan_exists'].fillna(False).astype(bool)
        the_final_df['plan_exists'] = pd.to_numeric(the_final_df['plan_exists'], errors='coerce').astype('boolean')
    
        the_final_df['created_at'] = pd.to_datetime(the_final_df['created_at'], errors='coerce')
        team_df = pd.read_csv('pison_users.csv')
        team_df = team_df[['email', 'Team']]
        team_df.rename(columns={'Team': 'pison_team'}, inplace=True)
        team_df['email'] = team_df['email'].astype(str).str.split(',')

# Explode the list into separate rows
        team_df_exploded = team_df.explode('email')

# Strip any leading/trailing whitespace from email addresses
        team_df_exploded['email'] = team_df_exploded['email'].str.strip()

# Mapping from email to pison_team
        email_to_team_map = team_df_exploded.set_index('email')['pison_team'].to_dict()

        the_final_df['pison_team'] = the_final_df['email'].map(email_to_team_map)
    except Exception as e:
        print(f"Error: {e}")
        return

    try:
        
        big_table = 'core-aca65d38.Big_Tables.Super_Table'
        agility_table = 'core-aca65d38.Big_Tables.Agility_Table'
        focus_table = 'core-aca65d38.Big_Tables.Focus_Table'
        ready_table = 'core-aca65d38.Big_Tables.Ready_Table'
        
        rel_cred_path = "key.json" 
        cred_path = os.path.abspath(rel_cred_path)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
        credentials = service_account.Credentials.from_service_account_file(cred_path)
        to_gbq(the_final_df, big_table, project_id='core-aca65d38', if_exists='replace', credentials=credentials)

        agility_df = the_final_df[the_final_df['reaction_test_type'] == 'AGILITY']
        focus_df = the_final_df[the_final_df['reaction_test_type'] == 'FOCUS']
        ready_df = the_final_df[the_final_df['reaction_test_type'] == 'READY']
        
        to_gbq(agility_df, agility_table, project_id='core-aca65d38', if_exists='replace', credentials=credentials)
        to_gbq(focus_df, focus_table, project_id='core-aca65d38', if_exists='replace', credentials=credentials)
        to_gbq(ready_df, ready_table, project_id='core-aca65d38', if_exists='replace', credentials=credentials)
        
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