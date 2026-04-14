import streamlit as st

from ui.topograma import render_topograma

st.set_page_config(page_title="PlaniTC_v2", layout="wide")

def main():
    st.title("PlaniTC_v2")
    tabs = st.tabs(["Topograma"])

    with tabs[0]:
        render_topograma()

if __name__ == "__main__":
    main()
