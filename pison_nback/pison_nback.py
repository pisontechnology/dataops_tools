#!/usr/bin/env python
# -*- coding: utf-8 -*-

from psychopy import visual, core, event, gui
from psychopy.hardware import keyboard
import csv
import os
import glob
import random
import datetime
import re
import math  # For computing standard deviation

# ========================================
# 1) DEFINE TEST PLANS (Levels 1-4)
# ========================================
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
        'min_stimDuration': 0.1,
        'max_stimDuration': 0.2
    },
    3: {
        'target_ratio': 0.50,
        'min_ISI': 1.0,
        'max_ISI': 2.0,
        'min_stimDuration': 0.10,
        'max_stimDuration': 0.15
    },
    4: {
        'target_ratio': 0.50,
        'min_ISI': 1.0,
        'max_ISI': 1.0,
        'min_stimDuration': 0.10,
        'max_stimDuration': 0.10
    }
}

# ========================================
# 2) GENERATE ONE CONTINUOUS COLOR SEQUENCE
# ========================================
def generate_full_sequence(n_back, stages, colors, target_ratio):
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
# 4) RUN CONTINUOUS ADAPTIVE N-BACK (IMMEDIATE FEEDBACK + .1s THRESHOLD DISPLAY)
# ========================================
def run_continuous_nback(win, n_back, filename, participant_id,
                         test_plan, initial_ISI, initial_stimDuration,
                         debug_enabled=False):
    """
    Runs a single stage (e.g., 60 trials) of the n-back test with:
      - 3 consecutive hits => speed up
      - 2 consecutive errors => slow down
    Provides *immediate feedback* on hits or false alarms.
    A miss is only determined after the trial ends.
    Keeps the *entire* ISI duration (doesn't end early).
    When the 3rd green box or 2nd red box is filled, show it for 0.1s before adapting.
    """
    # Single stage: 60 trials
    stages = [
        {
            'trials': 60,
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

    # Step sizes for speeding up / slowing down:
    min_ISI = test_plan['min_ISI']
    max_ISI = test_plan['max_ISI']
    isi_step = 0.25

    min_stimDuration = test_plan['min_stimDuration']
    max_stimDuration = test_plan['max_stimDuration']
    stim_step = 0.025

    # Consecutive counters:
    match_consecutive = 0
    error_consecutive = 0

    # Stats
    total_correct = 0
    total_trials_counted = 0

    overall_rt_list = []
    overall_targets = 0
    overall_hits = 0
    overall_misses = 0
    overall_falseAlarms = 0
    overall_correctRejections = 0

    # Feedback UI
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

    # Setup feedback boxes and separator line
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
        # first 2 boxes on the left -> red, last 3 -> green
        if i < 2:
            outline_color = 'red'
        else:
            outline_color = 'green'
        box = visual.Rect(
            win,
            width=fb_box_width,
            height=fb_box_height,
            pos=(x_fb_pos, fb_box_y),
            fillColor='black',
            lineColor=outline_color,
            lineWidth=2
        )
        feedback_boxes.append(box)

    error_box_right = feedback_boxes[1].pos[0] + fb_box_width / 2.0
    match_box_left = feedback_boxes[2].pos[0] - fb_box_width / 2.0
    x_line = (error_box_right + match_box_left) / 2.0
    margin = 0.05
    separator_line = visual.Line(
        win,
        start=(x_line, fb_box_y - fb_box_height/2 - margin),
        end=(x_line, fb_box_y + fb_box_height/2 + margin),
        lineColor='white',
        lineWidth=2,
        units='norm'
    )

    # We'll track how many boxes are currently filled:
    error_feedback_index = 0
    match_feedback_index = 0

    def reset_error_feedback():
        for i in range(2):
            feedback_boxes[1 - i].fillColor = 'black'
        return 0

    def reset_match_feedback():
        for i in range(3):
            feedback_boxes[2 + i].fillColor = 'black'
        return 0

    def draw_scene(stimulus=None):
        bg_image.draw()
        if stimulus is not None:
            stimulus.draw()
        if debug_enabled:
            debug_text.draw()
        timer_text.draw()
        for fb_box in feedback_boxes:
            fb_box.draw()
        separator_line.draw()

    # ----- THRESHOLD / ADAPTATION LOGIC ------
    def handle_adaptation_if_needed():
        """Checks if match_consecutive == 3 or error_consecutive == 2,
        then displays the final box for 0.1s so user can see they've triggered
        a speed up or slow down, and then performs the adaptation and resets."""
        nonlocal current_ISI, current_stimDuration
        nonlocal match_consecutive, error_consecutive
        nonlocal match_feedback_index, error_feedback_index

        # Speed up on 3 consecutive hits
        if match_consecutive >= 3:
            # CHANGED: show the fully-filled green boxes for 0.1s
            draw_scene()
            win.flip()
            core.wait(0.05)

            # Now do speed up
            new_ISI = max(current_ISI - isi_step, min_ISI)
            new_stimDuration = max(current_stimDuration - stim_step, min_stimDuration)
            if new_ISI != current_ISI or new_stimDuration != current_stimDuration:
                current_ISI = new_ISI
                current_stimDuration = new_stimDuration

            # Reset hits
            match_consecutive = 0
            match_feedback_index = reset_match_feedback()

        # Slow down on 2 consecutive errors
        if error_consecutive >= 2:
            # CHANGED: show the fully-filled red boxes for 0.1s
            draw_scene()
            win.flip()
            core.wait(0.5)

            # Now do slow down
            new_ISI = min(current_ISI + isi_step, max_ISI)
            new_stimDuration = min(current_stimDuration + stim_step, max_stimDuration)
            if new_ISI != current_ISI or new_stimDuration != current_stimDuration:
                current_ISI = new_ISI
                current_stimDuration = new_stimDuration

            # Reset errors
            error_consecutive = 0
            error_feedback_index = reset_error_feedback()

    # ----- IMMEDIATE RESPONSE LOGIC ------
    def handle_immediate_response(t_rt, is_target):
        """
        Called as soon as user presses SPACE. Returns (trial_correct, final_rt).
        Also updates the consecutive counters and UI immediately.
        """
        nonlocal match_consecutive, error_consecutive
        nonlocal match_feedback_index, error_feedback_index
        nonlocal overall_hits, overall_falseAlarms

        trial_is_correct = False
        final_rt = t_rt

        if is_target:
            # This is a HIT
            trial_is_correct = True
            match_consecutive += 1
            error_consecutive = 0

            overall_hits += 1
            # Immediate feedback -> fill next green box
            if match_feedback_index < 3:
                feedback_boxes[2 + match_feedback_index].fillColor = 'green'
                match_feedback_index += 1
            # Reset red UI
            error_feedback_index = reset_error_feedback()

        else:
            # This is a FALSE ALARM
            trial_is_correct = False
            error_consecutive += 1
            match_consecutive = 0

            overall_falseAlarms += 1
            # immediate feedback -> fill next red box
            if error_feedback_index < 2:
                feedback_boxes[1 - error_feedback_index].fillColor = 'red'
                error_feedback_index += 1
            # reset green UI
            match_feedback_index = reset_match_feedback()

        # Now check if we triggered threshold:
        handle_adaptation_if_needed()

        return (trial_is_correct, final_rt)

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

        for trial_idx in range(total_trials):
            # Clear any lingering events and wait 200 ms before starting the trial.
            event.clearEvents()
            core.wait(0.05)

            elapsed_time = global_clock.getTime()
            if elapsed_time >= total_time:
                print("Reached 90 seconds. Ending early.")
                break

            color_this = color_seq[trial_idx]
            is_targ = is_target_seq[trial_idx]
            stim_dur = current_stimDuration
            has_responded = False
            trial_correct = False
            trial_rt = None

            total_trials_counted += 1

            remaining = max(0, total_time - elapsed_time)
            mm = int(remaining) // 60
            ss = int(remaining) % 60
            if debug_enabled:
                debug_text.setText(
                    f"Participant: {participant_id}\n"
                    f"Trial: {trial_idx+1}/{total_trials}\n"
                    f"N-back: {n_back}\n"
                    f"Target? {is_targ}\n"
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

            # -------------------------------------------
            # 1) Stimulus Phase
            # -------------------------------------------
            stim_clock = core.Clock()
            kb = keyboard.Keyboard()
            kb.clock.reset()
            while stim_clock.getTime() < stim_dur:
                draw_scene(stimulus=stim)
                win.flip()

                keys = kb.getKeys(['space', 'escape'], waitRelease=False)
                if keys:
                    for k in keys:
                        if k.name == 'escape':
                            win.close()
                            core.quit()
                        elif k.name == 'space' and not has_responded:
                            has_responded = True
                            trial_rt = k.rt  # time during Stim
                            # Immediate feedback for hit/FA:
                            trial_correct, trial_rt = handle_immediate_response(trial_rt, is_targ)
                            # Show updated UI
                            draw_scene(stimulus=stim)
                            win.flip()
                    if has_responded:
                        # Once responded, no further keys in this Stim phase
                        break

            # -------------------------------------------
            # 2) ISI Phase (CHANGED: do NOT break early)
            # -------------------------------------------
            isi_clock = core.Clock()
            kb.clock.reset()
            while isi_clock.getTime() < current_ISI:
                draw_scene(stimulus=None)
                win.flip()

                # We keep the ISI going for the full duration.
                keys = kb.getKeys(['space', 'escape'], waitRelease=False)
                for k in keys:
                    if k.name == 'escape':
                        win.close()
                        core.quit()
                    elif k.name == 'space' and not has_responded:
                        has_responded = True
                        # RT includes time from Stim + this ISI offset
                        rt_in_isi = k.rt
                        trial_rt = stim_dur + rt_in_isi
                        trial_correct, trial_rt = handle_immediate_response(trial_rt, is_targ)
                        # Show updated UI
                        draw_scene(stimulus=None)
                        win.flip()
                # Note: do NOT break. The ISI runs fully.

            # -------------------------------------------
            # 3) If still no response => Miss or Correct Rejection
            # -------------------------------------------
            if not has_responded:
                if is_targ:
                    # Miss
                    trial_correct = False
                    overall_misses += 1
                    # We'll approximate RT for a miss as stim+ISI
                    trial_rt = stim_dur + current_ISI

                    error_consecutive += 1
                    match_consecutive = 0

                    # Fill the next red box
                    if error_feedback_index < 2:
                        feedback_boxes[1 - error_feedback_index].fillColor = 'red'
                        error_feedback_index += 1

                    match_feedback_index = reset_match_feedback()

                    # Show that box for the miss
                    draw_scene(stimulus=None)
                    win.flip()

                    handle_adaptation_if_needed()

                else:
                    # Correct Rejection
                    trial_correct = True
                    overall_correctRejections += 1
                    # no changes to consecutive counters

            if trial_correct:
                total_correct += 1
            if is_targ:
                overall_targets += 1

            # Record RT (for analysis) even if None
            if trial_rt is None:
                trial_rt = stim_dur + current_ISI
            overall_rt_list.append(trial_rt)

            # -------------------------------------------
            # 4) Write data row
            # -------------------------------------------
            writer.writerow([
                trial_idx + 1,
                n_back,
                color_this,
                is_targ,
                ('space' if has_responded else None),
                trial_correct,
                trial_rt,
                current_ISI,
                current_stimDuration,
                initial_ISI,
                initial_stimDuration,
                total_trials_counted == total_trials
            ])
            data_file.flush()

    # ========================================
    # Compute Final Stats
    # ========================================
    duration = global_clock.getTime()
    if overall_rt_list:
        avg_rt = sum(overall_rt_list) / len(overall_rt_list)
        std_rt = math.sqrt(sum((x - avg_rt)**2 for x in overall_rt_list) / len(overall_rt_list))
    else:
        avg_rt = 0
        std_rt = 0

    hit_rate = (overall_hits / overall_targets * 100) if overall_targets > 0 else 0
    miss_rate = (overall_misses / overall_targets * 100) if overall_targets > 0 else 0
    accuracy_metric = ((overall_hits + overall_correctRejections) / total_trials_counted * 100) if total_trials_counted > 0 else 0
    throughput = total_trials_counted / duration if duration > 0 else 0

    results_text = (
        f"Results:\n\n"
        f"Accuracy: {accuracy_metric:.1f}%\n"
        f"Average RT: {avg_rt:.3f} s\n"
        f"RT Std Dev: {std_rt:.3f} s\n"
        f"Total Misses: {overall_misses}\n"
        f"Total False Alarms: {overall_falseAlarms}\n"
        f"Total Hits: {overall_hits}\n"
        f"Total Targets: {overall_targets}\n"
        f"Hit Rate: {hit_rate:.1f}%\n"
        f"Miss Rate: {miss_rate:.1f}%\n"
        f"Total Trials: {total_trials_counted}\n"
        f"Throughput: {throughput:.2f} trials/s\n\n"
        "Press SPACE to continue."
    )

    results_stim = visual.TextStim(
        win, text=results_text, pos=(0,0.25), color='white', height=0.025, wrapWidth=1.8, alignText='center'
    )
    bg_image.draw()
    results_stim.draw()
    win.flip()
    event.waitKeys(keyList=['space'])

    return {
        'completed_all_trials': total_trials_counted >= total_trials,
        'accuracy': accuracy_metric,
        'avg_rt': avg_rt,
        'std_rt': std_rt,
        'total_misses': overall_misses,
        'total_trials': total_trials_counted,
        'total_falseAlarms': overall_falseAlarms,
        'total_hits': overall_hits,
        'total_targets': overall_targets,
        'hit_rate': hit_rate,
        'miss_rate': miss_rate,
        'throughput': throughput,
        'duration': duration,
        'last_ISI': current_ISI
    }

# ========================================
# 5) MAIN SCRIPT
# ========================================
if __name__ == '__main__':
    exp_info = {
        'Participant ID': 'test',
        'Start me where I left off': False,
        'Show Debug': False,
        'Session': '1',
        'Nback': ['1','2','3','4','5'],
        'Level': ['1','2','3','4'],
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

    participant_dir = os.path.join("data", participant_id)
    if not os.path.exists(participant_dir):
        os.makedirs(participant_dir)

    if not start_where_left_off:
        nback_level = int(exp_info['Nback'])
        selected_plan_number = exp_info['Level'][0]
    else:
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
            match_obj = re.search(r'_nback(\d+)_plan(\d+)_', last_file)
            if match_obj:
                last_nback = int(match_obj.group(1))
                last_plan = int(match_obj.group(2))
            else:
                last_nback = 1
                last_plan = 1

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
            else:
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
                        print(f"Repeating Test Plan {selected_plan_number} at nback level {nback_level}.")
                else:
                    selected_plan_number = str(last_plan)
                    nback_level = last_nback
                    print(f"Retaining n-back level {nback_level} with Test Plan {selected_plan_number}.")

    selected_plan = Levels[int(selected_plan_number)]
    initial_ISI = selected_plan['max_ISI']
    initial_stimDuration = selected_plan['max_stimDuration']
    test_plan = selected_plan

    win = visual.Window([1440,1080], color='black', units='norm')

    instructions = (
        "Welcome to the Prototype Progressive Focus Test!\n\n"
        "Instructions:\n"
        f"Press SPACE if the current color matches the color from {nback_level} trials ago.\n\n"
        "Adaptive Mechanism:\n"
        " - Three *consecutive* hits (correct target presses) speeds up.\n"
        " - Two *consecutive* errors (false alarm or miss) slows down.\n\n"
        "Immediate feedback:\n"
        " - If you press on a target, a green box will appear right away.\n"
        " - If you press on a non-target, a red box appears right away.\n"
        " - If you *miss* a target, the red box appears after the trial.\n\n"
        "When you fill that second red box or third green box, we’ll pause for a moment\n"
        "so you can see the threshold triggered, then we’ll adapt the timing.\n\n"
        "Press SPACE to begin, or ESC any time to exit."
    )
    instructions_stim = visual.TextStim(
        win, text=instructions, pos=(0,0), color='white', height=0.04,
        wrapWidth=1.8, alignText='center'
    )
    instructions_stim.draw()
    win.flip()

    while True:
        keys = event.waitKeys(keyList=['space','escape'])
        if 'space' in keys:
            break
        elif 'escape' in keys:
            print("ESC pressed during instructions -> quitting.")
            win.close()
            core.quit()

    # 5-second Countdown
    for count in range(5, 0, -1):
        countdown_text = visual.TextStim(
            win, text=f"Starting in {count}...", pos=(0,0), color='white', height=0.05
        )
        # Clear, then draw
        win.flip()
        countdown_text.draw()
        win.flip()
        core.wait(1)
    event.clearEvents()
    win.flip()      # Clear any leftover countdown text
    core.wait(0.2)

    MAX_NBACK = 5
    while nback_level <= MAX_NBACK:
        test_plan['target_ratio'] = 0.50
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
                            event.waitKeys(keyList=['space'])
                            break
                else:
                    advice = (
                        "Test Completed!\n\n"
                        f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                        f"Please repeat Test Plan {selected_plan_number} at n-back level {nback_level}."
                    )
            else:
                advice = (
                    "Accuracy Insufficient.\n\n"
                    f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                    "Please repeat this n-back level."
                )
                msg_stim = visual.TextStim(win, text=advice, pos=(0,0),
                                           color='white', height=0.03, units='norm')
                msg_stim.draw()
                win.flip()
                event.waitKeys(keyList=['space'])
                break
        else:
            # If plan == 4
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
                            event.waitKeys(keyList=['space'])
                            break
                else:
                    advice = (
                        "Test Completed!\n\n"
                        f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                        f"Please repeat Test Plan {selected_plan_number} at n-back level {nback_level}."
                    )
            else:
                advice = (
                    "Accuracy Insufficient.\n\n"
                    f"Accuracy: {performance['accuracy']:.1f}%\n\n"
                    "Please repeat this n-back level."
                )
                msg_stim = visual.TextStim(win, text=advice, pos=(0,0),
                                           color='white', height=0.03, units='norm')
                msg_stim.draw()
                win.flip()
                event.waitKeys(keyList=['space'])
                break

        msg_stim = visual.TextStim(win, text=advice, pos=(0,0),
                                   color='white', height=0.03, units='norm')
        msg_stim.draw()
        win.flip()
        event.waitKeys(keyList=['space'])

        selected_plan = Levels[int(selected_plan_number)]
        initial_ISI = selected_plan['max_ISI']
        initial_stimDuration = selected_plan['max_stimDuration']
        test_plan = selected_plan

    win.close()
    core.quit()
