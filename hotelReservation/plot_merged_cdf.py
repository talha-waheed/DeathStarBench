import re
import sys
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import subprocess
import itertools

req_type = ""

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

def regex_pattern(latency_metrics):
    latency_patterns = dict()
    for metric in latency_metrics:
        if metric == 'avg':
            latency_patterns[metric] = r"Latency\s+(\d+\.\d+)(ms|s)"
        elif metric == '50%':
            latency_patterns[metric] = r"50\.000%\s+(\d+\.\d+)(ms|s)"
        elif metric == '99%':
            latency_patterns[metric] = r"99\.000%\s+(\d+\.\d+)(ms|s)"
        elif metric == '99.9%':
            latency_patterns[metric] = r"99\.900%\s+(\d+\.\d+)(ms|s)"  
        elif metric == '99.99%':
            latency_patterns[metric] = r"99\.990%\s+(\d+\.\d+)(ms|s)"
        else:
            print(f"Unknown metric: {metric}")
            sys.exit(1)
    return latency_patterns

def get_real_rps_tput():
    tput = r"Requests/sec:\s*(\d+\.\d+)" 
    return tput

def parse_latency_stat_in_wrklog_file(wrklog_path, wrk_config, latency_metrics, latency_dict, stat_dict, rps_thr=99999):
    latency_patterns = regex_pattern(latency_metrics)
    with open(wrklog_path, 'r') as file:
        wrklog_file_read = file.read()
        
        pattern = r"reconnect_socket"
        match = re.search(pattern, wrklog_file_read)
        if match:
            print("WARNING: reconnect_socket exists")

        
        #########################################
        pattern = r"Requests/sec:\s*(\d+\.\d+)"
        match = re.search(pattern, wrklog_file_read)
        if match:
            tput = float(match.group(1))
            print(f"{wrk_config['routing_rule']}, {wrk_config['cluster']}, {wrk_config['req_type']}, {wrk_config['RPS']}, Actual tput: {tput}, Gap: {int(float(wrk_config['RPS']) - tput)}")
        else:
            print("Pattern not found")
            print(wrklog_path)
            assert False
        #########################################
        
        cluster = wrk_config["cluster"]
        # print(wrk_config)
        # rps_value = int(wrk_config[f"{cluster}_RPS"])
        rps_value = int(wrk_config[f"RPS"])
        if rps_value <= rps_thr:
            latency_dict["rps"].append(rps_value)
            latency_dict["mode"].append(wrk_config["mode"])
            latency_dict["routing_rule"].append(wrk_config["routing_rule"])
            latency_dict["cluster"].append(wrk_config["cluster"])
            latency_dict["tput"].append(tput)
            
            if wrk_config["routing_rule"] not in stat_dict:
                stat_dict[wrk_config["routing_rule"]] = dict()
            if str(rps_value) not in stat_dict[wrk_config["routing_rule"]]:
                stat_dict[wrk_config["routing_rule"]][str(rps_value)] = dict()
            if wrk_config["cluster"] not in stat_dict[wrk_config["routing_rule"]][str(rps_value)]:
                stat_dict[wrk_config["routing_rule"]][str(rps_value)][wrk_config["cluster"]] = dict()
                
            for target_metric, pattern in latency_patterns.items():
                latency_value = find_latency_value(pattern, wrklog_file_read)
                # print(f"target_metric: {target_metric}, latency_value: {latency_value}")
                if target_metric not in latency_dict:
                    latency_dict[target_metric] = []
                try:
                    stat_dict[wrk_config["routing_rule"]][str(rps_value)][wrk_config["cluster"]][target_metric] = float(latency_value)
                except Exception as e:
                    print(f"Error: {e}")
                    print(f"target_metric: {target_metric}, latency_value: {latency_value}")
                    print(wrklog_path)
                    print()
                    assert False
                latency_dict[target_metric].append(latency_value)
        
def find_and_process_wrklog_files(base_directory):
    wrklog_files = glob.glob(f'{base_directory}/**/*.wrklog', recursive=True)
    return wrklog_files

#####################################################################################################

def parse_wrk_config(wrklog_path):
    wrk_config = dict()
    lines = open(wrklog_path, 'r').readlines()
    i = 0
    while i < len(lines):
        if lines[i].strip() == "-- start of config --":
            i += 1
            while True:
                if lines[i].strip() == "-- end of config --":
                    break
                try:
                    key = lines[i].strip().split(',')[0]
                    value = lines[i].strip().split(',')[1]
                except Exception as e:
                    print(f"Error: {e}")
                    print(lines[i])
                    exit()
                wrk_config[key] = value
                i += 1
        i += 1
    return wrk_config
        

def extract_cdf_data(wrklog_path):
    with open(wrklog_path, 'r') as file:
        # Flag to indicate if we are in the "Detailed Percentile spectrum" section
        in_cdf_section = False
        cdf_data = []
        for line in file:
            if "Detailed Percentile spectrum:" in line:
                in_cdf_section = True
                continue
            if in_cdf_section:
                if "----" in line:
                    break  # End of the CDF section
                # Extract the relevant data using regular expression
                match = re.match(r"\s*(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+)", line)
                if match:
                    value, percentile, total_count = match.groups()
                    cdf_data.append((float(value), float(percentile), int(total_count)))
    return cdf_data


def find_and_process_wrklog_files(base_directory):
    wrklog_files = glob.glob(f'{base_directory}/**/*.wrklog', recursive=True)
    # for file in wrklog_files:
    #     print(file)
    return wrklog_files


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <base_directory> ")
        sys.exit(1)
    wrk_config_list = list()
    base_directory = sys.argv[1]
    wrklog_files = find_and_process_wrklog_files(base_directory)
    for wrklog_path in wrklog_files:
        wrk_config = parse_wrk_config(wrklog_path)
        wrk_config["percentile_data"] = extract_cdf_data(wrklog_path)
        wrk_config_list.append(wrk_config)
    stat_dict = dict()
    # latency_metrics = ['avg', '50%', '99%', '99.9%', '99.99%']
    latency_metrics = ['avg', '50%', '99%']
    latency_dict = dict()
    latency_dict["mode"] = []
    latency_dict["cluster"] = []
    latency_dict["rps"] = []
    latency_dict["routing_rule"] = []
    latency_dict["tput"] = []
    for wrklog_path in wrklog_files:
        wrk_config = parse_wrk_config(wrklog_path)
        # print(wrk_config)
        parse_latency_stat_in_wrklog_file(wrklog_path, wrk_config, latency_metrics, latency_dict, stat_dict)
    # print("latency_dict")
    # for key, value in latency_dict.items():
    #     print(f"{key}: {value}")
    # print("stat_dict")
    # for key, value in stat_dict.items():
    #     print(f"{key}: {value}")
    
    color_dict = {"SLATE": "blue", "WATERFALL": "red", "WATERFALL2": "red", "REMOTE": "green", "LOCAL": "orange"}
    cluster_map = {"west":0, "central":1, "south":2, "east":3}
    # cluster_map = {"west":0, "east":1}
    print("cluster_map", cluster_map)
    for wrk_config in wrk_config_list:
        wrk_config['cluster_id'] = cluster_map[wrk_config['cluster']]
    # sorted_wrk_config_list = sorted(wrk_config_list, key=lambda d: d['cluster'])
    sorted_wrk_config_list = sorted(wrk_config_list, key=lambda d: d['cluster_id'])
    # for wrk_config in sorted_wrk_config_list:
    #     print(f"sorted_wrk_config_list: {wrk_config['cluster']}, {wrk_config['cluster_id']}")
    
    # #1f77b4, #ff7f0e, #2ca02c, #d62728, #9467bd, #8c564b, #e377c2, #7f7f7f, #bcbd22, #17becf.
    
    # req_type_color_dict = {"user": "#1f77b4", "recommend": "#ff7f0e", "search": "#2ca02c", "reserve": "#d62728"}
    
    latency = dict()
    count = dict()
    for wrk_config in sorted_wrk_config_list:
        percentile_df = pd.DataFrame(wrk_config["percentile_data"], columns=['Value', 'Percentile', 'TotalCount'])
        percentile_df['Percentile'] *= 100
        routing_rule = wrk_config["routing_rule"]
        if 'req_type' in wrk_config:
            if wrk_config['routing_rule'] == "WATERFALL2":
                wrk_config['routing_rule'] = "WATERFALL"
            key = f"{wrk_config['routing_rule']}-{wrk_config['req_type']}"
            # else:
            #     key = f"{wrk_config['routing_rule']}-{wrk_config['req_type']}-cap{wrk_config['capacity']})"
        else:
            assert False
        for index, row in percentile_df.iterrows():
            if key not in latency:
                latency[key] = []
                count[key] = []
            latency[key].append(row['Value'])
            count[key].append(int(row['TotalCount']))
            
    plt.figure(figsize=(5, 4))
    latency = dict(sorted(latency.items()))
    for key in latency.keys():
        # print(f"key: {key}")
        weighted_latencies = np.repeat(latency[key], count[key])
        sorted_data = np.sort(weighted_latencies)
        cdf = np.arange(1, len(sorted_data)+1) / len(sorted_data)
        # plt.step(sorted_data, cdf, where="post", color=color_dict[key], label=key)
        # plt.plot(sorted_data, cdf, color=color_dict[key], label=key)
        if "SLATE" in key:
            linestyle = '-'
        else:
            if "800" in key:
                linestyle = '--'
            else:
                linestyle = ':'
        plt.plot(sorted_data, cdf, linestyle=linestyle, label=key, linewidth=1.2)
        # plt.plot(sorted_data, cdf, linestyle=linestyle, label=key, color=req_type_color_dict[key.split("-")[1]])
    plt.title('Hotel reservation', fontsize=16)
    plt.xlabel('Latency (ms)', fontsize=12)
    plt.ylabel('CDF', fontsize=12)
    plt.grid(True)
    plt.legend(fontsize=8)
    plt.savefig(f'{base_directory}/merged_cdf.pdf')
    print(f"output pdf: {base_directory}/merged_cdf.pdf")
    plt.show()
            
            
    # merged_latency = list(itertools.chain.from_iterable(merged_latency))
    # merged_latency.sort()
    # cdf = np.arange(1, len(merged_latency)+1) / len(merged_latency)
    # plt.figure(figsize=(8, 4))
    # plt.step(merged_latency, cdf, where="post", label="CDF", color='blue')
    # plt.title('Cumulative Distribution Function')
    # plt.xlabel('Value')
    # plt.ylabel('CDF')
    # plt.grid(True)
    # plt.legend()
    # plt.savefig('cdf.pdf')
    # plt.show()
    