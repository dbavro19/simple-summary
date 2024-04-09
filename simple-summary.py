import boto3
import botocore
from langchain_community.document_loaders import PyPDFLoader
import json
from opensearchpy import OpenSearch
from opensearchpy import RequestsHttpConnection, OpenSearch, AWSV4SignerAuth
import streamlit as st
import logging



def get_embeddings(bedrock, text):
    body_text = json.dumps({"inputText": text})
    modelId = 'amazon.titan-embed-text-v1'
    accept = 'application/json'
    contentType='application/json'

    response = bedrock.invoke_model(body=body_text, modelId=modelId, accept=accept, contentType=contentType)
    response_body = json.loads(response.get('body').read())
    embedding = response_body.get('embedding')

    return embedding

def index_doc(client, vectors, content, source, page_number):

    try:
        page = int(page_number)+1
    except:
        page = 0

    indexDocument={
        'vectors': vectors,
        'content': content,
        'source': source,
        'page': page
        }

    response = client.index(
        index = "tiaa", #Use your index 
        body = indexDocument,
    #    id = '1', commenting out for now
        refresh = False
    )
    return response


def parse_xml(xml, tag):
    temp=xml.split(">")
    
    tag_to_extract="</"+tag

    for line in temp:
        if tag_to_extract in line:
            parsed_value=line.replace(tag_to_extract, "")
            return parsed_value

def summarize_section(section):
    system_prompt=f"""
Summarize the provided section of a Document. The Summary should take the form of an executive summary and follow the form of the orignal doc
Summary should be detailed and throughout, capturing all important metrics, data points, quotes, and themes of the original document section
The summary should be at least a page in length


Return your summary in <summary> xml tags, do not include an preface, preamble or other text other than the summary itself 

"""
    user_prompt=f"""
<original_doc>
{section}
</original_doc>

"""
    content=[{
        "type": "text",
        "text": user_prompt
            }]
    
    prompt = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 10000,
        "temperature": 0,
        "system": system_prompt,
        "messages": [    
            {
                "role": "user",
                "content": content
            }
        ]
    }

    prompt = json.dumps(prompt)

    #model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    response = bedrock.invoke_model(body=prompt, modelId=model_id, accept="application/json", contentType="application/json")
    response_body = json.loads(response.get('body').read())
    llmOutput=response_body['content'][0]['text']

    section_summary = parse_xml(llmOutput, "summary").strip()

    return section_summary


def final_summary(sections):
    system_prompt = f"""
    You will be given a set of summaries of different sections of a document.
    Using all the different sections, create a final summary of the document.
    The summary should take the form of an executive summary, and be should be cohesive as its own document and follow a logical flow that makes sense for an executive summary
    Your Summary should be detailed and thorough, capturing all important metrics, data points, and themes of the original document sections
    Your summary should be a full page
    Your summary should be written in valid markdown

    provide the final combined summaries of the sections in <final_summary> xml tags in valid markdown, with no preamble or other text
    """

    user_prompt=f"""
<Section_summaries>
{sections}
</original_doc>

"""
    content=[{
        "type": "text",
        "text": user_prompt
            }]
    
    prompt = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 10000,
        "temperature": 0,
        "system": system_prompt,
        "messages": [    
            {
                "role": "user",
                "content": content
            }
        ]
    }

    prompt = json.dumps(prompt)

    #model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    response = bedrock.invoke_model(body=prompt, modelId=model_id, accept="application/json", contentType="application/json")
    response_body = json.loads(response.get('body').read())
    llmOutput=response_body['content'][0]['text']

    final_summary = parse_xml(llmOutput, "final_summary").strip()

    return final_summary


def process_pdf(filename):
    loader = PyPDFLoader(filename)
    pages = loader.load_and_split()
    return pages



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

def do_it(pages):

    sections=[]
    section_count=0

    for page in pages:
        content = page.page_content
        metadata  = page.metadata

        #extract source and page number
        source = metadata["source"]
        page_number = metadata["page"]

        embeddings = get_embeddings(bedrock, content)

        response = index_doc(oss_client, embeddings, content, source, page_number)

        #create summary
        section_summary = summarize_section(content)
        section_number = section_count+1
        sections.append(f"<section_{section_number}>{section_summary}</section_{section_number}>")
        section_count+=1
    
        print("Page: " + str(page_number) + " Done")

    print(len(sections))

    all_sections = "\n".join(sections)

    print(all_sections)

    print("---------------------------------------")

    final_result = final_summary(all_sections)

    cleaned_output = final_result.replace("$", "\$")

    print(cleaned_output)

    st.markdown(cleaned_output, unsafe_allow_html=True)






#Headers
with st.container():
    st.header("Generate summary of large PDF")


uploaded_file = st.file_uploader("Upload a PDF")


##Back to Streamlit
result=st.button("Upload File and Get Metadata")
if result:
    pdf_path = uploaded_file.name
    pages = process_pdf(pdf_path)
    do_it(pages)