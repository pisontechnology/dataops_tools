from psychopy import visual, core, event, gui
from psychopy.hardware import keyboard
import random
import csv
import os
import math

# ---------------------------
# Participant Information
# ---------------------------
exp_info = {
    'Participant ID': '',
    'Show Debug': True  # Checkbox for debug text display
}
dialog = gui.DlgFromDict(dictionary=exp_info, title='N-back Task')
if not dialog.OK:
    core.quit()

participant_id = exp_info['Participant ID'].strip()
if not participant_id:
    print("Participant ID is required.")
    core.quit()

debug_enabled = exp_info['Show Debug']

data_dir = "./data"  # Adjust as needed
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

filename = os.path.join(data_dir, f"data_{participant_id}.csv")
if os.path.exists(filename):
    print(f"File {filename} already exists. Please use a unique Participant ID.")
    core.quit()

# Create the PsychoPy window
win = visual.Window([800, 600], color='black', units='norm')

# === ADD A BACKGROUND IMAGE STIMULUS HERE ===
# Make sure "background.png" is in the same directory, or provide a correct path.
bg_image = visual.ImageStim(
    win,
    image="./background.png",  # Replace with path if not in same folder
    units='norm',
    size=(2, 2)                # (2,2) in norm units typically fills the entire window
)

debug_text = visual.TextStim(
    win, text='', pos=(-1.2, -0.7), color='white', height=0.05,
    anchorHoriz='left', anchorVert='bottom', units='norm'
)
stage_level_text = visual.TextStim(
    win, text='', pos=(0, 0), color='white',
    height=0.05, anchorHoriz='right', anchorVert='bottom',
    units='norm'
)
timer_text = visual.TextStim(
    win, text='', pos=(0, 0.8), color='white', height=0.05,
    units='norm'
)
mistakes_text = visual.TextStim(
    win, text='', pos=(0, 0), color='white', height=0.05, units='norm'
)

kb = keyboard.Keyboard()

colors_available = ['orange', 'blue', 'yellow']  # base set of colors

def generate_stages(total_stages=13):
    stages = {}
    # Initial parameters
    c = 2
    n_back = 1
    stim_duration = 0.25
    min_ISI = 1.0
    max_ISI = 1.0
    min_targets = 5
    trials = 10

    # Adjust initial max_ISI and targets so decrements make sense
    max_ISI = 2.0
    target_stim_duration = 0.1
    target_max_ISI = 1.5

    stim_decrement = 0.05
    isi_decrement = 0.5
    reduce_max_ISI_next = True

    def reached_targets(sd, mi):
        return sd <= target_stim_duration and mi <= target_max_ISI

    stage = 1
    first_stage_defined = False
    while stage <= total_stages:
        stages[stage] = {
            'colors': c,
            'n_back': n_back,
            'stim_duration': round(stim_duration, 2),
            'min_ISI': min_ISI,
            'max_ISI': round(max_ISI, 2),
            'min_targets': min_targets,
            'trials': trials
        }

        # Once stage 1 is defined, next stage should have n_back=2
        if stage == 1 and not first_stage_defined:
            first_stage_defined = True
            # For the next stage (stage=2), we set n_back=2 and increase colors
            n_back = 2
            c = 3
            min_targets = 10
            trials = 20

        stage += 1
        if stage > total_stages:
            break

        # If we reached targets and are increasing difficulty
        if reached_targets(stim_duration, max_ISI):
            stim_duration = 0.25
            max_ISI = 2.0
            c += 1
            n_back += 1
            reduce_max_ISI_next = True
        else:
            # Alternate decrements
            if reduce_max_ISI_next:
                if max_ISI > target_max_ISI:
                    max_ISI = max(max_ISI - isi_decrement, target_max_ISI)
                reduce_max_ISI_next = False
            else:
                if stim_duration > target_stim_duration:
                    stim_duration = max(stim_duration - stim_decrement, target_stim_duration)
                reduce_max_ISI_next = True

    return stages

stages = generate_stages(total_stages=13)
stage_numbers = list(stages.keys())
print(f"Stage order: {stage_numbers}")

response_key = 'space'
quit_key = 'escape'

trial_number_global = 0
global_clock = core.Clock()
total_time = 300
end_time = 300

try:
    with open(filename, 'w', newline='') as data_file:
        data_writer = csv.writer(data_file)
        data_writer.writerow(['Stage', 'Trial', 'N-back', 'Stimulus', 'Response', 'Correct', 'RT'])
        data_file.flush()

        continue_task = True
        prev_n_back = None
        stage_index = 0
        threshold = 75  # Fixed threshold for all stages

        while stage_index < len(stage_numbers):
            if not continue_task:
                break

            stage = stage_numbers[stage_index]
            stage_params = stages[stage]

            # Extract parameters
            n_back = stage_params['n_back']
            num_colors = stage_params['colors']
            stim_duration = stage_params['stim_duration']
            min_ISI = stage_params['min_ISI']
            max_ISI = stage_params['max_ISI']
            min_targets = stage_params['min_targets']
            trials = stage_params['trials']

            # If n_back changed (either forward or backward), show instructions
            if prev_n_back is not None and n_back != prev_n_back:
                instruction_text = visual.TextStim(
                    win,
                    text=f"n-back = {n_back}\n\nPress any key to continue.",
                    pos=(0,0),
                    color='white',
                    height=0.07
                )
                # Draw instruction text on top of background
                bg_image.draw()
                instruction_text.draw()
                win.flip()
                event.waitKeys()

            prev_n_back = n_back

            # Generate trial targets
            trial_targets = [True]*min_targets + [False]*(trials - min_targets)
            random.shuffle(trial_targets)

            print(f"\n=== Starting Stage {stage} ===")
            print(f"Generated {len(trial_targets)} trials with {trial_targets.count(True)} targets.")
            print(f"N-back: {n_back}, Colors: {num_colors}, Stim Duration: {stim_duration}, ISI: {min_ISI}-{max_ISI}")

            # If not enough colors in colors_available
            if num_colors > len(colors_available):
                print(f"Warning: Stage {stage} requires more colors than available.")
                stage_colors = colors_available.copy()
            else:
                stage_colors = random.sample(colors_available, num_colors)

            trial_counter = 0
            correct_responses = 0
            correct_nonresponses = 0
            incorrect = 0
            stimuli_sequence = []
            trial_correctness = []
            ended_early = False

            # Compute allowed mistakes at start of stage
            scored_total_stage = trials - n_back
            if scored_total_stage <= 0:
                allowed_mistakes = 0
            else:
                allowed_mistakes = math.floor(scored_total_stage * (1 - threshold/100))
            if allowed_mistakes < 0:
                allowed_mistakes = 0

            # Run trials for this stage
            while trial_counter < trials and continue_task:
                elapsed_time = global_clock.getTime()
                if elapsed_time >= end_time:
                    continue_task = False
                    print("Total experiment time reached. Ending task.")
                    break

                remaining_time = max(0, total_time - elapsed_time)
                minutes = int(remaining_time)//60
                seconds = int(remaining_time)%60

                # Compute scored_accuracy (for display)
                if trial_counter > n_back:
                    scored_correct = sum(trial_correctness[n_back:]) if len(trial_correctness) > n_back else 0
                    scored_total = trial_counter - n_back
                    if scored_total > 0:
                        scored_accuracy = (scored_correct / scored_total)*100
                    else:
                        scored_accuracy = 100
                else:
                    scored_accuracy = 100

                # We reduced what's displayed in timer_text for brevity
                timer_text.setText(
                    f"Time Remaining: {minutes}:{seconds:02d}\n"
                )

                forced_target = trial_targets[trial_counter]
                trial_counter += 1
                trial_number_global += 1

                current_color = random.choice(stage_colors)
                stimuli_sequence.append(current_color)
                if len(stimuli_sequence) > n_back + 1:
                    stimuli_sequence.pop(0)

                # Determine if target
                if len(stimuli_sequence) > n_back:
                    is_target = (current_color == stimuli_sequence[-(n_back+1)])
                else:
                    is_target = False

                print(f"\nTrial {trial_number_global}: Stage {stage}, N-back {n_back}")
                print(f"Current Color: {current_color}, Is Target: {is_target}")

                stim = visual.Rect(
                    win, width=0.35, height=0.15, pos=(0, 0.65),
                    fillColor=current_color, units='norm'
                )

                kb.clearEvents()
                response = None
                rt = None
                response_made = False

                if debug_enabled:
                    debug_text.setText(
                        f"Stage: {stage}\n"
                        f"Trial: {trial_number_global}\n"
                        f"N-back: {n_back}\n"
                        f"Correct Resp: {correct_responses}\n"
                        f"Correct Nonresp: {correct_nonresponses}\n"
                        f"Incorrect: {incorrect}\n"
                        f"Scored Acc: {scored_accuracy:.2f}%\n"
                        f"Stim Duration: {stim_duration:.2f}s\n"
                        f"ISI: {min_ISI:.2f}-{max_ISI:.2f}s\n"
                        f"Trials: {trial_counter}/{trials}\n"
                        f"Scored Accuracy: {scored_accuracy:.2f}%\n"
                        f"Target Accuracy: {threshold}%"
                    )
                else:
                    debug_text.setText('')

                stim_clock = core.Clock()
                kb.clock.reset()
                mistakes_text.setColor('white')
                mistakes_text.setText(
                    f'Stage: {stage}\n N-back: {n_back} \n Errors allowed: {allowed_mistakes}'
                )

                # -------------
                # Stimulus Loop
                # -------------
                while stim_clock.getTime() < stim_duration and continue_task:
                    # Draw background first
                    bg_image.draw()
                    # Then draw other stimuli
                    stim.draw()
                    mistakes_text.draw()
                    if debug_enabled:
                        debug_text.draw()
                    stage_level_text.draw()
                    timer_text.draw()
                    win.flip()

                    keys = kb.getKeys([response_key, quit_key], waitRelease=False)
                    for key_event in keys:
                        key = key_event.name
                        timestamp = key_event.rt
                        if key == response_key:
                            response = key
                            rt = timestamp
                            response_made = True
                            print(f"Trial {trial_number_global}: Response '{response}' at {rt:.3f}s.")
                        elif key == quit_key:
                            print("Experiment terminated by user.")
                            continue_task = False
                            break
                    if not continue_task or response_made:
                        break

                if not continue_task:
                    break

                # -------------------------------------------------------------
                # REMOVED THE EXTRA flip() HERE that can cause flicker:
                # win.flip()
                # -------------------------------------------------------------

                ISI_trial = random.uniform(min_ISI, max_ISI)

                # ----------------
                # Inter-Stimulus Interval (ISI) + response window
                # ----------------
                if not response_made and continue_task:
                    ISI_clock = core.Clock()
                    kb.clock.reset()
                    while ISI_clock.getTime() < ISI_trial and continue_task:
                        elapsed_time = global_clock.getTime()
                        if elapsed_time >= end_time:
                            continue_task = False
                            print("Total experiment time reached during ISI. Ending task.")
                            break

                        remaining_time = max(0, total_time - elapsed_time)
                        minutes = int(remaining_time)//60
                        seconds = int(remaining_time)%60

                        if trial_counter > n_back:
                            scored_correct = sum(trial_correctness[n_back:]) if len(trial_correctness) > n_back else 0
                            scored_total = trial_counter - n_back
                            if scored_total > 0:
                                scored_accuracy = (scored_correct / scored_total)*100
                            else:
                                scored_accuracy = 100
                        else:
                            scored_accuracy = 100

                        timer_text.setText(
                            f"Time Remaining: {minutes}:{seconds:02d}\n"
                        )

                        if debug_enabled:
                            debug_text.setText(
                                f"Stage: {stage}\n"
                                f"Trial: {trial_number_global}\n"
                                f"N-back: {n_back}\n"
                                f"Correct Resp: {correct_responses}\n"
                                f"Correct Nonresp: {correct_nonresponses}\n"
                                f"Incorrect: {incorrect}\n"
                                f"Scored Acc: {scored_accuracy:.2f}%\n"
                                f"Stim Duration: {stim_duration:.2f}s\n"
                                f"ISI: {min_ISI:.2f}-{max_ISI:.2f}s\n"
                                f"Trials: {trial_counter}/{trials}\n"
                                f"Scored Accuracy: {scored_accuracy:.2f}%\n"
                                f"Target Accuracy: {threshold}%"
                            )

                        # Draw background, then text
                        bg_image.draw()
                        if debug_enabled:
                            debug_text.draw()
                        timer_text.draw()
                        mistakes_text.draw()
                        win.flip()

                        keys = kb.getKeys([response_key, quit_key], waitRelease=False)
                        for key_event in keys:
                            key = key_event.name
                            timestamp = key_event.rt
                            if key == response_key:
                                response = key
                                rt = stim_duration + timestamp
                                response_made = True
                                print(f"Trial {trial_number_global}: Response '{response}' at {rt:.3f}s during ISI.")
                            elif key == quit_key:
                                print("Experiment terminated by user.")
                                continue_task = False
                                break
                        if response_made or not continue_task:
                            break

                if not continue_task:
                    break

                # -------------
                # Scoring
                # -------------
                if is_target and response == response_key:
                    correct = True
                    correct_responses += 1
                    show_feedback = True
                    print(f"Trial {trial_number_global}: Correct response to target.")
                elif is_target and response is None:
                    correct = False
                    incorrect += 1
                    allowed_mistakes -= 1
                    show_feedback = True
                    print(f"Trial {trial_number_global}: Missed target.")
                elif not is_target and response == response_key:
                    correct = False
                    incorrect += 1
                    allowed_mistakes -= 1
                    show_feedback = True
                    print(f"Trial {trial_number_global}: False alarm.")
                elif not is_target and response is None:
                    correct = True
                    correct_nonresponses += 1
                    show_feedback = False
                    print(f"Trial {trial_number_global}: Correct non-response to non-target.")
                else:
                    correct = False
                    incorrect += 1
                    allowed_mistakes -= 1
                    show_feedback = False

                trial_correctness.append(correct)

                # Check if no mistakes left
                if allowed_mistakes <= 0 and not correct:
                    print("No remaining mistakes allowed. Ending stage early.")
                    ended_early = True

                # -------------
                # Feedback (only if show_feedback == True)
                # -------------
                if show_feedback and not ended_early and continue_task:
                    if not correct:
                        mistakes_text.setColor('red')

                    ISI_clock = core.Clock()
                    kb.clock.reset()

                    while ISI_clock.getTime() < ISI_trial and continue_task:
                        elapsed_time = global_clock.getTime()
                        if elapsed_time >= end_time:
                            continue_task = False
                            print("Total experiment time reached during feedback. Ending task.")
                            break

                        remaining_time = max(0, total_time - elapsed_time)
                        minutes = int(remaining_time)//60
                        seconds = int(remaining_time)%60

                        if trial_counter > n_back:
                            scored_correct = sum(trial_correctness[n_back:])
                            scored_total = trial_counter - n_back
                            if scored_total > 0:
                                scored_accuracy = (scored_correct / scored_total)*100
                            else:
                                scored_accuracy = 100
                        else:
                            scored_accuracy = 100

                        timer_text.setText(
                            f"Time Remaining: {minutes}:{seconds:02d}\n"
                        )

                        if debug_enabled:
                            debug_text.setText(
                                f"Stage: {stage}\n"
                                f"Trial: {trial_number_global}\n"
                                f"N-back: {n_back}\n"
                                f"Correct Resp: {correct_responses}\n"
                                f"Correct Nonresp: {correct_nonresponses}\n"
                                f"Incorrect: {incorrect}\n"
                                f"Scored Acc: {scored_accuracy:.2f}%\n"
                                f"Stim Duration: {stim_duration:.2f}s\n"
                                f"ISI: {min_ISI:.2f}-{max_ISI:.2f}s"
                            )

                        mistakes_text.setText(
                            f'Stage: {stage}\n N-back: {n_back} \n Errors allowed: {allowed_mistakes}'
                        )

                        # Draw background and feedback info
                        bg_image.draw()
                        if debug_enabled:
                            debug_text.draw()
                        stage_level_text.draw()
                        timer_text.draw()
                        mistakes_text.draw()
                        win.flip()

                        keys = kb.getKeys([quit_key], waitRelease=False)
                        if quit_key in [k.name for k in keys]:
                            print("Experiment terminated by user during feedback.")
                            continue_task = False
                            break

                data_writer.writerow([stage, trial_number_global, n_back, current_color, response, correct, rt])
                data_file.flush()
                print(f"Trial {trial_number_global}: Data recorded.")

                if ended_early or allowed_mistakes <= 0:
                    break

            if not continue_task:
                break

            # -------------
            # End of Stage: Compute scored_accuracy
            # -------------
            if ended_early or allowed_mistakes <= 0:
                scored_correct = sum(trial_correctness[n_back:]) if len(trial_correctness) > n_back else 0
                scored_total = (len(trial_correctness)-n_back) if len(trial_correctness) > n_back else 0
                if scored_total > 0:
                    scored_accuracy = (scored_correct / scored_total)*100
                else:
                    scored_accuracy = 100
            else:
                total_trials = len(trial_correctness)
                if total_trials > n_back:
                    scored_correct = sum(trial_correctness[n_back:])
                    scored_total = total_trials - n_back
                    if scored_total > 0:
                        scored_accuracy = (scored_correct / scored_total)*100
                    else:
                        scored_accuracy = 100
                else:
                    scored_accuracy = 100

            print(f"\nStage {stage} completed.")
            print(f"Scored Accuracy (excluding first {n_back} trials): {scored_accuracy:.2f}%")

            # Display achieved accuracy on top of background
            accuracy_color = 'green' if scored_accuracy >= threshold else 'red'
            accuracy_text = visual.TextStim(
                win,
                text=f"Achieved Accuracy: {scored_accuracy:.2f}%",
                pos=(0,0),
                height=0.05,
                color=accuracy_color,
                alignText='center'
            )
            bg_image.draw()
            accuracy_text.draw()
            win.flip()
            core.wait(2)

            # Advance or regress stage
            if scored_accuracy >= threshold and not ended_early and allowed_mistakes > 0:
                if stage_index < len(stage_numbers)-1:
                    stage_index += 1
                else:
                    continue_task = False
            else:
                if stage_index > 0:
                    stage_index -= 1
                else:
                    # remain in the same stage if we're already at stage 0
                    pass

        # -------------
        # Final Message
        # -------------
        final_message = visual.TextStim(
            win,
            text='Test Completed!',
            pos=(0, 0),
            color='white',
            height=0.1,
            units='norm'
        )
        bg_image.draw()
        final_message.draw()
        win.flip()
        core.wait(5)

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if 'data_file' in locals() and not data_file.closed:
        data_file.close()
    win.close()
    core.quit()
