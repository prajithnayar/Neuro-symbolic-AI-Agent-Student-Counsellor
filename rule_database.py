# Define RuleDatabase class
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

class RuleDatabase:
    def __init__(self, uri, user, password):
        self._driver = None
        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
        except Exception as e:
            print(f"Failed to create the Neo4j driver: {e}")

    def close(self):
        if self._driver:
            self._driver.close()

    def clear_rules(self):
        with self._driver.session() as session:
            session.execute_write(self._delete_all_rules)

    @staticmethod
    def _delete_all_rules(tx):
        result = tx.run("MATCH (n) DETACH DELETE n")
        print(f"Cleared existing data: {result.consume().counters}")

    def populate_rules(self, rules_dict):
        with self._driver.session() as session:
            for category, rules in rules_dict.items():
                for rule_data in rules:
                    session.execute_write(self._create_rule_nodes, rule_data)

    @staticmethod
    def _create_rule_nodes(tx, rule_data):
        rule_id = rule_data["rule_id"]
        description = rule_data["description"]
        conclusion_name = rule_data["conclusion"]

        # Create Rule node
        tx.run("MERGE (r:Rule {rule_id: $rule_id}) "
               "SET r.description = $description",
               rule_id=rule_id, description=description)

        # Create Conclusion node and LEADS_TO relationship
        tx.run("MERGE (conc:Conclusion {name: $conclusion_name})",
               conclusion_name=conclusion_name)
        tx.run("MATCH (r:Rule {rule_id: $rule_id}) "
               "MATCH (conc:Conclusion {name: $conclusion_name}) "
               "MERGE (r)-[:LEADS_TO]->(conc)",
               rule_id=rule_id, conclusion_name=conclusion_name)

        # Recursively create ConditionGroup and Condition nodes
        def create_condition_nodes(tx, parent_node_id, parent_node_label, conditions):
            if "type" in conditions: # It's a ConditionGroup
                group_type = conditions["type"]
                group_id = f"{parent_node_id}_{group_type}_{hash(frozenset(str(c) for c in conditions['rules']))}" # Simple unique ID
                tx.run("MERGE (cg:ConditionGroup {group_id: $group_id}) "
                       "SET cg.type = $group_type",
                       group_id=group_id, group_type=group_type)

                if parent_node_label == "Rule":
                     tx.run("MATCH (r:Rule {rule_id: $parent_node_id}) "
                            "MATCH (cg:ConditionGroup {group_id: $group_id}) "
                            "MERGE (r)-[:HAS_CONDITION_GROUP]->(cg)",
                            parent_node_id=parent_node_id, group_id=group_id)
                elif parent_node_label == "ConditionGroup":
                     tx.run("MATCH (parent_cg:ConditionGroup {group_id: $parent_node_id}) "
                            "MATCH (child_cg:ConditionGroup {group_id: $group_id}) "
                            "MERGE (parent_cg)-[:HAS_MEMBER_CONDITION]->(child_cg)",
                            parent_node_id=parent_node_id, group_id=group_id)

                for rule in conditions["rules"]:
                    create_condition_nodes(tx, group_id, "ConditionGroup", rule)

            else: # It's a single Condition
                fact_name = conditions["fact"]
                operator = conditions["operator"]
                value = conditions["value"]
                # Simple unique ID for condition
                condition_id = f"{parent_node_id}_{fact_name}_{operator}_{value}"

                tx.run("MERGE (c:Condition {condition_id: $condition_id}) "
                       "SET c.fact_name = $fact_name, c.operator = $operator, c.value = $value",
                       condition_id=condition_id, fact_name=fact_name, operator=operator, value=value)

                tx.run("MERGE (f:Fact {name: $fact_name})", fact_name=fact_name)

                tx.run("MATCH (c:Condition {condition_id: $condition_id}) "
                       "MATCH (f:Fact {name: $fact_name}) "
                       "MERGE (c)-[:USES_FACT]->(f)",
                       condition_id=condition_id, fact_name=fact_name)

                if parent_node_label == "ConditionGroup":
                    tx.run("MATCH (cg:ConditionGroup {group_id: $parent_node_id}) "
                           "MATCH (c:Condition {condition_id: $condition_id}) "
                           "MERGE (cg)-[:HAS_CONDITION]->(c)",
                           parent_node_id=parent_node_id, condition_id=condition_id)
                elif parent_node_label == "Rule":
                     tx.run("MATCH (r:Rule {rule_id: $parent_node_id}) "
                            "MATCH (c:Condition {condition_id: $condition_id}) "
                            "MERGE (r)-[:HAS_CONDITION]->(c)",
                            parent_node_id=parent_node_id, condition_id=condition_id)


        create_condition_nodes(tx, rule_id, "Rule", rule_data["conditions"])


    def query_eligibility(self, student_facts):
        with self._driver.session() as session:
            # This is a simplified query. A real-world query would be more complex
            # to handle nested AND/OR logic and evaluate conditions against facts.
            # This example checks rules with a single top-level AND condition group
            # and directly evaluates conditions against student_facts.

            # Match rules that have a top-level AND condition group
            query = """
            MATCH (r:Rule)-[:HAS_CONDITION_GROUP]->(cg:ConditionGroup {type: 'AND'})
            MATCH (cg)-[:HAS_CONDITION]->(c:Condition)
            MATCH (r)-[:LEADS_TO]->(conc:Conclusion)
            WITH r, conc, collect(c) as conditions, $student_facts as facts
            WHERE all(condition in conditions WHERE
                CASE condition.operator
                    WHEN '=' THEN facts[condition.fact_name] = condition.value
                    WHEN '==' THEN facts[condition.fact_name] == condition.value
                    WHEN '!=' THEN facts[condition.fact_name] != condition.value
                    WHEN '>' THEN facts[condition.fact_name] > condition.value
                    WHEN '<' THEN facts[condition.fact_name] < condition.value
                    WHEN '>=' THEN facts[condition.fact_name] >= condition.value
                    WHEN '<=' THEN facts[condition.fact_name] <= condition.value
                    ELSE false
                END
            )
            RETURN r.rule_id as rule_id, r.description as description, conc.name as conclusion
            """
            result = session.run(query, student_facts=student_facts)
            return [record.data() for record in result]

# Define LLMAgent class
import openai
# os is already imported

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
