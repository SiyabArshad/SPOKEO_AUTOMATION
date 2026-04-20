import streamlit as st
import json
import time
import io
import csv
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
        zipcode = st.text_input("Zipcode", value="30041")

    if st.button("Run Scraper"):
        with st.spinner("Scraping Spokeo..."):
            try:
                results = scrape_spokeo(address, city, state, zipcode)
                
                # Append the DB ID to the results
                for r in results:
                    r['id'] = db_id
                    
                if not results:
                    st.warning("No contact data found for this address.")
                else:
                    st.success("Successfully scraped data!")
                    
                    # Reorder keys to put 'id' first
                    ordered_results = []
                    for r in results:
                        new_r = {'id': r['id']}
                        new_r.update(r)
                        ordered_results.append(new_r)
                    
                    # Display Table
                    st.subheader("Data Table")
                    st.dataframe(ordered_results, use_container_width=True)
                    
                    # Download Buttons
                    col_dl1, col_dl2 = st.columns(2)
                    
                    # CSV generation
                    output = io.StringIO()
                    keys = ordered_results[0].keys()
                    dict_writer = csv.DictWriter(output, fieldnames=keys)
                    dict_writer.writeheader()
                    dict_writer.writerows(ordered_results)
                    
                    with col_dl1:
                        st.download_button(
                            label="📥 Download as CSV (Excel)",
                            data=output.getvalue(),
                            file_name="spokeo_single_result.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col_dl2:
                        st.download_button(
                            label="📥 Download as JSON",
                            data=json.dumps(ordered_results, indent=2),
                            file_name="spokeo_single_result.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    
                    # Copyable JSON block
                    st.subheader("Raw JSON (Click copy icon in top right)")
                    st.code(json.dumps(ordered_results, indent=2), language="json")
                    
            except Exception as e:
                st.error(str(e))

elif input_mode == "Bulk JSON":
    st.markdown("Paste a JSON array of objects. Each object must have `id`, `address`, `city`, `state`, and `zipcode`.")
    sample_json = '''[
  {
    "id": "101",
    "address": "1255 WESTSHORE DR",
    "city": "CUMMING",
    "state": "GA",
    "zipcode": "30041"
  },
  {
    "id": "102",
    "address": "100 MAIN ST",
    "city": "ATLANTA",
    "state": "GA",
    "zipcode": "30303"
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
                zipcode = str(row.get('zipcode', ''))
                db_id = row.get('id', '')
                
                status_text.text(f"Scraping {addr}, {city}, {state} {zipcode}...")
                
                try:
                    res = scrape_spokeo(addr, city, state, zipcode)
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
                
                # Reorder dict keys to put 'id' first
                ordered_results = []
                for r in all_results:
                    new_r = {'id': r['id']}
                    new_r.update(r)
                    ordered_results.append(new_r)
                    
                st.dataframe(ordered_results)
                
                col1, col2 = st.columns(2)
                
                # CSV Export instead of Pandas/Excel
                output = io.StringIO()
                if ordered_results:
                    keys = ordered_results[0].keys()
                    dict_writer = csv.DictWriter(output, fieldnames=keys)
                    dict_writer.writeheader()
                    dict_writer.writerows(ordered_results)
                
                with col1:
                    st.download_button(
                        label="Download as CSV (Excel)",
                        data=output.getvalue(),
                        file_name="spokeo_results.csv",
                        mime="text/csv"
                    )
                
                with col2:
                    st.download_button(
                        label="Download as JSON",
                        data=json.dumps(ordered_results, indent=2),
                        file_name="spokeo_results.json",
                        mime="application/json"
                    )
            else:
                st.warning("Job completed but no contact data was found.")
                
        except json.JSONDecodeError:
            st.error("Invalid JSON format. Please check your syntax.")
