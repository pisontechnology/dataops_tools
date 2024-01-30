
# Documentation for Protocol Generator Tool

## Overview

The Pantheon Protocol Generator Tool is a Python-based utility designed to convert structured data from CSV files into a series of JSON files, each representing a unique protocol. 

## Usage

1. **Prepare Your CSV File:**
   The CSV file should be structured with the following columns:
   - `class_name`: Indicates whether the row is a new protocol (`protocol`) or a class within the protocol.
   - `activeClass_name`: Name used for active intervals in the JSON.
   - `inactive_duration`: Duration (in milliseconds) of the inactive interval that precedes and follows an active interval.
   - `active_duration`: Duration (in milliseconds) of the active interval where the data will be collected.
   - `preamble`: (Optional) Preamble text, images, videos, or links for a protocol or class.
   - `epilogue`: (Optional) Epilogue text, images, videos, or links for a protocol or class.
   - `repetitions`: Number of repetitions for a class.

   Example:
   ```
   class_name, activeClass_name, inactive_duration, active_duration, preamble, epilogue, repetitions
   protocol, MyProtocol, , , , ,
   ClassA, ActiveA, 500, 1000, Intro A, Outro A, 3
   ```

2. **Run the Protocol Generator:**
   Open the `protocol_generator.ipynb` in Jupyter Notebook.
   - Update the path to your CSV file in the notebook.
   - Run the notebook to execute the script.

3. **Output:**
   The tool will generate JSON files for each protocol defined in the CSV. Each JSON file will be named after the protocol and will contain:
   - The name of the protocol.
   - A list of classes, each with its own set of intervals (active and inactive), preambles, epilogues, and repetitions.
   - Duration values will be integers representing milliseconds.

## Example of Generated JSON Structure

```json
{
  "name": "MyProtocol",
  "parameters": [],
  "active": true,
  "classes": [
    {
      "class": "ClassA",
      "intervals": [
        {"label": "inactive", "durationInMillis": 500},
        {"label": "ActiveA", "durationInMillis": 1000},
        {"label": "inactive", "durationInMillis": 500}
      ],
      "repetitions": 3,
      "preamble": "Intro A",
      "epilogue": "Outro A"
    }
    // Additional classes...
  ],
  "randomClassOrder": false, // As per your setting in the notebook
  "preamble": "", // Global preamble for the protocol
  "epilogue": "", // Global epilogue for the protocol
  "group": "YourGroupName", // As per your setting in the notebook
  "disconnectDeviceOnFinish": true // As per your setting in the notebook
}
```

## Notes

- Ensure that the CSV file follows the specified format closely, as deviations may result in incorrect or incomplete JSON outputs.
- This tool is customizable through the Jupyter Notebook, allowing changes in logic or format as per specific requirements.

