import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from google.cloud import bigquery
import os
import json
import tempfile

# Show title and description.
st.title("💬 HR Management Chatbot")
st.write(
    "This is a simple chatbot that uses Gemini model to generate responses. "
    "To use this app, you need to provide an Gemini API key, which you can get [here](https://aistudio.google.com/app/apikey). "
)
if st.button('Clear', type="primary"):
    st.session_state.messages.clear()



# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management

def gemini_model(google_api_key):
  
    try:
        model = ChatGoogleGenerativeAI(model='gemini-1.5-flash-002', temperature=0, google_api_key=google_api_key)
    except Exception as e:
        st.error(f"An error occurred while setting up the Gemini model: {e}")

    return model

def app(model, query: str):

    table_schema = f"""
    table_metadata =
        table_name: Applicant_Details,
        description: This table contains detailed information about job applications, including application IDs, associated job IDs, recruiter details, customer information, application status, expected salary, and the CV file location.,
        columns:
            Appli_ID:
                data_type: string,
                description: Application ID of the applicant.,
                example_value: APP0263
            ,
            Job_ID:
                data_type: string,
                description: Job ID associated with the application.,
                example_value: JOB1678
            ,
            Rec_ID:
                data_type: string,
                description: Recruiter ID responsible for the application.,
                example_value: R018
            ,
            Cust_ID:
                data_type: string,
                description: Customer ID of the applicant.,
                example_value: CUST0001
            ,
            Data_date:
                data_type: datetime,
                description: Timestamp of when the application data was logged.,
                example_value: 2023-10-28 22:08:06.424926+00:00
            ,
            Status_ID:
                data_type: string,
                description: Status ID representing the application status.,
                example_value: A05
            ,
            Can_ID:
                data_type: string,
                description: Candidate ID associated with the application.,
                example_value: CAN01560
            ,
            Channel_ID:
                data_type: string,
                description: Channel ID through which the application was submitted.,
                example_value: CHN_01
            ,
            expected_sar:
                data_type: integer,
                description: Expected salary for the application in SAR (Saudi Riyals).,
                example_value: 103345
            ,
            CV_location:
                data_type: string,
                description: File path to the CV of the applicant.,
                example_value: C:/Company/Applications/JOB1678/APP0263_CV.pdf
    """

    big_query_prompt = """
    You are a sophisticated BigQuery SQL query generator.
    Translate the following natural language request (human query) into a valid BigQuery syntax (SQL query).
    Consider the table schema provided.
    FROM always `madt8102-test-pipeline-442401.hr_management_dataset.application_table`
    Format the SQL Query result as JSON with 'big_query' as a key.

    ###
    Example:
    Table Schema:
    table_name: Applicant_Details,
    description: 'This table contains detailed information about job applications, including application IDs, associated job IDs, recruiter details, customer information, application status, expected salary, and the CV file location.",
    columns:
        Appli_ID:
            data_type': string,
            description': Application ID of the applicant.,
            example_value': APP0263
        Job_ID':
            data_type': string,
            description': Job ID associated with the application.,
            example_value': JOB1678

    Human Query: Ranking the popular job from most to least popular

    SQL Query: SELECT Job_ID, COUNT(*) AS ApplicationCount
    FROM `madt8102-test-pipeline-442401.hr_management_dataset.application_table`
    GROUP BY Job_ID
    ORDER BY ApplicationCount DESC;

    ###
    Table Schema: {table_schema}
    Human Query: {query}
    SQL Query:
    """

    response_prompt = """
    Summary the information you get and answer the question, using question and query result to answer back to user

    ###
    Example:
    Question: What is the most popular channel for candidate?
    Query result: SELECT Channel_ID, COUNT(*) AS ApplicationCount FROM `madt8102-test-pipeline-442401.hr_management_dataset.application_table` GROUP BY Channel_ID ORDER BY ApplicationCount DESC LIMIT 1
    Answer: The most popular channel for candidate is CHN_01 which is 1088 candidates.

    ###
    Question: {user_query}
    Query result: {sql_result}
    Answer:
    """

    dataset_id = 'hr_management_dataset'
    table_id = 'application_table'
    project_id = 'madt8102-test-pipeline-442401'
    client = bigquery.Client(project=project_id)

    parser = JsonOutputParser()
    bigquery_prompt_template = PromptTemplate(template=big_query_prompt, input_variables=['table_schema', 'query'])
    bigquery_chain = bigquery_prompt_template | model | parser
    sql_bigquery_result = bigquery_chain.invoke({"table_schema": table_schema, "query": query})
    bigquery_query = sql_bigquery_result['big_query']
    # print(bigquery_query)
    bigquery_query_result = client.query(bigquery_query).to_dataframe()

    response_prompt_template = PromptTemplate(template=response_prompt, input_variables=['user_query', 'sql_result'])
    response_chain = response_prompt_template | model
    response_result = response_chain.invoke({"user_query": query, "sql_result": bigquery_query_result})

    return response_result.content, bigquery_query

def main():
    with st.sidebar:
        st.title(":red[Credential and Key]")
        uploaded_file = st.file_uploader("Upload Credential File .json", type="json")

        if not uploaded_file:
            st.info("Please add your Bigquery creditial to continue.", icon="🗝️")

        if uploaded_file is not None:
            if st.button("Add Creditial"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
                        temp_file.write(uploaded_file.read())
                        temp_file_path = temp_file.name

                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file_path
                st.success("Bigquery creditial successfully uploaded.", icon="✅")

        google_api_key = st.text_input("Gemini API Key", type="password")

        if not google_api_key:
            st.info("Please add your Gemini API key and Bigquery creditial to continue.", icon="🗝️")
            
        if google_api_key is not None:
            if st.button("Add Gemine API Key"):
                st.success("Gemini API key successfully uploaded.", icon="✅")

        with st.sidebar:
            st.subheader(":blue[SQL Syntax]")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # for message in st.session_state.messages:
    #     with st.chat_message(message["role"]):
    #         st.markdown(message["content"])

    try:
        if user_input := st.chat_input("What is up?"):

            # with st.chat_message("user"):
            #     st.markdown(user_input)

            st.session_state.messages.append({"role": "user", "content": user_input})

            model = gemini_model(google_api_key=google_api_key)
            bot_response, bigquery_query = app(model, query=user_input)

            # with st.chat_message("assistant"):
            #     with st.spinner("Thinking..."):
            #         st.markdown(bot_response)

            st.session_state.messages.append({"role": "assistant", "content": bot_response})
            with st.sidebar:
                st.code(bigquery_query)

        chat_css = """
        <style>
        .chat-container {
            display: flex;
            align-items: flex-start;
            margin: 10px 0;
        }
        .user-message {
            margin-right: auto;
            background-color: #fce4ec;
            color: black;
            padding: 10px;
            border-radius: 10px;
            max-width: 70%;
        }
        .assistant-message {
            margin-left: auto;
            background-color: #fff9c4;
            color: black;
            padding: 10px;
            border-radius: 10px;
            max-width: 70%;
        }
        .icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            background-color: #f5f5f5;
            border-radius: 50%;
            font-size: 20px;
            margin: 0 10px;
        }
        .user-container {
            display: flex;
            flex-direction: row-reverse;
            align-items: center;
        }
        .assistant-container {
            display: flex;
            flex-direction: row;
            align-items: center;
        }
        </style>
        """
        st.markdown(chat_css, unsafe_allow_html=True)
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(
                    f"""
                    <div class="chat-container user-container">
                        <div class="user-message">{message['content']}</div>
                        <div class="icon">👤</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class="chat-container assistant-container">
                        <div class="icon">🤖</div>
                        <div class="assistant-message">{message['content']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    except:
        st.markdown("🗝️Please make sure you have already added Bigquery creditial and Gemini API key to continue.")

if __name__ == '__main__':
    main()