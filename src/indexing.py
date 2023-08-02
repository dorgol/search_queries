import os
import subprocess
from typing import List

import streamlit as st
from langchain.docstore.document import Document
from langchain.document_loaders import DirectoryLoader
from langchain.document_loaders import TextLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from tqdm import tqdm
from config import chunk_size, chunk_overlap
from get_queries import get_saved_queries_list

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
os.environ["PROJECT_ID"] = 'ltx-dwh-playground'
os.environ["BUCKET_NAME"] = 'ltx_queries'


def download_full_folder():
    destination_path_full = "queries/"

    # Download full bucket
    command = [
        'gsutil', '-m', 'cp',
        '-r', f'gs://{os.environ["BUCKET_NAME"]}/query_*.txt',
        destination_path_full
    ]
    subprocess.run(command, check=True)


def download_part_folder(file_names):
    destination_path = "queries/updates/"

    # Download specific files
    for file_name in file_names:
        command = [
            'gsutil', '-m', 'cp',
            f'gs://{os.environ["BUCKET_NAME"]}/{file_name}',
            destination_path
        ]
        subprocess.run(command, check=True)

    # command_auth = ['gcloud', 'auth', 'login']
    # command_project = ['gcloud', 'config', 'set', 'project', os.environ["PROJECT_ID"]]
    #
    # # Authenticate and set project
    # subprocess.run(command_auth, check=True)
    # subprocess.run(command_project, check=True)


def load_documents(directory):
    # Load and process the text files
    loader = DirectoryLoader(directory, glob="./*.txt", loader_cls=TextLoader)
    documents = loader.load()
    return documents


def split_documents(documents):
    # splitting the text into
    # chunk_size = 1000, chunk_overlap = 200
    # TODO: replace chunk size and overlap with global params
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    documents = text_splitter.split_documents(documents)
    documents = [split for split in documents if len(split.page_content) >= 200]
    return documents


def get_embedding_function():
    embedding = OpenAIEmbeddings(openai_api_key=os.environ['OPENAI_API_KEY'],
                                 openai_organization=os.environ['OPENAI_ORGANIZATION'])
    return embedding


def indexing(documents):
    # Embed and store the texts
    # Supplying a persist_directory will store the embeddings on disk
    persist_directory = 'db'

    embedding = get_embedding_function()

    vectordb = Chroma.from_documents(documents=documents,
                                     embedding=embedding,
                                     persist_directory=persist_directory)

    # persist the db to disk
    vectordb.persist()


def load_db(remote=False):
    path_to_db = 'db'
    if not os.path.exists(path_to_db):
        os.makedirs(path_to_db)
    if remote:
        command = [
            'gsutil', '-m', 'cp',
            '-r', f'gs://{os.environ["BUCKET_NAME"]}/db/*', path_to_db
        ]
        subprocess.run(command, check=True)
    embedding = get_embedding_function()
    vectordb = Chroma(persist_directory=path_to_db, embedding_function=embedding)

    return vectordb


def empty_folder(folder_path):
    # Check if the folder exists
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        print("Folder does not exist or is not a directory.")
        return

    # Get the list of files in the folder
    file_list = os.listdir(folder_path)

    # Iterate through the files and delete them
    for file_name in file_list:
        file_path = os.path.join(folder_path, file_name)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                # If the file is a directory, use a recursive call to empty it
                empty_folder(file_path)
        except Exception as e:
            print(f"Error while deleting {file_path}: {e}")


def get_embedded_names():
    db = load_db()
    a = db._collection.get(include=['metadatas'])['metadatas']
    db_queries_list = []
    for i in a:
        if type(i) is dict:
            source = i['source']
            source = source.replace('queries/query_', '')
            source = source.replace('.txt', '')
            db_queries_list.append(int(source))
    return db_queries_list


def get_unembedded_names():
    gcs_queries_list = get_saved_queries_list()
    embedded_queries_list = get_embedded_names()
    diff = list(set(gcs_queries_list) - set(embedded_queries_list))
    if len(diff) > 0:
        for i in tqdm(list(range(len(diff)))):
            diff[i] = "query_{}.txt".format(diff[i])
    return diff


def update_indexing(new_documents: List[Document]):
    db = load_db()
    db = db.add_documents(new_documents)
    return db


def full_indexing():
    folder = "queries/"
    download_full_folder()
    documents = load_documents(directory=folder)
    documents = split_documents(documents)
    indexing(documents)
    empty_folder(folder)


def update_db():
    folder = "queries/updates/"
    file_names = get_unembedded_names()
    download_part_folder(file_names)
    documents = load_documents(directory=folder)
    documents = split_documents(documents)
    if len(documents) > 0:
        update_indexing(documents)
    empty_folder(folder)


def save_db_to_gcs():
    path_to_db = 'db'
    command = [
        'gsutil', '-m', 'cp',
        '-r', path_to_db, f'gs://{os.environ["BUCKET_NAME"]}/db/',

    ]
    subprocess.run(command, check=True)


if __name__ == '__main__':
    update_db()
    save_db_to_gcs()
