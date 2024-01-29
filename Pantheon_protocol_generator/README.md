
# Protocol Generator Tool Documentation

## Overview

The `protocol_generator` tool is designed to convert a CSV file into multiple JSON files for protocol management. Each JSON file represents a unique protocol with specific activities, durations, and instructions. This tool is particularly useful for applications requiring structured activity protocols.


## How to Use

### Prerequisites
- Ensure you have a CSV file formatted with columns: `class_name`, `activeClass_name`, `inactive_duration`, `active_duration`, `preamble`, `epilogue`, and `repetitions`. 
- The CSV file should have rows with `class_name` as "protocol" to indicate the start of a new protocol.

### Steps to Generate Protocols
1. **Prepare the CSV File**: Organize your activities in the CSV file. Each new protocol should start with a row where `class_name` is "protocol". The name for each protocol is taken from the `activeClass_name` column of these rows.

2. **Run the Tool**:
   - Call the `generate_multiple_protocols` function with the following parameters:
     - `input_csv`: Path to your CSV file.
     - `protocol_group`: A constant group name for all protocols (e.g., "test_group").
     - `random_class_order`: A boolean indicating whether to randomize the order of activities (True or False).
     - `disconnect_device_on_finish`: A boolean indicating whether to disconnect the device on finishing the protocol (True or False).

   Example:
   ```python
   generate_multiple_protocols('/path/to/your/csvfile.csv', 
                               protocol_group="your_group_name", 
                               random_class_order=True, 
                               disconnect_device_on_finish=False)
   ```

3. **Retrieve Generated Files**: The tool will generate JSON files in the specified directory. Each file corresponds to a protocol with the name taken from the `activeClass_name` when `class_name` is "protocol".

### Output
- JSON files named after each protocol with settings and activities as specified in the CSV file.

## Example CSV Format

```plaintext
class_name,activeClass_name,inactive_duration,active_duration,preamble,epilogue,repetitions
protocol,TestProtocol1,,,"Start of Protocol 1","End of Protocol 1",
activity1,Activity1,500,3000,"Preamble Activity 1","Epilogue Activity 1",5
activity2,Activity2,500,3000,"Preamble Activity 2","Epilogue Activity 2",5
protocol,TestProtocol2,,,"Start of Protocol 2","End of Protocol 2",
activity3,Activity3,500,3000,"Preamble Activity 3","Epilogue Activity 3",5
```

In the above example, two protocols ("TestProtocol1" and "TestProtocol2") will be generated with respective activities and instructions.
