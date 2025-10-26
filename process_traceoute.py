#!/usr/bin/env python3
"""
Extract minimum RTT from RIPE Atlas traceroute JSON using Sagan library.
"""

import json
import sys
from ripe.atlas.sagan import TracerouteResult
import os
from tqdm import tqdm
import pandas as pd


def extract_min_rtt(json_file_path):
    """
    Extract the minimum RTT from a traceroute JSON file.
    
    Args:
        json_file_path: Path to the traceroute JSON file
        
    Returns:
        float: Minimum RTT in milliseconds, or None if no valid RTT found
    """
    try:
        # Read the JSON file
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        # Handle both single result and array of results
        if isinstance(data, list):
            results = data
        else:
            results = [data]
        
        rtts = []
        probes = []
        d_a = None
        
        # Process each traceroute result
        for result_data in results:
            # Parse with Sagan
            result = TracerouteResult(result_data)
            d_a = result.destination_address
            if result.destination_ip_responded:
                rtts.append(result.last_median_rtt)
                probes.append(result.probe_id)

        return rtts, probes, d_a
    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found.", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error processing traceroute: {e}", file=sys.stderr)
        return None


def main():

    directory = 'Infer_Data_2'
    output_dict = {'library_name': [],'probes': [], 'rtts': []}

    for folder in os.listdir(directory):
        folder_path = os.path.join(directory, folder)
        if os.path.isdir(folder_path):
            current_rtts = []
            current_probes = []
            for filename in os.listdir(folder_path):
                if filename.endswith(".json"):
                    json_file = os.path.join(folder_path, filename)
                    rtts, probes, d_a = extract_min_rtt(json_file)
                    # Process the extracted data as needed
                    current_rtts.append(rtts)
                    current_probes.append(probes)
            # Assuming rtt values match to probes by index, iterate over them so that for duplicate probes we get the min rtt for those probes
            probe_rtt_map = {}
            for rtt_list, probe_list in zip(current_rtts, current_probes):
                for rtt, probe in zip(rtt_list, probe_list):
                    if probe in probe_rtt_map:
                        probe_rtt_map[probe] = min(probe_rtt_map[probe], rtt)
                    else:
                        probe_rtt_map[probe] = rtt
            #Get the list of probes and rtts
            probes_final = list(probe_rtt_map.keys())
            rtts_final = [probe_rtt_map[probe] for probe in probes_final]

            output_dict['library_name'].append(folder)
            output_dict['probes'].append(probes_final)
            output_dict['rtts'].append(rtts_final)


    # Convert the output dictionary to a pandas DataFrame
    df = pd.DataFrame(output_dict)

    # Save the DataFrame to a CSV file
    output_file = 'traceroute_results.csv'
    df.to_csv(output_file, index=False)

if __name__ == "__main__":
    main()
