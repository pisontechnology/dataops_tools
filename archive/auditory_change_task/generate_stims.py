import pandas as pd
import random

def rewrite_stim_number():
    # Load the CSV file into a DataFrame
    df = pd.read_csv("template.csv")
    
    # Generate new 'stim_number' values
    new_stim_numbers = []
    prev_number = None

    for _ in range(len(df)):
        # Choose the type of number for the next value (odd/even) with a 50% chance
        if prev_number is not None:
            # 50% chance of switching to a number with different parity (odd/even)
            if random.random() < 0.5:
                if prev_number % 2 == 0:
                    possible_numbers = [num for num in range(10) if num % 2 != 0]
                else:
                    possible_numbers = [num for num in range(10) if num % 2 == 0]
            else:
                # Stay in the same parity category
                possible_numbers = [num for num in range(10) if num % 2 == prev_number % 2]
            
            # Remove the previous number to avoid repeats
            if prev_number in possible_numbers:
                possible_numbers.remove(prev_number)
        else:
            # No previous number on the first iteration, so choose any number 0-9
            possible_numbers = list(range(10))
        
        # Choose a new random number from the possible options
        new_number = random.choice(possible_numbers)
        new_stim_numbers.append(new_number)
        prev_number = new_number

    # Update the DataFrame with the new values
    df['stim_number'] = new_stim_numbers
    
    # Save the modified DataFrame to a new CSV file
    df.to_csv("task.csv", index=False)
    print (df)

rewrite_stim_number()