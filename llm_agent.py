# llm_agent.py
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import os
import base64
import json

class LLMAgent:
    def __init__(self, project_id, location, credentials_json_base64):
        try:
            # Decode the base64 credentials JSON
            credentials_json = base64.b64decode(credentials_json_base64).decode('utf-8')
            credentials_info = json.loads(credentials_json)

            # Initialize Vertex AI with credentials
            vertexai.init(project=project_id, location=location, credentials=self._create_credentials(credentials_info))

            # Initialize the Generative Model
            self.model = GenerativeModel("gemini-1.5-flash-001") # You can choose a different model

        except Exception as e:
            print(f"Failed to initialize Vertex AI or model: {e}")
            # In a real Streamlit app, you might want to raise an exception
            # or set a flag to indicate that the LLM is not available.
            self.model = None
            self._initialization_error = str(e)


    def _create_credentials(self, credentials_info):
        # This is a simplified way to create credentials from a dict for initialization
        # For more robust handling in different environments, consider google.oauth2.service_account.Credentials
        from google.oauth2 import service_account
        return service_account.Credentials.from_service_account_info(credentials_info)


    def get_college_info(self, student_query, eligibility_results=None):
        """
        Interacts with the LLM to get college information based on student query and eligibility.

        Args:
            student_query (str): The student's question or request.
            eligibility_results (list, optional): A list of eligible conclusions from the symbolic logic.
                                                  Defaults to None.

        Returns:
            str: The LLM's generated response.
        """
        if not self.model:
            return f"AI service is not available due to an initialization error: {self._initialization_error}"

        system_instruction = (
            "You are an AI education consultant for CBSE high schoolers. "
            "Your role is to provide helpful and relevant information about colleges, subjects, and admission processes. "
            "Use the provided eligibility results to inform your response, but also use your general knowledge to answer broader questions. "
            "Keep your responses encouraging and informative."
        )

        user_message_parts = [
             Part.from_text(system_instruction),
             Part.from_text(f"Student query: {student_query}")
        ]

        if eligibility_results:
            eligibility_text = "\nBased on the information provided, the student appears to be eligible for the following:\n"
            for result in eligibility_results:
                eligibility_text += f"- {result['conclusion']} (Rule: {result['rule_id']}: {result['description']})\n"
            user_message_parts.append(Part.from_text("Consider the following eligibility results when formulating your response:" + eligibility_text))


        try:
            response = self.model.generate_content(
                user_message_parts,
                generation_config={
                    "max_output_tokens": 500,
                    "temperature": 0.7,
                },
            )
            return response.text

        except Exception as e:
            print(f"Vertex AI error: {e}")
            return f"Sorry, I'm having trouble connecting to the AI service right now: {e}"

# Example Usage (requires Google Cloud project, Vertex AI enabled, and credentials)
# In a Streamlit app, these would come from st.secrets
# project_id = "your-gcp-project-id"
# location = "your-gcp-region" # e.g., "us-central1"
# credentials_json_base64 = "your_base64_encoded_service_account_json"

# if project_id and location and credentials_json_base64:
#      llm_agent = LLMAgent(project_id, location, credentials_json_base64)
#      if llm_agent.model:
#          student_query = "What are good engineering colleges in India?"
#          sample_eligibility = [
#              {"rule_id": "SS_001", "description": "Eligibility for Engineering (India)...", "conclusion": "eligible_for_engineering_india"},
#          ]
#          llm_response = llm_agent.get_college_info(student_query, sample_eligibility)
#          print("\nLLM Response:")
#          print(llm_response)
#      else:
#          print("LLM Agent could not be initialized.")
# else:
#     print("Google Cloud credentials not found. Skipping LLM interaction.")
