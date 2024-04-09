import boto3
import botocore
import json
from opensearchpy import OpenSearch
from opensearchpy import RequestsHttpConnection, OpenSearch, AWSV4SignerAuth
import streamlit as st





config = botocore.config.Config(connect_timeout=300, read_timeout=300)
bedrock = boto3.client('bedrock-runtime' , 'us-east-1', config = config)

#Setup Opensearch connectionand clinet
host = '14dzfsbbbt70yuz57f23.us-west-2.aoss.amazonaws.com' #use Opensearch Serverless host here
region = 'us-west-2'# set region of you Opensearch severless collection
service = 'aoss'
credentials = boto3.Session().get_credentials() #Use enviroment credentials
auth = AWSV4SignerAuth(credentials, region, service) 

oss_client = OpenSearch(
    hosts = [{'host': host, 'port': 443}],
    http_auth = auth,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection,
    pool_maxsize = 20
)

def get_embeddings(bedrock, text):
    body_text = json.dumps({"inputText": text})
    modelId = 'amazon.titan-embed-text-v1'
    accept = 'application/json'
    contentType='application/json'

    response = bedrock.invoke_model(body=body_text, modelId=modelId, accept=accept, contentType=contentType)
    response_body = json.loads(response.get('body').read())
    embedding = response_body.get('embedding')

    return embedding

#Get KNN Results
def get_knn_results(client, userVectors):
    docType = "KB"

    query = {
        "size": 2,
        "query": {
            "knn": {
                "vectors": {
                    "vector": userVectors, "k": 2
                }
            }
        },
        "_source": False,
        "fields": ["content", "source", "page"],
    }


    response = client.search(
        body=query,
        index='tiaa',
    )

    print(response)

    similaritysearchResponse = ""
    count = 1
    for i in response["hits"]["hits"]:
        content = "Page Content: " + str(i["fields"]["content"])
        source = "Source: " + str(i["fields"]["source"])
        page_number = "Page Number: " + str(i["fields"]["page"])
        new_line = "\n"

        similaritysearchResponse =  similaritysearchResponse + content + new_line + source + new_line + page_number + new_line + new_line
        count = count + 1
    
    return similaritysearchResponse


def invoke_llm(bedrock, user_input, knn_results):

# Uses the Bedrock Client, the user input, and the document template as part of the prompt


    ##Setup Prompt
    system_prompt = f"""

Your goal is toanswer the user's question
Based on the provided <context>, Answer the user's question in a concise manner, provide the sources and source page number to where the relevant information can be found. Include the source information at the end of your response
Do not include any information outside of the information provided in the <context>. If the provided context does not contain a valid answer to the question, say so
Do not include any preamble


<context>
{knn_results}
</context>

Make sure your response is well formatted and human readable 
Return your response in valid markdown

"""

    prompt = {
        "anthropic_version":"bedrock-2023-05-31",
        "max_tokens":1000,
        "temperature":0.5,
        "system" : system_prompt,
        "messages":[
            {
                "role":"user",
                "content":[
                {
                    "type":"text",
                    "text": "<user_question>" +user_input +"</user_question>"
                }
                ]
            },
            {
                    "role": "assistant",
                    "content": "Based on the provided context:"
            }
        ]
    }

    json_prompt = json.dumps(prompt)

    response = bedrock.invoke_model(body=json_prompt, modelId="anthropic.claude-3-sonnet-20240229-v1:0", accept="application/json", contentType="application/json")

    #modelId = "anthropic.claude-v2"  # change this to use a different version from the model provider if you want to switch 
    #accept = "application/json"
    #contentType = "application/json"
    #Call the Bedrock API
    #response = bedrock.invoke_model(
    #    body=body, modelId=modelId, accept=accept, contentType=contentType
    #)

    #Parse the Response
    response_body = json.loads(response.get('body').read())

    llmOutput=response_body['content'][0]['text']

    cleaned_output = llmOutput.replace("$", "\$")

    #Return the LLM response
    return cleaned_output



def do_it(userQuery):
    userVectors = get_embeddings(bedrock, userQuery)
    similaritysearchResponse = get_knn_results(oss_client, userVectors)
    llmOutput = invoke_llm(bedrock, userQuery, similaritysearchResponse)
    return llmOutput


st.set_page_config(page_title="TIAA Document Q+A", page_icon=":tada", layout="wide")

#Headers
with st.container():
    st.header("Ask questions against your summarized documents")


#
with st.container():
    st.write("---")
    userQuery = st.text_input("Ask a Question")
    #userID = st.text_input("User ID")
    st.write("---")


##Back to Streamlit
result=st.button("ASK!")
if result:
    st.markdown(do_it(userQuery),unsafe_allow_html=True)



