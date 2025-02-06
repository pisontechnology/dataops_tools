from psychopy import visual, core, event, gui
from psychopy.hardware import keyboard
import csv
import os
import glob
import random
import datetime
import re  # For regex filename parsing

# ========================================
# 1) DEFINE TEST PLANS (Levels 1-4)
# ========================================
# Each test plan is defined by a dictionary.
Levels = {
    1: {
        'target_ratio': 0.50,        # 50% target ratio
        'min_ISI': 2.0,              # Minimum ISI in seconds
        'max_ISI': 3.0,              # Maximum ISI in seconds
        'min_stimDuration': 0.15,    # Minimum stimulus duration (s)
        'max_stimDuration': 0.25     # Maximum stimulus duration (s)
    },
    2: {
        'target_ratio': 0.50,
        'min_ISI': 1.5,
        'max_ISI': 2.5,
        'min_stimDuration': 0.10,
        'max_stimDuration': 0.20
    },
    3: {
        'target_ratio': 0.50,
        'min_ISI': 1.0,
        'max_ISI': 2.0,
        'min_stimDuration': 0.15,
        'max_stimDuration': 0.10
    },
    4: {
        'target_ratio': 0.50,
        'min_ISI': 1.0,
        'max_ISI': 1.5,
        'min_stimDuration': 0.10,
        'max_stimDuration': 0.10
    }
}

# ========================================
# 2) GENERATE ONE CONTINUOUS COLOR SEQUENCE
# ========================================
def generate_full_sequence(n_back, stages, colors, target_ratio):
    """
    Generates a SINGLE continuous color sequence and corresponding target list for the test,
    ensuring that the specified target_ratio of scorable trials are targets.
    """
    total_trials = sum(s['trials'] for s in stages)
    color_sequence = []
    is_target_list = []

    stage_info = stages[0]
    block_trials = stage_info['trials']
    target_ratio_stage = stage_info['target_ratio']
    scorable_portion = max(block_trials - n_back, 0)

    min_targets = int(target_ratio_stage * scorable_portion)
    if min_targets > scorable_portion:
        raise ValueError(
            f"Cannot have {min_targets} targets with only {scorable_portion} scorable trials (n_back={n_back})."
        )

    if scorable_portion > 0 and min_targets > 0:
        chunk_flags = [True] * min_targets + [False] * (scorable_portion - min_targets)
        random.shuffle(chunk_flags)
    else:
        chunk_flags = [False] * scorable_portion

    block_scorable_flags = [False] * n_back + chunk_flags
    block_scorable_flags = block_scorable_flags[:block_trials]

    for local_idx in range(block_trials):
        global_idx = len(color_sequence)
        want_target = block_scorable_flags[local_idx]

        if global_idx >= n_back:
            if want_target:
                new_color = color_sequence[global_idx - n_back]
                is_targ = True
            else:
                disallowed = color_sequence[global_idx - n_back]
                possible = [c for c in colors if c != disallowed]
                new_color = random.choice(possible)
                is_targ = False
        else:
            new_color = random.choice(colors)
            is_targ = False

        color_sequence.append(new_color)
        is_target_list.append(is_targ)

    return color_sequence, is_target_list

# ========================================
# 3) ANALYZE LAST SESSION DATA
# ========================================
def analyze_last_session(file_path):
    """
    Analyzes the last session's CSV to determine if the participant met the criteria.
    Returns a dictionary containing:
      - completed_all_trials (Boolean)
      - overall accuracy (in percent)
      - last_ISI (the final ISI value)
      - last_nback (the n-back level used)
    """
    completed_all_trials = False
    total_correct = 0
    total_trials = 0
    last_ISI = 3.0
    last_nback = 1

    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Completed_All_Trials', 'False') == 'True':
                completed_all_trials = True
            if row.get('Correct', 'False') == 'True':
                total_correct += 1
            total_trials += 1
            try:
                last_ISI = float(row.get('ISI', 3.0))
            except ValueError:
                last_ISI = 3.0
            try:
                last_nback = int(row.get('N-back', 1))
            except ValueError:
                last_nback = 1

    accuracy = (total_correct / total_trials) * 100 if total_trials > 0 else 0.0
    return {
        'completed_all_trials': completed_all_trials,
        'accuracy': accuracy,
        'last_ISI': last_ISI,
        'last_nback': last_nback
    }

# ========================================
# 4) RUN CONTINUOUS ADAPTIVE N-BACK
#    Immediate hit feedback, 80ms late lapse feedback;
#    adaptive adjustments on errors/hits.
# ========================================
def run_continuous_nback(win, n_back, filename, participant_id,
                         test_plan, initial_ISI, initial_stimDuration, debug_enabled=False):
    """
    Runs 70 trials of the n-back task.
      - Immediate responses turn the stimulus green (correct) or red (false alarm).
      - If no response is made on a target, the stimulus is shown in red for 80ms.
      - The task adapts: two errors slow the test (increase ISI/stim duration);
        three hits speed it up (decrease ISI/stim duration).
    Returns performance details (including the final ISI) in a dictionary.
    """
    # Single stage: 70 trials.
    stages = [
        {
            'trials': 70,
            'target_ratio': test_plan['target_ratio'],
            'stimDuration': test_plan['max_stimDuration']
        },
    ]

    colors_available = ['orange', 'blue', 'white']

    color_seq, is_target_seq = generate_full_sequence(
        n_back=n_back,
        stages=stages,
        colors=colors_available,
        target_ratio=test_plan['target_ratio']
    )

    total_trials = len(color_seq)
    total_time = 90.0
    global_clock = core.Clock()
    global_clock.reset()

    current_ISI = initial_ISI
    current_stimDuration = initial_stimDuration

    min_ISI = test_plan['min_ISI']
    max_ISI = test_plan['max_ISI']
    isi_step = 0.25

    min_stimDuration = test_plan['min_stimDuration']
    max_stimDuration = test_plan['max_stimDuration']
    stim_step = 0.025

    # Performance counters.
    false_alarm_count = 0
    lapse_count = 0
    match_count = 0
    total_correct = 0
    total_trials_counted = 0

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

    # =========== TRIAL PROGRESS BAR ===========
    num_bars = 14
    bar_width = 0.03
    bar_height = 0.05
    bar_spacing = 0.0
    bar_y = 0.1

    total_width = num_bars * bar_width
    start_x = -(total_width / 2.0) + (bar_width / 2.0)

    progress_bars = []
    for i in range(num_bars):
        x_pos = start_x + i * (bar_width + bar_spacing)
        rect = visual.Rect(
            win,
            width=bar_width,
            height=bar_height,
            pos=(x_pos, bar_y),
            fillColor='black',
            lineColor='black'
        )
        progress_bars.append(rect)

    padding_x = 0.005
    padding_y = 0.005
    frame_width = total_width + padding_x
    frame_height = bar_height + padding_y
    progress_frame = visual.Rect(
        win,
        width=frame_width,
        height=frame_height,
        pos=(0, bar_y),
        fillColor='black',
        lineColor='white',
        lineWidth=2
    )

    # =========== FEEDBACK BOXES ===========
    feedback_box_count = 5
    fb_box_width = 0.04
    fb_box_height = 0.04
    fb_box_spacing = 0.01
    fb_box_y = 0.50

    total_fb_width = feedback_box_count * fb_box_width + (feedback_box_count - 1) * fb_box_spacing
    start_fb_x = -(total_fb_width / 2.0) + (fb_box_width / 2.0)

    feedback_boxes = []
    for i in range(feedback_box_count):
        x_fb_pos = start_fb_x + i * (fb_box_width + fb_box_spacing)
        box = visual.Rect(
            win,
            width=fb_box_width,
            height=fb_box_height,
            pos=(x_fb_pos, fb_box_y),
            fillColor='black',
            lineColor='white',
            lineWidth=2
        )
        feedback_boxes.append(box)

    feedback_event_index = 0

    def reset_feedback_boxes():
        for b in feedback_boxes:
            b.fillColor = 'black'
        return 0

    # Helper function to draw the scene.
    def draw_scene(stimulus=None):
        bg_image.draw()
        if stimulus is not None:
            stimulus.draw()
        if debug_enabled:
            debug_text.draw()
        timer_text.draw()

        # Draw progress bars and frame.
        progress_frame.draw()
        completed_bars = trial_idx // 5
        for idx_bar, bar in enumerate(progress_bars):
            if idx_bar < completed_bars:
                bar.fillColor = 'white'
                bar.lineColor = 'white'
            else:
                bar.fillColor = 'black'
                bar.lineColor = 'black'
            bar.draw()

        # Draw feedback boxes.
        for fb_box in feedback_boxes:
            fb_box.draw()

    # Open CSV file for writing trial data.
    with open(filename, 'w', newline='') as data_file:
        writer = csv.writer(data_file)
        writer.writerow([
            'TrialIndex', 'N-back',
            'Color', 'IsTarget',
            'Response', 'Correct', 'RT',
            'ISI', 'StimDuration',
            'Initial_ISI', 'Initial_StimDuration',
            'Completed_All_Trials'
        ])

        # ---- Main Trial Loop ----
        for trial_idx in range(total_trials):
            elapsed_time = global_clock.getTime()
            if elapsed_time >= total_time:
                print("Reached 90 seconds. Ending early.")
                break

            # Info for this trial.
            color_this = color_seq[trial_idx]
            is_target = is_target_seq[trial_idx]
            stim_dur = current_stimDuration
            has_responded = False
            trial_correct = False
            trial_rt = None  # store response time

            total_trials_counted += 1

            # Debug text (if enabled).
            remaining = max(0, total_time - elapsed_time)
            mm = int(remaining) // 60
            ss = int(remaining) % 60
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

            # Create stimulus rectangle.
            stim = visual.Rect(
                win, width=0.35, height=0.15,
                pos=(0, 0.65), fillColor=color_this, units='norm'
            )

            # ===== Stimulus Phase =====
            stim_clock = core.Clock()
            kb.clock.reset()
            while stim_clock.getTime() < stim_dur:
                draw_scene(stimulus=stim)
                win.flip()

                # Check keys for immediate feedback.
                keys = kb.getKeys(['space', 'escape'], waitRelease=False)
                for k in keys:
                    if k.name == 'space' and not has_responded:
                        has_responded = True
                        trial_rt = k.rt
                        if is_target:
                            # Hit => green.
                            trial_correct = True
                            match_count += 1
                            if feedback_event_index < 5:
                                feedback_boxes[feedback_event_index].fillColor = 'green'
                                feedback_event_index += 1
                        else:
                            # False alarm => red.
                            trial_correct = False
                            false_alarm_count += 1
                            if feedback_event_index < 5:
                                feedback_boxes[feedback_event_index].fillColor = 'red'
                                feedback_event_index += 1
                    elif k.name == 'escape':
                        print("ESC pressed -> quitting.")
                        win.close()
                        core.quit()

                if has_responded:
                    break

            # ===== ISI Phase =====
            isi_clock = core.Clock()
            kb.clock.reset()
            while isi_clock.getTime() < current_ISI:
                draw_scene(stimulus=None)
                win.flip()

                keys = kb.getKeys(['space', 'escape'], waitRelease=False)
                for k in keys:
                    if k.name == 'space' and not has_responded:
                        has_responded = True
                        trial_rt = stim_dur + k.rt
                        if is_target:
                            trial_correct = True
                            match_count += 1
                            if feedback_event_index < 5:
                                feedback_boxes[feedback_event_index].fillColor = 'green'
                                feedback_event_index += 1
                        else:
                            trial_correct = False
                            false_alarm_count += 1
                            if feedback_event_index < 5:
                                feedback_boxes[feedback_event_index].fillColor = 'red'
                                feedback_event_index += 1
                    elif k.name == 'escape':
                        print("ESC pressed -> quitting.")
                        win.close()
                        core.quit()
                # The ISI always runs for the full duration.

            # If no response on a target => lapse.
            if not has_responded and is_target:
                lapse_count += 1
                if feedback_event_index < 5:
                    feedback_boxes[feedback_event_index].fillColor = 'red'
                    feedback_event_index += 1

                lapse_clock = core.Clock()
                while lapse_clock.getTime() < 0.08:
                    draw_scene(stimulus=None)
                    win.flip()

                trial_correct = False
            elif not has_responded and not is_target:
                trial_correct = True  # Correct rejection.

            if trial_correct:
                total_correct += 1

            # ==== Adaptive Adjustments after each trial ====
            total_errors = false_alarm_count + lapse_count
            if total_errors >= 2:
                new_ISI = min(current_ISI + isi_step, max_ISI)
                new_stimDur = min(current_stimDuration + stim_step, max_stimDuration)
                if new_ISI != current_ISI or new_stimDur != current_stimDuration:
                    current_ISI = new_ISI
                    current_stimDuration = new_stimDur
                    if debug_enabled:
                        print(f"Raising ISI => {current_ISI:.1f}s / Stim => {current_stimDuration:.2f}s")
                false_alarm_count = 0
                lapse_count = 0
                feedback_event_index = reset_feedback_boxes()

            if match_count >= 3:
                new_ISI = max(current_ISI - isi_step, min_ISI)
                new_stimDur = max(current_stimDuration - stim_step, min_stimDuration)
                if new_ISI != current_ISI or new_stimDur != current_stimDuration:
                    current_ISI = new_ISI
                    current_stimDuration = new_stimDur
                    if debug_enabled:
                        print(f"Lowering ISI => {current_ISI:.1f}s / Stim => {current_stimDuration:.2f}s")
                match_count = 0
                feedback_event_index = reset_feedback_boxes()

            # Write CSV row for this trial.
            writer.writerow([
                trial_idx + 1,
                n_back,
                color_this,
                is_target,
                'space' if has_responded else None,
                trial_correct,
                (trial_rt if has_responded else None),
                current_ISI,
                current_stimDuration,
                initial_ISI,
                initial_stimDuration,
                total_trials_counted == total_trials
            ])
            data_file.flush()

    # ---- End of Trials or Timeout ----
    final_accuracy = (total_correct / total_trials_counted) * 100.0 if total_trials_counted > 0 else 0.0
    completed_all_trials = (total_trials_counted >= total_trials)

    if completed_all_trials and final_accuracy >= 90.0:
        advice = (
            "Test Completed!\n\n"
            f"Overall Accuracy: {final_accuracy:.1f}%\n\n"
            "Congratulations! You have successfully completed this level.\n"
            "You will proceed to the next n-back level."
        )
    else:
        trials_completed = total_trials_counted if not completed_all_trials else total_trials
        advice = (
            "Test Incomplete or Insufficient Accuracy.\n\n"
            f"Trials Completed: {trials_completed}/{total_trials}\n"
            f"Overall Accuracy: {final_accuracy:.1f}%\n\n"
            "You did not meet the criteria to proceed.\n"
            "Please repeat this n-back level."
        )

    msg_stim = visual.TextStim(
        win, text=advice, pos=(0, 0), color='white',
        height=0.03, units='norm'
    )
    bg_image.draw()
    msg_stim.draw()
    win.flip()
    core.wait(5)

    return {
        'completed_all_trials': completed_all_trials,
        'accuracy': final_accuracy,
        'last_ISI': current_ISI  # Returned for promotion logic.
    }

# ========================================
# 5) MAIN SCRIPT
# ========================================
if __name__ == '__main__':
    # Participant Intake.
    exp_info = {
        'Participant ID': 'test',
        'Start me where I left off': False,
        'Show Debug': False,
        'Session': '1',
        'Nback': ['1','2','3','4','5'],
        'Level': ['1','2','3','4']  # Test plan selection options.
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

    # Create participant directory if needed.
    participant_dir = os.path.join("data", participant_id)
    if not os.path.exists(participant_dir):
        os.makedirs(participant_dir)

    # Initialize variables for n-back level and test plan.
    if not start_where_left_off:
        # Not resuming: use the first option from the dialog and start at n-back level 1.
        selected_plan_number = exp_info['Level'][0]
        nback_level = 1
    else:
        # "Start me where I left off" branch.
        existing_files = glob.glob(os.path.join(participant_dir, f"data_{participant_id}_*.csv"))
        if not existing_files:
            print("No existing data found. Starting at n-back=1 and Test Plan 1.")
            nback_level = 1
            selected_plan_number = '1'
        else:
            existing_files.sort(key=os.path.getmtime)
            last_file = existing_files[-1]
            print(f"Analyzing last session data: {last_file}")
            performance = analyze_last_session(last_file)
            # Extract previous n-back level and test plan from the filename.
            match = re.search(r'_nback(\d+)_plan(\d+)_', last_file)
            if match:
                last_nback = int(match.group(1))
                last_plan = int(match.group(2))
            else:
                last_nback = 1
                last_plan = 1

            # Decide the starting settings.
            # For test plans 1-3, only accuracy is required; for test plan 4, the full 70 trials are required.
            if last_plan < 4:
                if performance['accuracy'] >= 90.0:
                    if performance['last_ISI'] <= Levels[last_plan]['min_ISI'] + 1e-6:
                        if last_plan < max(Levels.keys()):
                            selected_plan_number = str(last_plan + 1)
                            nback_level = last_nback
                            print(f"Advancing to Test Plan {selected_plan_number} at n-back level {nback_level}.")
                        else:
                            selected_plan_number = '1'
                            nback_level = min(last_nback + 1, 5)
                            print(f"Advancing to n-back level {nback_level} with Test Plan {selected_plan_number}.")
                    else:
                        selected_plan_number = str(last_plan)
                        nback_level = last_nback
                        print(f"Repeating Test Plan {selected_plan_number} at n-back level {nback_level}.")
                else:
                    selected_plan_number = str(last_plan)
                    nback_level = last_nback
                    print(f"Retaining n-back level {nback_level} with Test Plan {selected_plan_number}.")
            else:  # last_plan == 4.
                if performance['completed_all_trials'] and performance['accuracy'] >= 90.0:
                    if performance['last_ISI'] <= Levels[last_plan]['min_ISI'] + 1e-6:
                        if last_plan < max(Levels.keys()):
                            selected_plan_number = str(last_plan + 1)
                            nback_level = last_nback
                            print(f"Advancing to Test Plan {selected_plan_number} at n-back level {nback_level}.")
                        else:
                            selected_plan_number = '1'
                            nback_level = min(last_nback + 1, 5)
                            print(f"Advancing to n-back level {nback_level} with Test Plan {selected_plan_number}.")
                    else:
                        selected_plan_number = str(last_plan)
                        nback_level = last_nback
                        print(f"Repeating Test Plan {selected_plan_number} at n-back level {nback_level}.")
                else:
                    selected_plan_number = str(last_plan)
                    nback_level = last_nback
                    print(f"Retaining n-back level {nback_level} with Test Plan {selected_plan_number}.")

    # Select the test plan based on the chosen plan number.
    selected_plan = Levels[int(selected_plan_number)]
    initial_ISI = selected_plan['max_ISI']
    initial_stimDuration = selected_plan['max_stimDuration']
    test_plan = selected_plan

    # Create window.
    win = visual.Window([800,600], color='black', units='norm')

    # Instructions.
    instructions = (
        "Welcome to the Prototype Progressive Focus Test by Pison!\n\n"
        "Instructions:\n"
        f"You will see a series of colored rectangles.\n"
        f"Press SPACE if the current color matches the color from {nback_level} trials ago.\n\n"
        "Understanding the Adaptive Mechanism:\n"
        " - Three correct matches speed up the test.\n"
        " - Two mistakes slow down the test.\n"
        " - To unlock a new stage in Test Plan 4, complete 70 trials at the fastest level with 90% accuracy.\n"
        "For Test Plans 1-3, promotion is based on accuracy and reaching the fastest ISI.\n"
        "Press SPACE to begin, or ESC at any time to exit."
    )
    instructions_stim = visual.TextStim(
        win, text=instructions, pos=(0,0), color='white', height=0.04,
        wrapWidth=1.8, alignText='center'
    )
    instructions_stim.draw()
    win.flip()

    # Wait for SPACE or ESC.
    while True:
        keys = event.waitKeys(keyList=['space','escape'])
        if 'space' in keys:
            break
        elif 'escape' in keys:
            print("ESC pressed during instructions -> quitting.")
            win.close()
            core.quit()

    # Main session loop.
    MAX_NBACK = 5
    while nback_level <= MAX_NBACK:
        # Always update the target ratio.
        test_plan['target_ratio'] = 0.50

        # Create CSV filename with embedded n-back and test plan info.
        current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = os.path.join(
            participant_dir,
            f"data_{participant_id}_{session_id}_nback{nback_level}_plan{selected_plan_number}_{current_timestamp}.csv"
        )

        performance = run_continuous_nback(
            win=win,
            n_back=nback_level,
            filename=filename,
            participant_id=participant_id,
            test_plan=test_plan,
            initial_ISI=initial_ISI,
            initial_stimDuration=initial_stimDuration,
            debug_enabled=exp_info['Show Debug']
        )

        current_plan = int(selected_plan_number)
        # For test plans 1-3, promotion is based solely on accuracy.
        if current_plan < 4:
            if performance['accuracy'] >= 90.0:
                if performance['last_ISI'] <= Levels[current_plan]['min_ISI'] + 1e-6:
                    if current_plan < max(Levels.keys()):
                        new_plan = current_plan + 1
                        advice = (
                            f"Test Completed!\n\n"
                            f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                            f"Proceeding with Test Plan {new_plan} at n-back level {nback_level}."
                        )
                        selected_plan_number = str(new_plan)
                    else:
                        if nback_level < MAX_NBACK:
                            new_nback = nback_level + 1
                            advice = (
                                f"Test Completed!\n\n"
                                f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                                f"Proceeding to n-back {new_nback} with Test Plan 1."
                            )
                            nback_level = new_nback
                            selected_plan_number = '1'
                        else:
                            advice = (
                                "Congratulations! You have completed all available n-back levels.\n\n"
                                f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                                "Thank you for your participation."
                            )
                            msg_stim = visual.TextStim(win, text=advice, pos=(0,0),
                                                       color='white', height=0.03, units='norm')
                            msg_stim.draw()
                            win.flip()
                            core.wait(5)
                            break
                else:
                    advice = (
                        "Test Completed!\n\n"
                        f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                        f"Please repeat Test Plan {selected_plan_number} at n-back level {nback_level}."
                    )
            else:
                advice = (
                    "Test Incomplete or Accuracy Insufficient.\n\n"
                    f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                    "Please repeat this n-back level."
                )
                msg_stim = visual.TextStim(win, text=advice, pos=(0,0),
                                           color='white', height=0.03, units='norm')
                msg_stim.draw()
                win.flip()
                core.wait(5)
                break
        else:  # current_plan == 4; require 70 trials.
            if performance['completed_all_trials'] and performance['accuracy'] >= 90.0:
                if performance['last_ISI'] <= Levels[current_plan]['min_ISI'] + 1e-6:
                    if current_plan < max(Levels.keys()):
                        new_plan = current_plan + 1
                        advice = (
                            f"Test Completed!\n\n"
                            f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                            f"Proceeding with Test Plan {new_plan} at n-back level {nback_level}."
                        )
                        selected_plan_number = str(new_plan)
                    else:
                        if nback_level < MAX_NBACK:
                            new_nback = nback_level + 1
                            advice = (
                                f"Test Completed!\n\n"
                                f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                                f"Proceeding to n-back {new_nback} with Test Plan 1."
                            )
                            nback_level = new_nback
                            selected_plan_number = '1'
                        else:
                            advice = (
                                "Congratulations! You have completed all available n-back levels.\n\n"
                                f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                                "Thank you for your participation."
                            )
                            msg_stim = visual.TextStim(win, text=advice, pos=(0,0),
                                                       color='white', height=0.03, units='norm')
                            msg_stim.draw()
                            win.flip()
                            core.wait(5)
                            break
                else:
                    advice = (
                        "Test Completed!\n\n"
                        f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                        f"Please repeat Test Plan {selected_plan_number} at n-back level {nback_level}."
                    )
            else:
                advice = (
                    "Test Incomplete or Accuracy Insufficient.\n\n"
                    f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                    "Please repeat this n-back level."
                )
                msg_stim = visual.TextStim(win, text=advice, pos=(0,0),
                                           color='white', height=0.03, units='norm')
                msg_stim.draw()
                win.flip()
                core.wait(5)
                break

        msg_stim = visual.TextStim(win, text=advice, pos=(0,0),
                                   color='white', height=0.03, units='norm')
        msg_stim.draw()
        win.flip()
        core.wait(5)
        
        # Update test plan settings for the next session.
        selected_plan = Levels[int(selected_plan_number)]
        initial_ISI = selected_plan['max_ISI']
        initial_stimDuration = selected_plan['max_stimDuration']
        test_plan = selected_plan

    win.close()
    core.quit()
