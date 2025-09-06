import os
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# =========================
# Setup
# =========================
load_dotenv()
st.set_page_config(page_title="Elite Auto Sales Academy", page_icon="🤖", layout="wide")

# Hide Streamlit chrome — UI is entirely your index.html
st.markdown("""
<style>
#MainMenu, header, footer, .stDeployButton, .stToolbar, .stDecoration, #stDecoration {display:none;}
.main .block-container {padding-top:0; padding-bottom:0; max-width:100%;}
div[data-testid="stSidebar"] {display:none;}
</style>
""", unsafe_allow_html=True)

# First try the simple.html file which doesn't require React build
index_path = os.path.join(os.path.dirname(__file__), "elite_chat_component", "frontend", "simple.html")

# If that doesn't exist, fall back to the regular build index
if not os.path.exists(index_path):
    build_path = os.path.join(os.path.dirname(__file__), "elite_chat_component", "frontend", "build")
    index_path = os.path.join(build_path, "index.html")
    
    # If that doesn't exist either, check the frontend directory
    if not os.path.exists(index_path):
        index_path = os.path.join(os.path.dirname(__file__), "elite_chat_component", "frontend", "index.html")
        if not os.path.exists(index_path):
            st.error("Could not find any suitable HTML file. Please check your file structure.")
            st.stop()

# Read and display the HTML file
try:
    with open(index_path, "r", encoding="utf-8") as file:
        html_content = file.read()
        # Render the HTML content
        components.html(html_content, height=800, scrolling=True)
except Exception as e:
    st.error(f"Error reading the index.html file: {str(e)}")
    st.stop()
