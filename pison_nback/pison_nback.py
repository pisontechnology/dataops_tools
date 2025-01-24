from psychopy import visual, core, event, gui
from psychopy.hardware import keyboard
import csv
import os
import random

# ========================================
# 1) STAGE DEFINITIONS
# ========================================
def get_variable_stages():
    """
    Return a list of dictionaries, each describing one stage (sub-block),
    with parameters for that portion:
        'trials'       : how many trials in that stage
        'minTargets'   : minimum forced targets within that stage
        'minISI','maxISI'
        'stimDuration' : how long to show stimulus
    The sum of all 'trials' will be the total for the experiment.
    """
    return [
        {
            'stage': 1,
            'trials': 4,
            'minTargets': 2,
            'minISI': 1.0,
            'maxISI': 3.0,
            'stimDuration': 0.15
        },
        {
            'stage': 2,
            'trials': 6,
            'minTargets': 3,
            'minISI': 1.0,
            'maxISI': 2.5,
            'stimDuration': 0.15
        },
        {
            'stage': 3,
            'trials': 8,
            'minTargets': 4,
            'minISI': 1.0,
            'maxISI': 2.0,
            'stimDuration': 0.15
        },
        {
            'stage': 4,
            'trials': 12,
            'minTargets': 6,
            'minISI': 1.0,
            'maxISI': 1.5,
            'stimDuration': 0.15
        },
        {
            'stage': 5,
            'trials': 30,
            'minTargets': 15,
            'minISI': 1.0,
            'maxISI': 1.0,
            'stimDuration': 0.15
        },
    ]



# ========================================
# 2) GENERATE ONE CONTINUOUS COLOR SEQUENCE
#    FOR ALL STAGES (no reset).
# ========================================
def generate_full_sequence(n_back, stages, colors):
    """
    Generates a SINGLE continuous color sequence + target list across all stages,
    ensuring each stage has at least 'minTargets' in that block of trials.

    Returns:
      color_sequence: list of length total_trials
      is_target_list: parallel list of booleans
      isi_min_list:   which minISI applies for each trial
      isi_max_list:   which maxISI applies for each trial
      stim_dur_list:  which stimDuration applies for each trial

    Because it's continuous, the last trial of stage i can set up a target
    in the first trial of stage i+1 (carry-over).
    """
    total_trials = sum(s['trials'] for s in stages)

    color_sequence = []
    is_target_list = []
    isi_min_list   = []
    isi_max_list   = []
    stim_dur_list  = []

    # We'll build the big list stage by stage, but never "reset".
    # Each stage's chunk must contain at least 'minTargets' among its
    # "scorable" portion (the portion after the first n_back in that chunk).
    # However, we must also account for carry-over from previous stages.

    for stage_idx, stage_info in enumerate(stages):
        block_trials  = stage_info['trials']
        min_targets   = stage_info['minTargets']
        minISI        = stage_info['minISI']
        maxISI        = stage_info['maxISI']
        stim_duration = stage_info['stimDuration']

        # We'll create a local list of booleans for how many forced targets
        # in the scorable portion of the block. But the block might be partially
        # scorable if there's carry-over from the previous block.
        # We'll do a simple approach: for the chunk of length block_trials,
        # we forcibly place exactly min_targets in positions after the first n_back
        # *within that chunk*, ignoring the global index. Then we build the colors
        # referencing the existing color_sequence if global_idx >= n_back.

        scorable_portion = block_trials - n_back
        if scorable_portion < 0:
            scorable_portion = 0

        if min_targets > scorable_portion:
            raise ValueError(
                f"Stage with {block_trials} trials cannot have {min_targets} forced targets "
                f"when scorable portion is only {scorable_portion} (n_back={n_back})."
            )

        block_scorable_flags = [False]*block_trials
        if scorable_portion > 0 and min_targets > 0:
            chunk_flags = [True]*min_targets + [False]*(scorable_portion - min_targets)
            random.shuffle(chunk_flags)
        else:
            chunk_flags = [False]*scorable_portion

        # Insert: first n_back in the block are forced False, then chunk_flags
        block_scorable_flags = [False]*n_back + chunk_flags
        block_scorable_flags = block_scorable_flags[:block_trials]  # trim if needed

        # Now build out the color portion for this block
        for local_idx in range(block_trials):
            global_idx = len(color_sequence)  # index for the entire run
            want_target = block_scorable_flags[local_idx]

            if global_idx >= n_back:
                # We can reference color_sequence[global_idx - n_back]
                if want_target:
                    new_color = color_sequence[global_idx - n_back]
                    is_targ = True
                else:
                    # pick color different from color_sequence[global_idx - n_back]
                    disallowed = color_sequence[global_idx - n_back]
                    possible = [c for c in colors if c != disallowed]
                    new_color = random.choice(possible)
                    is_targ = (new_color == color_sequence[global_idx - n_back])
            else:
                # Not enough history => random color, no forced target
                new_color = random.choice(colors)
                is_targ = False

            color_sequence.append(new_color)
            is_target_list.append(is_targ)
            isi_min_list.append(minISI)
            isi_max_list.append(maxISI)
            stim_dur_list.append(stim_duration)

    return color_sequence, is_target_list, isi_min_list, isi_max_list, stim_dur_list


# ========================================
# 3) RUN CONTINUOUS N-BACK
#    (One single loop, no stage resets)
# ========================================
def run_continuous_nback(win, n_back, feedback_option, filename, participant_id, debug_enabled=False):
    """
    1. Merges all stages into one single color sequence (with potential carry-over).
    2. Loops through all trials (sum of stage trials), presenting color_sequence[i].
    3. Uses stage i's minISI..maxISI and stimDuration for that trial i.
    4. If the last trial of stage 1 is color X, the first trial of stage 2
       can be a target if n=1 and it matches color X.
    5. 90-second global limit, feedback if requested, final CSV output.
    """
    # 1) Gather stage data
    stage_data = get_variable_stages()  # total ~50 trials
    # 2) Colors
    colors_available = ['orange', 'blue', 'white']

    # 3) Generate one continuous color & target list
    (color_seq,
     is_target_seq,
     isi_min_seq,
     isi_max_seq,
     stim_dur_seq) = generate_full_sequence(
         n_back=n_back,
         stages=stage_data,
         colors=colors_available
     )

    total_trials = len(color_seq)  # e.g. 50
    total_time = 90.0
    global_clock = core.Clock()
    global_clock.reset()

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

    # Tracking
    total_correct = 0
    total_trials_counted = 0

    # Prepare CSV
    with open(filename, 'w', newline='') as data_file:
        writer = csv.writer(data_file)
        writer.writerow([
            'TrialIndex', 'N-back',
            'Color', 'IsTarget',
            'Response', 'Correct', 'RT',
            'minISI', 'maxISI', 'StimDuration'
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
            minISI     = isi_min_seq[trial_idx]
            maxISI     = isi_max_seq[trial_idx]
            stim_dur   = stim_dur_seq[trial_idx]

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
                    f"Stim Dur: {stim_dur:.2f}s\n"
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

            # ---- Present Stimulus for 'stim_dur' seconds ----
            stim_clock = core.Clock()
            kb.clock.reset()
            while stim_clock.getTime() < stim_dur:
                bg_image.draw()
                stim.draw()
                if debug_enabled:
                    debug_text.draw()
                timer_text.draw()
                win.flip()

                # Check keys
                keys = kb.getKeys(['space','escape'], waitRelease=False)
                for k in keys:
                    if k.name == 'space':
                        response = 'space'
                        rt = k.rt
                        response_made = True
                    elif k.name == 'escape':
                        print("ESC pressed -> quitting.")
                        win.close()
                        core.quit()
                if response_made:
                    break

            # ---- ISI random in [minISI..maxISI] ----
            this_isi = random.uniform(minISI, maxISI)
            isi_clock = core.Clock()
            kb.clock.reset()
            while isi_clock.getTime() < this_isi:
                if not response_made:
                    # user can still respond
                    if global_clock.getTime() >= total_time:
                        break

                    elapsed_time = global_clock.getTime()
                    remaining = max(0, total_time - elapsed_time)
                    mm = int(remaining)//60
                    ss = int(remaining)%60
                    timer_text.setText(f"Time Remaining: {mm}:{ss:02d}")

                    bg_image.draw()
                    if debug_enabled:
                        debug_text.draw()
                    timer_text.draw()
                    win.flip()

                    keys = kb.getKeys(['space','escape'], waitRelease=False)
                    for k in keys:
                        if k.name == 'space':
                            response = 'space'
                            rt = stim_dur + k.rt
                            response_made = True
                        elif k.name == 'escape':
                            print("ESC pressed -> quitting.")
                            win.close()
                            core.quit()
                else:
                    if global_clock.getTime() >= total_time:
                        break
                    bg_image.draw()
                    if debug_enabled:
                        debug_text.draw()
                    timer_text.draw()
                    win.flip()

                    leftover = this_isi - isi_clock.getTime()
                    if leftover > 0:
                        core.wait(leftover)
                    break

                if global_clock.getTime() >= total_time:
                    break

            # ---- Scoring ----
            if is_target and response == 'space':
                correct = True
            elif is_target and response is None:
                correct = False
            elif (not is_target) and response == 'space':
                correct = False
            else:
                correct = True  # no target, no response

            if correct:
                total_correct += 1

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
                    feedback_color = "green"
                elif not correct:
                    show_feedback = True
                    feedback_symbol = "X"
                    feedback_color = "red"

            if show_feedback:
                feedback_stim = visual.TextStim(
                    win, text=feedback_symbol, pos=(0, 0.2),
                    color=feedback_color, height=0.2, bold=True
                )
                fb_clock = core.Clock()
                while fb_clock.getTime() < 0.5:
                    bg_image.draw()
                    if debug_enabled:
                        debug_text.draw()
                    timer_text.draw()
                    feedback_stim.draw()
                    win.flip()

            # ---- Write CSV ----
            writer.writerow([
                trial_idx + 1,  # 1-based
                n_back,
                color_this,
                is_target,
                response,
                correct,
                rt,
                minISI,
                maxISI,
                stim_dur
            ])
            data_file.flush()

        # ---- End of All Trials or Time ----
        if total_trials_counted > 0:
            final_accuracy = (total_correct / total_trials_counted)*100.0
        else:
            final_accuracy = 0.0

        # Advice
        if final_accuracy < 75.0:
            if n_back == 1:
                advice = "Your accuracy is below 75%. Repeat level 1."
            else:
                advice = (f"Your accuracy is below 75%. "
                          f"Consider moving DOWN to {n_back-1}-back.")
        elif final_accuracy < 90.0:
            advice = (f"Your accuracy is {final_accuracy:.1f}%. "
                      f"Repeat {n_back}-back.")
        else:
            advice = (f"Your accuracy is {final_accuracy:.1f}%. "
                      f"Consider moving UP to {n_back+1}-back.")

        final_text = (f"Test Completed!\n\n"
                      f"Overall Accuracy: {final_accuracy:.1f}%\n\n"
                      f"{advice}")

        msg_stim = visual.TextStim(
            win, text=final_text, pos=(0,0),
            color='white', height=0.03, units='norm'
        )
        bg_image.draw()
        msg_stim.draw()
        win.flip()
        core.wait(5)


# ========================================
# 4) MAIN SCRIPT
# ========================================
if __name__ == '__main__':
    exp_info = {
        'Participant ID': '',
        'Show Debug': True,
        'Nback': ['1','2','3','4'],
        'Feedback': ['No feedback', 'Error feedback', 'All Feedback'],
        'Session': '1'
    }
    dlg = gui.DlgFromDict(exp_info, title="N-back Task")
    if not dlg.OK:
        core.quit()

    participant_id = exp_info['Participant ID'].strip()
    session_id = exp_info['Session'].strip()
    if not participant_id:
        print("Participant ID is required.")
        core.quit()

    debug_enabled = bool(exp_info['Show Debug'])
    feedback_option = exp_info['Feedback']
    try:
        nback_level = int(exp_info['Nback'])
    except ValueError:
        print("Error: Nback must be an integer.")
        core.quit()

    # Create data directory if needed
    data_dir = "./data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Construct filename with participant ID + session ID
    filename = os.path.join(data_dir, f"data_{participant_id}_{session_id}.csv")

    # If the file already exists, we'll just warn (or do nothing):
    if os.path.exists(filename):
        print(f"WARNING: File {filename} already exists. We will overwrite it!")
        # or you could do something else, like rename:
        # new_name = filename.replace(".csv", "_backup.csv")
        # os.rename(filename, new_name)

    # Create a PsychoPy Window
    win = visual.Window([800,600], color='black', units='norm')

    # Run your continuous n-back (make sure you have imported or defined run_continuous_nback)
    run_continuous_nback(
        win=win,
        n_back=nback_level,
        feedback_option=feedback_option,
        filename=filename,
        participant_id=participant_id,
        debug_enabled=debug_enabled
    )

    # Cleanup
    win.close()
    core.quit()
