import os
import logging
from celery import Celery
from celery.result import AsyncResult, allow_join_result
from decimal import Decimal

logger = logging.getLogger(__name__)

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
app = Celery('opentaps_seas')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


PROGRESS_STATE = 'PROGRESS'


@app.task(bind=True)
def debug_task(self):
    logger.info('debug_task::Request: {0!r}'.format(self.request))


class ProgressRecorder(object):

    def __init__(self, task, name='Background Job',
                 success_url=None, success_label=None,
                 skip_url=None, skip_label=None,
                 back_url=None):
        self.task = task
        self.description = "Processing ..."
        self.current = 0
        self.total = 1
        self.extra = {
            'name': name,
            'success_url': success_url,
            'skip_url': skip_url,
            'skip_label': skip_label,
            'back_url': back_url,
        }

    def add_progress(self, description=None, total=None, current=None):
        if total:
            self.total = total
        if current:
            self.current = current
        if description:
            self.description = description
        else:
            self.current += 1

        if self.current > self.total:
            self.total = self.current

        self.set_progress(self.current, self.total, description=description)

    def set_progress(self, current, total, description=None):
        logger.info('ProgressRecorder:set_progress %s of %s : %s', current, total, description)
        self.current = current
        self.total = total
        if description:
            self.description = description
        percent = 0
        if total > 0:
            percent = (Decimal(current) / Decimal(total)) * Decimal(100)
            percent = float(round(percent, 2))
        self.task.update_state(
            state=PROGRESS_STATE,
            meta={
                'extra': self.extra,
                'current': current,
                'total': total,
                'percent': percent,
                'description': self.description,
            }
        )

    def set_failure(self, exc):
        self.task.update_state(
            state='FAILURE',
            meta={
                'extra': self.extra,
                'current': self.current,
                'total': self.total,
                'percent': 100.0,
                'exc_message': str(exc),
                'exc_type': str(type(exc))
            }
        )

    def stop_task(self, current, total, exc):
        self.task.update_state(
            state='FAILURE',
            meta={
                'extra': self.extra,
                'current': current,
                'total': total,
                'percent': 100.0,
                'exc_message': str(exc),
                'exc_type': str(type(exc))
            }
        )


class Progress(object):

    def __init__(self, task_id):
        self.task_id = task_id
        self.result = AsyncResult(task_id)

    def get_info(self):
        if self.result.ready():
            success = self.result.successful()
            with allow_join_result():
                return {
                    'state': self.result.state,
                    'complete': True,
                    'success': success,
                    'progress': _get_completed_progress(),
                    'result': self.result.get(self.task_id) if success else None,
                    'info': self.result.info
                }
        elif self.result.state == PROGRESS_STATE:
            return {
                'state': self.result.state,
                'complete': False,
                'success': None,
                'progress': self.result.info,
                'info': self.result.info
            }
        elif self.result.state in ['PENDING', 'STARTED']:
            return {
                'state': self.result.state,
                'complete': False,
                'success': None,
                'progress': _get_unknown_progress(),
                'info': self.result.info
            }
        return {
                'state': self.result.state,
                'info': self.result.info
            }


def _get_completed_progress():
    return {
        'current': 100,
        'total': 100,
        'percent': 100,
    }


def _get_unknown_progress():
    return {
        'current': 0,
        'total': 100,
        'percent': 0,
    }
