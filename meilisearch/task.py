from __future__ import annotations

from datetime import datetime
from time import sleep
from typing import Any, Dict, List, Optional
from urllib import parse

from meilisearch._httprequests import HttpRequests
from meilisearch.config import Config
from meilisearch.errors import MeiliSearchTimeoutError
from meilisearch.models.task import TaskInfo


class TaskHandler:
    """
    This class handles all tasks related operations for Meilisearch.


    Parameters
    ----------
        config: Config object containing permission and location of Meilisearch.

    Attributes
    ----------
        config (Config): Config object containing permission and location of Meilisearch.
        http (HttpRequests): HttpRequests object to handle communication with the Meilisearch API.
    """

    def __init__(self, config: Config):
        self.config = config
        self.http = HttpRequests(config)

    def get_tasks(
        self, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all tasks.

        Parameters
        ----------
        parameters (optional):
            parameters accepted by the get tasks route: https://docs.meilisearch.com/reference/api/tasks.html#get-tasks.

        Returns
        -------
        task:
            Dictionary with limit, from, next and results containing a list of all enqueued, processing, succeeded or failed tasks.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        if parameters is None:
            parameters = {}
        for param in parameters:
            if isinstance(parameters[param], list):
                parameters[param] = ",".join(parameters[param])
        return self.http.get(f"{self.config.paths.task}?{parse.urlencode(parameters)}")

    def get_task(self, uid: int) -> Dict[str, Any]:
        """Get one task.

        Parameters
        ----------
        uid:
            Identifier of the task.

        Returns
        -------
        task:
            Dictionary containing information about the status of the asynchronous task.

        Raises
        ------
        MeiliSearchApiError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        return self.http.get(f"{self.config.paths.task}/{uid}")

    def cancel_tasks(self, parameters: Dict[str, Any]) -> TaskInfo:
        """Cancel a list of enqueued or processing tasks.

        Parameters
        ----------
        parameters (optional):
            parameters accepted by the cancel tasks https://docs.meilisearch.com/reference/api/tasks.html#cancel-task.

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
        if parameters is None:
            parameters = {}
        for param in parameters:
            if isinstance(parameters[param], list):
                parameters[param] = ",".join(parameters[param])
        response = self.http.post(f"{self.config.paths.task}/cancel?{parse.urlencode(parameters)}")
        return TaskInfo(**response)

    def delete_tasks(self, parameters: Optional[Dict[str, Any]] = None) -> TaskInfo:
        """Delete a list of enqueued or processing tasks.
        Parameters
        ----------
        config:
            Config object containing permission and location of Meilisearch.
        parameters (optional):
            parameters accepted by the delete tasks route:https://docs.meilisearch.com/reference/api/tasks.html#delete-task.
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
        if parameters is None:
            parameters = {}
        for param in parameters:
            if isinstance(parameters[param], list):
                parameters[param] = ",".join(parameters[param])
        response = self.http.delete(f"{self.config.paths.task}?{parse.urlencode(parameters)}")
        return TaskInfo(**response)

    def wait_for_task(
        self,
        uid: int,
        timeout_in_ms: int = 5000,
        interval_in_ms: int = 50,
    ) -> Dict[str, Any]:
        """Wait until the task fails or succeeds in Meilisearch.

        Parameters
        ----------
        uid:
            Identifier of the task to wait for being processed.
        timeout_in_ms (optional):
            Time the method should wait before raising a MeiliSearchTimeoutError.
        interval_in_ms (optional):
            Time interval the method should wait (sleep) between requests.

        Returns
        -------
        task:
            Dictionary containing information about the processed asynchronous task.

        Raises
        ------
        MeiliSearchTimeoutError
            An error containing details about why Meilisearch can't process your request. Meilisearch error codes are described here: https://docs.meilisearch.com/errors/#meilisearch-errors
        """
        start_time = datetime.now()
        elapsed_time = 0.0
        while elapsed_time < timeout_in_ms:
            task = self.get_task(uid)
            if task["status"] not in ("enqueued", "processing"):
                return task
            sleep(interval_in_ms / 1000)
            time_delta = datetime.now() - start_time
            elapsed_time = time_delta.seconds * 1000 + time_delta.microseconds / 1000
        raise MeiliSearchTimeoutError(
            f"timeout of ${timeout_in_ms}ms has exceeded on process ${uid} when waiting for task to be resolve."
        )
