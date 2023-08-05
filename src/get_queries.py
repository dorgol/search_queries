import asyncio
import os
import re

import aiohttp
import requests
import streamlit as st
import toml
from google.cloud import storage
from tqdm import tqdm

from filter_terms import list_of_emails, list_of_filter_words


# TODO: add service account


def get_client():
    toml_data = st.secrets["gcp_service_account"]

    # Use the service account dictionary to create the storage client
    storage_client = storage.Client.from_service_account_info(toml_data)
    bucket_name = "ltx_queries"
    bucket = storage_client.get_bucket(bucket_name)
    return bucket


gcs_bucket = get_client()


async def fetch_queries(api_key, query_ids):
    headers = {"Authorization": f"Key {api_key}"}
    async with aiohttp.ClientSession() as session:
        results = {}
        for query_id in tqdm(query_ids):
            url = f"https://redash.lightricks.com/api/queries/{query_id}"
            async with session.get(url, headers=headers) as response:
                results[query_id] = await response.json()
        return results


def async_fetch(api_key, query_ids):
    loop = asyncio.get_event_loop()
    responses = loop.run_until_complete(fetch_queries(api_key, query_ids))
    return responses


def get_dashboards_data(api_key, page, page_size=100):
    # Define your Redash API endpoint and authentication token
    redash_endpoint = 'https://redash.lightricks.com/api'

    # Retrieve all dashboards
    headers = {'Authorization': f'Key {api_key}'}
    response = requests.get(f'{redash_endpoint}/dashboards', headers=headers,
                            params={'page': page, 'page_size': page_size})
    dashboards_data = response.json()

    # Extract the list of dashboards
    dashboards = dashboards_data['results']

    # Iterate over the dashboards and retrieve the queries
    dashboard_query_dicts = {}

    for dashboard in dashboards:
        dashboard_slug = dashboard['slug']
        response = requests.get(f'{redash_endpoint}/dashboards/{dashboard_slug}', headers=headers)
        dashboard_info = response.json()

        queries = dashboard_info['widgets']

        for query in queries:
            if 'visualization' in query:
                query_dict = query['visualization']['query']

                query_id = query_dict['id']
                query_name = query_dict['name']
                query_create_time = query_dict['created_at']
                query_text = query_dict['query']

                user = query_dict['user']
                user_name = user['name']
                user_email = user['email']

                query_info = {
                    'dashboard_slug': dashboard_slug,
                    'query_name': query_name,
                    'created_at': query_create_time,
                    'query': query_text,
                    'user_name': user_name,
                    'user_email': user_email
                }

                dashboard_query_dicts[query_id] = query_info

    return dashboard_query_dicts


def get_query_data(api_key, page, page_size=100):
    # api_key = keys['REDASH_API_KEY']
    redash_endpoint = 'https://redash.lightricks.com/api'

    # Retrieve all dashboards
    headers = {'Authorization': f'Key {api_key}'}
    response = requests.get(f'{redash_endpoint}/queries', headers=headers,
                            params={'page': page, 'page_size': page_size})
    queries = response.json()
    results = queries['results']
    query_dicts = {}
    for query in results:
        query_id = query['id']
        query_name = query['name']
        query_create_time = query['created_at']
        query_update_time = query['updated_at']
        query_text = query['query']

        user = query['user']
        user_name = user['name']
        user_email = user['email']

        query_info = {

            'query_name': query_name,
            'created_at': query_create_time,
            'updated_at': query_update_time,
            'query': query_text,
            'user_name': user_name,
            'user_email': user_email
        }

        query_dicts[query_id] = query_info

    return query_dicts


def filter_by_user(responses, emails_list):
    filtered_responses = {key: value for key, value in responses.items()
                          if value.get('user_email', {}) in emails_list}
    return filtered_responses


def filter_by_name(responses, exclusions):
    filtered_responses = {key: value for key, value in responses.items()
                          if not any(substring in value.get('query_name', '') for substring in exclusions)}
    return filtered_responses


def get_saved_queries_list():
    blobs = list(gcs_bucket.list_blobs())

    pattern = re.compile(r'\d+')

    file_list_with_numbers = []
    for blob in blobs:
        filename = blob.name
        number = int(pattern.search(filename).group()) if pattern.search(filename) else None
        file_list_with_numbers.append(number)

    return file_list_with_numbers


def save_queries(queries, update=True):
    if update is True:
        existing_queries = get_saved_queries_list()
        queries_list = []
        for query in queries:
            queries_list.append(query)

        set_existing = set(existing_queries)
        set_new = set(queries_list)
        queries_ids = list(set_new - set_existing)
        print(f"found {len(queries_ids)} new queries")
    else:
        queries_list = []
        for query in queries:
            queries_list.append(query)
        queries_ids = queries_list

    template = u"""/*
        Query Name: {query_name}
        Query ID: {query_id}
        Created By: {created_by}
        User Email: {user_email}
        Created At: {created_at}
        */
        {query}"""

    for query in queries_ids:
        query_data = queries[query]
        if all(key in query_data for key in ['query_name', 'created_at', 'query', 'user_name', 'user_email']):
            filename = "query_{}.txt".format(str(query))
            print(filename)
            content = template.format(
                query_name=query_data["query_name"],
                query_id=query,
                created_by=query_data["user_name"],
                created_at=query_data["created_at"],
                user_email=query_data["user_email"],
                query=query_data["query"],
            )

            blob = gcs_bucket.blob(filename)
            blob.upload_from_string(content)

        else:
            print("Invalid query format:", query_data)


with open('.streamlit/secrets.toml', 'r') as file:
    keys = toml.load(file)


def get_filtered(page):
    # responses = get_dashboards_data(keys['REDASH_API_KEY'], page)
    responses = get_query_data(keys['REDASH_API_KEY'], page)
    pd_responses = filter_by_user(responses, list_of_emails)
    filtered_responses = filter_by_name(pd_responses, list_of_filter_words)
    return filtered_responses


def get_all_responses(pages):
    responses = {}
    for page in tqdm(pages):
        try:
            response = get_filtered(page)
            for key, value in response.items():
                responses.update({key: value})
        except KeyError:
            print("Couldn't retrieve data")
    print(len(responses))
    return responses


if __name__ == '__main__':
    pages = list(range(1, 3))
    responses = get_all_responses(pages)
    save_queries(responses)
