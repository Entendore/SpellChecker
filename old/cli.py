import spacy
from core import AdvancedTextCorrector, apply_corrections

def interactive_mode(corrector):
    """Runs the interactive correction session."""
    print("\n--- Interactive Correction Session ---")
    user_input = input("Enter text to check: ")
    if not user_input.strip(): return

    errors = corrector.correct_text(user_input)
    if not errors:
        print("No errors found!")
        return

    print(f"\nFound {len(errors)} potential error(s).")
    user_decisions = {}

    for i, error in enumerate(errors):
        print(f"\nError {i+1}/{len(errors)}:")
        print(f"  - Type: {error['type'].capitalize()}")
        print(f"  - Original: '{error['original']}'")
        if error['type'] == 'grammar':
            print(f"  - Message: {error['message']}")
        print(f"  - Suggestion: '{error['suggestion']}'")

        while True:
            choice = input("  - [A]ccept, [I]gnore, or type your [O]wn correction: ").lower().strip()
            if choice in ['a', 'i', 'o']:
                break
            print("Invalid choice. Please enter 'A', 'I', or 'O'.")

        if choice == 'a':
            user_decisions[error['index']] = error['suggestion']
        elif choice == 'o':
            own_correction = input("  - Enter your correction: ").strip()
            user_decisions[error['index']] = own_correction
        # 'i' (ignore) requires no action

    final_text = apply_corrections(user_input, errors, user_decisions)
    print("\n--- Final Corrected Text ---")
    print(final_text)
    print("-" * 30)

def file_mode(corrector, file_path):
    """Processes a file and saves the corrected version."""
    print(f"\n--- Processing file: {file_path} ---")
    try:
        with open(file_path, 'r') as f:
            original_text = f.read()
        
        errors = corrector.correct_text(original_text)
        
        corrected_text = original_text
        for error in sorted(errors, key=lambda x: x['index'], reverse=True):
            corrected_text = corrected_text[:error['index']] + error['suggestion'] + corrected_text[error['index'] + len(error['original']):]

        output_path = f"corrected_{file_path}"
        with open(output_path, 'w') as f:
            f.write(corrected_text)
        
        print(f"Corrected {len(errors)} errors. Output saved to '{output_path}'.")

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    """Main function to run the CLI application."""
    print("--- Welcome to the Advanced NLP Corrector (CLI)! ---")
    
    try:
        # Load spaCy model and pass it to the core
        nlp_model = spacy.load("en_core_web_sm")
        corrector = AdvancedTextCorrector(nlp_model=nlp_model)
    except Exception as e:
        print(f"Failed to initialize the corrector: {e}")
        return

    while True:
        print("\nCommands: [i]nteractive, [f]ile <path>, [a]ddword <word>, [exit]")
        command = input("Enter a command: ").lower().strip()

        if command == 'exit':
            break
        elif command == 'i':
            interactive_mode(corrector)
        elif command.startswith('f '):
            _, path = command.split(' ', 1)
            file_mode(corrector, path)
        elif command.startswith('a '):
            _, word = command.split(' ', 1)
            result = corrector.add_word(word)
            print(result)
        else:
            print("Unknown command. Please try again.")

    print("\nExiting application. Goodbye!")

if __name__ == "__main__":
    main()