from psychopy import visual, core, event, gui
from psychopy.hardware import keyboard
import random
import csv
import os
import math

# ---------------------------
# 1) Participant Intake GUI
# ---------------------------
exp_info = {
    'Participant ID': '',
    'Show Debug': True,     # Checkbox
    'Starting Stage': '1',  # String that we'll convert to int
    # Add a dropdown so user can choose Single or Dual
    'Task Type': ['Single', 'Dual']
}
dialog = gui.DlgFromDict(dictionary=exp_info, title='N-back Task')
if not dialog.OK:
    core.quit()

participant_id = exp_info['Participant ID'].strip()
if not participant_id:
    print("Participant ID is required.")
    core.quit()

debug_enabled = exp_info['Show Debug']
task_type = exp_info['Task Type']  # "Single" or "Dual"

# Convert the Starting Stage to int
try:
    starting_stage = int(exp_info['Starting Stage'])
except ValueError:
    print("Error: Starting Stage must be an integer.")
    core.quit()
if starting_stage < 1:
    print("Error: Starting Stage must be 1 or greater.")
    core.quit()

# ---------------------------
# 2) File & Directory Setup
# ---------------------------
data_dir = "./data"
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

filename = os.path.join(data_dir, f"data_{participant_id}.csv")
if os.path.exists(filename):
    print(f"File {filename} already exists. Please use a unique Participant ID.")
    core.quit()

# ---------------------------
# 3) Create PsychoPy Window
# ---------------------------
win = visual.Window([800, 600], color='black', units='norm')

# (Optional) Background image
bg_image = visual.ImageStim(
    win,
    image="./background.png",  # Provide path if not in same folder
    units='norm',
    size=(2, 2)
)

# Debug text
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
    win, text='', pos=(0, -.05), color='white', height=0.05, units='norm'
)

kb = keyboard.Keyboard()

# ---------------------------
# 4) Shared Helper: Generate Stages
# ---------------------------
def generate_stages(total_stages=25):
    """
    Generate a dictionary of stage parameters.
    This logic is the same in both Single and Dual N-back tasks.
    Adjust the numbers if needed.
    """
    stages = {}
    # Initial parameters
    c = 2  # number of colors
    n_back = 1
    stim_duration = 0.25
    min_ISI = 1.0
    max_ISI = 2.0
    min_targets = 5
    trials = 10

    # Target goals
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

        # If stage 1 is the first to define, then set next stage => n_back=2
        if stage == 1 and not first_stage_defined:
            first_stage_defined = True
            n_back = 2
            c = 3
            min_targets = 10
            trials = 20

        stage += 1
        if stage > total_stages:
            break

        if reached_targets(stim_duration, max_ISI):
            # Reset stim and ISI, then increase difficulty
            stim_duration = 0.25
            max_ISI = 2.0
            c += 1
            n_back += 1
            reduce_max_ISI_next = True
        else:
            # Alternate: reduce max_ISI, then reduce stim
            if reduce_max_ISI_next:
                if max_ISI > target_max_ISI:
                    max_ISI = max(max_ISI - isi_decrement, target_max_ISI)
                reduce_max_ISI_next = False
            else:
                if stim_duration > target_stim_duration:
                    stim_duration = max(stim_duration - stim_decrement, target_stim_duration)
                reduce_max_ISI_next = True

    return stages

# Generate up to 13 stages (as in your example)
stages = generate_stages(total_stages=13)
stage_numbers = list(stages.keys())
if starting_stage not in stage_numbers:
    print(f"Error: Starting Stage {starting_stage} is invalid (must be 1 to {max(stage_numbers)}).")
    core.quit()

# ---------------------------
# 5) SINGLE N-BACK CODE
# ---------------------------
def run_single_nback(filename, participant_id, starting_stage, stages, stage_numbers,
                     debug_enabled, bg_image, win):
    """
    Runs the single N-back code (originally your single-nback script).
    Only difference: it's now wrapped in a function.
    """

    # Key Setup
    response_key = 'space'
    quit_key = 'escape'

    # We create a global clock to time-limit the experiment (300s)
    global_clock = core.Clock()
    total_time = 300
    end_time = 300

    colors_available = ['orange', 'blue', 'yellow']
    trial_number_global = 0

    try:
        with open(filename, 'w', newline='') as data_file:
            data_writer = csv.writer(data_file)
            # Column headers
            data_writer.writerow(['Stage', 'Trial', 'N-back', 'Stimulus', 'Response', 'Correct', 'RT'])
            data_file.flush()

            # We'll start at the stage_index for starting_stage
            stage_index = stage_numbers.index(starting_stage)
            continue_task = True
            prev_n_back = None
            threshold = 75  # accuracy threshold

            while stage_index < len(stage_numbers):
                if not continue_task:
                    break

                stage = stage_numbers[stage_index]
                stage_params = stages[stage]

                # Extract stage parameters
                n_back = stage_params['n_back']
                num_colors = stage_params['colors']
                stim_duration = stage_params['stim_duration']
                min_ISI = stage_params['min_ISI']
                max_ISI = stage_params['max_ISI']
                min_targets = stage_params['min_targets']
                trials = stage_params['trials']

                # Show instructions if n_back changes
                if prev_n_back is not None and n_back != prev_n_back:
                    instruction_text = visual.TextStim(
                        win,
                        text=f"SINGLE N-BACK\n\nn-back = {n_back}\n\nPress any key to continue.",
                        pos=(0,0),
                        color='white',
                        height=0.07
                    )
                    bg_image.draw()
                    instruction_text.draw()
                    win.flip()
                    event.waitKeys()

                prev_n_back = n_back

                # Generate trial targets
                trial_targets = [True]*min_targets + [False]*(trials - min_targets)
                random.shuffle(trial_targets)

                # If not enough colors in the pool
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

                # Allowed mistakes based on threshold
                scored_total_stage = trials - n_back
                if scored_total_stage <= 0:
                    allowed_mistakes = 0
                else:
                    allowed_mistakes = math.floor(scored_total_stage * (1 - threshold/100))
                allowed_mistakes = max(0, allowed_mistakes)

                while trial_counter < trials and continue_task:
                    elapsed_time = global_clock.getTime()
                    if elapsed_time >= end_time:
                        continue_task = False
                        print("Total experiment time reached. Ending task.")
                        break

                    remaining_time = max(0, total_time - elapsed_time)
                    minutes = int(remaining_time)//60
                    seconds = int(remaining_time)%60

                    # Compute scored accuracy so far (excluding first n_back)
                    if trial_counter > n_back:
                        scored_correct = sum(trial_correctness[n_back:]) if len(trial_correctness) > n_back else 0
                        scored_total = (trial_counter - n_back)
                        scored_accuracy = (scored_correct / scored_total)*100 if scored_total > 0 else 100
                    else:
                        scored_accuracy = 100

                    timer_text.setText(f"Time Remaining: {minutes}:{seconds:02d}\n")

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
                            f"Target Accuracy: {threshold}%"
                        )
                    else:
                        debug_text.setText('')

                    stim_clock = core.Clock()
                    kb.clock.reset()
                    mistakes_text.setColor('white')
                    mistakes_text.setText(
                        f'Stage: {stage}\nN-back: {n_back}\nErrors allowed: {allowed_mistakes}'
                    )

                    # Present stimulus
                    while stim_clock.getTime() < stim_duration and continue_task:
                        bg_image.draw()
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

                    # ISI
                    ISI_trial = random.uniform(min_ISI, max_ISI)
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
                                scored_total = (trial_counter - n_back)
                                scored_accuracy = (scored_correct / scored_total)*100 if scored_total > 0 else 100
                            else:
                                scored_accuracy = 100

                            timer_text.setText(f"Time Remaining: {minutes}:{seconds:02d}\n")

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
                                    f"Target Accuracy: {threshold}%"
                                )

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

                    # Scoring
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
                        print(f"Trial {trial_number_global}: Correct non-response.")
                    else:
                        correct = False
                        incorrect += 1
                        allowed_mistakes -= 1
                        show_feedback = False

                    trial_correctness.append(correct)

                    if allowed_mistakes <= 0 and not correct:
                        print("No remaining mistakes allowed. Ending stage early.")
                        ended_early = True

                    # Show feedback only if show_feedback == True
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
                                scored_total = (trial_counter - n_back)
                                scored_accuracy = (scored_correct / scored_total)*100 if scored_total>0 else 100
                            else:
                                scored_accuracy = 100

                            timer_text.setText(f"Time Remaining: {minutes}:{seconds:02d}\n")

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
                                f'Stage: {stage}\nN-back: {n_back}\nErrors allowed: {allowed_mistakes}'
                            )

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

                    # Record data
                    data_writer.writerow([stage, trial_number_global, n_back, current_color, response, correct, rt])
                    data_file.flush()

                    if ended_early or allowed_mistakes <= 0:
                        break

                # End of stage: compute scored_accuracy
                if ended_early or allowed_mistakes <= 0:
                    scored_correct = sum(trial_correctness[n_back:]) if len(trial_correctness) > n_back else 0
                    scored_total = len(trial_correctness) - n_back if len(trial_correctness) > n_back else 0
                    scored_accuracy = (scored_correct / scored_total)*100 if scored_total>0 else 100
                else:
                    total_trials = len(trial_correctness)
                    if total_trials > n_back:
                        scored_correct = sum(trial_correctness[n_back:])
                        scored_total = total_trials - n_back
                        scored_accuracy = (scored_correct / scored_total)*100 if scored_total>0 else 100
                    else:
                        scored_accuracy = 100

                print(f"\nStage {stage} completed.")
                print(f"Scored Accuracy (excluding first {n_back} trials): {scored_accuracy:.2f}%")

                # Show stage completion
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

                # Stage Up/Down
                if scored_accuracy >= threshold and not ended_early and allowed_mistakes > 0:
                    if stage_index < len(stage_numbers)-1:
                        stage_index += 1
                    else:
                        continue_task = False
                else:
                    if stage_index > 0:
                        stage_index -= 1
                    else:
                        # remain if we're at the first stage
                        pass

        # End message
        final_message = visual.TextStim(
            win,
            text='Test Completed (Single N-back)!',
            pos=(0, 0),
            color='white',
            height=0.04,
            units='norm'
        )
        bg_image.draw()
        final_message.draw()
        win.flip()
        core.wait(3)

    except Exception as e:
        print(f"An error occurred (Single N-back): {e}")


# ---------------------------
# 6) DUAL N-BACK CODE
# ---------------------------
def run_dual_nback(filename, participant_id, starting_stage, stages, stage_numbers,
                   debug_enabled, bg_image, win):
    """
    Runs the dual N-back code (originally your dual-nback script).
    We do the color and circle quadrant simultaneously.
    """

    # Key Setup
    response_key = 'space'
    quit_key = 'escape'

    global_clock = core.Clock()
    total_time = 300
    end_time = 300

    # A shifted fixation cross
    fixation = visual.TextStim(
        win,
        text='+',
        pos=(0, 0.3),
        color='white',
        height=0.1
    )

    colors_available = ['orange', 'blue', 'yellow']
    trial_number_global = 0

    # Circle positions around (0, 0.3)
    offset = 0.1
    circle_positions = [
        (fixation.pos[0] - offset, fixation.pos[1] + offset),  # top-left
        (fixation.pos[0] + offset, fixation.pos[1] + offset),  # top-right
        (fixation.pos[0] - offset, fixation.pos[1] - offset),  # bottom-left
        (fixation.pos[0] + offset, fixation.pos[1] - offset)   # bottom-right
    ]

    try:
        with open(filename, 'w', newline='') as data_file:
            data_writer = csv.writer(data_file)
            data_writer.writerow([
                'Stage', 'Trial', 'N-back',
                'Color_Stimulus', 'Circle_Quadrant',
                'Times_Space_Pressed', 'Correct',
                'RTs_of_each_press'
            ])
            data_file.flush()

            stage_index = stage_numbers.index(starting_stage)
            continue_task = True
            prev_n_back = None
            threshold = 75

            while stage_index < len(stage_numbers):
                if not continue_task:
                    break

                stage = stage_numbers[stage_index]
                stage_params = stages[stage]
                n_back = stage_params['n_back']
                num_colors = stage_params['colors']
                stim_duration = stage_params['stim_duration']
                min_ISI = stage_params['min_ISI']
                max_ISI = stage_params['max_ISI']
                min_targets = stage_params['min_targets']
                trials = stage_params['trials']

                # Show instructions if n_back changes
                if prev_n_back is not None and n_back != prev_n_back:
                    instruction_text = visual.TextStim(
                        win,
                        text=(
                            f"DUAL N-BACK\n\nn-back = {n_back}\n\nRules:\n"
                            "- Press SPACE 1x if exactly ONE stimulus (color or circle) matches from n trials back.\n"
                            "- Press SPACE 2x if BOTH stimuli match.\n\n"
                            "Press any key to continue."
                        ),
                        pos=(0, 0), color='white', height=0.07
                    )
                    bg_image.draw()
                    instruction_text.draw()
                    win.flip()
                    event.waitKeys()

                prev_n_back = n_back

                # If you want to keep min_targets logic
                trial_targets = [True]*min_targets + [False]*(trials - min_targets)
                random.shuffle(trial_targets)

                # Enough colors check
                if num_colors > len(colors_available):
                    print(f"Warning: Stage {stage} requires more colors than available.")
                    stage_colors = colors_available.copy()
                else:
                    stage_colors = random.sample(colors_available, num_colors)

                color_sequence = []
                circle_sequence = []
                trial_counter = 0
                trial_correctness = []
                ended_early = False

                scored_total_stage = trials - n_back
                if scored_total_stage <= 0:
                    allowed_mistakes = 0
                else:
                    allowed_mistakes = math.floor(scored_total_stage * (1 - threshold/100))
                allowed_mistakes = max(0, allowed_mistakes)

                while trial_counter < trials and continue_task:
                    elapsed_time = global_clock.getTime()
                    if elapsed_time >= end_time:
                        continue_task = False
                        print("Total experiment time reached. Ending task.")
                        break

                    remaining_time = max(0, total_time - elapsed_time)
                    minutes = int(remaining_time)//60
                    seconds = int(remaining_time)%60

                    if trial_counter > n_back:
                        scored_correct = sum(trial_correctness[n_back:])
                        scored_total = (trial_counter - n_back)
                        scored_accuracy = (scored_correct / scored_total)*100 if scored_total>0 else 100
                    else:
                        scored_accuracy = 100

                    timer_text.setText(f"Time Remaining: {minutes}:{seconds:02d}\n")

                    current_color = random.choice(stage_colors)
                    current_circle_pos = random.choice(circle_positions)

                    color_sequence.append(current_color)
                    circle_sequence.append(current_circle_pos)

                    if len(color_sequence) > n_back + 1:
                        color_sequence.pop(0)
                    if len(circle_sequence) > n_back + 1:
                        circle_sequence.pop(0)

                    trial_counter += 1
                    trial_number_global += 1

                    if len(color_sequence) > n_back:
                        is_color_match = (current_color == color_sequence[-(n_back+1)])
                    else:
                        is_color_match = False

                    if len(circle_sequence) > n_back:
                        is_circle_match = (current_circle_pos == circle_sequence[-(n_back+1)])
                    else:
                        is_circle_match = False

                    match_count = sum([is_color_match, is_circle_match])
                    print(f"\nTrial {trial_number_global} [Stage {stage}, N-back {n_back}]: "
                          f"Color={current_color} (match={is_color_match}), "
                          f"Circle={current_circle_pos} (match={is_circle_match}), "
                          f"Matches={match_count}")

                    stim_rect = visual.Rect(
                        win, width=0.35, height=0.15, pos=(0, 0.65),
                        fillColor=current_color, units='norm'
                    )
                    stim_circle = visual.Circle(
                        win, radius=0.05, fillColor='white', lineColor='white',
                        pos=current_circle_pos, units='norm'
                    )

                    kb.clearEvents()
                    all_space_keypress_times = []

                    if debug_enabled:
                        debug_text.setText(
                            f"Stage: {stage}\n"
                            f"Trial: {trial_number_global}\n"
                            f"N-back: {n_back}\n"
                            f"Allowed Mistakes: {allowed_mistakes}\n"
                            f"Scored Acc: {scored_accuracy:.2f}%\n"
                            f"Match Count: {match_count} (Press SPACE {match_count}x)"
                        )
                    else:
                        debug_text.setText('')

                    mistakes_text.setColor('white')
                    mistakes_text.setText(
                        f'Stage: {stage}\nN-back: {n_back}\nErrors allowed: {allowed_mistakes}'
                    )

                    # Stimulus display
                    stim_clock = core.Clock()
                    kb.clock.reset()

                    while stim_clock.getTime() < stim_duration and continue_task:
                        bg_image.draw()
                        fixation.draw()
                        stim_rect.draw()
                        stim_circle.draw()

                        mistakes_text.draw()
                        timer_text.draw()
                        if debug_enabled:
                            debug_text.draw()
                        stage_level_text.draw()
                        win.flip()

                        keys = kb.getKeys([response_key, quit_key], waitRelease=False)
                        for key_event in keys:
                            key = key_event.name
                            timestamp = key_event.rt
                            if key == response_key:
                                all_space_keypress_times.append(timestamp)
                                print(f"Trial {trial_number_global}: SPACE pressed at {timestamp:.3f}s.")
                            elif key == quit_key:
                                print("User terminated the task.")
                                continue_task = False
                                break
                        if not continue_task:
                            break

                    if not continue_task:
                        break

                    # ISI
                    ISI_trial = random.uniform(min_ISI, max_ISI)
                    ISI_clock = core.Clock()
                    kb.clock.reset()

                    while ISI_clock.getTime() < ISI_trial and continue_task:
                        elapsed_time = global_clock.getTime()
                        if elapsed_time >= end_time:
                            continue_task = False
                            print("Total experiment time reached. Ending task.")
                            break

                        remaining_time = max(0, total_time - elapsed_time)
                        minutes = int(remaining_time)//60
                        seconds = int(remaining_time)%60

                        if trial_counter > n_back:
                            scored_correct = sum(trial_correctness[n_back:])
                            scored_total = (trial_counter - n_back)
                            scored_accuracy = (scored_correct / scored_total)*100 if scored_total>0 else 100
                        else:
                            scored_accuracy = 100

                        timer_text.setText(f"Time Remaining: {minutes}:{seconds:02d}\n")
                        if debug_enabled:
                            debug_text.setText(
                                f"Stage: {stage}\n"
                                f"Trial: {trial_number_global}\n"
                                f"N-back: {n_back}\n"
                                f"Allowed Mistakes: {allowed_mistakes}\n"
                                f"Scored Acc: {scored_accuracy:.2f}%\n"
                                f"Match Count: {match_count} (Press SPACE {match_count}x)"
                            )

                        bg_image.draw()
                        fixation.draw()
                        timer_text.draw()
                        mistakes_text.draw()
                        if debug_enabled:
                            debug_text.draw()
                        stage_level_text.draw()
                        win.flip()

                        keys = kb.getKeys([response_key, quit_key], waitRelease=False)
                        for key_event in keys:
                            key = key_event.name
                            timestamp = key_event.rt
                            if key == response_key:
                                all_space_keypress_times.append(stim_duration + timestamp)
                                print(f"Trial {trial_number_global}: SPACE pressed at {stim_duration + timestamp:.3f}s (ISI).")
                            elif key == quit_key:
                                print("User terminated the task.")
                                continue_task = False
                                break
                        if not continue_task:
                            break

                    if not continue_task:
                        break

                    # Score
                    pressed_count = len(all_space_keypress_times)
                    correct = (pressed_count == match_count)
                    trial_correctness.append(int(correct))

                    if correct:
                        print(f"Trial {trial_number_global}: CORRECT (pressed={pressed_count}, needed={match_count}).")
                    else:
                        print(f"Trial {trial_number_global}: INCORRECT (pressed={pressed_count}, needed={match_count}).")
                        allowed_mistakes -= 1

                    rts_str = ";".join([f"{rt:.3f}" for rt in all_space_keypress_times])
                    data_writer.writerow([
                        stage, trial_number_global, n_back,
                        current_color, str(current_circle_pos),
                        pressed_count, correct, rts_str
                    ])
                    data_file.flush()

                    if allowed_mistakes <= 0 and not correct:
                        print("No remaining mistakes allowed. Ending stage early.")
                        ended_early = True
                        break

                # End of Stage
                if ended_early or allowed_mistakes <= 0:
                    scored_correct = sum(trial_correctness[n_back:]) if len(trial_correctness) > n_back else 0
                    scored_total = len(trial_correctness) - n_back if len(trial_correctness) > n_back else 0
                    scored_accuracy = (scored_correct / scored_total)*100 if scored_total>0 else 100
                else:
                    total_trials = len(trial_correctness)
                    if total_trials > n_back:
                        scored_correct = sum(trial_correctness[n_back:])
                        scored_total = total_trials - n_back
                        scored_accuracy = (scored_correct / scored_total)*100 if scored_total>0 else 100
                    else:
                        scored_accuracy = 100

                print(f"\nStage {stage} completed. Scored Accuracy = {scored_accuracy:.2f}%")

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

                if scored_accuracy >= threshold and not ended_early and allowed_mistakes > 0:
                    if stage_index < len(stage_numbers)-1:
                        stage_index += 1
                    else:
                        continue_task = False
                else:
                    if stage_index > 0:
                        stage_index -= 1
                    else:
                        pass

        # Final message
        final_message = visual.TextStim(
            win,
            text='Test Completed (Dual N-back)!',
            pos=(0, 0),
            color='white',
            height=0.04,
            units='norm'
        )
        bg_image.draw()
        final_message.draw()
        win.flip()
        core.wait(3)

    except Exception as e:
        print(f"An error occurred (Dual N-back): {e}")


# ---------------------------
# 7) MAIN LOGIC
# ---------------------------
if task_type == 'Single':
    run_single_nback(
        filename=filename,
        participant_id=participant_id,
        starting_stage=starting_stage,
        stages=stages,
        stage_numbers=stage_numbers,
        debug_enabled=debug_enabled,
        bg_image=bg_image,
        win=win
    )
else:
    run_dual_nback(
        filename=filename,
        participant_id=participant_id,
        starting_stage=starting_stage,
        stages=stages,
        stage_numbers=stage_numbers,
        debug_enabled=debug_enabled,
        bg_image=bg_image,
        win=win
    )

# Cleanup
win.close()
core.quit()
