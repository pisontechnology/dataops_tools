# Video / Sensor Data Viewer + Labeler


## *"Do you think God stays in heaven because he too lives in fear of what he's created?"* - Steve Buscemi as Romero, Spy Kids 2: Island of Lost Dreams (2002)

Here lies the documentation for a tool that should not exist in a single Python executable nor should be written in Python at all. Hopefully it will assist you in further tooling. Any questions, including those of a philosophical nature, can be directed to tubbs@mit.edu, where I may or may not answer (I am at school).

## Overview
This tool is a part of Pison's baseball data analysis pipeline. It allows you to simultaneously view signals *and* the video footage of the activities that generated the signal, like batting and catching, synchronized with nanosecond precision (theoretically). It also allows you to label events in the signal using the frame-by-frame footage as a ground truth. 


## Launching the Tool
Part of the beauty of this beast is that it is very lightweight to get started with. It has a small collection of imports, all of which I would consider to be fairly standard, but you may have to install some of them in your environment using your favorite trusty package manager. If I remember, I will put those in a requirements.txt, but if you can't find a requirements.txt in this folder, it is because I forgot.

All you have to do is just run the file from your terminal or press run. When you do this, you will see a prompt in the terminal that says `Available groups: ADC, ACC, GYRO, QUAT` [corresponding to EMG, Accelerometer, Gyroscope, and Quaternion (if you would ever want it)]. Enter the names of the groups that you would like to plot, matching them as they are listed and separating them by comma. 

Once you do this, the program is going to churn for a little bit, and then it will automatically open two windows: one for the frame viewer and one for the sensor data plot. The frame viewer will just be a black box, and the sensor data plot should just look like an empty plot. 

## Navigation 
**Before you traverse through frames, you have to be clicked into the window with the frame viewer (the black box).** Otherwise it will register your keystrokes as typing in the terminal, or worse, nothing at all, instead of navigation events. 

Here are your navigation controls, which you can easily change by altering the `display_frames` function: 

 1. `n`: Advance by one frame. Once you press this for the first time, the frame viewer window should go from a blank black screen to the first frame of the video, and the sensor data window should populate with your chosen signals. 
 2. `b`: Go back one frame. 
 3. `s`: Skip 10 frames forward. You can change this number to whatever. 
 4. `r`: Skip 10 frames backward. Ditto.
 5. `q`: Close the program and windows. 

You may feel like spamming either `n` or `b` to navigate through data quickly, but that will bog down the event handling and everything will start to lag. Try to make use of keys that allow you to skip multiple frames at a time, even if that means you need to add a key to skip through 100+ frames.

## Labeling 
To create a label, click anywhere on a signal in the sensor data plot. Your first click might be registered as you leaving the frame viewer window and entering the new window, so you may have to click again. At this point you will see a line in the terminal `Clicked at index XXXXXXX. Enter label for this point (leave blank to skip):` Now you can enter your label in the terminal. You will then see a line that says `Label 'xyz' saved for timestamp [UNIX EPOCH]`. The label and the corresponding timestamp will be saved automatically to the CSV. Click back into the frame viewer window to continue navigating, or click again in the signal plotter window to create another label. 

## When You Are Done
You need to either press `q` to close the windows or trash the terminal. Then you can restart as needed. 

## Now I Will Hold Your Hand and Guide You Through a Forest Fire 
The code can be thought of as a sleep paralysis demon with four heads: 

 1. Unpacking and preprocessing of sensor data
 2. Dealing with timestamps\(TM) (Synchronization) 
 3. Event handling 
 4. Display 

### 1.  Unpacking and Preprocessing of Sensor Data 
At some point this will have really cool BigQuery functionality, which I thinking a certain someone (Sam) is working on, so this section might become inaccurate as time goes on. But I will show you what it is right now. Go ahead and scroll on down to `main()`. Here you will find `video_path`, where you need to put the path to the video you would like to view, `csv_path`, where you need to put the path to the corresponding CSV with sensor data, `timestamps_path`, where you need to put the path to the textfile that lives with the video (as of winter 2024, it will be in the Google Drive in the folder with the video), and `labels_path`, where you need to put a path to where you would like the created label CSV to live. 

From here, our big player is `transform_sensor_data` which takes in the raw signals CSV and unpacks it into a data frame where each column corresponds to a single channel of sensor (i.e. ADC channels 0-4, Accelerometer X-Z, etc.) Be really careful in modifying this, since the CSVs are massive and the functioning is currently written as efficiently as I could possibly get it (time-wise, at least). At some point, you may be receiving a CSV that is already in this format, and in that case, just convert `csv_path` to a dataframe and pass that directly into the call to `display_frames`. Oh, also worth noting that `transform_sensor_data` also has the EMG filtering functions rolled into it (`butter_highpass, highpass_filter, notch_filter, apply_filters_to_channels`) so if you don't use `transform_sensor_data`, go ahead and also apply `apply_filters_to_channels` to your dataframe. 

### 2. Dealing with Timestamps (Synchronization) 
Most of the code that deals with synchronizing the video frames and the sensor data lives in `read_and_convert_timestamps` and `display_frames`, but instead of going through that syntax I will briefly go over how I go about the synchronization in the code. The timestamps in the `timestamps_path` text file correspond to the exact UTC timestamps, **IN EASTERN TIME**, that each frame of the video was taken. The timestamps in the sensor data are in Unix Epoch Nanoseconds **IN STANDARD TIME**. So, before you can do absolutely anything, you have to get the video timestamps to match the format of the sensor timestamps for comparison. This is done in `read_and_convert_timestamps`. 

Now you can think about synchronization. This is tricky since everything is operating at a different rate (the video frame rate is 30 FPS, the EMG sampling rate is 1000, the IMU sampling rate is something that is not 30 or 1000 (like 100ish)). But basically, all you have to do is grab the timestamp of the frame, convert it to Unix Epoch Nanoseconds, and then find the closest match in the sensor timestamps that occurs either at or after the start of the video. Note that this will very rarely be a perfect match, and that is alright. **Sometimes, you will encounter very strange things like the frame locking to a specific timestamp in the sensor data and never advancing as you navigate through the frames. This is most likely because there is some weird form of packet loss or other data loss around the timestamp that you are dealing with.** There are two commented out debugging statements in `display_frames` that can help you in diagnosing this issue if you think it is occurring. 

### 3. Event Handling 
This tool uses an interactive form of Matplotlib for the frame navigation and clicking, and most of these things I ripped straight from the developer documentation and exist in `display_frames` and `update_plot`. If you see a weird line in the code it is probably necessary for the event handling to work, for reasons I regrettably do not fully understand. 

### 4. Display 
For each frame that gets displayed, you will see a stagnant red line in the sensor plot. This shows you exactly where in the signal the frame is occurring, and as you navigate, the signal shifts around that line. As default, you are seeing 3000 samples of the signal (1500 on either side of the red line) at a time, which is three seconds at a sampling rate of 1000. If you want to change this, change the value of `window_samples` in `display_frames`, but note that you are dealing with a classic spatial v.s. temporal resolution problem as you alter the display. 

## Weird Things (And Easy Things to Fix!) 

 1. Right now I hardcoded the title of the plot to be the name of the video I was working with to debug, but you should make it so that it rips it from the video filename and updates automatically. 
 2. (Warning: not as easy to fix) Something fishy is going on where the EMG plot is piecewise at some points in the signal. 
 3. (Warning: not really attended to yet) Add the audio from the video as a data stream that can be plotted. Will have to consider more weird synchronization stuff for this. 
 4. Change the event handling so that when you click on a point to label, it also tracks which subplot you clicked on and saves it to the CSV.

