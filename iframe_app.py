import os
import streamlit as st
from streamlit.components.v1 import html

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

# Path to your React build
build_dir = os.path.join(os.path.dirname(__file__), "elite_chat_component", "frontend", "build")

# Create an iframe that points to a local HTML file
st.markdown("""
<div style="height: 800px; width: 100%;">
    <iframe src="http://localhost:8000" width="100%" height="800px" frameBorder="0"></iframe>
</div>
""", unsafe_allow_html=True)

st.markdown("""
## Instructions

To view the React component:

1. Open a new terminal window
2. Navigate to your build directory with:
   ```
   cd "/Users/huzaifaghori/Python Projects/streamlit component/elite_chat_component/frontend/build"
   ```
3. Start a simple HTTP server:
   ```
   python -m http.server
   ```
4. The React app should now be visible in the iframe above

This approach avoids module loading issues by serving your React app through a proper web server.
""")
