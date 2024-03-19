
import streamlit as st
from typing import Literal
from dataclasses import dataclass
import cohere 
import requests
from bs4 import BeautifulSoup
from st_supabase_connection import SupabaseConnection
from pinecone import Pinecone, ServerlessSpec


pc = Pinecone(api_key=st.secrets["PINECONE_API_KEY"])
index = pc.Index("rorag")

co = cohere.Client(st.secrets["COHERE_API_KEY"]) 


# Streamlit header
st.set_page_config(page_title="Ask Questions on ReachOut")
st.title("ReachOut Questions and Answers")
st.write("This is a smart retriever for ReachOut. You can ask questions about topics you would find on ReachOut and it respond, with references to where it got the answers from.")
st.write("This is just a Proof of Concept and all queries and responses will be logged for further analysis.")


# Data Source
#data_source = st.selectbox(
#    'What ReachOut data do you want to search?',
#    ('au.reachout.com', 'Forums Only', 'Youth Sites Only', 'All ReachOut Sites'))
#temperature = st.slider('Temperature (how closely the response follows source material, lower values are less likely to make things up)', 0.1, 0.9, 0.3, 0.1)
# Initialize connection.
conn = st.experimental_connection("supabase",type=SupabaseConnection)

# Initialize session state variable for tracking prompt submission
if 'prompt_submitted' not in st.session_state:
    st.session_state.prompt_submitted = False

# Initialize a session state to track whether the initial message has been sent
if "initial_message_sent" not in st.session_state:
    st.session_state.initial_message_sent = False

# Initialize the prompt
if "initial_prompt" not in st.session_state:
    st.session_state.initial_prompt = """You are an AI assistant for ReachOut Australia, an organisation that helps young Australians with issues related to Mental Health. You have been provided with documents and citations from the ReachOut website. Do not speak outside this context. Only answer to the questions related to the material mentioned.
If you don't know the answer to any query, just say you don't know. DO NOT try to make up an answer. DO NOT say you will continue searching for relevant information.
You should not say that you are an AI or assistant, just respond with the answer.
I want you to respond with markdown so the result can be nicely presented on a website.
If the question is not related to the context, politely respond that you are tuned to only answer questions that are related to the context."""

# Set a default prompt
default_prompt = """You are an AI assistant for ReachOut Australia, an organisation that helps young Australians with issues related to Mental Health. You have been provided with documents and citations from the ReachOut website. Do not speak outside this context. Only answer to the questions related to the material mentioned.
If you don't know the answer to any query, just say you don't know. DO NOT try to make up an answer. DO NOT say you will continue searching for relevant information.
You should not say that you are an AI or assistant, just respond with the answer.
I want you to respond with markdown so the result can be nicely presented on a website.
If the question is not related to the context, politely respond that you are tuned to only answer questions that are related to the context."""

# Check if the prompt has already been submitted
if not (st.session_state.prompt_submitted | st.session_state.initial_message_sent):
    # Create a text input widget with the default prompt
    user_prompt = st.text_area("Edit the prompt if you like:", value=default_prompt, height=250)

    # Create a submit button
    if st.button("Submit Prompt"):
        # Once the button is pressed, set the prompt as submitted
        st.session_state.prompt_submitted = True
        st.session_state.initial_prompt = user_prompt
        st.session_state.chat_history.append({"role": "User", "message": st.session_state.initial_prompt})
        st.session_state.chat_history.append({"role": "Chatbot", "message": "Yes understood, I will act accordingly, and will be polite, short and to the point."})

else:
    # Display the submitted prompt as static text
    st.write("Your prompt: ", st.session_state.initial_prompt)
    user_prompt = st.session_state.initial_prompt


# loading styles.css
def load_css():
    with open("static/styles.css", "r")  as f:
        css = f"<style>{f.read()} </style>"
        st.markdown(css, unsafe_allow_html = True)

def initialize_session_state() :
    


    # Initialize a session state to store the input field value
    if "input_value" not in st.session_state:
        st.session_state.input_value = ""

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "documents" not in st.session_state:
        st.session_state.documents = []
        
        prompt = """You are an AI assistant for ReachOut Australia, an organisation that helps young Australians with issues related to Mental Health. You have been provided with documents and citations from the ReachOut website. Do not speak outside this context. Only answer to the questions related to the material mentioned.
If you don't know the answer to any query, just say you don't know. DO NOT try to make up an answer. DO NOT say you will continue searching for relevant infromation.
You should not say that you are an AI or assistant, just respond with the answer.
I want you to respond with markdown so the result can be nicely presented on a website.
If the question is not related to the context, politely respond that you are tuned to only answer questions that are related to the context."""

       # st.session_state.chat_history.append({"role": "User", "message": st.session_state.initial_prompt})
       # st.session_state.chat_history.append({"role": "Chatbot", "message": "Yes understood, I will act accordingly, and will be polite, short and to the point."})


#Callblack function which when activated calls all the other
#functions 

def on_click_callback():

    load_css()
    customer_prompt = st.session_state.customer_prompt

    if customer_prompt:
        
        if not st.session_state.prompt_submitted:
            #st.session_state.chat_history.append({"role": "User", "message": st.session_state.initial_prompt})
            #st.session_state.chat_history.append({"role": "Chatbot", "message": "Yes understood, I will act accordingly, and will be polite, short and to the point."})
            st.session_state.prompt_submitted = True

        st.session_state.input_value = ""
        st.session_state.initial_message_sent = True

        with st.spinner('Generating response...'):
                # create the query embedding
                xq = co.embed(
                    texts=[customer_prompt],
                    model='embed-english-v3.0',
                    input_type='search_query',
                    truncate='END'
                ).embeddings

                # query, returning the top 10 most similar results
                res = index.query(vector = xq, top_k=6, include_metadata=True)

                docs_retrieved = [result.metadata['Text'] for result in res.matches]
                #docs_retrieved

                urls_retrieved = [result.metadata['Link'] for result in res.matches]
                #urls_retrieved

                titles_retrieved = [result.metadata['Title'] for result in res.matches]
                #titles_retrieved

                # retrieved documents
                documents = [
                    {"title": titles_retrieved[0], "snippet": docs_retrieved[0], "url": urls_retrieved[0]},
                    {"title": titles_retrieved[1], "snippet": docs_retrieved[1], "url": urls_retrieved[1]},
                    {"title": titles_retrieved[2], "snippet": docs_retrieved[2], "url": urls_retrieved[2]},
                    {"title": titles_retrieved[3], "snippet": docs_retrieved[3], "url": urls_retrieved[3]},
                    {"title": titles_retrieved[4], "snippet": docs_retrieved[4], "url": urls_retrieved[4]},
                    {"title": titles_retrieved[5], "snippet": docs_retrieved[5], "url": urls_retrieved[5]},
                ]

                llm_response = co.chat(
                    message=customer_prompt,
                    documents=documents,
                    preamble=st.session_state.initial_prompt,
                    chat_history=st.session_state.chat_history,
                    model="command-r",
                    temperature=0.1
                    )
                
                edit_text = llm_response.text
                citations = llm_response.citations

                # Sort citations in reverse order to avoid messing up indices when replacing
                citations.sort(key=lambda c: c["start"], reverse=True)

                # Replace citation text with markdown links
                for citation in citations:
                    start, end = citation["start"], citation["end"]
                    citation_text = edit_text[start:end]
                    document_ids = citation["document_ids"]
                    # Assuming document_ids contains only one document ID
                    document_id = document_ids[0]
                    document = next(doc for doc in llm_response.documents if doc["id"] == document_id)
                    url = document["url"]
                    edit_text = edit_text[:start] + f"[{citation_text}]({url})" + edit_text[end:]
                
                st.session_state.chat_history.append({"role": "User", "message": customer_prompt})
                st.session_state.chat_history.append({"role": "Chatbot", "message": edit_text})

                #edit_text

                # Generating markdown output with unique URLs
                unique_urls = set()
                markdown_output_unique = '<ul>'

                for item in llm_response.documents:
                    if item['url'] not in unique_urls:
                        markdown_output_unique += f'<li><a href="{item["url"]}">{item["title"]}</a></li>'
                        unique_urls.add(item['url'])
                markdown_output_unique += '</ul>'
                
                st.session_state.chat_history.append({"role": "Documents", "message": markdown_output_unique})

        # Return next steps from website
        # Check if there are any documents
        if len(llm_response.documents) > 0:
            url = llm_response.documents[0]["url"]
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            section_heading = soup.find('h2', text='What can I do now?')
            # Check if there is a section heading
            if section_heading is not None:
                section_content = section_heading.find_next_siblings()
                st.session_state.chat_history.append({"role": "NextSteps", "message": str(section_content).replace('[', '').replace(']', '').replace('<a href="', '<a href="https://au.reachout.com')})

        # Generate 3 more questions to continue the line of questioning.
        llm_response_qs = co.chat( 
                    message="""Come up with 3 other questions in markdown that a user could ask that would continue the conversation in a helpful way to find out more information. Only respond with a list of the questions, nothing else at all. Only respond with the actual questions. 
  DO NOT respond with anything before the actual questions. 
  DO NOT resond with anything after the actual questions.
  ONLY RESPOND WITH THE ACTUAL QUESTIONS, NOTHING ELSE AT ALL.
  The response should look like the following (do not include any other text after the third question item);
  '<ul>
  <li> <Question 1>? </li>
  <li> <Question 2>? </li>
  <li> <Question 3>? </li>
  </ul>'
  """,
                    model='command-r',
                    temperature=0.02,
                    preamble="""You are an AI assistant for ReachOut Australia, an organisation that helps young Australians with issues related to Mental Health. You have been provided with documents and citations from the ReachOut website. Do not speak outside this context. Only answer to the questions related to the material mentioned.
If you don't know the answer to any query, just say you don't know. DO NOT try to make up an answer. DO NOT say you will continue searching for relevant information.
You should not say that you are an AI or assistant, just respond with the answer.
I want you to respond with markdown so the result can be nicely presented on a website.
 Only respond with a list of the questions, nothing else at all. Only respond with the actual questions. DO NOT respond with anything before the actual questions. DO NOT resond with anything after the actual questions.
 DO NOT say anything like, 'Here are three questions about the <topic>:'.
  DO NOT not say anything like, 'Would you like me to generate more questions about <topic>?'""",
                    # return_prompt=True,
                    chat_history=st.session_state.chat_history,
                    prompt_truncation = 'auto',
                    # stream=True,
                )
        
        st.session_state.chat_history.append({"role": "Questions", "message": llm_response_qs.text})
        
        conn.table("qlog").insert(
        [{"question": customer_prompt, 
          "response": llm_response.text, 
          "references": markdown_output_unique,
          "prompt": st.session_state.initial_prompt,
          "questions": llm_response_qs.text,
          "temp": 0.3}], count="None").execute()



def main():

    initialize_session_state()
    chat_placeholder = st.container()
    prompt_placeholder = st.form("chat-form")

    with chat_placeholder:
        for chat in st.session_state.chat_history[0:]:
            if chat["role"] == "User":
                msg = chat["message"]
            else:
                msg = chat["message"]

            div = f"""
            <div class = "chatRow 
            {'' if chat["role"] != 'User' else 'rowReverse'}">
                <img class="chatIcon" src = "app/static/{'ro-circle.png' if chat["role"] == 'Chatbot' 
                                                         else 'chat-logo.png' if chat["role"] == 'User' 
                                                         else 'references-circle.png' if chat["role"] == 'Documents' 
                                                         else 'ns.png' if chat["role"] == 'NextSteps'
                                                         else 'qmark.png'}" width=32 height=32>
                <div class = "chatBubble {'adminBubble' if chat["role"] != 'User' else 'humanBubble'}">&#8203; <p>{msg}</p></div>
            </div>"""
            st.markdown(div, unsafe_allow_html=True)
            
        
    with st.form(key="chat_form"):
        cols = st.columns((6, 1))
        
        # Display the initial message if it hasn't been sent yet
        if not st.session_state.initial_message_sent:
            cols[0].text_input(
                "Chat",
                placeholder="Hi, what's on your mind?",
                label_visibility="collapsed",
                key="customer_prompt",
            )  
        else:
            cols[0].text_input(
                "Chat",
                value=st.session_state.input_value,
                label_visibility="collapsed",
                key="customer_prompt",
            )

        cols[1].form_submit_button(
            "Ask",
            type="secondary",
            on_click=on_click_callback,
        )


    st.session_state.input_value = cols[0].text_input
    #st.write([record for record in st.session_state.chat_history if record["role"] == "User"])
    #st.write(st.session_state.chat_history)


if __name__ == "__main__":
    main()




