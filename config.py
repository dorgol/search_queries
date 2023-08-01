import os
import streamlit as st
API_ENDPOINT = "https://api.openai.com/v1/chat/completions"
os.environ['REDASH_URL'] = 'https://redash.lightricks.com/queries'
model_name = 'gpt-4'
os.environ['OPENAI_API_KEY'] = st.secrets["OPENAI_API_KEY"]

chunk_size = 4000
chunk_overlap = 200
