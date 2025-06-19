import pandas as pd
import os

# Write a script that merges two CSV files 
script_dir = os.path.dirname(os.path.abspath(__file__))
path0 = os.path.join(script_dir, "..", "data", "raw", "articles.csv")
path1 = os.path.join(script_dir, "..", "data", "raw", "new-articles.csv")
path2 = os.path.join(script_dir, "..", "data", "raw", "new-articles2.csv")
path3 = os.path.join(script_dir, "..", "data", "raw", "new-articles3.csv")
path4 = os.path.join(script_dir, "..", "data", "raw", "new-articles4.csv")
output_file = os.path.join(script_dir, "..", "data", "raw", "merged-articles.csv")

df0 = pd.read_csv(path0)
df1 = pd.read_csv(path1)
df2 = pd.read_csv(path2)
df3 = pd.read_csv(path3)    
df4 = pd.read_csv(path4)

merged_df = pd.concat([df0, df1, df2, df3, df4], ignore_index=True)
merged_df.to_csv(output_file, index=False)
