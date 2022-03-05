import subprocess
import threading
import loguru
import sched
import time
import shlex
from pathlib import Path
from typing import Any, Union


class SubProcessCommand:
    """ Utility wrapper around Popen to more cleanly integrate common functionality into a script """

    def __init__(self, cmd: str, work_dir: Path = Path.cwd(), blocking: bool = True, logger: Any = loguru.logger,
                 log_output: bool = True):
        """
        Args:
            cmd: Command to execute
            work_dir: Working directory of the process
            blocking: If True, blocks calling program flow until subprocess completes. Non-blocking call if False.
            logger: Standard interface logger to pipe output into
            log_output: Should output be logged?
        """
        self._r_lock = threading.RLock()
        self._kill_event = threading.Event()
        self._thread = threading.Thread()
        self._scheduler = sched.scheduler(time.time, time.sleep)
        self._pending_kill_event = 0
        self._raw_cmd = cmd
        self._work_dir = work_dir
        self._blocking = blocking
        self._logger = logger
        self._log_output = log_output
        self._complete = False
        self._ret_code = 0
        self._stdout = ""
        self._stderr = ""

    @property
    def complete(self) -> bool:
        with self._r_lock:
            return self._complete

    @property
    def ret_code(self) -> int:
        with self._r_lock:
            return self._ret_code

    def execute(self, timeout: Union[int, float, None] = None) -> int:
        """
        Executes the command given during class creation

        Args:
            timeout: How long to wait for the subprocess to complete

        Returns:
            Return code of the subprocess
        """
        if timeout is not None:
            self._pending_kill_event = self._scheduler.enter(timeout, 1, self._kill)

        if self._blocking:
            return self._run_process()
        else:
            self._thread = threading.Thread(target=self._run_process)
            self._thread.start()
            return 0

    def _kill(self) -> None:
        with self._r_lock:
            if self._thread.is_alive():
                self._kill_event.set()

    def _run_process(self) -> int:
        self._ret_code = 0

        # Start the subprocess
        cmd = shlex.split(self._raw_cmd)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self._work_dir.as_posix())

        # Print the output while still executing
        while not self._kill_event.is_set():
            time.sleep(0.01)
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                break
            if self._log_output and self._logger and output:
                self._logger.info(output)

        # Terminate the pending kill event
        try:
            if not self._blocking:
                self._scheduler.cancel(self._pending_kill_event)
        except ValueError:
            pass    # Event is already missing

        # Grab the return code
        if self._kill_event.is_set():
            self._ret_code = -1
            if self._logger and self._log_output:
                self._logger.error("Process exited due to forced termination")
        else:
            self._ret_code = process.poll()

        return self._ret_code
