# Import required libraries
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import glob
import os

# Set page configuration
st.set_page_config(
    page_title="Energy Consumption KPI Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add title and description
st.title("Energy Consumption KPI Dashboard")
st.markdown("Analysis of PJM's Regional Hourly Energy Consumption Data")

# Define a custom color scheme
COLOR_SCHEME = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
MAIN_COLOR = '#1f77b4'  # Primary color for single-color charts

# Function to load and preprocess data
@st.cache_data
def load_data():
    """
    Load and preprocess all energy consumption data files
    """
    # Get all CSV files in the data directory (excluding parquet files)
    data_files = glob.glob('data/*_hourly.csv')  # Changed pattern to match all _hourly.csv files
    
    # Debug information
    st.sidebar.write(f"Found {len(data_files)} data files")
    
    # Create empty list to store dataframes
    dfs = []
    
    # Load each file and append to list
    for file in data_files:
        try:
            # Read CSV and handle different column structures
            temp_df = pd.read_csv(file)
            
            # Debug information
            st.sidebar.write(f"Processing {os.path.basename(file)}")
            
            # Check if we need to fix column names
            if len(temp_df.columns) == 2:  # If file has exactly 2 columns
                temp_df.columns = ['Datetime', 'MW']  # Set standard column names
            elif any(col.endswith('_MW') for col in temp_df.columns):  # Handle pre-named columns
                mw_col = next(col for col in temp_df.columns if col.endswith('_MW'))
                temp_df = temp_df.rename(columns={mw_col: 'MW'})
                
            # Get the region name from the filename
            region = os.path.basename(file).split('_')[0].upper()  # Added .upper() for consistency
            
            # Rename the MW column to include region
            mw_col = 'MW' if 'MW' in temp_df.columns else temp_df.columns[1]
            temp_df = temp_df[['Datetime', mw_col]].copy()
            temp_df.columns = ['Datetime', f'{region}_MW']
            
            dfs.append(temp_df)
            
        except Exception as e:
            st.sidebar.warning(f"Could not load {file}: {str(e)}")
    
    # Show how many files were successfully loaded
    st.sidebar.write(f"Successfully loaded {len(dfs)} files")
    
    # Merge all dataframes on Datetime
    if dfs:
        df = dfs[0]
        for other_df in dfs[1:]:
            df = pd.merge(df, other_df, on='Datetime', how='outer')
    else:
        st.error("No data files could be loaded!")
        st.stop()
    
    # Process datetime and add time-based columns
    df['Datetime'] = pd.to_datetime(df['Datetime'])
    df['Hour'] = df['Datetime'].dt.hour
    df['Date'] = df['Datetime'].dt.date
    df['Month'] = df['Datetime'].dt.month
    df['Year'] = df['Datetime'].dt.year
    df['Day_of_week'] = df['Datetime'].dt.dayofweek
    
    return df

# Function to select region
def get_selected_region(df):
    # Get all columns that end with '_MW'
    region_columns = [col for col in df.columns if col.endswith('_MW')]
    # Remove '_MW' from names for display
    regions = [col.replace('_MW', '') for col in region_columns]
    
    selected_region = st.sidebar.selectbox(
        "Select Region",
        regions,
        index=0
    )
    
    return f"{selected_region}_MW"

# Load the data
try:
    df = load_data()
    selected_column = get_selected_region(df)
except FileNotFoundError:
    st.error("Error: No PJM data files found in the 'data' folder.")
    st.stop()

# Sidebar for date range selection
st.sidebar.header("Date Range Selection")
min_date = df['Date'].min()
max_date = df['Date'].max()

start_date = st.sidebar.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("End Date", max_date, min_value=min_date, max_value=max_date)

# Filter data based on date range
mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
filtered_df = df.loc[mask]

# Create three columns for KPI metrics
col1, col2, col3 = st.columns(3)

# KPI 1: Average Daily Consumption
with col1:
    avg_consumption = filtered_df[selected_column].mean()
    st.metric(
        label="Average Consumption (MW)",
        value=f"{avg_consumption:,.2f}"
    )

# KPI 2: Peak Consumption
with col2:
    peak_consumption = filtered_df[selected_column].max()
    st.metric(
        label="Peak Consumption (MW)",
        value=f"{peak_consumption:,.2f}"
    )

# KPI 3: Load Factor (Average/Peak ratio)
with col3:
    load_factor = (avg_consumption / peak_consumption) * 100
    st.metric(
        label="Load Factor (%)",
        value=f"{load_factor:.1f}%"
    )

# Create two columns for charts
chart_col1, chart_col2 = st.columns(2)

# Chart 1: Daily Consumption Trend
with chart_col1:
    st.subheader("Daily Consumption Trend")
    daily_consumption = filtered_df.groupby('Date')[selected_column].mean().reset_index()
    fig_daily = px.line(
        daily_consumption,
        x='Date',
        y=selected_column,
        title='Average Daily Energy Consumption',
        color_discrete_sequence=[MAIN_COLOR]
    )
    fig_daily.update_layout(
        yaxis_title="Megawatts (MW)",
        plot_bgcolor='white',
        paper_bgcolor='white',
        yaxis=dict(gridcolor='lightgray')
    )
    st.plotly_chart(fig_daily, use_container_width=True)

# Chart 2: Hourly Consumption Pattern
with chart_col2:
    st.subheader("Average Hourly Consumption Pattern")
    hourly_avg = filtered_df.groupby('Hour')[selected_column].mean().reset_index()
    fig_hourly = px.line(
        hourly_avg,
        x='Hour',
        y=selected_column,
        title='Average Hourly Consumption Pattern',
        markers=True,
        color_discrete_sequence=[MAIN_COLOR]
    )
    fig_hourly.update_layout(
        yaxis_title="Megawatts (MW)",
        plot_bgcolor='white',
        paper_bgcolor='white',
        yaxis=dict(gridcolor='lightgray')
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

# Additional Analysis Section
st.header("Additional Analysis")

# Chart 3: Monthly Box Plot
monthly_box = px.box(
    filtered_df,
    x='Month',
    y=selected_column,
    title='Monthly Consumption Distribution'
)
monthly_box.update_layout(
    xaxis_title="Month",
    yaxis_title="Megawatts (MW)"
)
st.plotly_chart(monthly_box, use_container_width=True)

# Chart 4: Day of Week Analysis
dow_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
dow_avg = filtered_df.groupby('Day_of_week')[selected_column].mean().reset_index()
dow_avg['Day'] = dow_avg['Day_of_week'].apply(lambda x: dow_names[x])

dow_chart = px.bar(
    dow_avg,
    x='Day',
    y=selected_column,
    title='Average Consumption by Day of Week'
)
dow_chart.update_layout(yaxis_title="Megawatts (MW)")
st.plotly_chart(dow_chart, use_container_width=True)

# Add year-over-year comparison if data spans multiple years
years = filtered_df['Year'].unique()
if len(years) > 1:
    st.subheader("Year-over-Year Comparison")
    yearly_avg = filtered_df.groupby('Year')[selected_column].mean().reset_index()
    yoy_chart = px.bar(
        yearly_avg,
        x='Year',
        y=selected_column,
        title='Average Annual Consumption'
    )
    yoy_chart.update_layout(yaxis_title="Megawatts (MW)")
    st.plotly_chart(yoy_chart, use_container_width=True)

# Footer with data insights
st.markdown("---")
st.markdown("### Key Insights")
st.markdown(f"""
- This dashboard analyzes energy consumption data for the selected PJM region
- Date range: {start_date} to {end_date}
- Key metrics include average consumption ({avg_consumption:,.2f} MW), peak demand ({peak_consumption:,.2f} MW), and load factor ({load_factor:.1f}%)
- The load factor indicates how effectively the electrical system is being utilized
- Daily and hourly trends help identify consumption patterns
- Monthly box plots reveal seasonal variations
- Day of week analysis shows weekday vs weekend patterns
""")

# Add data source information
st.markdown("---")
st.markdown("### Data Source")
st.markdown("Data provided by PJM Interconnection LLC. Multiple regions available for analysis.")