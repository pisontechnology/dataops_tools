
import cv2
import matplotlib.pyplot as plt
plt.rc('font', family='Arial')
import pandas as pd
from datetime import timezone
import numpy as np
from typing import List, Tuple, Union
from scipy.signal import butter, iirnotch, filtfilt
import csv 

pd.set_option('display.float_format', lambda x: '%.0f' % x)

clicked_index = None

###FILTERING###
def butter_highpass(
    cutoff: float, fs: float, order: int = 4
) -> Tuple[List[float], List[float]]:
    """
    Design a highpass Butterworth filter and return its coefficients.
    """
    assert cutoff > 0, "Cutoff frequency must be greater than 0"
    assert (
        fs > 2 * cutoff
    ), "Sampling frequency must be greater than twice the cutoff frequency"
    assert order > 0, "Order must be a positive integer"

    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype="high", analog=False)
    return b, a


def highpass_filter(
    data: List[float], cutoff: float, fs: float, order: int = 4
) -> List[float]:
    """
    Apply a highpass Butterworth filter to the data.
    """
    b, a = butter_highpass(cutoff, fs, order=order)
    y = filtfilt(b, a, data)
    return y


def notch_filter(
    data: List[float], notch_freq: float, Q: float, fs: float
) -> List[float]:
    """
    Apply a notch filter to the data.
    """
    assert notch_freq > 0, "Notch frequency must be greater than 0"
    assert (
        fs > 2 * notch_freq
    ), "Sampling frequency must be greater than twice the notch frequency"
    assert Q > 0, "Q factor must be a positive number"

    nyquist = 0.5 * fs
    freq_ratio = notch_freq / nyquist
    b, a = iirnotch(freq_ratio, Q)

    filtered_data = filtfilt(b, a, data)

    return filtered_data

def apply_filters_to_channels(df, raw_channels, fs, highpass_cutoff=20, notch_base_freq=60, Q=30):
    for emg_channel in raw_channels:
        filtered_emg_channel_name = emg_channel + '_filtered'
        hp_data = highpass_filter(df[emg_channel], highpass_cutoff, fs)
        notch_hp_data = notch_filter(hp_data, notch_base_freq, Q, fs)
        df[filtered_emg_channel_name] = notch_hp_data
    return df
######

###UNPACKING + APPLY FILTERS####
def transform_sensor_data(csv_path):
    #load the unformatted CSV into a dataframe
    no_formatting = pd.read_csv(csv_path)

    #create the new dataframe structure
    data = pd.DataFrame(columns=[
        'timestamp', 'timestampNanos', 'elapsedTimeSeconds', 'data_type','unit', 
        'adc_0', 'adc_1', 'adc_2', 'adc_3', 'adc_4',  
        'accX', 'accY', 'accZ', 'gyroX', 'gyroY', 'gyroZ', 
        'quatW', 'quatX', 'quatY', 'quatZ'
    ])

    #copy over shared columns
    data['timestamp'] = no_formatting['timestamp']
    data['timestampNanos'] = no_formatting['timestampNanos']
    data['elapsedTimeSeconds'] = no_formatting['elapsedTimeSeconds']
    data['data_type'] = no_formatting['name']

    data['unit'] = np.nan  # Placeholder until we have unit values

    #spit the sensor_values column into seperate column
    sensor_values = no_formatting['sensor_values'].str.strip('[]').str.split(expand=True)
    print(sensor_values)

    #mapping that splits up sensor_values 
    sensor_map = {
        'EMG': ['adc_0', 'adc_1', 'adc_2', 'adc_3', 'adc_4'],
        'ACCELEROMETER': ['accX', 'accY', 'accZ'],
        'GYROSCOPE': ['gyroX', 'gyroY', 'gyroZ'],
        'QUATERNION': ['quatW', 'quatX', 'quatY', 'quatZ']
    }

    #assign sensor values to respective columns in new dataframe
    for sensor, columns in sensor_map.items():
        sensor_rows = no_formatting['name'] == sensor
        data.loc[sensor_rows, columns] = sensor_values.loc[sensor_rows, :len(columns)-1].values

    #the code was bugging out and chatgpt said this would helo
    numeric_cols = data.columns.difference(['timestamp', 'timestampNanos', 'elapsedTimeSeconds', 'data_type', 'unit'])
    data[numeric_cols] = data[numeric_cols].apply(pd.to_numeric, errors='coerce')

    adc_rows = data[data['data_type'] == 'EMG']
    imu_rows = data[data['data_type'].isin(['ACCELEROMETER', 'GYROSCOPE', 'QUATERNION'])]

    imu_df = pd.DataFrame(imu_rows)
    adc_df = pd.DataFrame(adc_rows)


    adc_df.drop_duplicates(subset=['timestampNanos'],inplace=True)
    adc_df.to_csv('/Users/ella.tubbs/Desktop/check_adc_df.csv')
    apply_filters_to_channels(adc_df, ['adc_0', 'adc_1', 'adc_2', 'adc_3', 'adc_4'], fs=1000, highpass_cutoff=20, notch_base_freq=60, Q=30)

    all_data_df = pd.concat([adc_df, imu_df], ignore_index=True).sort_values(by='timestampNanos')
    

    return all_data_df

def read_and_convert_timestamps(file_path):
    """
    Reads textfile datetimes into Unix Epoch Nanoseconds
    """
    df = pd.read_csv(file_path, header=None, names=['timestamp', 'frame'])
    df.drop_duplicates(inplace=True)

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['unix_timestamp'] = df['timestamp'].apply(lambda x: int(x.replace(tzinfo=timezone.utc).timestamp() * 1e9))
    df['unix_timestamp'] = df['unix_timestamp'] + 1.8e+13
    df['frame'] = df['frame'] - 1

    frame_timestamps = df.set_index('frame')['unix_timestamp'].to_dict()

    return frame_timestamps
######

###EVENT HANDLING###
def onclick(event, df, ax, fig, rate, csv_file_path):
    """
    Handle mouse click event on the plot.
    """
    global clicked_index
    if event.xdata is not None and event.inaxes is not None:
        clicked_index = int(event.xdata)
        ax.plot(clicked_index, event.ydata, 'ro')  #mark the clicked position with a red dot
        fig.canvas.draw()

        #immediately prompt for label in the terminal
        print(f"Clicked at index {clicked_index}. Enter label for this point (leave blank to skip): ", end='')
        label = input()
        if label:
            save_label_to_csv(csv_file_path, df.iloc[clicked_index]['timestampNanos'], label)
            print(f"Label '{label}' saved for timestamp {df.iloc[clicked_index]['timestampNanos']}")
        else:
            print("Labeling skipped.")

def save_label_to_csv(csv_file_path, timestamp, label):
    """
    Save the label and timestamp to a CSV file.
    """
    with open(csv_file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, label])
    #print(f"Label '{label}' saved for timestamp {timestamp}")
######

###CV FUNCTIONS###
def process_video(video_path, frame_index=0):
    """
    Generator to process the video and yield frames with timestamps.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    while cap.isOpened():
        ret, frame = cap.read()
        if ret:
            timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)
            yield frame, timestamp
        else:
            break
    cap.release()


def select_time_series_columns(df):
    """
    Select groups of columns for time series plot.
    """
    group_map = {
        'ADC': ['adc_0_filtered', 'adc_1_filtered', 'adc_2_filtered', 'adc_3_filtered', 'adc_4_filtered'],
        'ACC': ['accX', 'accY', 'accZ'],
        'GYRO': ['gyroX', 'gyroY', 'gyroZ'],
        'QUAT': ['quatW', 'quatX', 'quatY', 'quatZ']
    }

    print("Available groups: ADC, ACC, GYRO, QUAT")
    selected_groups = input("Enter group names, separated by commas: ").split(',')

    selected_columns = []
    for group in selected_groups:
        group = group.strip().upper()
        if group in group_map:
            selected_columns.extend(group_map[group])

    return selected_columns


def update_plot(fig, df, selected_cols, current_index, window_size):
    """
    Update time series plot with segments for the current frame and a vertical line indicating the current frame.
    Different groups are separated by space and have different colors, and each group has a single label.
    Y-axis numbers are turned off. More x-axis ticks are added with vertical labels.
    """
    fig.clear()

    colors = {
        'ADC': '#00406B',
        'ACC': '#FECB03',
        'GYRO': '#00EEFF',
        'QUAT': 'purple'
    }
    labels = {
        'ADC': 'EMG',
        'ACC': 'Accelerometer',
        'GYRO': 'IMU',
        'QUAT': 'Quaternion'
    }
    start_index = max(0, current_index - window_size // 2)
    end_index = min(df.shape[0], current_index + window_size // 2)

    #map individual column names to groups 
    group_map = {
        'ADC': ['adc_0_filtered', 'adc_1_filtered', 'adc_2_filtered', 'adc_3_filtered', 'adc_4_filtered'],
        'ACC': ['accX', 'accY', 'accZ'],
        'GYRO': ['gyroX', 'gyroY', 'gyroZ'],
        'QUAT': ['quatW', 'quatX', 'quatY', 'quatZ']
    }

    #determine number of plots and spacing 
    num_plots = sum([1 for col in selected_cols if col in df.columns])
    num_groups = len(set([group for group, cols in group_map.items() for col in cols if col in selected_cols]))
    total_plots = num_plots + num_groups - 1 

    #create subplot for each column + empty subplots for spacing
    axs = fig.subplots(total_plots, 1, sharex=True)
    if total_plots == 1:  #if only one plot, axs is not a list
        axs = [axs]

    plot_index = 0
    group_start_index = 0 
    for group, group_cols in group_map.items():
        for col in group_cols:
           
            if col in selected_cols:
                #print('type:', col)
                #print('values for window', df[col].iloc[start_index:end_index])
                color = colors[group]
                start_index = max(0, current_index - window_size // 2)
                end_index = min(df.shape[0], current_index + window_size // 2)

                axs[plot_index].plot(range(start_index, end_index), df[col].iloc[start_index:end_index], label=col, color=color)
                axs[plot_index].axvline(x=current_index, color='red', linestyle='-')
                axs[plot_index].set_yticklabels([])  

                axs[plot_index].set_xticks(range(start_index, end_index, int(window_size / 8)))  
                axs[plot_index].set_xticklabels(axs[plot_index].get_xticks(), rotation=90)  

                plot_index += 1

        if plot_index - group_start_index > 0: 
            #add group label
            fig.text(0.04, 0.5 * (axs[group_start_index].get_position().y0 + axs[plot_index - 1].get_position().y1), labels[group], 
                     va='center', ha='center', rotation='vertical', fontsize=12)
        
        group_start_index = plot_index

        if plot_index < total_plots:  #empty subplot for spacing added 
            axs[plot_index].axis('off')  
            plot_index += 1

    axs[-1].set_xlabel('Index')
    fig.suptitle('Athlete 2 Round 2.1: Catch', fontsize=14)

    fig.subplots_adjust(hspace=0.5, left=0.1)  #adjust vertical spacing and left margin 





######

###RUNNER###
def display_frames(video_path, df, rate, csv_file_path, timestamp_file_path):
    """
    Display video frames and a sliding window of time series data around each frame.
    Adds functionality to label a point in the time series by clicking on the plot.
    """

    global clicked_index

    plt.ion()

    selected_cols = select_time_series_columns(df)
    #print('COLUMNS SELECTED: ', selected_cols)
    frame_gen = process_video(video_path)
    current_frame = 0
    window_samples = 3000  #number of samples to display at a time

    fig, ax = plt.subplots()
    #watch for click on plot
    cid = fig.canvas.mpl_connect('button_press_event', lambda event: onclick(event, df, ax, fig, rate, csv_file_path))

    frame_timestamps = read_and_convert_timestamps(timestamp_file_path)

    #get timestamp of first video frame
    first_video_timestamp = frame_timestamps[0] if frame_timestamps else None

    frame, _ = next(frame_gen, (None, None))

    while frame is not None:
        cv2.imshow('Frame', frame)

        key = cv2.waitKey(0) & 0xFF

        if key == ord('n'):  #next frame
            current_frame += 1
        elif key == ord('b'):  #previous frame
            current_frame = max(current_frame - 1, 0)
        elif key == ord('s'):  #skip frames forward
            current_frame += 10
        elif key == ord('r'):  #skip frames backward
            current_frame = max(current_frame - 10, 0)
        elif key == ord('q'):  #quit
            break

        frame_time = frame_timestamps.get(current_frame, None)
        if frame_time is not None:
            #get part of series data that occurs on or after the first frame of the video 
            valid_timestamps = df[df['timestampNanos'] >= first_video_timestamp]
            valid_timestamps = valid_timestamps.drop_duplicates(subset='timestampNanos')

            if not valid_timestamps.empty:
                #define pd series of the differences, in nanoseconds, between the series timestamps and the current frame time
                time_diffs = (valid_timestamps['timestampNanos'] - frame_time).abs()
                #get the index of the series timestamp with the smallest difference from the frame time
                closest_index = time_diffs.idxmin()
                closest_timestamp = valid_timestamps.at[closest_index, 'timestampNanos']

                #debugging output
                #print(f"[Frame number: {current_frame}, Frame Time: {frame_time:.0f}], [Closest Timeseries: {closest_timestamp}, Index: {closest_index}]")
                #print(f"Time differences (ns):\n {time_diffs.head()}") #prints the first few lines of the time differences for debugging

            else:
                print("No valid timestamps found after the first video timestamp.")
     
            #plots sliding window and vertical line to show where in the signal the frame is coming from 
            update_plot(fig, df, selected_cols, closest_index, window_samples)

        #if a point was clicked, prompt terminal for label 
        if clicked_index is not None:
            timestamp = df.iloc[clicked_index]['timestampNanos']
            label = input("Enter label for the clicked point: ")
            if label:
                save_label_to_csv(csv_file_path, timestamp, label)
            clicked_index = None  #reset the clicked index 

        #get new instance of frame and call next frame from generator 
        frame_gen = process_video(video_path, current_frame)
        frame, _ = next(frame_gen, (None, None))

    cv2.destroyAllWindows()
    plt.close()
    fig.canvas.mpl_disconnect(cid)
######

def main():
    video_path = '/Users/ella.tubbs/Desktop/better_baseball.mp4'
    csv_path = '/Users/ella.tubbs/Desktop/goodgoodbaseball.csv'
    timestamps_path = '/Users/ella.tubbs/Desktop/better_baseball_timestamps.txt'
    labels_path = '/Users/ella.tubbs/Desktop/labels.csv'

    formatted_df = transform_sensor_data(csv_path)
    formatted_df.to_csv('/Users/ella.tubbs/Desktop/checkdf.csv')
    


    rate = 1000  #sampling rate of sensor
    display_frames(video_path, formatted_df, rate, labels_path, timestamps_path)


if __name__ == "__main__":
    main()

