import streamlit as st
from streamlit_gsheets import GSheetsConnection


# Create a connection object.
conn = st.connection("gsheets", type=GSheetsConnection)

df = conn.read(
    spreadsheet= "https://docs.google.com/spreadsheets/d/1P1ntjpaQC5pPX_3j-m3GScgJRGqhHalNpumwmOVpeXc/edit?gid=0#gid=0",
    worksheet="Sheet1",
    ttl="10m",
    usecols=[0, 1],
    nrows=3,
)

# Print results.
for row in df.itertuples():
    st.write(f"{row.name} has a :{row.pet}:")
