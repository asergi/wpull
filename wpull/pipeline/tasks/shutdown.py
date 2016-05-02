import datetime
import gettext
import logging

import asyncio

from wpull.application.app import Application
from wpull.application.hook import HookableMixin
from wpull.backport.logging import BraceMessage as __
from wpull.pipeline.pipeline import ItemTask
import wpull.string
import wpull.url
import wpull.util
import wpull.warc
from wpull.stats import Statistics
from wpull.pipeline.app import AppSession
import wpull.application.hook
from wpull.application.hook import HookDisconnected


_logger = logging.getLogger(__name__)
_ = gettext.gettext


class BackgroundAsyncCleanupTask(ItemTask[AppSession]):
    @asyncio.coroutine
    def process(self, session: AppSession):
        for server in session.async_servers:
            server.close()

        for task in session.background_async_tasks:
            yield from task


class LoggingShutdownTask(ItemTask[AppSession]):
    @asyncio.coroutine
    def process(self, session: AppSession):
        self._close_console_logger(session)
        self._close_file_logger(session)

    @classmethod
    def _close_console_logger(cls, session: AppSession):
        if session.console_log_handler:
            logger = logging.getLogger()
            logger.removeHandler(session.console_log_handler)
            session.console_log_handler = None

    @classmethod
    def _close_file_logger(cls, session: AppSession):
        if session.file_log_handler:
            logger = logging.getLogger()
            logger.removeHandler(session.file_log_handler)
            session.file_log_handler = None


class AppStopTask(ItemTask[AppSession], HookableMixin):
    def __init__(self):
        super().__init__()
        self.hook_dispatcher.register('AppStopTask.exit_status')

    @asyncio.coroutine
    def process(self, session: AppSession):
        statistics = session.factory['Statistics']
        app = session.factory['Application']
        self._update_exit_code_from_stats(statistics, app)

        try:
            new_exit_code = self.hook_dispatcher.call('AppStopTask.exit_status', session, app.exit_code)
            app.exit_code = new_exit_code
        except HookDisconnected:
            pass

    @classmethod
    def _update_exit_code_from_stats(cls, statistics: Statistics,
                                     app: Application):
        '''Set the current exit code based on the Statistics.'''
        for error_type in statistics.errors:
            exit_code = app.ERROR_CODE_MAP.get(error_type)
            if exit_code:
                app.update_exit_code(exit_code)

    @staticmethod
    @wpull.application.hook.hook_function('AppStopTask.exit_status')
    def plugin_exit_status(app_session: AppSession, exit_code: int) -> int:
        '''Return the program exit status code.

        Exit codes are values from :class:`errors.ExitStatus`.

        Args:
            exit_code: The exit code Wpull wants to return.

        Returns:
            int: The exit code that Wpull will return.
        '''
        return exit_code