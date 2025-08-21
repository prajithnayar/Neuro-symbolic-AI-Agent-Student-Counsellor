# streamlit_app.py
import streamlit as st
# RuleDatabase and LLMAgent classes are assumed to be defined in the environment
# from rule_database import RuleDatabase
# from llm_agent import LLMAgent
import os

st.title("CBSE High School Education Consultant")
st.write("Get college and subject eligibility based on your academic profile and explore college options with AI.")

st.header("Enter Your Academic Information")

col1, col2 = st.columns(2)

with col1:
    st.subheader("CBSE Details")
    student_aggregate_percentage = st.number_input("CBSE Aggregate Percentage (%)", min_value=0.0, max_value=100.0, value=75.0, step=0.1)
    student_completed_cbse = st.checkbox("Completed CBSE 12th?", value=True)

    st.subheader("Subject Grades (Percentage)")
    student_grade_math = st.number_input("Math Percentage", min_value=0.0, max_value=100.0, value=75.0, step=0.1)
    student_grade_physics = st.number_input("Physics Percentage", min_value=0.0, max_value=100.0, value=75.0, step=0.1)
    student_grade_chemistry = st.number_input("Chemistry Percentage", min_value=0.0, max_value=100.0, value=75.0, step=0.1)


with col2:
    st.subheader("Additional Grades")
    student_grade_biology = st.number_input("Biology Percentage", min_value=0.0, max_value=100.0, value=75.0, step=0.1)
    student_grade_computer_science = st.number_input("Computer Science Percentage", min_value=0.0, max_value=100.0, value=75.0, step=0.1)


    st.subheader("Standardized Tests")
    student_taken_jee = st.checkbox("Taken JEE Main?", value=False)
    student_jee_main_percentile = st.number_input("JEE Main Percentile", min_value=0.0, max_value=100.0, value=0.0, step=0.1, disabled=not student_taken_jee)

    student_taken_neet = st.checkbox("Taken NEET?", value=False)
    student_neet_score = st.number_input("NEET Score", min_value=0, value=0, step=1, disabled=not student_taken_neet) # Assuming score, not percentage

    student_taken_sat_act = st.checkbox("Taken SAT/ACT?", value=False)
    student_sat_score = st.number_input("SAT Score", min_value=400, max_value=1600, value=400, step=10, disabled=not student_taken_sat_act)
    student_act_score = st.number_input("ACT Score", min_value=1, max_value=36, value=1, step=1, disabled=not student_taken_sat_act) # Added ACT input


st.header("Ask the AI Consultant")
student_query = st.text_area("Enter your questions about colleges, subjects, or admissions:", "Suggest some good engineering colleges in India based on my profile.")

if st.button("Get Consultation"):
    # Collect student facts
    student_facts = {
        "student_aggregate_percentage": student_aggregate_percentage,
        "student_completed_cbse": student_completed_cbse,
        "student_grade_math": student_grade_math,
        "student_grade_physics": student_grade_physics,
        "student_grade_chemistry": student_grade_chemistry,
        "student_grade_biology": student_grade_biology,
        "student_grade_computer_science": student_grade_computer_science,
        "student_taken_jee": student_taken_jee,
        "student_jee_main_percentile": student_jee_main_percentile,
        "student_taken_neet": student_taken_neet,
        "student_neet_score": student_neet_score,
        "student_taken_sat_act": student_taken_sat_act,
        "student_sat_score": student_sat_score,
        "student_act_score": student_act_score,
    }

    st.subheader("Consultation Results")
    try:
        # Initialize RuleDatabase and query eligibility
        # Replace with your Neo4j Aura connection details and secure secrets handling
        # In Streamlit Cloud, use st.secrets
        neo4j_uri = st.secrets["NEO4J_URI"]
        neo4j_user = st.secrets["NEO4J_USER"]
        neo4j_password = st.secrets["NEO4J_PASSWORD"]

        db = RuleDatabase(neo4j_uri, neo4j_user, neo4j_password)
        # Assuming rules are already populated in the database
        # If not, you would call db.populate_rules(eligibility_rules) here,
        # but this might be better done as a separate setup step or on app startup.

        eligibility_results = db.query_eligibility(student_facts)
        db.close()

        st.write("### Eligibility Based on Rules:")
        if eligibility_results:
            for result in eligibility_results:
                st.write(f"- **{result['conclusion']}** (Rule: {result['rule_id']}: {result['description']})")
        else:
            st.write("No specific eligibility conclusions found based on the provided rules and your profile.")

    except Exception as e:
        st.error(f"Error querying eligibility rules: {e}")
        eligibility_results = None # Ensure eligibility_results is defined even on error


    try:
        # Initialize LLMAgent and get college info
        # Replace with your OpenAI API key and secure secrets handling
        # In Streamlit Cloud, use st.secrets
        openai_api_key = st.secrets["OPENAI_API_KEY"]
        llm_agent = LLMAgent(openai_api_key)

        with st.spinner("Getting AI insights..."):
            llm_response = llm_agent.get_college_info(student_query, eligibility_results)

        st.write("### AI Consultant Response:")
        st.write(llm_response)

    except Exception as e:
        st.error(f"Error getting AI consultation: {e}")
