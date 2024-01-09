# dataops_tools

### Pantheon Protocol Generator Documentation

#### Overview
The Pantheon Protocol Generator is designed to convert CSV data into a structured JSON format suitable for specific protocols. It is tailored to handle two types of protocols:
1. Activity based protocols
2. Cognitive Test protocols

The tool reads data from a CSV file, processes it according to the specified protocol type, and generates a JSON file with the structured data.

#### Features
- **Customizable Protocol Types**: Handles Activity and Cognitive Test protocols.
- **Dynamic Parameter Setting**: Allows setting various parameters such as protocol name, group, random class order, and device disconnection behavior.
- **NaN Handling**: Converts NaN values in the CSV to empty strings in the JSON file.
- **Flexible Input**: Can process different CSV structures based on the protocol type.

#### Files
- `protocol_generator.ipynb`: The Jupyter notebook containing the implementation of the protocol generator.
- `cognitive_test_example.csv`: An example CSV file for the Cognitive Test Test Protocol. This creates a 30 second SRT.
- `activity_example.csv`: An example CSV file for the Activity Protocol. This creates a protocol for gesture primitives.

#### Usage
1. **Setting Up**: 
   - Open `protocol_generator.ipynb` in a Jupyter notebook environment.
   - Ensure that Pandas library is installed for CSV processing.

2. **Function Call**:
   - The main function `generate_protocol` takes the following parameters:
     - `input_csv`: Path to the input CSV file.
     - `protocol_name`: Name of the protocol.
     - `protocol_type`: Type of the protocol (0 for Activity, 1 for Cognitive Test test).
     - `protocol_group`: Name of the group for the protocol.
     - `random_class_order`: Boolean value to set random class order.
     - `disconnect_device_on_finish`: Boolean value to determine if the device should disconnect on finish.
   - Example call: 
     ```python generate_protocol(input_csv="path_to_csv.csv", 
                       protocol_name="Example_Protocol", 
                       protocol_type=0, 
                       protocol_group="Group1", 
                       random_class_order=False, 
                       disconnect_device_on_finish=True)
     ```

3. **Output**:
   - The function generates a JSON file named after the `protocol_name`, containing the processed data from the CSV file.

4. **Additional Context** (if needed):
   - For each protocol type, specific CSV column names and structure are expected. Users should ensure that their CSV files conform to the expected format for correct processing.
   - In the case of NaN values in the input CSV, these will be replaced with empty strings in the output JSON.
   - Users may need to modify the function or provide additional context based on specific requirements or CSV structures.
   - It is recommended to validate the generated JSON file to ensure it meets the intended use case and format.

This documentation provides a basic overview and usage guide. For any specific requirements or detailed understanding, users should refer to the code in `protocol_generator.ipynb` and adapt it as necessary.
