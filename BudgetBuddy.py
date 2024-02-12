import os
import json
import datetime
import csv
import matplotlib.pyplot as plt

# Constants
INPUT_DIRECTORY = "input"
OUTPUT_DIRECTORY = "output"
PROCESSED_FILE_PATH = "transactions.csv"
CONFIG_FILE = "config.json"

def initialize_csv(file_path, fieldnames=["Date", "Description", "Amount", "Category"]):
    """Initializes a new CSV file with the given fieldnames."""
    with open(file_path, 'w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

def write_csv(file_path, data):
    """Writes the given data to a CSV file."""
    with open(file_path, 'a', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=data[0].keys())
        writer.writerows(data)

def read_csv(file_path):
    """Reads a CSV file from the input directory and returns the data as a list of dictionaries."""
    with open(file_path, 'r') as csv_file:
        reader = csv.DictReader(csv_file)
        if "Transaction Date" in reader.fieldnames:
            # Handle the first source data format
            transactions = [{'Date': row['Transaction Date'], 'Description': row['Description'], 'Amount': row['Amount']} for row in reader]
        elif "Date" in reader.fieldnames:
            # Handle the second source data format
            transactions = [{'Date': row['Date'], 'Description': row['Original Description'], 'Amount': row['Amount']} for row in reader]
        else:
            raise ValueError("Unable to determine the format of the CSV file.")

        return transactions

def append_csv(file_path, data):
    """Appends the given data to a CSV file."""
    with open(file_path, 'a', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=data[0].keys())
        writer.writerows(data)

def categorize_transactions(transactions, keyword_mapping):
    """Categorizes transactions based on the given keyword mapping."""
    categorized_transactions = {category: [] for category in keyword_mapping}

    for transaction in transactions:
        description = transaction.get('Description', '').lower()
        category = 'Uncategorized'
        keyword_used = None

        for key, values in keyword_mapping.items():
            for value in values:
                if value.lower() in description:
                    category = key
                    keyword_used = value
                    break

        if category == 'Ignore':
            continue

        categorized_transactions[category].append({'transaction': transaction, 'keyword_used': keyword_used})

    return categorized_transactions

def prompt_for_category(transaction, config):
    """Prompts the user to select a category for an uncategorized transaction."""
    print(f"\nUncategorized Transaction: {transaction['Description']} ({transaction['Amount']})")
    categories = list(config["keyword_mapping"].keys()) + ['Create New Category']

    print("Choose a category for the transaction:")
    for i, category in enumerate(categories, start=1):
        print(f"{i}. {category}")

    while True:
        try:
            choice = int(input("Enter the number corresponding to the category: "))
            if 0 <= choice <= len(categories):
                selected_category = categories[choice - 1]
                if selected_category == 'Create New Category':
                    new_category = input("Enter the new category name: ")
                    config["keyword_mapping"][new_category] = [transaction['Description']]
                    with open(CONFIG_FILE, 'w') as json_file:
                        json.dump(config, json_file, indent=2)
                    return new_category
                elif selected_category not in ['Ignore']:
                    config["keyword_mapping"][selected_category].append(transaction['Description'])
                    with open(CONFIG_FILE, 'w') as json_file:
                        json.dump(config, json_file, indent=2)
                    return selected_category
            else:
                print("Invalid choice. Please enter a valid number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def process_and_store_transactions(transactions, processed_file_path, categorized_transactions):
    """Processes and stores transactions in the given file path."""
    processed_data = []

    for transaction in transactions:
        date = transaction.get('Date', datetime.date.today().strftime("%Y-%m-%d"))
        description = transaction.get('Description', '')
        amount = float(transaction.get('Amount', 0))
        category = 'Uncategorized'

        for cat, transactions_list in categorized_transactions.items():
            for trans in transactions_list:
                if trans['transaction']['Description'].lower() == description.lower() and abs(trans['transaction']['Amount'] - amount) < 0.01:
                    category = cat  
                    break

        transaction['Category'] = category
        processed_data.append({'Date': date, 'Description': description, 'Amount': -amount, 'Category': category})

    print("Processed Data:", processed_data)  # Debugging print statement
    write_csv(processed_file_path, processed_data)

def calculate_budget_status(categorized_transactions, budget):
    """Calculates and displays the budget status."""

    print (categorized_transactions)
    
    total_spent = {category: sum([abs(float(transaction['Amount'])) for transaction in transactions]) for category, transactions in categorized_transactions.items()}
    total_budget = sum(budget.values())
    total_spent_all_categories = sum(total_spent.values())

    budget_status = {category: {'budget': budget.get(category, 0), 'spent': total_spent[category], 'percentage_used': 0} for category in categorized_transactions.keys()}

    for category, status in budget_status.items():
        if status['budget'] > 0:
            status['percentage_used'] = (status['spent'] / status['budget']) * 100

    print("\nBudget Status:")
    for category, status in budget_status.items():
        print(f"{category}: Budget - ${format(status['budget'], ',.2f')}, Spent - ${format(status['spent'], ',.2f')}, Percentage Used - {status['percentage_used']:.2f}%")
        if status['spent'] > status['budget']:
            print(f"Warning: You have exceeded the budget for this category by ${format(abs(status['spent'] - status['budget']), ',.2f')}")

    total_spent_formatted = format(total_spent_all_categories, ',.2f')
    print("\nTotal Budget:")
    print(f"Total Budget: ${format(total_budget, ',.2f')}")
    print(f"Total Spent Across All Categories: ${total_spent_formatted}")

def save_results_as_image(categorized_transactions, budget_status, total_budget, total_spent_all_categories, output_directory):
    """Saves the results as an image in the given directory."""
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    image_filename = os.path.join(output_directory, f"budget_results_{current_datetime}.png")

    plt.figure(figsize=(12, 8))

    # Check if categorized_transactions is not empty
    if categorized_transactions:
        categories = list(categorized_transactions.keys())
        non_empty_categories = [cat for cat in categories if categorized_transactions[cat]]  # Check if each category has transactions

        if non_empty_categories:
            num_categories = len(non_empty_categories)

            for idx, category in enumerate(non_empty_categories):
                transactions = categorized_transactions[category]
                total_spent = sum(abs(transaction['Amount']) for transaction in transactions)

                ax = plt.subplot2grid((1, num_categories), (0, idx))
                ax.barh(range(len(transactions)), [abs(x['Amount']) for x in transactions], align='left', color='g')
                ax.set_xlabel('Total Spent')
                ax.set_title(f'Spending for {category}')
                ax.tick_params(axis='y', labelsize=8)

        else:
            print("No transactions found for any category. Unable to generate image.")
            return
    else:
        print("No categorized transactions found. Unable to generate image.")
        return

    plt.figtext(0.5, 0.01, f"Total Spent: ${total_spent_all_categories}", ha="center")
    plt.figtext(0.5, 0.99, f"Total Budget: ${total_budget}", ha="center")

    plt.tight_layout()
    plt.savefig(image_filename)
    print(f"\nResults saved as {image_filename}")

def main():
    """Initializes the program and processes transactions."""
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "keyword_mapping": {
                "Food": ["grocery", "food", "supermarket"],
                "Transportation": ["gas", "petrol", "public transportation"],
                "Uncategorized": []
            },
            "budget": {
                "Food": 300.00,
                "Transportation": 150.00
            }
        }
        with open(CONFIG_FILE, 'w') as json_file:
            json.dump(default_config, json_file, indent=2)

    config = json.load(open(CONFIG_FILE))

    initialize_csv(PROCESSED_FILE_PATH)

    # Loop through all files in the input directory
    for filename in os.listdir(INPUT_DIRECTORY):
        if filename.endswith(".csv"):
            input_file_path = os.path.join(INPUT_DIRECTORY, filename)
            transactions = read_csv(input_file_path)
            print("Transactions loaded from", input_file_path)
            print("Transactions:", transactions)

            categorized_transactions = categorize_transactions(transactions, config["keyword_mapping"])
            print("Categorized Transactions:", categorized_transactions)

            for category, transactions in categorized_transactions.items():
                if len(transactions) > 0:
                    process_and_store_transactions(transactions, PROCESSED_FILE_PATH, categorized_transactions)

    calculate_budget_status(categorized_transactions, config["budget"])
    save_results_as_image(categorized_transactions, config["budget"], sum(config["budget"].values()), sum([sum([abs(float(transaction['Amount'])) for transaction in transactions]) for transactions in categorized_transactions.values()]), OUTPUT_DIRECTORY)

    # Print contents of the processed file
    print("Contents of the processed file:")
    with open(PROCESSED_FILE_PATH, 'r') as processed_file:
        print(processed_file.read())

if __name__ == "__main__":
    main()