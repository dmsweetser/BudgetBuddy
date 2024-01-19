import os
import json
import datetime
import csv
import matplotlib.pyplot as plt
import re
import pandas as pd
import seaborn as sns

# Constants
INPUT_DIRECTORY = "input"
OUTPUT_DIRECTORY = "output"
PROCESSED_FILE_PATH = "transactions.csv"
CONFIG_FILE = "config.json"
MULTIPLE_BUDGETS = True

def process_input_files(input_directory):
    """Processes files in the input directory and returns transactions."""
    transactions = []
    for filename in os.listdir(input_directory):
        file_path = os.path.join(input_directory, filename)
        if os.path.isfile(file_path) and file_path.endswith('.csv'):
            transactions.extend(read_csv(file_path))
    return transactions

def initialize_csv(file_path, fieldnames=["Date", "Description", "Amount", "Category"]):
    """Initializes a new CSV file with the given fieldnames."""
    if os.path.dirname(file_path) != '':
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Check if the file exists before creating it
    if not os.path.exists(file_path):
        with open(file_path, 'w', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

def write_csv(file_path, data):
    if len(data) > 0:
        """Writes the given data to a CSV file."""
        try:
            with open(file_path, 'a', newline='') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=data[0].keys())
                writer.writerows(data)
        except FileNotFoundError:
            print(f"File '{file_path}' not found. Initializing a new file...")
            initialize_csv(file_path)
            write_csv(file_path, data)

def read_csv(file_path):
    """Reads a CSV file and returns the data as a list of dictionaries."""
    try:
        with open(file_path, 'r') as csv_file:
            reader = csv.DictReader(csv_file)
            return list(reader)
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return []

def append_csv(file_path, data):
    """Appends the given data to a CSV file."""
    try:
        with open(file_path, 'a', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=data[0].keys())
            writer.writerows(data)
    except FileNotFoundError:
        print(f"File '{file_path}' not found. Initializing a new file...")
        initialize_csv(file_path)
        append_csv(file_path, data)

def merge_transactions(transactions):
    """Merges transactions with the same description and date but different amounts."""
    merged_transactions = []
    current_transaction = None

    for transaction in transactions:
        if not current_transaction or current_transaction['Date'] != transaction['Date'] or current_transaction['Description'] != transaction['Description']:
            if current_transaction and len(merged_transactions) > 0:
                last_transaction = merged_transactions[-1]
                cast_amount = abs(float(last_transaction['Amount']))
                combined_amount = cast_amount + abs(float(current_transaction['Amount']))
                last_transaction['Amount'] = str(combined_amount)
            elif current_transaction:
                merged_transactions.append({'Date': current_transaction['Date'], 'Description': current_transaction['Description'], 'Amount': abs(float(current_transaction['Amount'])), 'Category': current_transaction['Category']})
            current_transaction = transaction
            continue

        merged_transactions.append(transaction)

    if current_transaction and len(merged_transactions) > 0:
        last_transaction = merged_transactions[-1]
        cast_amount = abs(float(last_transaction['Amount']))
        combined_amount = cast_amount + abs(float(current_transaction['Amount']))
        last_transaction['Amount'] = str(combined_amount)

    for transaction in merged_transactions:
        transaction['Amount'] = str(abs(float(transaction['Amount'])))

    return merged_transactions

def categorize_transactions(transactions, keyword_mapping):
    """Categorizes transactions based on the given keyword mapping."""
    categorized_transactions = {category: [] for category in keyword_mapping}
    uncategorized_transactions = []

    for transaction in transactions:
        description = transaction.get('Description', '').lower()
        category = 'Uncategorized'
        keyword_used = None

        for key, values in keyword_mapping.items():
            for value in values:
                if re.search(r'\b{}\b'.format(value), description, re.IGNORECASE):
                    category = key
                    keyword_used = value
                    break

        if category == 'Ignore':
            continue

        if category not in categorized_transactions:
            categorized_transactions[category] = []

        transaction['Category'] = category
        categorized_transactions[category].append(transaction)
        uncategorized_transactions = [t for t in uncategorized_transactions if t != transaction]

    return categorized_transactions, uncategorized_transactions

def prompt_for_category(transaction, config, categorized_transactions):
    """Prompts the user to select a category for an uncategorized transaction."""
    print(f"\nUncategorized Transaction: {transaction['Description']} ({transaction['Amount']})")

    budget_categories = list(config["budget"].keys())
    categories = budget_categories + ['Ignore']

    while True:
        for i, category in enumerate(categories, start=1):
            print(f"{i}. {category}")

        try:
            user_input = int(input("\nChoose a category for the transaction (enter the number corresponding to the category): ")) - 1
            if 0 <= user_input < len(categories):
                selected_category = categories[user_input]
                if selected_category == 'Ignore':
                    print("Transaction marked as 'Ignore'. It won't be included in the budget.")
                elif selected_category in budget_categories:
                    config["keyword_mapping"].setdefault(selected_category, [])
                    transaction['Category'] = selected_category
                    if selected_category not in categorized_transactions:
                        categorized_transactions[selected_category] = []  # Ensure the category exists

                    # Check if the description is not already present in the category
                    if transaction['Description'] not in config["keyword_mapping"][selected_category]:
                        config["keyword_mapping"][selected_category].append(transaction['Description'])
                        categorized_transactions[selected_category].append(transaction)
                    else:
                        print("Duplicate description. This description is already associated with the selected category.")
                        continue  # Retry the loop

                else:
                    print("Invalid category. Please choose a valid category or 'Ignore'.")
                    continue  # Retry the loop

                break  # Exit the loop if a valid choice is made
            else:
                print("Invalid input. Please choose a valid category or 'Ignore'.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

def process_and_store_transactions(transactions, processed_file_path, categorized_transactions, uncategorized_transactions):
    """Processes and stores transactions in the given file path."""
    processed_data = []
    transactions_to_remove = []

    for transaction in transactions:
        date = transaction.get('Date', datetime.date.today().strftime("%Y-%m-%d"))
        description = transaction.get('Description', '')
        amount = float(transaction.get('Amount', 0))
        category = 'Uncategorized'

        for cat, transactions_list in categorized_transactions.items():
            for trans in transactions_list:
                if trans['Date'] == date and trans['Description'].lower() == description.lower():
                    category = cat
                    transaction['Category'] = category
                    transactions_to_remove.append(trans)
                    break

        if category == 'Uncategorized':
            uncategorized_transactions.append(transaction)

        processed_data.append({'Date': date, 'Description': description, 'Amount': -amount, 'Category': category})

    new_transactions = [trans for trans in transactions if trans not in transactions_to_remove]
    transactions.clear()
    transactions.extend(new_transactions)

    write_csv(processed_file_path, processed_data)  # Write processed_data directly

def calculate_budget_status(categorized_transactions, budget):
    """Calculates and displays the budget status."""
    total_spent = {category: sum([abs(float(transaction['Amount'])) for transaction in transactions]) for category, transactions in categorized_transactions.items()}
    total_budget = sum(budget.values()) if MULTIPLE_BUDGETS else sum(total_spent.values())

    budget_status = {category: {'budget': budget.get(category, 0), 'spent': total_spent[category], 'percentage_used': 0} for category in categorized_transactions.keys()}

    for category, status in budget_status.items():
        if status['budget'] > 0:
            status['percentage_used'] = (status['spent'] / status['budget']) * 100

    print("\nBudget Status:")
    for category, status in budget_status.items():
        print(f"{category}: Budget - ${format(status['budget'], ',.2f')}, Spent - ${format(status['spent'], ',.2f')}, Percentage Used - {status['percentage_used']:.2f}%")
        if status['spent'] > status['budget'] and status['budget'] > 0:
            print(f"Warning: You have exceeded the budget for this category by ${format(abs(status['spent'] - status['budget']), ',.2f')}")

    total_spent_formatted = format(sum(total_spent.values()), ',.2f')
    if MULTIPLE_BUDGETS:
        print("Total Budget:")
        for category, budget in budget.items():
            print(f"{category}: ${format(budget, ',.2f')}")
    else:
        print(f"Total Budget: ${total_budget}")
        print(f"Total Spent Across All Categories: ${total_spent_formatted}")

def save_results_as_image(categorized_transactions, budget_status, total_budget, output_directory):
    """Saves the results as an image in the given directory."""
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    image_filename = os.path.join(output_directory, f"budget_results_{current_datetime}.png")

    try:
        df = pd.concat([pd.DataFrame(transactions) for transactions in categorized_transactions.values()], axis=0)
        df.reset_index(inplace=True)  # Resetting index to use it as x-axis
        fig, ax = plt.subplots(figsize=(12, 8))
        sns.barplot(x=df.index, y='Amount', hue='Category', data=df)
        ax.set_title('Budget Status')
        ax.set_xlabel('Index')  # Setting the x-axis label to 'Index'
        ax.set_ylabel('Amount')
        plt.savefig(image_filename)
        print(f"\nResults saved as {image_filename}")
    except Exception as e:
        print(f"Error saving image: {e}")

def import_config(file_path):
    """Imports the config file in various formats."""
    try:
        with open(file_path, 'r') as file:
            if file.name.endswith('.csv'):
                return json.load(pd.read_csv(file))
            elif file.name.endswith('.json'):
                return json.load(file)
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return {}

def export_config(config, file_path):
    """Exports the config to various formats."""
    try:
        with open(file_path, 'w') as file:
            json.dump(config, file)
    except Exception as e:
        print(f"Error exporting config to '{file_path}': {e}")

def main():
    """Initializes the program and processes transactions."""
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "keyword_mapping": {
                "Food": ["grocery", "food", "supermarket"],
                "Transportation": ["gas", "petrol", "public transportation"]
            },
            "budget": {},
            "uncategorized_transactions": []
        }
        with open(CONFIG_FILE, 'w') as json_file:
            json.dump(default_config, json_file)

    config = import_config(CONFIG_FILE)

    initialize_csv(PROCESSED_FILE_PATH)

    existing_transactions = read_csv(PROCESSED_FILE_PATH)  # Read existing transactions

    transactions = process_input_files(INPUT_DIRECTORY)

    # Filter out transactions that already exist in processed file
    transactions = [t for t in transactions if t not in existing_transactions]

    categorized_transactions, uncategorized_transactions = categorize_transactions(transactions, config["keyword_mapping"])

    for category, transactions in categorized_transactions.items():
        if len(transactions) > 0:
            processed_data = merge_transactions(transactions)
            process_and_store_transactions(processed_data, PROCESSED_FILE_PATH, categorized_transactions, uncategorized_transactions)

    calculate_budget_status(categorized_transactions, config["budget"])
    save_results_as_image(categorized_transactions, config["budget"], sum(config["budget"].values()), OUTPUT_DIRECTORY)

    if len(uncategorized_transactions) > 0:
        for transaction in uncategorized_transactions:
            prompt_for_category(transaction, config, categorized_transactions)
        export_config(config, CONFIG_FILE)

if __name__ == "__main__":
    main()