import re
import sys
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import subprocess

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
        
        #########################################
        pattern = r"Requests/sec:\s*(\d+\.\d+)"
        match = re.search(pattern, wrklog_file_read)
        if match:
            tput = float(match.group(1))
            print("Requests per second:", tput)
        else:
            print("Pattern not found")
            assert False
        #########################################
        
        cluster = wrk_config["cluster"]
        print(wrk_config)
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
                print(f"target_metric: {target_metric}, latency_value: {latency_value}")
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
                match = re.match(r"\s*(\d+\.\d+)\s+(\d+\.\d+)", line)
                if match:
                    value, percentile = match.groups()
                    cdf_data.append((float(value), float(percentile)))
    return cdf_data


def find_and_process_wrklog_files(base_directory):
    wrklog_files = glob.glob(f'{base_directory}/**/*.wrklog', recursive=True)
    for file in wrklog_files:
        print(file)
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
        print(wrk_config)
        parse_latency_stat_in_wrklog_file(wrklog_path, wrk_config, latency_metrics, latency_dict, stat_dict)
    print("latency_dict")
    for key, value in latency_dict.items():
        print(f"{key}: {value}")
    print("stat_dict")
    for key, value in stat_dict.items():
        print(f"{key}: {value}")
    # stat_dict[routing_rule][cluster][rps][percentile] = latency_value
    color_dict = {"SLATE": "blue", "WATERFALL": "red", "WATERFALL2": "red", "REMOTE": "green", "LOCAL": "orange"}
    
    # 1
    # cluster_map = dict()
    # cid = 0
    # for wrk_config in wrk_config_list:
    #     if wrk_config['cluster'] not in cluster_map:
    #         cluster_map[wrk_config['cluster']] = cid
    #         cid += 1
    
    # 2
    
    cluster_map = {"west":0, "central":1, "south":2, "east":3}
    # cluster_map = {"west":0, "east":1}
    
    print("cluster_map", cluster_map)
    
    for wrk_config in wrk_config_list:
        wrk_config['cluster_id'] = cluster_map[wrk_config['cluster']]
        
    # sorted_wrk_config_list = sorted(wrk_config_list, key=lambda d: d['cluster'])
    sorted_wrk_config_list = sorted(wrk_config_list, key=lambda d: d['cluster_id'])
    for wrk_config in sorted_wrk_config_list:
        print(f"sorted_wrk_config_list: , {wrk_config['cluster']}, {wrk_config['cluster_id']}")
        
    fig, axs = plt.subplots(1, len(cluster_map), figsize=(5*len(cluster_map), 5))
    fig.suptitle(' ', fontsize=30)
    # fig.suptitle('Latency CDF', fontsize=20)
    label_set = set()
    for wrk_config in sorted_wrk_config_list:
        df = pd.DataFrame(wrk_config["percentile_data"], columns=['Value', 'Percentile'])
        df['Percentile'] *= 100
        title = f"{wrk_config['cluster']}, {wrk_config['RPS']} RPS"
        label = f"{wrk_config['routing_rule']}-{wrk_config['req_type']}"
        if label not in label_set:
            label_set.add(label)
        else:
            label = None
        axs[cluster_map[wrk_config['cluster']]].plot(df['Value'], df['Percentile'], label=label)
        # axs[cluster_map[wrk_config['cluster']]].plot(df['Value'], df['Percentile'], label=label, color=color_dict[wrk_config['routing_rule']])
        # axs[cluster_map[wrk_config['cluster']]].plot(df['Value'], df['Percentile'], color=color_dict[wrk_config['routing_rule']])
        
        text_to_display = wrk_config["routing_rule"] + "\n"
        for percentile in latency_metrics:
            number = str(int(stat_dict[wrk_config['routing_rule']][str(wrk_config['RPS'])][wrk_config['cluster']][percentile]))
            text_to_display += f"{percentile}:{number}\n"
        if wrk_config['routing_rule'] == 'SLATE':
            axs[cluster_map[wrk_config['cluster']]].text(0.25, 0.0, text_to_display, transform=axs[cluster_map[wrk_config['cluster']]].transAxes, ha='center', color=color_dict[wrk_config['routing_rule']])
        else:
            axs[cluster_map[wrk_config['cluster']]].text(0.8, 0.0, text_to_display, transform=axs[cluster_map[wrk_config['cluster']]].transAxes, ha='center', color=color_dict[wrk_config['routing_rule']])
            
        axs[cluster_map[wrk_config['cluster']]].set_title(title, fontsize=20)
        # axs[cluster_map[wrk_config['cluster']]].legend(fontsize=12)
        for ax in axs:
            ax.set_xlabel('Latency (ms)', fontsize=20)
            ax.set_ylabel('Percentile (%)', fontsize=20)
            ax.tick_params(axis='x', labelsize=15)
            ax.tick_params(axis='y', labelsize=15)
            # ax.set_xticks(fontsize=15)  # Set x-tick label fontsize
            ax.set_yticks(np.arange(0,101,25))  # Set y-tick label fontsize
            ax.axhline(y=50, color='r', linestyle='--', linewidth=0.5, alpha=0.5)
            ax.axhline(y=90, color='r', linestyle='--', linewidth=0.5, alpha=0.5)
            ax.axhline(y=99, color='r', linestyle='--', linewidth=0.5, alpha=0.5)
    
    for i in range(len(axs)):
        # Assuming all subplots share the same legend
        handles, labels = axs[i].get_legend_handles_labels()
        if len(labels) > 0:
            break
    assert len(labels) > 0
    print(labels)
    # plt.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3, fontsize=12)
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5,1.0), ncol=4, fontsize=16)
    # plt.legend(handles, labels, loc='upper center', fontsize=12)
    plt.subplots_adjust(bottom=0.2)  # You might need to adjust this value
    plt.tight_layout()
    app_name = sys.argv[1].split('/')[0]
    experiment_tag = sys.argv[1].split('/')[-2]
    figure_file_path = f'{base_directory}/cdf.pdf'
    plt.savefig(figure_file_path)
    print(f"Figure saved as {figure_file_path}")
    plt.show()