import streamlit as st
import requests
import sseclient
import os
from typing import List, Dict, Union, Generator
from textwrap import shorten
import json
import pandas as pd
import datetime as dt
import humanize

st.set_page_config(
    layout="centered",
    page_title="Tech Summit - Cortex Agents",
    page_icon=":material/ac_unit:",
)


if "current_thread" not in st.session_state:
    st.session_state["current_thread"] = None

if "parent_message_id" not in st.session_state:
    st.session_state["parent_message_id"] = 0

if "submitted_prompt" not in st.session_state:
    st.session_state["submitted_prompt"] = None


class Callbacks:
    """Manages callback functions for UI interactions and session state management."""

    @classmethod
    def set_thread(cls, id: str):
        """
        Set the current active thread and reset the parent message ID.

        Args:
            id: The thread ID to set as active
        """
        st.session_state["current_thread"] = id
        st.session_state["parent_message_id"] = 0

    @classmethod
    def reset_thread(cls):
        """Reset the current thread and clear all related session state."""
        st.session_state.pop("current_thread")
        st.session_state.pop("parent_message_id")
        st.session_state.pop("submitted_prompt")

    @classmethod
    def submit_prompt(cls, prompt: str):
        """
        Store the submitted prompt in session state.

        Args:
            prompt: Key name to retrieve the prompt value from session state
        """
        st.session_state["submitted_prompt"] = st.session_state[prompt]


class AppConfig:
    """
    Handles all configurations for the application including secrets validation and API URL setup.

    This class validates required secrets from the .streamlit/secrets.toml file and constructs
    the necessary API endpoints for Snowflake Cortex Agent interactions.
    """

    def __init__(
        self,
        database_name: str,
        schema_name: str,
        agent_name: str,
        application_name: str,
    ) -> None:
        """
        Initialize application configuration and validate required secrets.

        Args:
            database_name: Name of the Snowflake database containing the agent
            schema_name: Name of the schema containing the agent
            agent_name: Name of the Cortex Agent to interact with
            application_name: Unique identifier for this application instance

        Raises:
            st.stop: If required secrets are missing or invalid
        """
        checks: List[Dict] = [
            dict(
                name="secrets",
                path=".streamlit/secrets.toml",
                message="Secrets File",
                keys_required=["pat", "account_url"],
            )
        ]
        failed_checks = []
        for check in checks:
            if os.path.exists(check.get("path")):
                for key in check.get("keys_required"):
                    value = st.secrets.get(key, "")
                    if len(value) == 0:
                        failed_checks.append(
                            f"- No value for field **{key}** found in **{check.get('name')}** file"
                        )
                    else:
                        self.__setattr__(key.upper(), value)
        if failed_checks:
            st.error(
                "**Missing required secrets:** \n" + "\n".join(failed_checks),
                icon=":material/warning:",
            )
            st.stop()
        else:
            self.AGENT_DB = database_name
            self.AGENT_SCHEMA = schema_name
            self.AGENT_NAME = agent_name
            self.APPLICATION_NAME = application_name
            self.BASE_API_URL = self.ACCOUNT_URL + "/api/v2/"
            self.AGENT_API_URL = (
                self.BASE_API_URL
                + f"databases/{self.AGENT_DB}/schemas/{self.AGENT_SCHEMA}/agents/{self.AGENT_NAME}:run"
            )
            self.THREADS_API_URL = self.BASE_API_URL + "cortex/threads"
            self.TOKEN = "Bearer " + self.PAT
            self.HEADERS = {
                "Content-Type": "application/json",
                "Authorization": self.TOKEN,
            }


class CortexThreads:
    """
    Manages Cortex Threads API interactions for conversation management.

    Provides methods to create, list, retrieve, rename, and delete conversation threads
    using the Snowflake Cortex Threads API.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize the CortexThreads manager with application configuration.

        Args:
            config: AppConfig instance containing API credentials and endpoints
        """
        self.config = config

    def _process_response(self, request: requests.Request) -> requests.Request:
        """
        Process and validate API response, handling errors gracefully.

        Args:
            request: The requests.Request object to process

        Returns:
            The validated request object

        Raises:
            HTTPError: Displays error in Streamlit UI if request fails
        """
        try:
            request.raise_for_status()
            return request
        except requests.exceptions.HTTPError as e:
            st.exception(e)

    def create_thread(self):
        """
        Create a new conversation thread in Cortex.

        Returns:
            str: The ID of the newly created thread
        """
        body = {"origin_application": self.config.APPLICATION_NAME}
        thread_response = requests.post(
            url=self.config.THREADS_API_URL, headers=self.config.HEADERS, json=body
        )
        return self._process_response(request=thread_response).json().get("thread_id")

    def list_threads(self):
        """
        Retrieve all threads associated with the application.

        Returns:
            list: List of thread objects with metadata
        """
        parametized_url = (
            self.config.THREADS_API_URL
            + "/?origin_application="
            + self.config.APPLICATION_NAME
        )
        thread_response = requests.get(url=parametized_url, headers=self.config.HEADERS)
        return self._process_response(request=thread_response).json()

    def get_thread_messages(self, id: str):
        """
        Retrieve all messages from a specific thread.

        Args:
            id: The thread ID to retrieve messages from

        Returns:
            dict: Thread data including messages and metadata
        """
        parametized_url = self.config.THREADS_API_URL + "/" + str(id)
        thread_response = requests.get(url=parametized_url, headers=self.config.HEADERS)

        return self._process_response(request=thread_response).json()

    def rename_thread(self, id: str, name: str):
        """
        Update the name of an existing thread.

        Args:
            id: The thread ID to rename
            name: New name for the thread (will be truncated to 20 characters)
        """
        body = {"thread_name": name}
        parametized_url = self.config.THREADS_API_URL + "/" + str(id)
        thread_response = requests.post(
            url=parametized_url, headers=self.config.HEADERS, json=body
        )
        self._process_response(request=thread_response)

    def delete_thread(self, id: str):
        """
        Delete a thread and all its messages.

        Args:
            id: The thread ID to delete
        """
        parametized_url = self.config.THREADS_API_URL + "/" + str(id)
        thread_response = requests.delete(
            url=parametized_url, headers=self.config.HEADERS
        )
        self._process_response(request=thread_response)
        if st.session_state["current_thread"] == id:
            st.session_state["current_thread"] = None
            st.session_state["parent_message_id"] = 0


class CortexAgent:
    """
    Manages interactions with Snowflake Cortex Agent for AI-powered conversations.

    Handles agent invocation, streaming responses, and parsing of various response types
    including text, annotations, tables, and charts.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize the CortexAgent with application configuration.

        Args:
            config: AppConfig instance containing API credentials and endpoints
        """
        self.config = config

    def _process_response(self, request: requests.Request) -> requests.Request:
        """
        Process and validate API response, handling errors gracefully.

        Args:
            request: The requests.Request object to process

        Returns:
            The validated request object

        Raises:
            HTTPError: Displays error in Streamlit UI if request fails
        """
        try:
            request.raise_for_status()
            return request
        except requests.exceptions.HTTPError as e:
            st.exception(e)

    def call_cortex_agent(
        self, prompt: str, thread_id: str, parent_message_id: int = 0
    ) -> Union[Generator, int]:
        """
        Send a prompt to the Cortex Agent and stream the response.

        Args:
            prompt: The user's question or command
            thread_id: The conversation thread ID
            parent_message_id: ID of the parent message in the thread (default: 0)

        Yields:
            tuple: (is_text_response, content) where is_text_response is True for final
                   text and False for thinking process

        Returns:
            The processed response object
        """
        payload = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            "stream": True,
            "thread_id": thread_id,
            "parent_message_id": parent_message_id,
        }
        agent_reponse = requests.post(
            url=self.config.AGENT_API_URL,
            headers=self.config.HEADERS,
            json=payload,
            stream=True,
        )
        agent_response = self._process_response(request=agent_reponse)
        sse = sseclient.SSEClient(agent_response)
        for event in sse.events():
            match event.event:
                case "response.thinking.delta":
                    yield (False, json.loads(event.data).get("text"))
                case "response.text.delta":
                    yield (True, json.loads(event.data).get("text"))
                case "response.text.annotation":
                    annotation = json.loads(event.data).get("annotation")
                    annotation_index = json.loads(event.data).get("annotation_index")
                    doc_id = annotation.get("doc_id")
                    yield (
                        True,
                        f"""  :small[:blue-background[[**{annotation_index}**]({doc_id})]] """,
                    )
        return self._process_response(request=agent_reponse)

    def get_last_message_id(self, messages: list):
        """
        Extract and store the last message ID from thread messages.

        Args:
            messages: Dictionary containing the messages list from a thread
        """
        st.session_state["parent_message_id"] = messages.get("messages")[:-1][0].get(
            "message_id"
        )

    def _format_annotations(self, annotations: list):
        """
        Format annotations for display with document references.

        Args:
            annotations: List of annotation objects from the agent response

        Returns:
            list: Formatted annotation dictionaries with number, url, and position
        """
        annotations_dict = []
        for index, annotation in enumerate(annotations, start=1):
            annotations_dict.append(
                dict(
                    number=index,
                    url=annotation.get("doc_id"),
                    position=annotation.get("index"),
                )
            )
        return annotations_dict

    def _format_table(self, table: dict):
        """
        Convert table response data into a pandas DataFrame.

        Args:
            table: Table object from agent response containing result_set and metadata

        Returns:
            pd.DataFrame: Formatted table data with proper column names
        """
        data = table.get("result_set").get("data")
        schema = [
            col.get("name")
            for col in table.get("result_set").get("resultSetMetaData").get("rowType")
        ]
        return pd.DataFrame(data, columns=schema)

    def parse_payload(self, message: dict):
        """
        Parse and display a message payload in the Streamlit UI.

        Handles different types of content including text, annotations, tables, and charts.
        Renders the content appropriately using Streamlit components.

        Args:
            message: Message dictionary containing role and message_payload
        """
        role = message.get("role")
        with st.chat_message(name=role):
            payload = json.loads(message.get("message_payload")).get("content")
            if role == "user":
                st.write(payload[0].get("text"))
            else:
                results = list(
                    filter(
                        lambda step: step.get("type")
                        in ["text", "annotations", "chart", "table"],
                        payload,
                    )
                )
                for item in results:
                    if isinstance(item, dict):
                        if raw_response := item.get("text"):
                            if annotations := item.get("annotations"):
                                annotations_dict = self._format_annotations(
                                    annotations=annotations
                                )
                                response_list = list(raw_response)
                                sorted_positions = sorted(
                                    annotations_dict,
                                    key=lambda item: item["number"],
                                    reverse=True,
                                )
                                for annotation in sorted_positions:
                                    annotation_number = f" {annotation.get('number')} "
                                    response_list.insert(
                                        annotation.get("position"),
                                        f""" :grey-background[:small[[{annotation_number}]({annotation.get("url")})]] """,
                                    )

                                st.markdown("".join(response_list))
                            else:
                                st.markdown(raw_response)
                        if data_response := item.get("table"):
                            data = self._format_table(table=data_response)
                            st.dataframe(data)

                        if chart_response := item.get("chart"):
                            chart_data = json.loads(chart_response.get("chart_spec"))
                            st.vega_lite_chart(chart_data)


def main() -> None:
    app = AppConfig(
        database_name="SNOWFLAKE_INTELLIGENCE",
        schema_name="AGENTS",
        agent_name="DATA_FOR_GOOD",
        application_name="threads_demo",
    )
    threads = CortexThreads(config=app)
    agent = CortexAgent(config=app)
    callbacks = Callbacks()

    with st.container(horizontal_alignment="right"):
        st.button(
            ":grey[New Thread]",
            type="tertiary",
            icon=":material/add:",
            on_click=callbacks.reset_thread,
        )
    with st.sidebar:
        if all_threads := threads.list_threads():
            threads_times = {
                th.get("thread_id"): humanize.naturaldate(
                    dt.datetime.fromtimestamp(th.get("updated_on") / 1000),
                )
                for th in all_threads
            }
            today_ids = []
            yesterday_ids = []
            older_ids = []
            for id, cat in threads_times.items():
                match cat:
                    case "today":
                        today_ids.append(id)
                    case "yesterday":
                        yesterday_ids.append(id)
                    case _:
                        older_ids.append(id)
            bucketed_times = dict(
                today=today_ids, yesterday=yesterday_ids, older=older_ids
            )
            st.subheader("Recent Chats", divider="grey")
            today_group = st.container()
            with today_group:
                st.markdown(f"**:grey[:small[Today]]**")
            yesterday_group = st.container()
            with yesterday_group:
                st.markdown(f"**:grey[:small[Yesterday]]**")
            older_group = st.container()
            with older_group:
                st.markdown(f"**:grey[:small[Older]]**")
            container_map = dict(
                today=today_group, yesterday=yesterday_group, older=older_group
            )
            for thread in all_threads:
                group = [
                    key
                    for key, val in bucketed_times.items()
                    if thread.get("thread_id") in val
                ][0]
                assigned_group = container_map.get(group)
                with assigned_group:
                    name = thread.get("thread_name")
                    with st.container(horizontal=True):
                        st.button(
                            "",
                            icon=":material/close_small:",
                            key=str(thread.get("thread_id")) + "delete",
                            type="tertiary",
                            width="content",
                            on_click=threads.delete_thread,
                            args=[thread.get("thread_id")],
                        )
                        st.button(
                            f":small[{shorten(text=name, width=25, placeholder='...')}]",
                            key=thread.get("thread_id"),
                            type="tertiary",
                            width="content",
                            on_click=callbacks.set_thread,
                            args=[thread.get("thread_id")],
                            help=name,
                        )
        else:
            st.session_state["current_thread"] = None

    if st.session_state["current_thread"]:
        thread_messages = threads.get_thread_messages(
            id=st.session_state["current_thread"]
        )
        messages = thread_messages.get("messages")
        if len(messages):
            agent.get_last_message_id(messages=thread_messages)
            messages = sorted(
                thread_messages.get("messages"),
                key=lambda item: item.get("created_on"),
                reverse=False,
            )
            for message in messages:
                agent.parse_payload(message=message)

    st.chat_input(
        "Ask me",
        on_submit=callbacks.submit_prompt,
        args=["input_prompt"],
        key="input_prompt",
    )
    if st.session_state["submitted_prompt"]:
        if st.session_state["current_thread"] is None:
            st.session_state["current_thread"] = threads.create_thread()
            threads.rename_thread(
                id=st.session_state["current_thread"],
                name=st.session_state["submitted_prompt"],
            )

        call_code = agent.call_cortex_agent(
            prompt=st.session_state["submitted_prompt"],
            thread_id=st.session_state["current_thread"],
            parent_message_id=st.session_state["parent_message_id"],
        )
        planning_txt = ""
        text_txt = ""
        with st.chat_message(name="user"):
            st.write(st.session_state["submitted_prompt"])
        planning_exp = st.status(label="Thinking", state="running")
        planning_emp = planning_exp.empty()
        with st.chat_message(name="assistant"):
            results_emp = st.empty()

        while True:
            try:
                nxt = next(call_code)
                if nxt[0]:
                    results_emp.empty()
                    text_txt += nxt[1]
                    with results_emp.container():
                        st.write(text_txt)
                else:
                    with planning_exp:
                        planning_emp.empty()
                        planning_txt += nxt[1]
                        with planning_emp.container():
                            st.write(planning_txt)
            except StopIteration:
                st.session_state["submitted_prompt"] = None
                st.rerun()


if __name__ == "__main__":
    main()
