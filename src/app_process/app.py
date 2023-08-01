import os

import streamlit as st

from generate import get_relevant, summary_query
from indexing_process.indexing import load_db

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
os.environ["OPENAI_ORGANIZATION"] = st.secrets["OPENAI_ORGANIZATION"]


def main():
    user_input = st.text_input("I'm looking for data about",
                               "number of installations per period in Facetune android")
    vectordb = load_db()
    retriever, docs = get_relevant(vectordb, user_input)
    response = summary_query(docs, user_input)
    st.write(response['output_text'])

    st.markdown(
        "##### :warning: If the answer contains query number without links, you can get the link by inserting the "
        "query number "
        "in the following link: https://redash.lightricks.com/queries/{query_number}")

    with st.expander("See sources"):
        st.write(response['input_documents'])

    with st.expander("See explanations"):
        st.write(response['intermediate_steps'])


if __name__ == "__main__":
    main()
