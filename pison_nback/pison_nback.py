from psychopy import visual, core, event, gui
from psychopy.hardware import keyboard
import csv
import os
import glob
import random
import datetime

# ========================================
# 1) TEST PLAN DEFINITIONS
# ========================================
# Updated test_plan includes 'min_stimDuration' and 'max_stimDuration' for adaptive stimulus duration
test_plan = {
    'target_ratio': 0.50,        # Placeholder; will be set based on n-back level
    'min_ISI': 1.0,              # Minimum ISI in seconds
    'max_ISI': 3.0,              # Maximum ISI in seconds
    'min_stimDuration': 0.15,    # Minimum stimulus duration in seconds
    'max_stimDuration': 0.30     # Maximum stimulus duration in seconds
}

# Define target ratios for each n-back level
target_ratios = {
    1: 0.60,  # 60%
    2: 0.50,  # 50%
    3: 0.40,  # 40%
    4: 0.30,  # 30%
    5: 0.20   # 20%
}

# Mapping from initial_ISI to Speed
initial_ISI_to_speed = {
    3.0: '1',
    2.5: '2',
    2.0: '3',
    1.5: '4',
    1.0: '5'
}

# Mapping from Speed to initial_ISI
Speeds_to_initial_ISI = {
    '1': 3.0,  
    '2': 2.5,
    '3': 2.0,
    '4': 1.5,
    '5': 1.0  
}

# ========================================
# 2) GENERATE ONE CONTINUOUS COLOR SEQUENCE
#    FOR THE SINGLE STAGE.
# ========================================
def generate_full_sequence(n_back, stages, colors, target_ratio):
    """
    Generates a SINGLE continuous color sequence + target list for the entire test,
    ensuring that the specified target_ratio of scorable trials are targets.

    Returns:
      color_sequence: list of length total_trials
      is_target_list: parallel list of booleans
    """
    total_trials = sum(s['trials'] for s in stages)

    color_sequence = []
    is_target_list = []

    # Only one stage exists
    stage_info = stages[0]
    block_trials = stage_info['trials']
    target_ratio_stage = stage_info['target_ratio']
    scorable_portion = block_trials - n_back
    scorable_portion = max(scorable_portion, 0)

    min_targets = int(target_ratio_stage * scorable_portion)

    if min_targets > scorable_portion:
        raise ValueError(
            f"Cannot have {min_targets} targets with only {scorable_portion} scorable trials (n_back={n_back})."
        )

    # Create target flags
    if scorable_portion > 0 and min_targets > 0:
        chunk_flags = [True]*min_targets + [False]*(scorable_portion - min_targets)
        random.shuffle(chunk_flags)
    else:
        chunk_flags = [False]*scorable_portion

    # Insert: first n_back in the block are forced False, then chunk_flags
    block_scorable_flags = [False]*n_back + chunk_flags
    block_scorable_flags = block_scorable_flags[:block_trials]  # Trim if needed

    # Now build out the color portion for this block
    colors_available = colors  # ['orange', 'blue', 'white']
    for local_idx in range(block_trials):
        global_idx = len(color_sequence)  # index for the entire run
        want_target = block_scorable_flags[local_idx]

        if global_idx >= n_back:
            # Reference color_sequence[global_idx - n_back]
            if want_target:
                new_color = color_sequence[global_idx - n_back]
                is_targ = True
            else:
                # Pick color different from color_sequence[global_idx - n_back]
                disallowed = color_sequence[global_idx - n_back]
                possible = [c for c in colors_available if c != disallowed]
                new_color = random.choice(possible)
                is_targ = False
        else:
            # Not enough history => random color, no forced target
            new_color = random.choice(colors_available)
            is_targ = False

        color_sequence.append(new_color)
        is_target_list.append(is_targ)

    return color_sequence, is_target_list

# ========================================
# 3) ANALYZE LAST SESSION DATA
# ========================================
def analyze_last_session(file_path):
    """
    Analyzes the last session's CSV data to determine if the participant met the criteria.

    Args:
        file_path (str): Path to the last session's CSV file.

    Returns:
        dict: Contains 'completed_all_trials' (bool), 'accuracy' (float), 'last_ISI' (float), and 'last_nback' (int).
    """
    completed_all_trials = False
    total_correct = 0
    total_trials = 0
    last_ISI = 3.0  # Default value
    last_nback = 1   # Default value

    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Completed_All_Trials', 'False') == 'True':
                completed_all_trials = True
            if row.get('Correct', 'False') == 'True':
                total_correct += 1
            total_trials += 1
            # Update last_ISI with the ISI from the current row
            try:
                last_ISI = float(row.get('ISI', 3.0))
            except ValueError:
                last_ISI = 3.0  # Fallback to default if parsing fails
            # Update last_nback with the N-back from the current row
            try:
                last_nback = int(row.get('N-back', 1))
            except ValueError:
                last_nback = 1  # Fallback to default if parsing fails

    accuracy = (total_correct / total_trials) * 100 if total_trials > 0 else 0.0
    return {
        'completed_all_trials': completed_all_trials,
        'accuracy': accuracy,
        'last_ISI': last_ISI,
        'last_nback': last_nback
    }

# ========================================
# 4) RUN CONTINUOUS ADAPTIVE N-BACK
#    (Adaptive ISI and Stimulus Duration based on performance)
# ========================================
def run_continuous_nback(win, n_back, feedback_option, filename, participant_id, test_plan, initial_ISI, initial_stimDuration, debug_enabled=False):
    """
    1. Generates a color sequence for all trials.
    2. Loops through all trials, presenting color_sequence[i].
    3. Adjusts ISI and stimDuration based on participant's performance.
    4. 90-second global limit, feedback if requested, final CSV output.

    Returns:
        dict: Contains 'completed_all_trials' (bool) and 'accuracy' (float).
    """
    # 1) Define the single stage
    stages = [
        {
            'trials': 60,  # Total number of trials
            'target_ratio': test_plan['target_ratio'],
            'stimDuration': test_plan['max_stimDuration']  # Starting with max stimDuration
        },
    ]

    # 2) Colors
    colors_available = ['orange', 'blue', 'white']

    # 3) Generate one continuous color & target list based on target_ratio
    color_seq, is_target_seq = generate_full_sequence(
        n_back=n_back,
        stages=stages,
        colors=colors_available,
        target_ratio=test_plan['target_ratio']
    )

    total_trials = len(color_seq)  # 60
    total_time = 90.0
    global_clock = core.Clock()
    global_clock.reset()

    # Initialize ISI and stimDuration
    current_ISI = initial_ISI  # Start with initial_ISI based on 'Speed'
    current_stimDuration = initial_stimDuration  # Start with initial stimDuration

    min_ISI = test_plan['min_ISI']
    max_ISI = test_plan['max_ISI']
    isi_step = 0.5

    min_stimDuration = test_plan['min_stimDuration']
    max_stimDuration = test_plan['max_stimDuration']
    stim_step = 0.05  # Step size for stimDuration adjustment

    # Performance tracking
    false_alarm_count = 0
    lapse_count = 0  # Track lapses (missed targets)
    match_count = 0
    correct_detections_streak = 0  # For decreasing stimDuration and ISI
    errors_streak = 0  # For increasing stimDuration and ISI

    # Visual elements
    debug_text = visual.TextStim(
        win, text='', pos=(-1.0, -0.85), color='white', height=0.04,
        anchorHoriz='left', anchorVert='bottom', units='norm'
    )
    timer_text = visual.TextStim(
        win, text='', pos=(0, 0.8), color='white', height=0.05, units='norm'
    )
    bg_image = visual.ImageStim(
        win,
        image="./background.png",
        units='norm',
        size=(2, 2)
    )

    kb = keyboard.Keyboard()

    # Define ISI Progress Bar (Original Positions)
    ISI_levels = [3.0, 2.5, 2.0, 1.5, 1.0]  # Reversed order: slowest to fastest
    x_positions_ISI = [-0.1, -0.05, 0.0, 0.05, 0.1]  # Horizontal positions for ISI rectangles
    progress_colors = ['green', 'green', 'yellow', 'orange', 'red']  # Colors for each rectangle
    y_position_ISI = 0.1  # Vertical position for ISI progress bar

    # Create rectangles for ISI progress bar with different colors, initially filled with black
    progress_rects_ISI = [
        visual.Rect(
            win, 
            width=0.05, 
            height=0.05, 
            pos=(x, y_position_ISI), 
            fillColor='black',  # Start with black fill
            lineColor='black'
        ) 
        for x in x_positions_ISI
    ]

    # Assign colors to rectangles (to be used for dynamic updates)
    rect_assigned_colors = progress_colors.copy()

    # Tracking
    total_correct = 0
    total_trials_counted = 0

    # Prepare CSV
    with open(filename, 'w', newline='') as data_file:
        writer = csv.writer(data_file)
        # =========================================
        # Add headers to the CSV file
        # =========================================
        writer.writerow([
            'TrialIndex', 'N-back',
            'Color', 'IsTarget',
            'Response', 'Correct', 'RT',
            'ISI', 'StimDuration',
            'Initial_ISI', 'Initial_StimDuration',  # ADDED (for Speed and StimSpeed)
            'Completed_All_Trials'  # NEW COLUMN TO INDICATE if all trials were completed
        ])

        # ---- Main Trial Loop ----
        for trial_idx in range(total_trials):
            elapsed_time = global_clock.getTime()
            if elapsed_time >= total_time:
                print("Reached 90 seconds. Ending early.")
                break

            # Grab this trial's info
            color_this = color_seq[trial_idx]
            is_target  = is_target_seq[trial_idx]
            stim_dur   = current_stimDuration  # Use adaptive stimDuration

            kb.clearEvents()
            response = None
            rt = None
            response_made = False

            total_trials_counted += 1

            # Debug text
            remaining = max(0, total_time - elapsed_time)
            mm = int(remaining)//60
            ss = int(remaining)%60

            if debug_enabled:
                debug_text.setText(
                    f"Participant: {participant_id}\n"
                    f"Trial: {trial_idx+1}/{total_trials}\n"
                    f"N-back: {n_back}\n"
                    f"Target? {is_target}\n"
                    f"ISI: {current_ISI:.1f}s\n"
                    f"StimDur: {current_stimDuration:.2f}s\n"
                    f"Time Left: {mm}:{ss:02d}"
                )
            else:
                debug_text.setText("")

            timer_text.setText(f"Time Remaining: {mm}:{ss:02d}")

            # Build the stimulus
            stim = visual.Rect(
                win, width=0.35, height=0.15, pos=(0, 0.65),
                fillColor=color_this, units='norm'
            )

            # ---- Update and Draw ISI Progress Bar ----
            for rect, isi, assigned_color in zip(progress_rects_ISI, ISI_levels, rect_assigned_colors):
                if isi >= current_ISI:
                    rect.fillColor = assigned_color  # Change fillColor to assigned color
                else:
                    rect.fillColor = 'black'  # Keep fillColor black
                rect.draw()

            # ---- Present Stimulus for 'stim_dur' seconds ----
            stim_clock = core.Clock()
            kb.clock.reset()
            while stim_clock.getTime() < stim_dur:
                bg_image.draw()
                stim.draw()
                if debug_enabled:
                    debug_text.draw()
                timer_text.draw()

                # Draw ISI Progress Bar
                for rect in progress_rects_ISI:
                    rect.draw()

                win.flip()

                # Check keys
                keys = kb.getKeys(['space','escape'], waitRelease=False)
                for k in keys:
                    if k.name == 'space' and not response_made:
                        response = 'space'
                        rt = k.rt
                        response_made = True
                    elif k.name == 'escape':
                        print("ESC pressed -> quitting.")
                        win.close()
                        core.quit()
                if response_made:
                    break

            # ---- ISI Phase ----
            isi_clock = core.Clock()
            kb.clock.reset()
            while isi_clock.getTime() < current_ISI:
                bg_image.draw()
                if debug_enabled:
                    debug_text.draw()
                timer_text.draw()

                # Draw ISI Progress Bar
                for rect in progress_rects_ISI:
                    rect.draw()

                win.flip()

                # Check keys
                keys = kb.getKeys(['space','escape'], waitRelease=False)
                for k in keys:
                    if k.name == 'space' and not response_made:
                        response = 'space'
                        rt = stim_dur + k.rt
                        response_made = True
                    elif k.name == 'escape':
                        print("ESC pressed -> quitting.")
                        win.close()
                        core.quit()

            # ---- Scoring ----
            if is_target and response == 'space':
                correct = True
                match_count += 1  # Correct detection
                correct_detections_streak += 1
                errors_streak = 0  # Reset errors streak
            elif is_target and response is None:
                correct = False
                lapse_count += 1  # Lapse (missed target)
                correct_detections_streak = 0
                errors_streak += 1
            elif (not is_target) and response == 'space':
                correct = False
                false_alarm_count += 1  # False alarm
                correct_detections_streak = 0
                errors_streak += 1
            else:
                correct = True  # No target, no response
                correct_detections_streak = 0
                errors_streak = 0

            if correct:
                total_correct += 1

            # ---- Adaptive ISI and Stimulus Duration Adjustment ----
            # Increase ISI and stimDuration if 2 cumulative errors (false alarms + lapses)
            if (false_alarm_count + lapse_count) >= 2:
                new_ISI = min(current_ISI + isi_step, max_ISI)
                new_stimDur = min(current_stimDuration + stim_step, max_stimDuration)
                if new_ISI != current_ISI or new_stimDur != current_stimDuration:
                    current_ISI = new_ISI
                    current_stimDuration = new_stimDur
                    if debug_enabled:
                        print(f"ISI increased to {current_ISI:.1f}s and StimDur increased to {current_stimDuration:.2f}s due to errors (False Alarms: {false_alarm_count}, Lapses: {lapse_count}).")
                false_alarm_count = 0  # Reset counters
                lapse_count = 0

            # Decrease ISI and stimDuration if 3 correct detections
            if match_count >= 3:
                new_ISI = max(current_ISI - isi_step, min_ISI)
                new_stimDur = max(current_stimDuration - stim_step, min_stimDuration)
                if new_ISI != current_ISI or new_stimDur != current_stimDuration:
                    current_ISI = new_ISI
                    current_stimDuration = new_stimDur
                    if debug_enabled:
                        print(f"ISI decreased to {current_ISI:.1f}s and StimDur decreased to {current_stimDuration:.2f}s due to correct detections.")
                match_count = 0  # Reset counter

            # ---- Feedback if needed ----
            show_feedback = False
            feedback_symbol = None
            feedback_color = None

            if feedback_option == 'No feedback':
                pass
            elif feedback_option == 'Error feedback':
                if not correct:
                    show_feedback = True
                    feedback_symbol = "X"
                    feedback_color = "red"
            elif feedback_option == 'All Feedback':
                if (correct and is_target and response == 'space'):
                    show_feedback = True
                    feedback_symbol = "✓"
                    feedback_color = "white"  # Changed to white for consistency
                elif not correct:
                    show_feedback = True
                    feedback_symbol = "X"
                    feedback_color = "red"

            if show_feedback:
                feedback_stim = visual.TextStim(
                    win, text=feedback_symbol, pos=(0, 0.3),
                    color=feedback_color, height=0.2, bold=True
                )
                fb_clock = core.Clock()
                while fb_clock.getTime() < 0.1:
                    bg_image.draw()
                    if debug_enabled:
                        debug_text.draw()
                    timer_text.draw()

                    # Draw ISI Progress Bar
                    for rect in progress_rects_ISI:
                        rect.draw()

                    # Draw Feedback
                    feedback_stim.draw()

                    win.flip()

            # ---- Write CSV row ----
            writer.writerow([
                trial_idx + 1,            # 1-based
                n_back,
                color_this,
                is_target,
                response,
                correct,
                rt,
                current_ISI,              # Log the current ISI
                current_stimDuration,     # Log the current stimDuration
                initial_ISI,              # Log the initial_ISI
                initial_stimDuration,     # Log the initial stimDuration
                total_trials_counted == total_trials  # Indicates if all trials were completed
            ])
            data_file.flush()

    # ---- End of All Trials or Time ----
    final_accuracy = (total_correct / total_trials_counted)*100.0 if total_trials_counted > 0 else 0.0
    completed_all_trials = total_trials_counted >= total_trials

    if completed_all_trials and final_accuracy >= 90.0:
        # Participant met both criteria
        advice = ("Test Completed!\n\n"
                  f"Overall Accuracy: {final_accuracy:.1f}%\n\n"
                  "Congratulations! You have successfully completed this level.\n"
                  "You will proceed to the next n-back level.")
    else:
        # Participant did not meet the criteria
        trials_completed = total_trials_counted if not completed_all_trials else total_trials
        advice = ("Test Incomplete or Insufficient Accuracy.\n\n"
                  f"Trials Completed: {trials_completed}/{total_trials}\n"
                  f"Overall Accuracy: {final_accuracy:.1f}%\n\n"
                  "You did not meet the criteria to proceed to the next level.\n"
                  "Please repeat this n-back level.")

    final_text = advice

    # To display the advice, including a background image
    # Make sure 'background.png' exists in the working directory
    msg_stim = visual.TextStim(
        win, text=final_text, pos=(0,0),
        color='white', height=0.03, units='norm'
    )
    bg_image.draw()
    msg_stim.draw()
    win.flip()
    core.wait(5)

    # Return performance metrics
    return {
        'completed_all_trials': completed_all_trials,
        'accuracy': final_accuracy
    }

# ========================================
# 5) MAIN SCRIPT
# ========================================
if __name__ == '__main__':
    # Participant Intake
    exp_info = {
        'Participant ID': 'test',
        'Start me where I left off': False,  # Checkbox
        'Show Debug': False,
        'Feedback': ['All Feedback','No feedback', 'Error feedback'],
        'Session': '1',
        'Nback': ['1','2','3','4','5'],
        'Speed': ['1','2','3','4','5']  # Repurposed to set initial ISI
    }
    dlg = gui.DlgFromDict(exp_info, title="N-back Task")
    if not dlg.OK:
        core.quit()

    participant_id = exp_info['Participant ID'].strip()
    start_where_left_off = exp_info['Start me where I left off']
    session_id = exp_info['Session'].strip()

    if not participant_id:
        print("Participant ID is required.")
        core.quit()

    # Create participant directory
    participant_dir = os.path.join("data", participant_id)
    if not os.path.exists(participant_dir):
        os.makedirs(participant_dir)

    # Initialize variables
    nback_level = 1
    speed_level = '1'
    feedback_option = exp_info['Feedback']
    initial_ISI = Speeds_to_initial_ISI[speed_level]
    initial_stimDuration = test_plan['max_stimDuration']

    if start_where_left_off:
        # Start where the participant left off
        existing_files = glob.glob(os.path.join(participant_dir, f"data_{participant_id}_*.csv"))
        if not existing_files:
            # No existing data, start at n-back=1 and speed=1
            print("No existing data found. Starting at n-back=1 and speed=1.")
            nback_level = 1
            speed_level = '1'
        else:
            # Sort files by modification time to get the latest
            existing_files.sort(key=os.path.getmtime)
            last_file = existing_files[-1]
            print(f"Analyzing last session data: {last_file}")
            performance = analyze_last_session(last_file)

            if performance['completed_all_trials'] and performance['accuracy'] >= 90.0:
                # Advance to next n-back level
                nback_level = min(performance['last_nback'] + 1, 5)  # Assuming 5 is the max n-back level
                speed_level = '1'
                print(f"Advancing to n-back level {nback_level} at speed {speed_level}.")
            else:
                # Retain the current n-back level and set speed based on last_ISI
                nback_level = performance['last_nback']
                speed_level = initial_ISI_to_speed.get(performance['last_ISI'], '1')
                print(f"Retaining n-back level {nback_level} at speed {speed_level} based on last ISI {performance['last_ISI']}.")
    else:
        # Not starting where left off, use intake
        # Get 'Nback' and 'Speed' from intake
        try:
            nback_level = int(exp_info['Nback'])
        except ValueError:
            print("Error: Nback must be an integer.")
            core.quit()

        speed_level = exp_info['Speed']
        if speed_level not in Speeds_to_initial_ISI:
            print(f"Error: Invalid Speed selected: {speed_level}")
            core.quit()

    # If not starting where left off, adjust test_plan accordingly
    if not start_where_left_off:
        # Get 'Feedback' option
        feedback_option = exp_info['Feedback']
        # Get 'Speed' and map to initial_ISI
        initial_ISI = Speeds_to_initial_ISI[speed_level]
    else:
        # When starting where left off, 'feedback_option' is already set based on intake
        feedback_option = exp_info['Feedback']
        # Map speed_level to initial_ISI
        initial_ISI = Speeds_to_initial_ISI.get(speed_level, 3.0)  # Default to 3.0 if not found

    # Initialize stimDuration based on initial_ISI
    # Starting with the maximum stimDuration
    initial_stimDuration = test_plan['max_stimDuration']

    # Update test_plan with target_ratio based on n-back level
    if nback_level not in target_ratios:
        print(f"Error: Unsupported n-back level: {nback_level}")
        core.quit()
    test_plan['target_ratio'] = target_ratios[nback_level]

    # Create a PsychoPy Window
    win = visual.Window([800,600], color='black', units='norm')

    # ---- Instruction Screen ----
    instructions = (
        "Welcome to the Prototype Progressive Focus Test by Pison!\n\n"
        "Instructions:\n"
        f"In this task, you will see a series of colored rectangles.\n"
        f"Your goal is to press the SPACE BAR whenever the current color matches the color that appeared {nback_level} trial(s) ago.\n\n"
        "This test is ADAPTIVE which means it will adjust based on your skill. Do better and the test gets harder. Do worse and the test gets easier.\n\n"
        "Try to respond as accurately and quickly as possible.\n\n"
        "Press the SPACE BAR once you understand the rules to begin.\n"
        "Press the ESCAPE key at any time to exit the test."
    )
    instructions_stim = visual.TextStim(
        win,
        text=instructions,
        pos=(0,0),
        color='white',
        height=0.04,
        wrapWidth=1.8,  # To ensure text wraps within the window
        alignText='center'
    )

    # Draw and display instructions
    instructions_stim.draw()
    win.flip()

    # Wait for participant to press SPACE or ESCAPE
    keys = []
    while True:
        keys = event.waitKeys(keyList=['space','escape'])
        if 'space' in keys:
            break  # Proceed to the test
        elif 'escape' in keys:
            print("ESC pressed during instructions -> quitting.")
            win.close()
            core.quit()

    # ---- Main Progression Loop ----
    # Loop until maximum n-back level is reached or participant fails to meet criteria
    MAX_NBACK = 5

    while nback_level <= MAX_NBACK:
        # Update test_plan with current target_ratio
        test_plan['target_ratio'] = target_ratios[nback_level]

        # Prepare filename
        current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = os.path.join(
            participant_dir, 
            f"data_{participant_id}_{session_id}_nback{nback_level}_speed{speed_level}_{current_timestamp}.csv"
        )

        # Run the test
        performance = run_continuous_nback(
            win=win,
            n_back=nback_level,
            feedback_option=feedback_option,
            filename=filename,
            participant_id=participant_id,
            test_plan=test_plan,
            initial_ISI=initial_ISI,
            initial_stimDuration=initial_stimDuration,
            debug_enabled=exp_info['Show Debug']
        )

        # ---- After Test Completion ----
        # Determine if participant met the criteria to advance
        if performance['completed_all_trials'] and performance['accuracy'] >= 90.0:
            if nback_level == MAX_NBACK:
                # Participant completed the maximum n-back level
                advice = (
                    "Congratulations! You have completed all available n-back levels.\n\n"
                    f"Overall Accuracy: {performance['accuracy']:.1f}%\n\n"
                    "Thank you for your participation."
                )
                # Display final advice
                final_text = advice

                msg_stim = visual.TextStim(
                    win, text=final_text, pos=(0,0),
                    color='white', height=0.03, units='norm'
                )
                bg_image.draw()
                msg_stim.draw()
                win.flip()
                core.wait(5)
                break  # Exit the loop

            else:
                # Advance to next n-back level
                next_nback = nback_level + 1
                next_speed = '1'
                advice = (
                    "Test Completed!\n\n"
                    f"Overall Accuracy: {performance['accuracy']:.1f}%\n\n"
                    f"Congratulations! You have successfully completed n-back level {nback_level}.\n"
                    f"You will proceed to the next n-back level ({next_nback}) at speed {next_speed}."
                )

                # Display advice
                final_text = advice

                msg_stim = visual.TextStim(
                    win, text=final_text, pos=(0,0),
                    color='white', height=0.03, units='norm'
                )
                bg_image.draw()
                msg_stim.draw()
                win.flip()
                core.wait(5)

                # Update nback_level and speed_level
                nback_level = next_nback
                speed_level = '1'  # Reset to lowest speed
                initial_ISI = Speeds_to_initial_ISI[speed_level]
                initial_stimDuration = test_plan['max_stimDuration']
                # Continue the loop to run the next level
        else:
            # Participant did not meet the criteria
            trials_completed = 60 if performance['completed_all_trials'] else total_trials_counted
            advice = (
                "Test Incomplete or Insufficient Accuracy.\n\n"
                f"Trials Completed: {trials_completed}/{stages[0]['trials']}\n"
                f"Overall Accuracy: {performance['accuracy']:.1f}%\n\n"
                "You did not meet the criteria to proceed to the next level.\n"
                "Please repeat this n-back level."
            )

            # Display advice
            final_text = advice

            msg_stim = visual.TextStim(
                win, text=final_text, pos=(0,0),
                color='white', height=0.03, units='norm'
            )
            bg_image.draw()
            msg_stim.draw()
            win.flip()
            core.wait(5)

            # Optionally, allow participant to repeat the level or end the test
            # Here, we'll end the test
            break  # Exit the loop

    # Cleanup
    win.close()
    core.quit()
