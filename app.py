import streamlit as st
import pandas as pd
from google import genai
import json
from datetime import datetime, timedelta

# 1. Setup Page Configuration & API Client
st.set_page_config(page_title="AI Smart Inventory", page_icon="🍏", layout="wide")
st.title("🍏 AI Smart Visual Inventory & Expiry Tracker")

# Initialize Gemini Client (Replace with your actual API key)
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY, http_options={"api_version":"v1"})

# Initialize a simple session database to keep track of items across clicks
if "inventory" not in st.session_state:
    st.session_state.inventory = []

# 2. Main Sidebar layout for uploading images
with st.sidebar:
    st.header("📸 Upload Receipt or Fridge Photo")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Image Preview", use_container_width=True)
        analyze_button = st.button("🤖 Analyze with AI", type="primary")

# 3. AI Processing Logic
if uploaded_file and analyze_button:
    with st.spinner("AI is inspecting your items..."):
        try:
            # Read the uploaded image bytes
            image_bytes = uploaded_file.read()
            
            # Construct a robust prompt asking for raw, clean JSON data
            prompt = """
            Analyze this image of groceries or a grocery receipt. 
            Identify all food/grocery items visible. 
            Estimate a reasonable shelf-life expiry duration in days for each item starting from today.
            
            Respond ONLY with a valid JSON array of objects. Do not include markdown formatting like ```json.
            Example format:
            [
                {"item": "Milk", "days_to_expire": 5},
                {"item": "Apples", "days_to_expire": 14}
            ]
            """
            
            # Request analysis from Gemini 1.5 Flash
            response = client.models.generate_content(
                model="gemini-2.5-flash-latest",
                contents=[
                    genai.types.Part.from_bytes(data=image_bytes, mime_type=uploaded_file.type),
                    prompt
                ]
            )
            
            # Parse the text response into Python objects
            raw_text = response.text.strip()
            parsed_items = json.loads(raw_text)
            
            # Add dates to the AI data and append to our database
            today = datetime.today()
            for entry in parsed_items:
                expiry_date = today + timedelta(days=int(entry["days_to_expire"]))
                st.session_state.inventory.append({
                    "Item Name": entry["item"],
                    "Days Remaining": int(entry["days_to_expire"]),
                    "Expiry Date": expiry_date.strftime("%Y-%m-%d")
                })
            st.success("Successfully added items to inventory!")
            
        except Exception as e:
            st.error(f"Error parsing AI response. Please try again. Technical details: {e}")

# 4. Main Dashboard Display
st.header("📋 Current Pantry & Refrigerator Inventory")

if st.session_state.inventory:
    # Convert data into a Pandas DataFrame for easy viewing
    df = pd.DataFrame(st.session_state.inventory)
    
    # Sort inventory so items expiring the soonest appear at the very top
    df = df.sort_values(by="Days Remaining")
    
    # Visual Polish: Highlight rows based on expiration status
    def highlight_expiry(row):
        days = row["Days Remaining"]
        if days <= 2:
            return ['background-color: #ffcccc; color: black'] * len(row)  # Red Alert
        elif days <= 5:
            return ['background-color: #ffe6cc; color: black'] * len(row)  # Orange Warning
        return ['background-color: #e6ffcc; color: black'] * len(row)      # Green Safe

    styled_df = df.style.apply(highlight_expiry, axis=1)
    
    # Render the interactive data table
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Simple Reset button to clear data for a new live demo
    if st.button("🧹 Clear Inventory"):
        st.session_state.inventory = []
        st.rerun()
else:
    st.info("Your inventory is currently empty. Upload an image in the sidebar to populate data!")
