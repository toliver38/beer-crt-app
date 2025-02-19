# beer-crt-app

A simple menu app for a bar to display in the style of a CRT monitor. Created for Lucky Anchor Alehouse in Deptford.

## Features

- Display active beers on the main menu.
- Admin panel to manage beers (add, remove, restore).
- Inline editing of beer details via AJAX.
- Webhook support for external beer list updates.
- Basic authentication for admin panel access.

## Setup

### Prerequisites

- Python 3.x
- pip (Python package installer)
- SQLite

### Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/toliver38/beer-crt-app.git
    cd beer-crt-app
    ```

2. Create and activate a virtual environment:

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required packages:

    ```sh
    pip install -r requirements.txt
    ```

4. Create a `.env` file in the project root directory and set the admin credentials:

    ```sh
    cp example.env .env
    ```

    Edit the `.env` file and set the `ADMIN_USER` and `ADMIN_PASS` values.

5. Create an `example.json` file in the project root directory with sample beers data:

    ```sh
    cp example.json.example example.json
    ```

### Running the App

1. Initialize the database:

    ```sh
    python app.py
    ```

    This will create the `beers.db` SQLite database and populate it with sample data from `example.json`.

2. Run the Flask app:

    ```sh
    python app.py
    ```

3. Open your web browser and navigate to `http://127.0.0.1:5000` to view the beer menu.

4. To access the admin panel, navigate to `http://127.0.0.1:5000/admin` and log in with the credentials set in the `.env` file.

## Usage

### Admin Panel

- **Add New Beer**: Fill out the form and submit to add a new beer to the menu.
- **Remove Beer**: Click the "Remove" button next to a beer to mark it as inactive.
- **Restore Removed Beers**: Use the search form to find and restore removed beers.
- **Inline Editing**: Click the "Edit" button next to a beer to enable inline editing. Make changes and click "Save" to update the beer details.

### Webhooks

The app supports webhooks for external beer list updates. The webhook endpoint is `/webhook` and accepts JSON payloads with the following structure:

- **Add Beer**:

    ```json
    {
        "action": "added",
        "brewery": "Brewery Name",
        "beer": "Beer Name",
        "style": "Beer Style",
        "abv": "ABV",
        "price_half": "Price (1/2)",
        "price_two_third": "Price (2/3)",
        "price_pint": "Price (Pint)",
        "display_order": 1,
        "category": "Category",
        "type": "Draft"
    }
    ```

- **Remove Beer**:

    ```json
    {
        "action": "removed",
        "beer_id": 1
    }
    ```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
