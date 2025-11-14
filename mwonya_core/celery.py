import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mwonya_core.settings')

celery_app = Celery('mwonya_core')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()

celery_app.conf.timezone = 'UTC'

celery_app.conf.beat_schedule = {
    # 'send-scheduled-notifications': {
    #     'task': 'creator.tasks.send_scheduled_notifications',
    #     'schedule': crontab(minute='*/15'),  # Every 15 minutes
    # },
    # 'process-queued-media': {
    #     'task': 'creator.tasks.process_queued_media',
    #     'schedule': crontab(minute='*/5'),  # Every 5 minutes
    # },
    # 'cleanup-old-processing-tasks': {
    #     'task': 'creator.tasks.cleanup_old_processing_tasks',
    #     'schedule': crontab(hour='*/1'),  # Every hour
    # },
    # 'cleanup-failed-uploads': {
    #     'task': 'creator.tasks.cleanup_failed_uploads_task',
    #     'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    # },
    # 'cleanup-failed-tasks': {
    #     'task': 'creator.tasks.check_for_news',
    #     'schedule': 300.0,  # Run every 5 minutes
    # },
    # 'cleanup-old-notifications': {
    #     'task': 'creator.tasks.cleanup_old_notifications',
    #     'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    # },
}