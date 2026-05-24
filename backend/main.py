import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
df = pd.read_csv(BASE_DIR / 'data' / 'T1.csv')

print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
print(df.head(10))

# first look at core columns
print("\nSample performance ratio calculation:")
df['performance'] = df['LV ActivePower (kW)'] / df['Theoretical_Power_Curve (KWh)']
print(df[['Date/Time', 'Wind Speed (m/s)', 'LV ActivePower (kW)', 'Theoretical_Power_Curve (KWh)', 'performance']].head(10))
