import openai
import os

class LLMAgent:
    def __init__(self, api_key):
        self.client = openai.OpenAI(api_key=api_key)

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
        system_message = (
            "You are an AI education consultant for CBSE high schoolers. "
            "Your role is to provide helpful and relevant information about colleges, subjects, and admission processes. "
            "Use the provided eligibility results to inform your response, but also use your general knowledge to answer broader questions. "
            "Keep your responses encouraging and informative."
        )

        user_message = f"Student query: {student_query}"
        if eligibility_results:
            eligibility_text = "\nBased on the information provided, the student appears to be eligible for the following:\n"
            for result in eligibility_results:
                eligibility_text += f"- {result['conclusion']} (Rule: {result['rule_id']}: {result['description']})\n"
            user_message += eligibility_text
            system_message += "\nConsider the following eligibility results when formulating your response:" + eligibility_text


        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", # Or another suitable model
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content

        except openai.APIError as e:
            print(f"OpenAI API error: {e}")
            return "Sorry, I'm having trouble connecting to the AI service right now."
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return "An unexpected error occurred while processing your request."
