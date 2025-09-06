import os
import streamlit as st
import streamlit.components.v1 as components

# =========================
# Setup
# =========================
st.set_page_config(page_title="Elite Auto Sales Academy", page_icon="🤖", layout="wide")

# Hide Streamlit chrome — UI is entirely your index.html
st.markdown("""
<style>
#MainMenu, header, footer, .stDeployButton, .stToolbar, .stDecoration, #stDecoration {display:none;}
.main .block-container {padding-top:0; padding-bottom:0; max-width:100%;}
div[data-testid="stSidebar"] {display:none;}
</style>
""", unsafe_allow_html=True)

# Path to your React build directory
build_dir = os.path.join(os.path.dirname(__file__), "elite_chat_component", "frontend", "build")
build_index = os.path.join(build_dir, "index.html")

if not os.path.exists(build_index):
    st.error(f"Could not find build index.html at {build_index}")
    st.stop()

# Read the build index.html file
try:
    with open(build_index, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Modify paths to be relative (from absolute paths starting with /)
    html_content = html_content.replace('src="/', 'src="./elite_chat_component/frontend/build/')
    html_content = html_content.replace('href="/', 'href="./elite_chat_component/frontend/build/')
    
    # Display the HTML component
    components.html(html_content, height=800, scrolling=True)
except Exception as e:
    st.error(f"Error loading React build: {str(e)}")
