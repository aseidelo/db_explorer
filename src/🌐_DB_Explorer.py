import streamlit as st
import pandas as pd
from langchain_openai import ChatOpenAI
from db.db import Db
from llm import ContextManager


def status_card(main_text, secondary_text, status=False):
    with st.container(border=True):
        col1, col2, col3 = st.columns([4, 2, 1])
        with col1:
            st.write(main_text)
        with col2:
            st.caption(secondary_text)
        with col3:
            st.write('🟢' if status else '🔴')

def expander_card(main_text, content):
    with st.expander(main_text):
        st.write(content)

@st.dialog("Add database")
def dialog_add_db():
    col1, col2 = st.columns([2, 1])
    with col1:
        db_name = st.text_input("DB Name")
        db_endpoint = st.text_input("Endpoint")
    with col2:
        db_type = st.selectbox("Db type", ["postgres", "mysql", "sqlite"])
        db_port = st.number_input("Port", value=None, max_value=99999, step=1)
    col1, col2 = st.columns(2)
    with col1:
        db_user = st.text_input("User")
    with col2:
        db_password = st.text_input("Password", type="password")
    if st.button("Submit"):
        print(db_type, db_endpoint, db_port, db_name, db_user, db_password)
        db = Db(db_type, db_name, db_user, db_password, db_endpoint, db_port)
        st.session_state.db_connections[db.connection_url] = db
        st.rerun()

st.set_page_config(
    page_title="DB Explorer",
    page_icon="🌐",
)

if 'llm' not in st.session_state:
    st.session_state['llm'] = {
        **st.secrets.llm
    }

    st.session_state.llm['provider'] = 'openai'
    st.session_state.llm['is_connected'] = False

    try:

        llm = ChatOpenAI(
            **st.secrets.llm
        )

        # response = llm.invoke('oi')

        st.session_state.llm['instance'] = llm
        st.session_state.llm['is_connected'] = True
    except Exception as e:
        print (e)
        pass

if 'db_connections' not in st.session_state:
    st.session_state['db_connections'] = []

    for connection in st.secrets.connection:
        db = Db(**st.secrets.connection[connection])
        st.session_state.db_connections.append(db)

    print(st.session_state.db_connections)

if 'context_manager' not in st.session_state:
    llm = st.session_state.llm['instance']
    dbs = st.session_state.db_connections
    st.session_state['context_manager'] = ContextManager(llm, dbs)

with st.sidebar:
    # st.write("# 🌐 DB Explorer")    

    st.caption("LLM")
    status_card(
        st.session_state.llm['model'],
        st.session_state.llm['provider'],
        st.session_state.llm['is_connected']
    )
    st.caption("Databases")

    for db in st.session_state.db_connections:
        expander_card(f'{db.db_name}:{db.type}', db.short_description())

    # if st.button("Add database"):
    #     dialog_add_db()

question = st.chat_input("Ask something about your data")

if question:
    st.write(f'User: {question}')
    context_manager = st.session_state["context_manager"]

    agent_responses = context_manager.answer(
        question
    )
    
    for agent_response in agent_responses:
        st.write(f"{agent_response['speaker']}:")
        st.write(agent_response['speech'])
