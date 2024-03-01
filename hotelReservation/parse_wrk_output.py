import re
import sys
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

new_latency = dict()
req_type = ""

def parse_config_section(log_content):
    config_patterns = {
        'distribution': r"distribution:\s+(\w+)",
        'duration': r"duration:\s+(\d+)",
        'req_type': r"req_type:\s+(\w+)",
        'RPS': r"RPS:\s+(\d+)"
    }

    config_data = {}
    for key, pattern in config_patterns.items():
        match = re.search(pattern, log_content)
        if match:
            config_data[key] = match.group(1)
        else:
            config_data[key] = "Value not found"

    return config_data

def find_latency_value(pattern, log_content):
    match = re.search(pattern, log_content)
    if match:
        value, unit = match.groups()
        # Convert value to milliseconds if in seconds
        if unit == 's':
            return str(float(value) * 1000)  # Convert to milliseconds
        return value  # Already in milliseconds
    else:
        return "Value not found"

def parse_log_file(file_path, columns, rps_threshold):
    # Include unit in the regex to differentiate between ms and s
    latency_patterns = dict()
    # columns = ['avg', '50%', '99%', '99.9%', '99.99%']
    for col in columns:
        if col == 'avg':
            latency_patterns[col] = r"Latency\s+(\d+\.\d+)(ms|s)"
        elif col == '50%':
            latency_patterns[col] = r"50\.000%\s+(\d+\.\d+)(ms|s)"
        elif col == '99%':
            latency_patterns[col] = r"99\.000%\s+(\d+\.\d+)(ms|s)"
        elif col == '99.9%':
            latency_patterns[col] = r"99\.900%\s+(\d+\.\d+)(ms|s)"  
        elif col == '99.99%':
            latency_patterns[col] = r"99\.990%\s+(\d+\.\d+)(ms|s)"
        else:
            print(f"Unknown column: {col}")
            sys.exit(1)
    #  latency_patterns = {
    #     'avg': r"Latency\s+(\d+\.\d+)(ms|s)",
    #     '50%': ,
    #     '99%': r"99\.000%\s+(\d+\.\d+)(ms|s)",
    #     # '99.9%': r"99\.900%\s+(\d+\.\d+)(ms|s)",
    #     # '99.99%': r"99\.990%\s+(\d+\.\d+)(ms|s)"
    # }

    try:
        with open(file_path, 'r') as file:
            log_content = file.read()
    except Exception as e:
        print(f"Error opening file {file_path}: {e}")
        return
    
    
    config_data = parse_config_section(log_content)
    rps_value = int(config_data.get("RPS", 0))
    if rps_value <= rps_threshold:
        for key, pattern in latency_patterns.items():
            latency_value = find_latency_value(pattern, log_content)
            # print(f"key: {key}, latency_value: {latency_value}")
            if key not in new_latency:
                new_latency[key] = []
            new_latency[key].append(latency_value)

        global req_type
        req_type = config_data.get("req_type", "unknown")

        if "rps" not in new_latency:
            new_latency["rps"] = []
        new_latency["rps"].append(rps_value)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py '<pattern>'")
        sys.exit(1)

    rps_threshold = 1500
    print(f"NOTE: rps_threshold: {rps_threshold}")
    # columns = ['avg', '50%', '99%', '99.9%', '99.99%']
    columns = ['avg', '50%', '99%']
    # columns = ['avg', '50%']
    for pattern in sys.argv[1:]:
        for file_path in glob.glob(pattern):
            parse_log_file(file_path, columns, rps_threshold)


    df = pd.DataFrame(new_latency)
    
    # Convert all latency values to numeric, assuming non-numeric values are errors or 'Value not found'
    for col in columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Ensure 'rps' column is integer
    df['rps'] = pd.to_numeric(df['rps'], errors='coerce').astype(int)

    df.sort_values(by='rps', inplace=True)
    
    plt.figure(figsize=(10, 6))
    for column in columns:
        plt.plot(df['rps'], df[column], label=column, marker='o')

    plt.title(f'hotel reservatoin - {req_type}', fontsize=20)
    plt.xlabel('Requests per Second (RPS)', fontsize=20)
    plt.ylabel('Latency (ms)', fontsize=20)
    plt.xticks(fontsize=14)  # Set x-tick label fontsize
    plt.yticks(fontsize=14)  # Set y-tick label fontsize
    plt.legend(fontsize=14)
    plt.savefig(f'latency_{req_type}.png')
    plt.show()

    df.to_csv(f'latency_{req_type}.csv', index=False)
