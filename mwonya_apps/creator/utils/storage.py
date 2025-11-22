# storage.py - Custom storage backends for flexible file handling

from django.core.files.storage import FileSystemStorage
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import os


class MediaStorage(FileSystemStorage):
    """
    Custom storage for media files with organized structure
    Can be easily swapped with S3 or other cloud storage
    """

    def __init__(self, *args, **kwargs):
        kwargs['location'] = settings.MEDIA_ROOT
        kwargs['base_url'] = settings.MEDIA_URL
        super().__init__(*args, **kwargs)


class RawAudioStorage(MediaStorage):
    """Storage for raw/original uploaded audio files"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.location = os.path.join(settings.MEDIA_ROOT, 'raw')


class HLSStorage(MediaStorage):
    """Storage for processed HLS files"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.location = os.path.join(settings.MEDIA_ROOT, 'hls')


class ImageStorage(MediaStorage):
    """Storage for images (covers, profiles, etc.)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.location = os.path.join(settings.MEDIA_ROOT, 'images')


class FailedStorage(MediaStorage):
    """Storage for failed processing files"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.location = os.path.join(settings.MEDIA_ROOT, 'failed')


# AWS S3 Storage backends (for when you migrate to cloud)
class S3RawAudioStorage(S3Boto3Storage):
    """S3 Storage for raw audio files"""
    location = 'raw'
    file_overwrite = False


class S3HLSStorage(S3Boto3Storage):
    """S3 Storage for HLS processed files"""
    location = 'hls'
    file_overwrite = False


class S3ImageStorage(S3Boto3Storage):
    """S3 Storage for images"""
    location = 'images'
    file_overwrite = False


# Helper function to get the appropriate storage backend
def get_storage_backend(storage_type):
    """
    Get the appropriate storage backend based on settings

    Args:
        storage_type: 'raw', 'hls', 'image', or 'failed'

    Returns:
        Storage backend instance
    """
    use_s3 = getattr(settings, 'USE_S3_STORAGE', False)

    storage_map = {
        'local': {
            'raw': RawAudioStorage,
            'hls': HLSStorage,
            'image': ImageStorage,
            'failed': FailedStorage,
        },
        's3': {
            'raw': S3RawAudioStorage,
            'hls': S3HLSStorage,
            'image': S3ImageStorage,
            'failed': S3Boto3Storage,  # Can customize this too
        }
    }

    backend_type = 's3' if use_s3 else 'local'
    storage_class = storage_map[backend_type].get(storage_type)

    if storage_class:
        return storage_class()

    raise ValueError(f"Unknown storage type: {storage_type}")