
import streamlit as st
import os
from langchain.chains import GraphCypherQAChain
from langchain_community.graphs import Neo4jGraph
# Update the import for GoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAI
from langchain_community.llms import OpenAI

# --- INSTRUCTIONS ---
# 1. Install required libraries:
#    pip install streamlit langchain neo4j openai google-generativeai langchain-google-genai
# 2. Get your Neo4j credentials from Neo4j AuraDB.
# 3. Add your OpenAI or Google Generative AI API key.
# 4. Save this file as `streamlit_app.py` and run it from your terminal:
#    streamlit run streamlit_app.py
# --------------------

def setup_chain():
    """Initializes the Neo4j graph and the LangChain agent."""
    try:
        # Use Streamlit secrets for credentials in a deployed app, or environment variables
        neo4j_url = st.secrets["NEO4J_URL"] if "NEO4J_URL" in st.secrets else os.getenv("NEO4J_URL", "bolt://localhost:7687")
        neo4j_username = st.secrets["NEO4J_USERNAME"] if "NEO4J_USERNAME" in st.secrets else os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_password = st.secrets["NEO4J_PASSWORD"] if "NEO4J_PASSWORD" in st.secrets else os.getenv("NEO4J_PASSWORD", "your_password_here")

        # For Google Generative AI, set your API key in Streamlit secrets or as an environment variable
        # st.secrets["GOOGLE_API_KEY"] or os.getenv("GOOGLE_API_KEY")
        llm = GoogleGenerativeAI(model="gemini-pro", temperature=0)

        graph = Neo4jGraph(url=neo4j_url, username=neo4j_username, password=neo4j_password)
        graph.refresh_schema()

        # Create the GraphCypherQAChain with a custom prompt
        chain = GraphCypherQAChain.from_llm(
            llm=llm,
            graph=graph,
            verbose=False,
            cypher_prompt_template="""
            You are an expert in academic eligibility and a top-notch Neo4j developer.
            Your task is to convert user questions about student eligibility into optimized Cypher queries.
            You have access to the following node labels and relationships:
            - Node Labels: Student, Stream, Degree, Requirement, College, Country
            - Relationships: HAS_STREAM, ELIGIBLE_FOR, REQUIRES, OFFERS, LOCATED_IN

            Generate a single Cypher query for the user's question, without any other text.
            Question: {question}
            """,
        )
        return chain
    except Exception as e:
        st.error(f"Failed to connect to the knowledge graph. Please ensure your Neo4j database is running and credentials are correct. Error: {e}")
        return None

# --- STREAMLIT UI ---
st.set_page_config(page_title="Academic Advisor Bot")
st.title("🎓 Academic Advisor Bot")
st.markdown("Ask me questions about college and degree eligibility based on academic streams and location.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chain = setup_chain()
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I can help you find your academic path. How can I assist you today?"})

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What would you like to know?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get the response from the LLM chain
    if st.session_state.chain:
        with st.spinner('Thinking...'):
            try:
                response = st.session_state.chain.run(prompt)
                st.session_message = {"role": "assistant", "content": response}
                st.chat_message("assistant").markdown(response)
                st.session_state.messages.append(st.session_message)
            except Exception as e:
                error_message = f"I'm sorry, I couldn't process that query. An error occurred: {e}"
                st.error(error_message)
                st.session_message = {"role": "assistant", "content": error_message}
                st.session_state.messages.append(st.session_message)
    else:
        st.session_message = {"role": "assistant", "content": "The application could not connect to the database. Please check the setup and try again."}
        st.chat_message("assistant").markdown(st.session_message["content"])
        st.session_state.messages.append(st.session_message)
