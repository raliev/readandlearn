# "Read and Learn"

This project is a specialized web-based reader designed to bridge the gap between extensive reading and targeted vocabulary study. The application processes uploaded text files by splitting them into readable "pages" that respect sentence and paragraph boundaries, ensuring no context is lost between breaks.

Instead of simply splitting text by spaces, the system scans a loaded dictionary to identify and prioritize the longest possible matching phrases (e.g., identifying "web application" as a single entity rather than two separate words). Known terms are rendered as interactive elements, allowing users to build a temporary vocabulary list while reading. This list can then be reviewed in a dedicated "Study Mode" that temporarily hides the text to focus purely on definitions, clearing the list upon completion to prepare for the next reading segment.

*The idea is that the reader first marks unfamiliar words, then sees their translations (but does not see the original text), and then returns to the text without the translations visible (assuming they remember them). In other words, this implements the idea of “the dictionary is in the next room.” It is assumed that this approach helps with memorization compared to showing the translation immediately when clicking on a word.*

## Features

  * **Smart Pagination:** breaks input text into fragments of a specified length, ensuring that cuts only occur after complete sentences or paragraphs.
  * **Greedy Phrase Matching:** implements a "longest match" algorithm where the text is tokenized based on the dictionary. If the dictionary contains "Rauf Aliev," the system prioritizes this phrase over the individual word "Rauf."
  * **Interactive Vocabulary Building:** distinguishes between "known" (clickable) tokens and unknown text. Clicking a highlighted phrase adds it to a sidebar list for immediate review.
  * **Focus-Based Study Session:** includes a "Show Translation" mode that hides the main text and presents the selected sidebar words as flashcards. Closing the session clears the list, allowing the user to resume reading with a fresh slate.
  * **State Persistence:** uses file content hashing (MD5) to uniquely identify uploads and saves the user's current page number in browser storage, allowing instant resumption of reading sessions.
  * **Default & Custom Loading:** supports uploading custom `.txt` files and `.json` dictionaries, while defaulting to `lepetitprince.txt` if no file is provided.

## Prerequisites

  * Python 3.6 or higher
  * Flask

## Installation

1.  Clone the repository or download the source code.
2.  Install the required dependencies:

<!-- end list -->

```bash
pip install flask
```

3.  Ensure your directory contains the following files:
      * `app.py` (The main application logic)
      * `lepetitprince.txt` (Optional: The default text to load on start)
      * `dictionary.json` (Optional: The default dictionary)

## Usage

1.  Run the application:

<!-- end list -->

```bash
python app.py
```

2.  Open your web browser and navigate to:

<!-- end list -->

```
http://localhost:5000
```

3.  **Reading:** Use the "Prev" and "Next" buttons or the page input field to navigate through the text fragments.
4.  **Translating:** Click on the outlined words (those found in your dictionary) to move them to the "Selected Words" sidebar.
5.  **Studying:** Click "Start Study Session" to hide the text and review the translations of your selected words. Click "Done/Close" to return to the text and reset the list.

## Data Formats

### Dictionary Format (.json)

The dictionary must be a valid JSON object. The application performs case-insensitive matching but prefers exact matches.

```json
{
    "rauf": "A male name",
    "rauf aliev": "A specific person's full name",
    "leesburg": "A town in Virginia, USA"
}
```

### Text Format (.txt)

Standard UTF-8 encoded plain text files are supported.

## Configuration

To change the default files loaded at startup, place files named `lepetitprince.txt` and `dictionary.json` in the root directory of the application.

## License

MIT License