from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Union
from urllib import parse

from meilisearch._httprequests import HttpRequests
from meilisearch.config import Config
from meilisearch.models.document import Document, DocumentsResults
from meilisearch.models.index import IndexStats
from meilisearch.models.task import Task, TaskInfo, TaskResults
from meilisearch.task import get_task, get_tasks, wait_for_task


# pylint: disable=too-many-public-methods
class Index:
    """
    Indexes routes wrapper.

    Index class gives access to all indexes routes and child routes (inherited).
    https://docs.meilisearch.com/reference/api/indexes.html
    """

    def __init__(
        self,
        config: Config,
        uid: str,
        primary_key: Optional[str] = None,
        created_at: Optional[Union[datetime, str]] = None,
        updated_at: Optional[Union[datetime, str]] = None,
    ) -> None:
        """
        Parameters
        ----------
        config:
            Config object containing permission and location of Meilisearch.
        uid:
            UID of the index on which to perform the index actions.
        primary_key:
            Primary-key of the index.
        """
        self.config = config
        self.http = HttpRequests(config)
        self.uid = uid
        self.primary_key = primary_key
        self.created_at = self._iso_to_date_time(created_at)
        self.updated_at = self._iso_to_date_time(updated_at)

    def delete(self) -> Dict[str, Any]:
        """Delete the index.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """

        return self.http.delete(f"{self.config.paths.index}/{self.uid}")

    def update(self, primary_key: str) -> Dict[str, Any]:
        """Update the index primary-key.

        Parameters
        ----------
        primary_key:
            The primary key to use for the index.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        payload = {"primaryKey": primary_key}
        return self.http.patch(f"{self.config.paths.index}/{self.uid}", payload)

    def fetch_info(self) -> Index:
        """Fetch the info of the index.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        index_dict = self.http.get(f"{self.config.paths.index}/{self.uid}")
        self.primary_key = index_dict["primaryKey"]
        self.created_at = self._iso_to_date_time(index_dict["createdAt"])
        self.updated_at = self._iso_to_date_time(index_dict["updatedAt"])
        return self

    def get_primary_key(self) -> str | None:
        """Get the primary key.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.fetch_info().primary_key

    @staticmethod
    def create(
        config: Config, uid: str, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create the index.

        Parameters
        ----------
        uid:
            UID of the index.
        options:
            Options passed during index creation (ex: { 'primaryKey': 'name' }).

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        if options is None:
            options = {}
        payload = {**options, "uid": uid}
        return HttpRequests(config).post(config.paths.index, payload)

    def get_tasks(self, parameters: Optional[Dict[str, Any]] = None) -> TaskResults:
        """Get all tasks of a specific index from the last one.

        Parameters
        ----------
        parameters (optional):
            parameters accepted by the get tasks route: https://docs.meilisearch.com/reference/api/tasks.html#get-tasks.

        Returns
        -------
        tasks:
        TaskResults instance with attributes:
            - from
            - next
            - limit
            - results : list of Task instances containing all enqueued, processing, succeeded or failed tasks of the index

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        if parameters is not None:
            parameters.setdefault("indexUids", []).append(self.uid)
        else:
            parameters = {"indexUids": [self.uid]}

        tasks = get_tasks(self.config, parameters=parameters)
        return TaskResults(tasks)

    def get_task(self, uid: int) -> Task:
        """Get one task through the route of a specific index.

        Parameters
        ----------
        uid:
            identifier of the task.

        Returns
        -------
        task:
            Task instance containing information about the processed asynchronous task of an index.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        task = get_task(self.config, uid)
        return Task(**task)

    def wait_for_task(
        self,
        uid: int,
        timeout_in_ms: int = 5000,
        interval_in_ms: int = 50,
    ) -> Task:
        """Wait until Meilisearch processes a task until it fails or succeeds.

        Parameters
        ----------
        uid:
            identifier of the task to wait for being processed.
        timeout_in_ms (optional):
            time the method should wait before raising a MeiliSearchTimeoutError.
        interval_in_ms (optional):
            time interval the method should wait (sleep) between requests.

        Returns
        -------
        task:
            Task instance containing information about the processed asynchronous task.

        Raises
        ------
        MeiliSearchTimeoutError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        task = wait_for_task(self.config, uid, timeout_in_ms, interval_in_ms)
        return Task(**task)

    def get_stats(self) -> IndexStats:
        """Get stats of the index.

        Get information about the number of documents, field frequencies, ...
        https://docs.meilisearch.com/reference/api/stats.html

        Returns
        -------
        stats:
            IndexStats instance containing information about the given index.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        stats = self.http.get(f"{self.config.paths.index}/{self.uid}/{self.config.paths.stat}")
        return IndexStats(stats)

    def search(self, query: str, opt_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Search in the index.

        Parameters
        ----------
        query:
            String containing the searched word(s)
        opt_params (optional):
            Dictionary containing optional query parameters
            https://docs.meilisearch.com/reference/api/search.html#search-in-an-index

        Returns
        -------
        results:
            Dictionary with hits, offset, limit, processingTime and initial query

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        if opt_params is None:
            opt_params = {}
        body = {"q": query, **opt_params}
        return self.http.post(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.search}",
            body=body,
        )

    def get_document(
        self, document_id: Union[str, int], parameters: Optional[Dict[str, Any]] = None
    ) -> Document:
        """Get one document with given document identifier.

        Parameters
        ----------
        document_id:
            Unique identifier of the document.
        parameters (optional):
            parameters accepted by the get document route: https://docs.meilisearch.com/reference/api/documents.html#get-one-document

        Returns
        -------
        document:
            Document instance containing the documents information.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        if parameters is None:
            parameters = {}
        elif "fields" in parameters and isinstance(parameters["fields"], list):
            parameters["fields"] = ",".join(parameters["fields"])

        document = self.http.get(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}/{document_id}?{parse.urlencode(parameters)}"
        )
        return Document(document)

    def get_documents(self, parameters: Optional[Dict[str, Any]] = None) -> DocumentsResults:
        """Get a set of documents from the index.

        Parameters
        ----------
        parameters (optional):
            parameters accepted by the get documents route: https://docs.meilisearch.com/reference/api/documents.html#get-documents

        Returns
        -------
        documents:
        DocumentsResults instance with attributes:
            - total
            - offset
            - limit
            - results : list of Document instances containing the documents information

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        if parameters is None:
            parameters = {}
        elif "fields" in parameters and isinstance(parameters["fields"], list):
            parameters["fields"] = ",".join(parameters["fields"])

        response = self.http.get(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}?{parse.urlencode(parameters)}"
        )
        return DocumentsResults(response)

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        primary_key: Optional[str] = None,
    ) -> TaskInfo:
        """Add documents to the index.

        Parameters
        ----------
        documents:
            List of documents. Each document should be a dictionary.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        url = self._build_url(primary_key)
        add_document_task = self.http.post(url, documents)
        return TaskInfo(**add_document_task)

    def add_documents_in_batches(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 1000,
        primary_key: Optional[str] = None,
    ) -> List[TaskInfo]:
        """Add documents to the index in batches.

        Parameters
        ----------
        documents:
            List of documents. Each document should be a dictionary.
        batch_size (optional):
            The number of documents that should be included in each batch. Default = 1000
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.

        Returns
        -------
        tasks_info:
            List of TaskInfo instances containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request.
            Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """

        tasks: List[TaskInfo] = []

        for document_batch in self._batch(documents, batch_size):
            task = self.add_documents(document_batch, primary_key)
            tasks.append(task)

        return tasks

    def add_documents_json(
        self,
        str_documents: str,
        primary_key: Optional[str] = None,
    ) -> TaskInfo:
        """Add string documents from JSON file to the index.

        Parameters
        ----------
        str_documents:
            String of document from a JSON file.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.add_documents_raw(str_documents, primary_key, "application/json")

    def add_documents_csv(
        self,
        str_documents: str,
        primary_key: Optional[str] = None,
    ) -> TaskInfo:
        """Add string documents from a CSV file to the index.

        Parameters
        ----------
        str_documents:
            String of document from a CSV file.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.add_documents_raw(str_documents, primary_key, "text/csv")

    def add_documents_ndjson(
        self,
        str_documents: str,
        primary_key: Optional[str] = None,
    ) -> TaskInfo:
        """Add string documents from a NDJSON file to the index.

        Parameters
        ----------
        str_documents:
            String of document from a NDJSON file.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.add_documents_raw(str_documents, primary_key, "application/x-ndjson")

    def add_documents_raw(
        self,
        str_documents: str,
        primary_key: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> TaskInfo:
        """Add string documents to the index.

        Parameters
        ----------
        str_documents:
            String of document.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.
        type:
            The type of document. Type available: 'csv', 'json', 'jsonl'

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        url = self._build_url(primary_key)
        response = self.http.post(url, str_documents, content_type)
        return TaskInfo(**response)

    def update_documents(
        self, documents: List[Dict[str, Any]], primary_key: Optional[str] = None
    ) -> TaskInfo:
        """Update documents in the index.

        Parameters
        ----------
        documents:
            List of documents. Each document should be a dictionary.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        url = self._build_url(primary_key)
        response = self.http.put(url, documents)
        return TaskInfo(**response)

    def update_documents_ndjson(
        self,
        str_documents: str,
        primary_key: Optional[str] = None,
    ) -> TaskInfo:
        """Update documents as a ndjson string in the index.

        Parameters
        ----------
        str_documents:
            String of document from a NDJSON file.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.update_documents_raw(str_documents, primary_key, "application/x-ndjson")

    def update_documents_json(
        self,
        str_documents: str,
        primary_key: Optional[str] = None,
    ) -> TaskInfo:
        """Update documents as a json string in the index.

        Parameters
        ----------
        str_documents:
            String of document from a JSON file.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.update_documents_raw(str_documents, primary_key, "application/json")

    def update_documents_raw(
        self,
        str_documents: str,
        primary_key: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> TaskInfo:
        """Update documents as a string in the index.

        Parameters
        ----------
        str_documents:
            String of document.
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.
        type:
            The type of document. Type available: 'csv', 'json', 'jsonl'

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        url = self._build_url(primary_key)
        response = self.http.put(url, str_documents, content_type)
        return TaskInfo(**response)

    def update_documents_in_batches(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 1000,
        primary_key: Optional[str] = None,
    ) -> List[TaskInfo]:
        """Update documents to the index in batches.

        Parameters
        ----------
        documents:
            List of documents. Each document should be a dictionary.
        batch_size (optional):
            The number of documents that should be included in each batch. Default = 1000
        primary_key (optional):
            The primary-key used in index. Ignored if already set up.

        Returns
        -------
        tasks_info:
            List of TaskInfo instances containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request.
            Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """

        tasks = []

        for document_batch in self._batch(documents, batch_size):
            update_task = self.update_documents(document_batch, primary_key)
            tasks.append(update_task)

        return tasks

    def delete_document(self, document_id: Union[str, int]) -> TaskInfo:
        """Delete one document from the index.

        Parameters
        ----------
        document_id:
            Unique identifier of the document.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        response = self.http.delete(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}/{document_id}"
        )
        return TaskInfo(**response)

    def delete_documents(self, ids: List[Union[str, int]]) -> TaskInfo:
        """Delete multiple documents from the index.

        Parameters
        ----------
        list:
            List of unique identifiers of documents.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        response = self.http.post(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}/delete-batch",
            [str(i) for i in ids],
        )
        return TaskInfo(**response)

    def delete_all_documents(self) -> TaskInfo:
        """Delete all documents from the index.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        response = self.http.delete(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}"
        )
        return TaskInfo(**response)

    # GENERAL SETTINGS ROUTES

    def get_settings(self) -> Dict[str, Any]:
        """Get settings of the index.

        https://docs.meilisearch.com/reference/api/settings.html

        Returns
        -------
        settings
            Dictionary containing the settings of the index.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.get(f"{self.config.paths.index}/{self.uid}/{self.config.paths.setting}")

    def update_settings(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Update settings of the index.

        https://docs.meilisearch.com/reference/api/settings.html#update-settings

        Parameters
        ----------
        body:
            Dictionary containing the settings of the index.
            More information:
            https://docs.meilisearch.com/reference/api/settings.html#update-settings

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.patch(
            f"{self.config.paths.index}/{self.uid}/{self.config.paths.setting}", body
        )

    def reset_settings(self) -> Dict[str, Any]:
        """Reset settings of the index to default values.

        https://docs.meilisearch.com/reference/api/settings.html#reset-settings

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.delete(f"{self.config.paths.index}/{self.uid}/{self.config.paths.setting}")

    # RANKING RULES SUB-ROUTES

    def get_ranking_rules(self) -> List[str]:
        """Get ranking rules of the index.

        Returns
        -------
        settings: list
            List containing the ranking rules of the index.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.get(self.__settings_url_for(self.config.paths.ranking_rules))

    def update_ranking_rules(self, body: List[str]) -> Dict[str, Any]:
        """Update ranking rules of the index.

        Parameters
        ----------
        body:
            List containing the ranking rules.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.put(self.__settings_url_for(self.config.paths.ranking_rules), body)

    def reset_ranking_rules(self) -> Dict[str, Any]:
        """Reset ranking rules of the index to default values.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.delete(
            self.__settings_url_for(self.config.paths.ranking_rules),
        )

    # DISTINCT ATTRIBUTE SUB-ROUTES

    def get_distinct_attribute(self) -> Optional[str]:
        """Get distinct attribute of the index.

        Returns
        -------
        settings:
            String containing the distinct attribute of the index. If no distinct attribute None is returned.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.get(self.__settings_url_for(self.config.paths.distinct_attribute))

    def update_distinct_attribute(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Update distinct attribute of the index.

        Parameters
        ----------
        body:
            String containing the distinct attribute.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.put(self.__settings_url_for(self.config.paths.distinct_attribute), body)

    def reset_distinct_attribute(self) -> Dict[str, Any]:
        """Reset distinct attribute of the index to default values.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.delete(
            self.__settings_url_for(self.config.paths.distinct_attribute),
        )

    # SEARCHABLE ATTRIBUTES SUB-ROUTES

    def get_searchable_attributes(self) -> List[str]:
        """Get searchable attributes of the index.

        Returns
        -------
        settings:
            List containing the searchable attributes of the index.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.get(self.__settings_url_for(self.config.paths.searchable_attributes))

    def update_searchable_attributes(self, body: List[str]) -> Dict[str, Any]:
        """Update searchable attributes of the index.

        Parameters
        ----------
        body:
            List containing the searchable attributes.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.put(self.__settings_url_for(self.config.paths.searchable_attributes), body)

    def reset_searchable_attributes(self) -> Dict[str, Any]:
        """Reset searchable attributes of the index to default values.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.delete(
            self.__settings_url_for(self.config.paths.searchable_attributes),
        )

    # DISPLAYED ATTRIBUTES SUB-ROUTES

    def get_displayed_attributes(self) -> List[str]:
        """Get displayed attributes of the index.

        Returns
        -------
        settings:
            List containing the displayed attributes of the index.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.get(self.__settings_url_for(self.config.paths.displayed_attributes))

    def update_displayed_attributes(self, body: List[str]) -> Dict[str, Any]:
        """Update displayed attributes of the index.

        Parameters
        ----------
        body:
            List containing the displayed attributes.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.put(self.__settings_url_for(self.config.paths.displayed_attributes), body)

    def reset_displayed_attributes(self) -> Dict[str, Any]:
        """Reset displayed attributes of the index to default values.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.delete(
            self.__settings_url_for(self.config.paths.displayed_attributes),
        )

    # STOP WORDS SUB-ROUTES

    def get_stop_words(self) -> List[str]:
        """Get stop words of the index.

        Returns
        -------
        settings:
            List containing the stop words of the index.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.get(self.__settings_url_for(self.config.paths.stop_words))

    def update_stop_words(self, body: List[str]) -> Dict[str, Any]:
        """Update stop words of the index.

        Parameters
        ----------
        body: list
            List containing the stop words.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.put(self.__settings_url_for(self.config.paths.stop_words), body)

    def reset_stop_words(self) -> Dict[str, Any]:
        """Reset stop words of the index to default values.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.delete(
            self.__settings_url_for(self.config.paths.stop_words),
        )

    # SYNONYMS SUB-ROUTES

    def get_synonyms(self) -> Dict[str, List[str]]:
        """Get synonyms of the index.

        Returns
        -------
        settings: dict
            Dictionary containing the synonyms of the index.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.get(self.__settings_url_for(self.config.paths.synonyms))

    def update_synonyms(self, body: Dict[str, List[str]]) -> Dict[str, Any]:
        """Update synonyms of the index.

        Parameters
        ----------
        body: dict
            Dictionary containing the synonyms.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.put(self.__settings_url_for(self.config.paths.synonyms), body)

    def reset_synonyms(self) -> Dict[str, Any]:
        """Reset synonyms of the index to default values.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.delete(
            self.__settings_url_for(self.config.paths.synonyms),
        )

    # FILTERABLE ATTRIBUTES SUB-ROUTES

    def get_filterable_attributes(self) -> List[str]:
        """Get filterable attributes of the index.

        Returns
        -------
        settings:
            List containing the filterable attributes of the index

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.get(self.__settings_url_for(self.config.paths.filterable_attributes))

    def update_filterable_attributes(self, body: List[str]) -> Dict[str, Any]:
        """Update filterable attributes of the index.

        Parameters
        ----------
        body:
            List containing the filterable attributes.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.put(self.__settings_url_for(self.config.paths.filterable_attributes), body)

    def reset_filterable_attributes(self) -> Dict[str, Any]:
        """Reset filterable attributes of the index to default values.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.delete(
            self.__settings_url_for(self.config.paths.filterable_attributes),
        )

    # SORTABLE ATTRIBUTES SUB-ROUTES

    def get_sortable_attributes(self) -> List[str]:
        """Get sortable attributes of the index.

        Returns
        -------
        settings:
            List containing the sortable attributes of the index

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.get(self.__settings_url_for(self.config.paths.sortable_attributes))

    def update_sortable_attributes(self, body: List[str]) -> Dict[str, Any]:
        """Update sortable attributes of the index.

        Parameters
        ----------
        body:
            List containing the sortable attributes.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.put(self.__settings_url_for(self.config.paths.sortable_attributes), body)

    def reset_sortable_attributes(self) -> Dict[str, Any]:
        """Reset sortable attributes of the index to default values.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.delete(
            self.__settings_url_for(self.config.paths.sortable_attributes),
        )

    # TYPO TOLERANCE SUB-ROUTES

    def get_typo_tolerance(self) -> Dict[str, Any]:
        """Get typo tolerance of the index.

        Returns
        -------
        settings: dict
            Dictionary containing the typo tolerance of the index.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.get(self.__settings_url_for(self.config.paths.typo_tolerance))

    def update_typo_tolerance(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Update typo tolerance of the index.

        Parameters
        ----------
        body: dict
            Dictionary containing the typo tolerance.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.patch(self.__settings_url_for(self.config.paths.typo_tolerance), body)

    def reset_typo_tolerance(self) -> Dict[str, Any]:
        """Reset typo tolerance of the index to default values.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.delete(
            self.__settings_url_for(self.config.paths.typo_tolerance),
        )

    def get_pagination_settings(self) -> Dict[str, Any]:
        """Get pagination settngs of the index.

        Returns
        -------
        settings: dict
            Dictionary containing the pagination settings of the index.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.get(self.__settings_url_for(self.config.paths.pagination))

    def update_pagination_settings(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Update the pagination settings of the index.

        Parameters
        ----------
        body: dict
            Dictionary containing the pagination settings.
            https://docs.meilisearch.com/reference/api/pagination.html#update-pagination-settings

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.patch(
            path=self.__settings_url_for(self.config.paths.pagination), body=body
        )

    def reset_pagination_settings(self) -> Dict[str, Any]:
        """Reset pagination settings of the index to default values.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.delete(self.__settings_url_for(self.config.paths.pagination))

    def get_faceting_settings(self) -> Dict[str, Any]:
        """Get the faceting settings of an index.

        Returns
        -------
        settings: dict
            Dictionary containing the faceting settings of the index.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """

        return self.http.get(self.__settings_url_for(self.config.paths.faceting))

    def update_faceting_settings(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Update the faceting settings of the index.

        Parameters
        ----------
        body: dict
            Dictionary containing the faceting settings.
            https://docs.meilisearch.com/reference/api/faceting.html#update-faceting-settings

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.patch(path=self.__settings_url_for(self.config.paths.faceting), body=body)

    def reset_faceting_settings(self) -> Dict[str, Any]:
        """Reset faceting settings of the index to default values.

        Returns
        -------
        task_info:
            TaskInfo instance containing information about a task to track the progress of an asynchronous process.
            https://docs.meilisearch.com/reference/api/tasks.html#get-one-task

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.delete(self.__settings_url_for(self.config.paths.faceting))

    @staticmethod
    def _batch(
        documents: List[Dict[str, Any]], batch_size: int
    ) -> Generator[List[Dict[str, Any]], None, None]:
        total_len = len(documents)
        for i in range(0, total_len, batch_size):
            yield documents[i : i + batch_size]

    @staticmethod
    def _iso_to_date_time(iso_date: Optional[Union[datetime, str]]) -> Optional[datetime]:
        """
        Meilisearch returns the date time information in iso format. Python's implementation of
        datetime can only handle up to 6 digits in microseconds, however Meilisearch sometimes
        returns more digits than this in the micosecond sections so when that happens this method
        reduces the number of microseconds so Python can handle it. If the value passed is either
        None or already in datetime format the original value is returned.
        """
        if not iso_date:
            return None

        if isinstance(iso_date, datetime):
            return iso_date

        try:
            return datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            split = iso_date.split(".")
            reduce = len(split[1]) - 6
            reduced = f"{split[0]}.{split[1][:-reduce]}Z"
            return datetime.strptime(reduced, "%Y-%m-%dT%H:%M:%S.%fZ")

    def __settings_url_for(self, sub_route: str) -> str:
        return f"{self.config.paths.index}/{self.uid}/{self.config.paths.setting}/{sub_route}"

    def _build_url(
        self,
        primary_key: Optional[str] = None,
    ) -> str:
        if primary_key is None:
            return f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}"
        primary_key = parse.urlencode({"primaryKey": primary_key})
        return f"{self.config.paths.index}/{self.uid}/{self.config.paths.document}?{primary_key}"
