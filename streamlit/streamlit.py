import streamlit as st
from langchain_community.document_loaders import PyPDFLoader, TextLoader, MarkdownLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.llms import HuggingFacePipeline
from langchain.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from openai import OpenAI
import os

# Sidebar section
st.sidebar.title("Settings")

# Let the user choose between OpenAI or Hugging Face
llm_choice = st.sidebar.selectbox("Choose LLM", ("OpenAI GPT-3.5", "Hugging Face Mistral"))

# If OpenAI is chosen, capture the API key
if llm_choice == "OpenAI GPT-3.5":
    openai_api_key = st.sidebar.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    if not openai_api_key:
        st.info("Please provide your OpenAI API key to proceed.")

# Main title of the app
st.title("📝 File Q&A with LLMs")

# File uploader for txt, md, and PDF files
uploaded_file = st.file_uploader("Upload an article", type=("pdf", "txt", "md"))

# Text input for users to ask a question related to the uploaded article
question = st.text_input(
    "Ask something about the article",
    placeholder="Can you give me a short summary?",
    disabled=not uploaded_file,
)

# If a file and question are provided, process the input
if uploaded_file and question:
    # Load the document based on the file type
    file_type = uploaded_file.name.split(".")[-1]
    if file_type == "pdf":
        loader = PyPDFLoader(uploaded_file)
    elif file_type == "txt":
        loader = TextLoader(uploaded_file)
    elif file_type == "md":
        loader = MarkdownLoader(uploaded_file)
    else:
        st.error("Unsupported file type.")
        st.stop()

    # Load document and split into chunks
    documents = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)

    # Initialize the selected LLM
    if llm_choice == "OpenAI GPT-3.5" and openai_api_key:
        # OpenAI GPT-3.5 model
        client = OpenAI(api_key=openai_api_key)
        
        # Prepare the message prompt
        article = uploaded_file.read().decode()
        my_prompt = f"Here's an article: {article}.\n\n\n{question}"
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": my_prompt}
        ]
        
        # Send the message to OpenAI's GPT-3.5 model
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        # Get the response content
        answer = response.choices[0].message.content

    elif llm_choice == "Hugging Face Mistral":
        # Hugging Face Mistral model
        tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-v0.1")
        model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-v0.1")

        # Create a pipeline for generating responses
        hf_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer)

        # Initialize embeddings and vector store
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = Chroma.from_documents(docs, embeddings)

        # Create the conversational chain for retrieval and question answering
        qa_chain = ConversationalRetrievalChain.from_llm(hf_pipeline, vectorstore.as_retriever())

        # Ask the question to the chatbot
        response = qa_chain({"question": question, "chat_history": []})

        # Get the response answer
        answer = response["answer"]

    # Display the answer generated by the selected model
    st.write("### Answer")
    st.write(answer)
