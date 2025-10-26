# library_min_rtt_analysis.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ast import literal_eval
from matplotlib import pyplot as plt


#Loading base file
base_file = 'traceroute_results.csv'
df = pd.read_csv(base_file)
#library_name, probes, rtts

# Get the number of nearby VPs, that have a higher than 5 ms min RTT to the library, per library (Scatter plot)
# Get the number of closeby VPs, that are 30 KMs away from the target location as min RTT -- next town (Scatter plot)
# Get the number of close VPs available per library (CDF)
# Get the number of libraries that failed to be geolocated correctly at all (Close VP RTT > 5 ms) and (far vp RTT - 14.75)/0.015 - distance > 30 KM) 
# or df['probes'] is empty -- Just a number
# Number of libraries with no replying IPs at all -- just a number

#Loading VP file
vp_file = 'vantage_point_results.csv'
df_vp = pd.read_csv(vp_file)
df_vp = df_vp[['Library','Nearby_Probes','Closest_Probes','Closest_Distances_KM']]

#Merge the dataframes on library_name and Library
df_merged = pd.merge(df, df_vp, left_on='library_name', right_on='Library', how='left')
df_merged.drop(columns=['Library'], inplace=True)

#Convert string representation of lists to actual lists and handle NaN values
df_merged['probes'] = df_merged['probes'].fillna('[]').apply(literal_eval)
df_merged['rtts'] = df_merged['rtts'].fillna('[]').apply(literal_eval)
df_merged['Nearby_Probes'] = df_merged['Nearby_Probes'].fillna('[]').apply(literal_eval)
df_merged['Closest_Probes'] = df_merged['Closest_Probes'].fillna('[]').apply(literal_eval)
df_merged['Closest_Distances_KM'] = df_merged['Closest_Distances_KM'].fillna('[]').apply(literal_eval)

#Save the merged dataframe
df_merged.to_csv('merged_traceroute_vp_results.csv', index=False)

#For each library, find the probes that are in df['probes'] and also in df['Nearby_Probes'] that have a value in df['rtts'], greater than 5 ms
#Also get the intersection of probes between df['probes'] and df['Closest_Probes']
def analyze_library(row):
    probes = row['probes']
    rtts = row['rtts']
    nearby_probes = row['Nearby_Probes']
    closest_probes = row['Closest_Probes']
    closest_distances = row['Closest_Distances_KM']
    
    # Probes with RTT > 5 ms
    high_rtt_probes = [probe for probe, rtt in zip(probes, rtts) if rtt > 5]
    high_rtt_count = len(set(high_rtt_probes) & set(nearby_probes))
    
    # Total probes that replied
    close_probes = [probe for probe, dist in zip(closest_probes, closest_distances)]
    close_probes_count = len(set(probes) & set(close_probes))
    
    return pd.Series({'High_RTT_Probes_Count': high_rtt_count,
                      'Close_Probes_Count': close_probes_count})

print("Analyzing libraries for high RTT and close probes...")
df_analysis = df_merged.apply(analyze_library, axis=1)

df_vp_analysis = pd.concat([df_merged, df_analysis], axis=1)

#Formula: rtt = 14.75 + 0.015 * distance_km
#=> distance_km = (rtt - 14.75) / 0.015

#For the probes that are both in df['probes'] and df['Closest_Probes'], 
# and the distance at the same index in df['Closest_Distances_KM'], 
# check if [(rtt - 14.75)/0.015] - distance > 30 KM or < 0 KM
def check_geolocation_failure(row):
    probes = row['probes']
    rtts = row['rtts']
    closest_probes = row['Closest_Probes']
    closest_distances = row['Closest_Distances_KM']
    nearby_probes = row['Nearby_Probes']
    
    failure_count = 0
    for probe, dist in zip(closest_probes, closest_distances):
        if probe in nearby_probes:
            continue
        if probe in probes:
            idx = probes.index(probe)
            rtt = rtts[idx]
            estimated_distance = (rtt - 14.75) / 0.015
            if estimated_distance - dist > 30 or estimated_distance < 0:
                failure_count += 1
                
    return failure_count
print("Checking for geolocation failures...")
df_vp_analysis['Geolocation_Failure_Count'] = df_vp_analysis.apply(check_geolocation_failure, axis=1)

#Sum the Geolocation_Failure_Count and High_RTT_Probes_Count for libraries with no replying IPs at all
no_reply_libraries = df_vp_analysis[(df_vp_analysis['probes'].apply(len) == 0) | (df_vp_analysis['High_RTT_Probes_Count'] + df_vp_analysis['Geolocation_Failure_Count'] >= df_vp_analysis['Closest_Probes'].apply(len))]
no_reply_count = len(no_reply_libraries)
print(f"Number of libraries with no replying IPs at all: {no_reply_count}")

# Save the final analysis dataframe
df_vp_analysis.to_csv('library_vp_analysis.csv', index=False)

# Diagrams and plots
#A CDF of number of High_RTT_Probes_Count and Geolocation_Failure_Count per library
plt.figure(figsize=(10, 6))

# Plot High_RTT_Probes_Count
data1 = df_vp_analysis['High_RTT_Probes_Count']
data1_sorted = np.sort(data1)
cdf1 = np.arange(1, len(data1_sorted)+1) / len(data1_sorted)
plt.plot(data1_sorted, cdf1, marker='.', linestyle='none', label='Nearby Probe Failures', color='blue')

# Plot Geolocation_Failure_Count
data2 = df_vp_analysis['Geolocation_Failure_Count']
data2_sorted = np.sort(data2)
cdf2 = np.arange(1, len(data2_sorted)+1) / len(data2_sorted)
plt.plot(data2_sorted, cdf2, marker='.', linestyle='none', label='Far Probe Failures', color='red')

plt.xlabel('Number of Probes')
plt.ylabel('CDF')
plt.title('CDF of Probe Failures')
plt.grid()
plt.legend()
plt.savefig('cdf_probe_failures.png')
plt.show()
#Just mention the max number of probes is 10

#CDF of len(df['probes']) per library amd len(df['Closest_Probes']) per library
plt.figure(figsize=(10, 6))
data = df_vp_analysis['probes'].apply(len)
data_sorted = np.sort(data)
cdf = np.arange(1, len(data_sorted)+1) / len(data_sorted)
plt.plot(data_sorted, cdf, marker='.', linestyle='none', color='green')

data2 = df_vp_analysis['Closest_Probes'].apply(len)
data2_sorted = np.sort(data2)
cdf2 = np.arange(1, len(data2_sorted)+1) / len(data2_sorted)
plt.plot(data2_sorted, cdf2, marker='.', linestyle='none', color='orange')
plt.xlabel('Number of Probes')
plt.ylabel('CDF')
plt.title('CDF of Number of Probes that Replied and All Selected Probes')
plt.grid()
plt.legend(['Probes', 'Closest Probes'])
plt.savefig('cdf_probes.png')
plt.show()


#CDF of % of items in df['Closest Probes'] that are also in df['Nearby Probes'] per library
plt.figure(figsize=(10, 6))
def compute_percentage(row):
    probes = row['Nearby_Probes']
    closest_probes = row['Closest_Probes']
    if len(closest_probes) == 0:
        return 0
    intersection_count = len(set(probes) & set(closest_probes))
    percentage = (intersection_count / len(closest_probes)) * 100
    return percentage

data = df_vp_analysis.apply(compute_percentage, axis=1)
data_sorted = np.sort(data)
cdf = np.arange(1, len(data_sorted)+1) / len(data_sorted)
plt.plot(data_sorted, cdf, marker='.', linestyle='none', color='purple')
plt.xlabel('Percentage Overlap Between Nearby and Total Number of Probes (%)')
plt.ylabel('CDF')
plt.title('CDF of Percentage Overlap Between Nearby and Total Number of Probes')
plt.grid()
plt.savefig('cdf_percentage_overlap_probes.png')
plt.show()
