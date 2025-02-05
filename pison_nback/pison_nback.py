from psychopy import visual, core, event, gui
from psychopy.hardware import keyboard
import csv
import os
import glob
import random
import datetime

# ========================================
# 1) DEFINE TEST PLANS FOR Levels 1-6
# ========================================
# Each test plan is defined by a dictionary. (Currently they are all identical,
# but you can modify the values for different test plans as needed.)
Levels = {
    1: {
        'target_ratio': 0.50,        # All tests will have a 50% target ratio
        'min_ISI': 2.0,              # Minimum ISI in seconds
        'max_ISI': 3.0,              # Maximum ISI in seconds
        'min_stimDuration': 0.15,    # Minimum stimulus duration in seconds
        'max_stimDuration': 0.25     # Maximum stimulus duration in seconds
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
    Generates a SINGLE continuous color sequence + target list for the entire test,
    ensuring that the specified target_ratio of scorable trials are targets.
    """
    total_trials = sum(s['trials'] for s in stages)

    color_sequence = []
    is_target_list = []

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

    if scorable_portion > 0 and min_targets > 0:
        chunk_flags = [True]*min_targets + [False]*(scorable_portion - min_targets)
        random.shuffle(chunk_flags)
    else:
        chunk_flags = [False]*scorable_portion

    block_scorable_flags = [False]*n_back + chunk_flags
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
    Analyzes the last session's CSV to see if the participant met the criteria.
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

    accuracy = (total_correct / total_trials)*100 if total_trials > 0 else 0.0
    return {
        'completed_all_trials': completed_all_trials,
        'accuracy': accuracy,
        'last_ISI': last_ISI,
        'last_nback': last_nback
    }

# ========================================
# 4) RUN CONTINUOUS ADAPTIVE N-BACK
#    Immediate hits, 80ms-late lapse feedback,
#    box color PERSISTS.
# ========================================
def run_continuous_nback(win, n_back, filename, participant_id,
                         test_plan, initial_ISI, initial_stimDuration, debug_enabled=False):
    """
    1) Generate 70 trials (14 bars x 5 trials each).
    2) Show color rectangles, check for target matches.
       - If user presses SPACE, color the box (green if correct, red if false alarm) IMMEDIATELY.
       - If user never presses SPACE and it's a target => fill red box & pause for 80ms so user sees it, but the box remains red.
    3) 2 total errors => raise ISI/stim, 3 hits => lower ISI/stim, then reset boxes.
    4) 14-bar progress bar, 5 feedback boxes at y=0.50 that persist until adaptation reset.
    """

    # Single stage => 70 trials
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

    total_trials = len(color_seq)  # 70
    total_time = 90.0
    global_clock = core.Clock()
    global_clock.reset()

    current_ISI = initial_ISI
    current_stimDuration = initial_stimDuration

    min_ISI = test_plan['min_ISI']
    max_ISI = test_plan['max_ISI']
    # Adaptation steps changed from 0.5 to 0.2 seconds:
    isi_step = 0.2

    min_stimDuration = test_plan['min_stimDuration']
    max_stimDuration = test_plan['max_stimDuration']
    # Adaptation step for stim duration changed from 0.05 to 0.2 seconds:
    stim_step = 0.02

    # Performance counters
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

    total_fb_width = feedback_box_count * fb_box_width + (feedback_box_count - 1)*fb_box_spacing
    start_fb_x = -(total_fb_width / 2.0) + (fb_box_width / 2.0)

    feedback_boxes = []
    for i in range(feedback_box_count):
        x_fb_pos = start_fb_x + i*(fb_box_width + fb_box_spacing)
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

    # Helper function to draw everything
    def draw_scene(stimulus=None):
        bg_image.draw()
        if stimulus is not None:
            stimulus.draw()
        if debug_enabled:
            debug_text.draw()
        timer_text.draw()

        # bounding frame + progress bars
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

        # feedback boxes
        for fb_box in feedback_boxes:
            fb_box.draw()

    # for CSV
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

            # Info for this trial
            color_this = color_seq[trial_idx]
            is_target = is_target_seq[trial_idx]
            stim_dur = current_stimDuration
            has_responded = False
            trial_correct = False
            trial_rt = None  # store RT

            total_trials_counted += 1

            # Debug text
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

                # Check keys for immediate feedback
                keys = kb.getKeys(['space', 'escape'], waitRelease=False)
                for k in keys:
                    if k.name == 'space' and not has_responded:
                        has_responded = True
                        trial_rt = k.rt
                        # Evaluate correctness
                        if is_target:
                            # Hit => green
                            trial_correct = True
                            match_count += 1
                            if feedback_event_index < 5:
                                feedback_boxes[feedback_event_index].fillColor = 'green'
                                feedback_event_index += 1
                        else:
                            # False alarm => red
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
                    break  # exit the stimulus loop once a response is made

            # ===== ISI Phase =====
            # In this modified version, the ISI loop always runs for the full duration,
            # regardless of whether a response has already been made.
            isi_clock = core.Clock()
            kb.clock.reset()
            while isi_clock.getTime() < current_ISI:
                draw_scene(stimulus=None)
                win.flip()

                # Check keys for immediate feedback during ISI (if needed)
                keys = kb.getKeys(['space', 'escape'], waitRelease=False)
                for k in keys:
                    if k.name == 'space' and not has_responded:
                        has_responded = True
                        trial_rt = stim_dur + k.rt
                        # Evaluate correctness
                        if is_target:
                            # Hit => green
                            trial_correct = True
                            match_count += 1
                            if feedback_event_index < 5:
                                feedback_boxes[feedback_event_index].fillColor = 'green'
                                feedback_event_index += 1
                        else:
                            # False alarm => red
                            trial_correct = False
                            false_alarm_count += 1
                            if feedback_event_index < 5:
                                feedback_boxes[feedback_event_index].fillColor = 'red'
                                feedback_event_index += 1
                    elif k.name == 'escape':
                        print("ESC pressed -> quitting.")
                        win.close()
                        core.quit()
                # Note: No break condition here so that the ISI lasts the full duration.

            # If the user never responded but it's a target => lapse
            if not has_responded and is_target:
                # Color red 80ms "before next stimulus" and keep it
                lapse_count += 1
                # Fill the next feedback box red
                if feedback_event_index < 5:
                    feedback_boxes[feedback_event_index].fillColor = 'red'
                    feedback_event_index += 1

                # Show for 80ms, but do NOT revert color
                lapse_clock = core.Clock()
                while lapse_clock.getTime() < 0.08:
                    draw_scene(stimulus=None)
                    win.flip()

                trial_correct = False
            elif not has_responded and not is_target:
                # Correct rejection
                trial_correct = True

            # Tally correct
            if trial_correct:
                total_correct += 1

            # ==== Adaptive Adjustments after each trial ====
            total_errors = false_alarm_count + lapse_count
            if total_errors >= 2:
                # Raise ISI/stim
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
                # Lower ISI/stim
                new_ISI = max(current_ISI - isi_step, min_ISI)
                new_stimDur = max(current_stimDuration - stim_step, min_stimDuration)
                if new_ISI != current_ISI or new_stimDur != current_stimDuration:
                    current_ISI = new_ISI
                    current_stimDuration = new_stimDur
                    if debug_enabled:
                        print(f"Lowering ISI => {current_ISI:.1f}s / Stim => {current_stimDuration:.2f}s")

                match_count = 0
                feedback_event_index = reset_feedback_boxes()

            # ---- Write CSV row ----
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
    final_accuracy = (total_correct / total_trials_counted)*100.0 if total_trials_counted > 0 else 0.0
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

    final_text = advice
    msg_stim = visual.TextStim(
        win, text=final_text, pos=(0,0), color='white',
        height=0.03, units='norm'
    )
    bg_image.draw()
    msg_stim.draw()
    win.flip()
    core.wait(5)

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
        'Start me where I left off': False,
        'Show Debug': False,
        'Session': '1',
        'Nback': ['1','2','3','4','5'],
        'Level': ['1','2','3','4']  # now selecting a test plan instead of a speed
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
    # If not starting where left off, get the selected test plan from the dialog.
    if not start_where_left_off:
        selected_plan_number = exp_info['Level']
    else:
        # "Start where left off"
        existing_files = glob.glob(os.path.join(participant_dir, f"data_{participant_id}_*.csv"))
        if not existing_files:
            print("No existing data found. Starting at n-back=1 and Levels=1.")
            nback_level = 1
            selected_plan_number = '1'
        else:
            existing_files.sort(key=os.path.getmtime)
            last_file = existing_files[-1]
            print(f"Analyzing last session data: {last_file}")
            performance = analyze_last_session(last_file)
            if performance['completed_all_trials'] and performance['accuracy'] >= 90.0:
                nback_level = min(performance['last_nback'] + 1, 5)
                selected_plan_number = '1'
                print(f"Advancing to n-back level {nback_level} with Levels=1.")
            else:
                nback_level = performance['last_nback']
                # If criteria were not met, retain the previous test plan
                selected_plan_number = exp_info['Level']
                print(f"Retaining n-back level {nback_level} with Levels={selected_plan_number}.")

    # Select the test plan based on the chosen plan number
    selected_plan = Levels[int(selected_plan_number)]
    initial_ISI = selected_plan['max_ISI']
    initial_stimDuration = selected_plan['max_stimDuration']
    # Use the selected plan for the test
    test_plan = selected_plan

    # Create window
    win = visual.Window([800,600], color='black', units='norm')

    # Instructions
    instructions = (
        "Welcome to the Prototype Progressive Focus Test by Pison!\n\n"
        "Instructions:\n"
        f"You will see a series of colored rectangles.\n"
        f"Press SPACE if the current color matches the color from {nback_level} trials ago.\n\n"
        "Understanding the Adaptive Mechanism:\n"
        " - If you make three correct matches the test becomes faster.\n"
        " - If you make two mistakes the test becomes slower.\n"
        " - Your goal is to get to the highest level of a given stage.\n"
        " - To unlock a new stage, complete 70 trials at the highest level with a 90 percent accuracy rate.\n"
        "Press SPACE to begin, or ESC at any time to exit."
    )
    instructions_stim = visual.TextStim(
        win, text=instructions, pos=(0,0), color='white', height=0.04,
        wrapWidth=1.8, alignText='center'
    )
    instructions_stim.draw()
    win.flip()

    # Wait for SPACE or ESC
    while True:
        keys = event.waitKeys(keyList=['space','escape'])
        if 'space' in keys:
            break
        elif 'escape' in keys:
            print("ESC pressed during instructions -> quitting.")
            win.close()
            core.quit()

    # Main loop
    MAX_NBACK = 5
    while nback_level <= MAX_NBACK:
        # Always update the test plan's target ratio to 50% (if needed)
        test_plan['target_ratio'] = 0.50

        # CSV filename: include test plan in the file name
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

        if performance['completed_all_trials'] and performance['accuracy'] >= 90.0:
            if nback_level == MAX_NBACK:
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
                next_nback = nback_level + 1
                # Reset test plan to plan 1 for the next level if desired
                selected_plan_number = '1'
                advice = (
                    "Test Completed!\n\n"
                    f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                    f"You completed n-back {nback_level}. "
                    f"Proceeding to n-back {next_nback} with Levels {selected_plan_number}."
                )
                msg_stim = visual.TextStim(win, text=advice, pos=(0,0),
                                           color='white', height=0.03, units='norm')
                msg_stim.draw()
                win.flip()
                core.wait(5)

                nback_level = next_nback
                # Update test plan for the new level if needed
                selected_plan = Levels[int(selected_plan_number)]
                initial_ISI = selected_plan['max_ISI']
                initial_stimDuration = selected_plan['max_stimDuration']
                test_plan = selected_plan
            # End of if performance successful
        else:
            # Not meeting criteria
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

    win.close()
    core.quit()
