from InquirerPy import prompt
from pylsl import StreamInfo, StreamOutlet
import sys

def read_tags_from_file(file_path):
    """Read tags from a file, one per line."""
    try:
        with open(file_path, 'r') as file:
            tags = [line.strip() for line in file if line.strip()]
        if not tags:
            raise ValueError("The file is empty or contains only blank lines.")
        return tags
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

def main():
    # Get file path from user
    print("Enter the path to the tags file:")
    file_path = input().strip()

    # Read tags from the file
    tags = read_tags_from_file(file_path)

    # Set up the LSL stream
    info = StreamInfo('MarkerStream', 'Markers', 1, 0, 'string', 'marker_stream')
    outlet = StreamOutlet(info)

    print("\nTags loaded and LSL stream initialized. Press Ctrl+C to exit.")

    while True:
        try:
            # Create a radio-button-like selection menu
            questions = [
                {
                    "type": "list",
                    "name": "selected_tag",
                    "message": "Select a tag to send:",
                    "choices": tags,
                }
            ]
            answer = prompt(questions)
            selected_tag = answer["selected_tag"]
            outlet.push_sample([selected_tag])
            print(f"Sent tag: {selected_tag}\n")
        except KeyboardInterrupt:
            print("\nExiting.")
            break

if __name__ == "__main__":
    main()
