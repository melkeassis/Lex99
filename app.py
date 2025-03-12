import time
import streamlit as st
from utils import cria_chain_conversa, PASTA_ARQUIVOS

def sidebar():
    uploaded_pdfs = st.file_uploader(
        'Add your pdf files', 
        type=['.pdf'], 
        accept_multiple_files=True
    )
    if uploaded_pdfs is None:
        st.info("Nenhum PDF enviado. Serão utilizados os documentos padrão (se disponíveis).")
    else:
        # Remove os PDFs antigos da pasta de upload
        for arquivo in PASTA_ARQUIVOS.glob('*.pdf'):
            arquivo.unlink()
        for pdf in uploaded_pdfs:
            with open(PASTA_ARQUIVOS / pdf.name, 'wb') as f:
                f.write(pdf.read())
    
    label_botao = 'Initialize'
    if 'chain' in st.session_state:
        label_botao = 'Update ChatBot'
    if st.button(label_botao, use_container_width=True):
        st.success('Initializing...')
        cria_chain_conversa()
        st.rerun()

def chat_window():
    # Header sem imagem – somente texto
    st.markdown("""
        <h1>
            Welcome to Lex 99pay! Ask your question.
        </h1>
    """, unsafe_allow_html=True)
    
    if 'chain' not in st.session_state:
        st.error('Ask a question about 99pay services or policies, or upload a document for analysis.')
        st.stop()
    
    chain = st.session_state['chain']
    memory = chain.memory
    mensagens = memory.load_memory_variables({})['chat_history']
    container = st.container()
    for mensagem in mensagens:
        chat = container.chat_message(mensagem.type)
        chat.markdown(mensagem.content)
    
    nova_mensagem = st.chat_input('Ask your question...')
    if nova_mensagem:
        # Exibe a mensagem do usuário
        chat = container.chat_message('human')
        chat.markdown(nova_mensagem)
        # Mensagem temporária enquanto a resposta é gerada
        chat = container.chat_message('ai')
        chat.markdown('Generating response...')
        
        resposta = chain.invoke({'question': nova_mensagem})
        answer_text = resposta.get('answer', '')
        source_docs = resposta.get('source_documents', [])
        
        if source_docs:
            sources_str = ', '.join([doc.metadata.get('source', 'unknown') for doc in source_docs])
        else:
            sources_str = "Nenhuma fonte encontrada. Resposta possivelmente baseada em conhecimento geral."
        
        final_answer = answer_text + "\n\nFonte de dados: " + sources_str
        st.session_state['Last answer'] = final_answer
        chat.markdown(final_answer)
        st.rerun()

def main():
    st.markdown("""
        <style>
        .stApp {
            background-color: #FFEB3B; /* cor amarelo */
        }
        </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        sidebar()
    chat_window()

if __name__ == '__main__':
    main()
