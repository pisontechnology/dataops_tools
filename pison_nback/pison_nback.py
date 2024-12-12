from psychopy import visual, core, event, gui
from psychopy.hardware import keyboard
import random
import csv
import os

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

data_dir = "C:/Users/tue.vu_pison/Desktop/git/NBack/data"
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

filename = os.path.join(data_dir, f"data_{participant_id}.csv")
if os.path.exists(filename):
    print(f"File {filename} already exists. Please use a unique Participant ID.")
    core.quit()

win = visual.Window([800, 600], color='black', units='norm')

# Removed textual feedback text stimulus
# feedback_text = visual.TextStim(win, text='', pos=(0, 0), color='white', height=0.1)

debug_text = visual.TextStim(win, text='', pos=(-0.9, -0.9), color='white', height=0.05,
                             anchorHoriz='left', anchorVert='bottom', units='norm')
stage_level_text = visual.TextStim(win, text='', pos=(0.9, -0.9), color='white',
                                   height=0.05, anchorHoriz='right', anchorVert='bottom',
                                   units='norm')
timer_text = visual.TextStim(win, text='', pos=(0, 0.8), color='white', height=0.075,
                             units='norm')

# ADDED: Polygon for feedback under the stimuli area. Default color = gray
feedback_polygon = visual.Rect(win, width=0.5, height=0.05, fillColor='gray', lineColor='gray', pos=(0, -0.28))

kb = keyboard.Keyboard()

colors = ['orange', 'blue', 'yellow']

stages = {
    1: {'colors': 2, 'n_back': 1, 'stim_duration': 0.25, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 12, 'trials': 24},
    2: {'colors': 3, 'n_back': 2, 'stim_duration': 0.25, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 6, 'trials': 9},
    3: {'colors': 3, 'n_back': 2, 'stim_duration': 0.20, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 6, 'trials': 9},
    4: {'colors': 3, 'n_back': 2, 'stim_duration': 0.15, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 6, 'trials': 9},
    5: {'colors': 3, 'n_back': 2, 'stim_duration': 0.10, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 6, 'trials': 9},
    6: {'colors': 3, 'n_back': 3, 'stim_duration': 0.25, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 6, 'trials': 9},
    7: {'colors': 3, 'n_back': 3, 'stim_duration': 0.20, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 6, 'trials': 9},
    8: {'colors': 3, 'n_back': 3, 'stim_duration': 0.15, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 6, 'trials': 9},
    9: {'colors': 3, 'n_back': 3, 'stim_duration': 0.1, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 6, 'trials': 9},
    10: {'colors': 3, 'n_back': 4, 'stim_duration': 0.25, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 6, 'trials': 9},
    11: {'colors': 3, 'n_back': 4, 'stim_duration': 0.20, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 6, 'trials': 9},
    12: {'colors': 3, 'n_back': 4, 'stim_duration': 0.15, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 6, 'trials': 9},
    13: {'colors': 3, 'n_back': 4, 'stim_duration': 0.1, 'min_ISI': 1.0, 'max_ISI': 1.0, 'min_targets': 6, 'trials': 9}
}

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

        while stage_index < len(stage_numbers):
            if not continue_task:
                break

            stage = stage_numbers[stage_index]
            stage_params = stages[stage]

            if stage == 1:
                threshold = 90
            else:
                threshold = 75

            trial_targets = [True] * stage_params['min_targets'] + [False] * (stage_params['trials'] - stage_params['min_targets'])
            random.shuffle(trial_targets)
            n_back = stage_params['n_back']
            num_colors = stage_params['colors']
            stim_duration = stage_params['stim_duration']
            min_ISI = stage_params['min_ISI']
            max_ISI = stage_params['max_ISI']

            print(f"\n=== Starting Stage {stage} ===")
            print(f"Generated {len(trial_targets)} trials with {trial_targets.count(True)} targets.")
            print(f"Number of Colors: {num_colors}, N-back: {n_back}, Stim Duration: {stim_duration}, ISI: {min_ISI}-{max_ISI}")

            if prev_n_back is None or n_back != prev_n_back:
                instruction_text = visual.TextStim(
                    win,
                    text=f"The n-back has changed to {n_back}. Respond if the colors match the color from {n_back} trials ago.\n\nPress any key to continue.",
                    pos=(0, 0),
                    color='white',
                    height=0.07
                )
                instruction_text.draw()
                win.flip()
                event.waitKeys()
                print(f"User informed of n-back change to {n_back}.")
            prev_n_back = n_back

            if num_colors > len(colors):
                print(f"Warning: Stage {stage} requires more colors than available.")
                stage_colors = colors.copy()
            else:
                stage_colors = random.sample(colors, num_colors)
            print(f"Stage {stage} Colors: {stage_colors}")

            trial_counter = 0
            correct_responses = 0
            correct_nonresponses = 0
            incorrect = 0
            stimuli_sequence = []
            trial_correctness = []

            total_stage_trials = stage_params['trials']
            ended_early = False

            for trial_index, forced_target in enumerate(trial_targets, start=1):
                if not continue_task:
                    break

                elapsed_time = global_clock.getTime()
                remaining_time = max(0, total_time - elapsed_time)
                minutes = int(remaining_time) // 60
                seconds = int(remaining_time) % 60

                if trial_counter > n_back:
                    scored_correct = sum(trial_correctness[n_back:]) if len(trial_correctness) > n_back else 0
                    scored_total = trial_counter - n_back
                    scored_accuracy = (scored_correct / scored_total) * 100 if scored_total > 0 else 100
                else:
                    scored_accuracy = 100

                timer_text.setText(
                    f"Time Remaining: {minutes}:{seconds:02d}\n"
                    f"Trials: {trial_counter}/{total_stage_trials}\n"
                    f"Accuracy: {scored_accuracy:.2f}% / {threshold}%\n"
                )

                if elapsed_time >= end_time:
                    continue_task = False
                    print("Total experiment time reached. Ending task.")
                    break

                trial_counter += 1
                trial_number_global += 1
                current_color = random.choice(stage_colors)
                stimuli_sequence.append(current_color)
                if len(stimuli_sequence) > n_back + 1:
                    stimuli_sequence.pop(0)

                # Determine if current trial is target
                if len(stimuli_sequence) > n_back:
                    is_target = (current_color == stimuli_sequence[-(n_back + 1)])
                else:
                    is_target = False

                print(f"\nTrial {trial_number_global}: Stage {stage}, N-back {n_back}")
                print(f"Current Color: {current_color}, Is Target: {is_target}")

                stim = visual.Rect(win, width=0.5, height=0.5, fillColor=current_color)
                kb.clearEvents()
                response = None
                rt = None
                response_made = False

                if trial_counter > n_back:
                    scored_correct = sum(trial_correctness[n_back:]) if len(trial_correctness) > n_back else 0
                    scored_total = trial_counter - n_back
                    scored_accuracy = (scored_correct / scored_total) * 100 if scored_total > 0 else 100
                else:
                    scored_accuracy = 100

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
                else:
                    debug_text.setText('')

                # Draw stimulus
                stim_clock = core.Clock()
                kb.clock.reset()

                # Ensure feedback polygon is gray at the start of the trial
                feedback_polygon.fillColor = 'gray'  # CHANGED: reset to gray at trial start
                
                while stim_clock.getTime() < stim_duration:
                    stim.draw()
                    feedback_polygon.draw()  # ADDED: Draw polygon
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
                            print(f"Trial {trial_number_global}: Response '{response}' at {rt:.3f}s during stimulus.")
                        elif key == quit_key:
                            print("Experiment terminated by user.")
                            continue_task = False
                            break
                    if not continue_task or response_made:
                        break

                if not continue_task:
                    break

                win.flip()

                ISI_trial = random.uniform(min_ISI, max_ISI)
                if not response_made:
                    ISI_clock = core.Clock()
                    kb.clock.reset()
                    while ISI_clock.getTime() < ISI_trial:
                        elapsed_time = global_clock.getTime()
                        remaining_time = max(0, total_time - elapsed_time)
                        minutes = int(remaining_time) // 60
                        seconds = int(remaining_time) % 60

                        if trial_counter > n_back:
                            scored_correct = sum(trial_correctness[n_back:]) if len(trial_correctness) > n_back else 0
                            scored_total = trial_counter - n_back
                            scored_accuracy = (scored_correct / scored_total) * 100 if scored_total > 0 else 100
                        else:
                            scored_accuracy = 100

                        timer_text.setText(
                            f"Time Remaining: {minutes}:{seconds:02d}\n"
                            f"Trials: {trial_counter}/{total_stage_trials}\n"
                            f"Accuracy: {scored_accuracy:.2f}% / {threshold}%\n"
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
                        else:
                            debug_text.setText('')

                        # Draw polygon (still gray here if no response yet)
                        feedback_polygon.draw()
                        if debug_enabled:
                            debug_text.draw()
                        timer_text.draw()
                        win.flip()

                        if elapsed_time >= end_time:
                            continue_task = False
                            print("Total experiment time reached during ISI. Ending task.")
                            break

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
                        if not continue_task or response_made:
                            break

                if not continue_task:
                    break

                # Scoring correctness
                if is_target and response == response_key:
                    correct = True
                    correct_responses += 1
                    show_feedback = True
                    print(f"Trial {trial_number_global}: Correct response to target.")
                elif is_target and response is None:
                    correct = False
                    incorrect += 1
                    show_feedback = True
                    print(f"Trial {trial_number_global}: Missed target.")
                elif not is_target and response == response_key:
                    correct = False
                    incorrect += 1
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
                    show_feedback = False

                trial_correctness.append(correct)

                if trial_counter > n_back:
                    scored_correct = sum(trial_correctness[n_back:])
                    scored_total = trial_counter - n_back
                    if scored_total > 0:
                        scored_accuracy = (scored_correct / scored_total) * 100
                    else:
                        scored_accuracy = 100
                    # Check if max possible accuracy < threshold
                    trials_left = total_stage_trials - trial_counter
                    max_possible_scored_correct = scored_correct + trials_left
                    max_possible_scored_total = scored_total + trials_left
                    if max_possible_scored_total > 0:
                        max_possible_scored_accuracy = (max_possible_scored_correct / max_possible_scored_total) * 100
                    else:
                        max_possible_scored_accuracy = 100

                    if max_possible_scored_accuracy < threshold:
                        print("Not possible to achieve threshold accuracy this stage. Ending stage early.")
                        ended_early = True
                        break

                # Show feedback via polygon color during ISI if show_feedback is True
                # CHANGED: Instead of textual feedback, change polygon color
                if show_feedback:
                    ISI_clock = core.Clock()
                    kb.clock.reset()
                    
                    # If correct is True => green, else red
                    feedback_polygon.fillColor = 'green' if correct else 'red'
                    feedback_polygon.lineColor = 'green' if correct else 'red'

                    while ISI_clock.getTime() < ISI_trial:
                        elapsed_time = global_clock.getTime()
                        remaining_time = max(0, total_time - elapsed_time)
                        minutes = int(remaining_time) // 60
                        seconds = int(remaining_time) % 60

                        if trial_counter > n_back:
                            scored_correct = sum(trial_correctness[n_back:])
                            scored_total = trial_counter - n_back
                            scored_accuracy = (scored_correct / scored_total) * 100 if scored_total > 0 else 100
                        else:
                            scored_accuracy = 100

                        timer_text.setText(
                            f"Time Remaining: {minutes}:{seconds:02d}\n"
                            f"Trials: {trial_counter}/{total_stage_trials}\n"
                            f"Accuracy: {scored_accuracy:.2f}% / {threshold}%\n"
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
                        else:
                            debug_text.setText('')

                        feedback_polygon.draw()  # The polygon now shows green or red
                        if debug_enabled:
                            debug_text.draw()
                        stage_level_text.draw()
                        timer_text.draw()
                        win.flip()

                        if elapsed_time >= end_time:
                            continue_task = False
                            print("Total experiment time reached during feedback. Ending task.")
                            break

                        keys = kb.getKeys([quit_key], waitRelease=False)
                        if quit_key in [key_event.name for key_event in keys]:
                            print("Experiment terminated by user during feedback.")
                            continue_task = False
                            break

                    # After feedback ISI, revert polygon to gray
                    feedback_polygon.fillColor = 'gray'
                    feedback_polygon.lineColor = 'gray'

                data_writer.writerow([stage, trial_number_global, n_back, current_color, response, correct, rt])
                data_file.flush()
                print(f"Trial {trial_number_global}: Data recorded.")

            if not continue_task:
                break

            if ended_early:
                scored_correct = sum(trial_correctness[n_back:]) if len(trial_correctness) > n_back else 0
                scored_total = (trial_counter - n_back) if trial_counter > n_back else 0
                if scored_total > 0:
                    scored_accuracy = (scored_correct / scored_total) * 100
                else:
                    scored_accuracy = 100
            else:
                total_trials = trial_counter
                total_correct = correct_responses + correct_nonresponses

                if total_trials > 0:
                    overall_accuracy = (total_correct / total_trials) * 100
                else:
                    overall_accuracy = 100

                if total_trials > n_back:
                    scored_correct = sum(trial_correctness[n_back:])
                    scored_total = total_trials - n_back
                    scored_accuracy = (scored_correct / scored_total) * 100
                else:
                    scored_accuracy = 100

                print(f"\nStage {stage} completed.")
                print(f"Overall Accuracy (all trials): {overall_accuracy:.2f}%")
                print(f"Scored Accuracy (excluding first {n_back} trials): {scored_accuracy:.2f}%")

            if scored_accuracy >= threshold:
                if stage_index < len(stage_numbers) - 1:
                    stage_index += 1
                else:
                    continue_task = False
            else:
                if stage_index > 0:
                    stage_index -= 1

        final_message = visual.TextStim(
            win,
            text='Test Completed!',
            pos=(0, 0),
            color='white',
            height=0.1,
            units='norm'
        )
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
