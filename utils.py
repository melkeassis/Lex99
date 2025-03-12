from pathlib import Path
import streamlit as st
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_community.vectorstores.faiss import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_openai.chat_models import ChatOpenAI
from dotenv import load_dotenv, find_dotenv
from configs import *
import os

_ = load_dotenv(find_dotenv())

PASTA_ARQUIVOS = Path(__file__).parent / 'arquivos'
PASTA_DOCUMENTOS_PADRAO = Path(__file__).parent / 'documentos_padrao'

def importacao_documentos():
    documentos = []
    
    # Tenta carregar os arquivos enviados via upload (salvos em PASTA_ARQUIVOS)
    if PASTA_ARQUIVOS.exists():
        arquivos_upload = list(PASTA_ARQUIVOS.glob('*.pdf'))
        if arquivos_upload:
            for arquivo in arquivos_upload:
                loader = PyPDFLoader(str(arquivo))
                documentos.extend(loader.load())
    
    # Carrega os documentos padrão, se existirem
    if PASTA_DOCUMENTOS_PADRAO.exists():
        for arquivo in PASTA_DOCUMENTOS_PADRAO.glob('*.pdf'):
            loader = PyPDFLoader(str(arquivo))
            documentos.extend(loader.load())
    
    # Se nenhum documento for encontrado, exibe aviso
    if not documentos:
        st.warning("Nenhum documento disponível. Por favor, faça o upload ou verifique a pasta de documentos padrão.")
    
    return documentos

def split_de_documentos(documentos):
    # Ajustamos os parâmetros do chunk para melhorar a preservação de trechos relevantes:
    recur_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,      # tamanho reduzido para evitar cortar trechos importantes
        chunk_overlap=300,    # overlap maior para manter o contexto
        separators=["\n\n", "\n", ".", " ", ""]
    )
    documentos = recur_splitter.split_documents(documentos)
    for i, doc in enumerate(documentos):
        doc.metadata['source'] = doc.metadata['source'].split('/')[-1]
        doc.metadata['doc_id'] = i
    return documentos

def cria_vector_store(documentos):
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Chave da API não encontrada. Verifique se os secrets do Streamlit Cloud estão configurados corretamente.")
    embedding_model = OpenAIEmbeddings(openai_api_key=api_key)
    vector_store = FAISS.from_documents(
        documents=documentos,
        embedding=embedding_model
    )
    return vector_store

def cria_chain_conversa():
    documentos = importacao_documentos()
    # Se nenhum documento for encontrado, insere um documento dummy para evitar erro
    if not documentos:
        st.info("Nenhum documento encontrado. Inicializando chatbot com base mínima.")
        from langchain.docstore.document import Document
        documentos = [Document(page_content="Nenhum documento disponível.", metadata={"source": "dummy", "doc_id": 0})]
    documentos = split_de_documentos(documentos)
    vector_store = cria_vector_store(documentos)
    
    chat_api_key = st.secrets["OPENAI_API_KEY"]
    if not chat_api_key:
        raise ValueError("Chave da API não encontrada. Verifique se os secrets do Streamlit Cloud estão configurados corretamente.")
    chat = ChatOpenAI(
        model=get_config('model_name'),
        api_key=chat_api_key
    )
    memory = ConversationBufferMemory(
        return_messages=True,
        memory_key='chat_history',
        output_key='answer'
    )
    retriever = vector_store.as_retriever(
        search_type=get_config('retrieval_search_type'),
        search_kwargs=get_config('retrieval_kwargs')
    )
    prompt = PromptTemplate.from_template(get_config('prompt'))
    chat_chain = ConversationalRetrievalChain.from_llm(
        llm=chat,
        memory=memory,
        retriever=retriever,
        return_source_documents=True,
        verbose=True,
        combine_docs_chain_kwargs={'prompt': prompt}
    )
    st.session_state['chain'] = chat_chain
