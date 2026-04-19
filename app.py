import streamlit as st
import pandas as pd
import json
import time
import io
from scraper import scrape_spokeo

st.set_page_config(page_title="Spokeo Automator", layout="wide")
st.title("Spokeo Contact Scraper")

st.markdown("""
This tool uses your local Chrome profile to safely scrape contact data from Spokeo. 
**Please ensure all background Chrome processes are fully closed via the Windows System Tray before running.**
""")

input_mode = st.radio("Input Mode", ["Single Address", "Bulk JSON"])

if input_mode == "Single Address":
    col1, col2 = st.columns(2)
    with col1:
        db_id = st.text_input("Database ID (optional)")
        address = st.text_input("Address", value="1255 WESTSHORE DR")
    with col2:
        city = st.text_input("City", value="CUMMING")
        state = st.text_input("State", value="GA")

    if st.button("Run Scraper"):
        with st.spinner("Scraping Spokeo..."):
            try:
                results = scrape_spokeo(address, city, state)
                
                # Append the DB ID to the results
                for r in results:
                    r['id'] = db_id
                    
                if not results:
                    st.warning("No contact data found for this address.")
                else:
                    st.success("Successfully scraped data!")
                    st.json(results)
                    
                    # Convert to dataframe for easy copy/export
                    df = pd.DataFrame(results)
                    st.dataframe(df)
            except Exception as e:
                st.error(str(e))

elif input_mode == "Bulk JSON":
    st.markdown("Paste a JSON array of objects. Each object must have `id`, `address`, `city`, and `state`.")
    sample_json = '''[
  {
    "id": "101",
    "address": "1255 WESTSHORE DR",
    "city": "CUMMING",
    "state": "GA"
  },
  {
    "id": "102",
    "address": "100 MAIN ST",
    "city": "ATLANTA",
    "state": "GA"
  }
]'''
    json_input = st.text_area("JSON Input", value=sample_json, height=300)
    
    if st.button("Run Bulk Job"):
        try:
            data = json.loads(json_input)
            
            if not isinstance(data, list):
                st.error("Input must be a JSON array (list) of objects.")
                st.stop()
                
            all_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, row in enumerate(data):
                # Pause between multiple requests to respect rate limits
                if idx > 0:
                    status_text.text(f"Sleeping for 3 seconds before next request...")
                    time.sleep(3)
                
                addr = row.get('address', '')
                city = row.get('city', '')
                state = row.get('state', '')
                db_id = row.get('id', '')
                
                status_text.text(f"Scraping {addr}, {city}, {state}...")
                
                try:
                    res = scrape_spokeo(addr, city, state)
                    if res:
                        for r in res:
                            r['id'] = db_id
                            all_results.append(r)
                except Exception as e:
                    st.error(f"Error on {addr}: {str(e)}")
                    # Stop the loop if Chrome is locked, no point in continuing
                    if "PROFILE LOCKED" in str(e):
                        break
                
                progress_bar.progress((idx + 1) / len(data))
                
            status_text.text("Bulk job finished!")
            
            if all_results:
                st.success(f"Scraped {len(all_results)} contact records!")
                df = pd.DataFrame(all_results)
                
                # Reorder columns to put ID first
                cols = ['id'] + [c for c in df.columns if c != 'id']
                df = df[cols]
                
                st.dataframe(df)
                
                # Export options
                col1, col2 = st.columns(2)
                
                # Excel Export
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                
                with col1:
                    st.download_button(
                        label="Download as Excel (.xlsx)",
                        data=buffer.getvalue(),
                        file_name="spokeo_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                # JSON Export
                with col2:
                    st.download_button(
                        label="Download as JSON",
                        data=json.dumps(all_results, indent=2),
                        file_name="spokeo_results.json",
                        mime="application/json"
                    )
            else:
                st.warning("Job completed but no contact data was found.")
                
        except json.JSONDecodeError:
            st.error("Invalid JSON format. Please check your syntax.")
