# =================================================================
# utils/file_handlers.py - File handling utilities
# =================================================================

import os
import uuid
import json
import shutil
from pathlib import Path
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone

from .storage import get_storage_backend


def generate_track_path(instance, filename):
    """
    Generate organized path for raw audio files
    Format: raw/{artist_id}/{track_id}/{filename}
    """
    ext = filename.split('.')[-1]
    track_id = str(instance.id) if instance.id else str(uuid.uuid4())
    artist_id = str(instance.artist.id)

    return f'raw/{artist_id}/{track_id}/original.{ext}'


def generate_hls_path(track_id):
    """
    Generate path for HLS output
    Format: hls/{track_id}/
    """
    return f'hls/{track_id}/'


def generate_image_path(instance, filename, image_type):
    """
    Generate organized path for images

    Args:
        instance: Model instance
        filename: Original filename
        image_type: 'cover', 'profile', 'banner', etc.

    Format: images/{type}/{year}/{month}/{uuid}.{ext}
    """
    from datetime import datetime

    ext = filename.split('.')[-1].lower()
    file_uuid = uuid.uuid4()
    now = datetime.now()

    return f'images/{image_type}/{now.year}/{now.month:02d}/{file_uuid}.{ext}'


# Specific path generators for models
def track_cover_path(instance, filename):
    """Path for track cover art"""
    return generate_image_path(instance, filename, 'track_covers')


def album_cover_path(instance, filename):
    """Path for album cover art"""
    return generate_image_path(instance, filename, 'album_covers')


def artist_profile_path(instance, filename):
    """Path for artist profile images"""
    return generate_image_path(instance, filename, 'artist_profiles')


def artist_cover_path(instance, filename):
    """Path for artist cover/banner images"""
    return generate_image_path(instance, filename, 'artist_covers')


def podcast_cover_path(instance, filename):
    """Path for podcast cover art"""
    return generate_image_path(instance, filename, 'podcast_covers')


def playlist_cover_path(instance, filename):
    """Path for playlist cover art"""
    return generate_image_path(instance, filename, 'playlist_covers')


class FileManager:
    """
    Centralized file management for audio processing and storage
    """

    def __init__(self, track):
        self.track = track
        self.track_id = str(track.id)
        self.raw_storage = get_storage_backend('raw')
        self.hls_storage = get_storage_backend('hls')
        self.failed_storage = get_storage_backend('failed')

    def get_raw_file_path(self):
        """Get the full path to the raw audio file"""
        if self.track.audio_file:
            return self.track.audio_file.path
        return None

    def get_hls_directory(self):
        """Get the HLS output directory for this track"""
        return os.path.join(settings.MEDIA_ROOT, 'hls', self.track_id)

    def get_hls_manifest_path(self):
        """Get path to the main HLS manifest file"""
        return os.path.join(self.get_hls_directory(), 'playlist.m3u8')

    def get_hls_metadata_path(self):
        """Get path to the metadata JSON file"""
        return os.path.join(self.get_hls_directory(), 'metadata.json')

    def create_hls_directory_structure(self):
        """
        Create the directory structure for HLS output
        Returns: dict with paths to quality directories
        """
        base_dir = self.get_hls_directory()

        directories = {
            'base': base_dir,
            'high': os.path.join(base_dir, 'high'),
            'med': os.path.join(base_dir, 'med'),
            'low': os.path.join(base_dir, 'low'),
        }

        for dir_path in directories.values():
            os.makedirs(dir_path, exist_ok=True)

        return directories

    def save_metadata(self, metadata_dict):
        """
        Save metadata JSON for the track

        Args:
            metadata_dict: Dictionary containing track metadata
        """
        metadata_path = self.get_hls_metadata_path()

        with open(metadata_path, 'w') as f:
            json.dump(metadata_dict, f, indent=2)

    def get_metadata(self):
        """
        Read metadata JSON for the track

        Returns:
            dict: Metadata dictionary or None if not found
        """
        metadata_path = self.get_hls_metadata_path()

        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return None

    def move_to_failed(self, reason=""):
        """
        Move failed processing files to failed directory

        Args:
            reason: Reason for failure
        """
        if not self.track.audio_file:
            return

        failed_dir = os.path.join(settings.MEDIA_ROOT, 'failed', self.track_id)
        os.makedirs(failed_dir, exist_ok=True)

        # Copy original file
        original_path = self.get_raw_file_path()
        if original_path and os.path.exists(original_path):
            failed_file_path = os.path.join(failed_dir, os.path.basename(original_path))
            shutil.copy2(original_path, failed_file_path)

        # Save failure log
        failure_log = {
            'track_id': self.track_id,
            'track_title': self.track.title,
            'artist': str(self.track.artist.stage_name),
            'reason': reason,
            'timestamp': str(timezone.now()),
            'original_file': str(self.track.audio_file),
        }

        log_path = os.path.join(failed_dir, 'failure_log.json')
        with open(log_path, 'w') as f:
            json.dump(failure_log, f, indent=2)

    def cleanup_raw_file(self):
        """Delete the raw file after successful processing"""
        if self.track.audio_file:
            try:
                self.track.audio_file.delete(save=False)
            except Exception as e:
                print(f"Error deleting raw file: {e}")

    def cleanup_all_files(self):
        """Delete all files associated with this track"""
        # Delete HLS directory
        hls_dir = self.get_hls_directory()
        if os.path.exists(hls_dir):
            shutil.rmtree(hls_dir)

        # Delete raw file
        self.cleanup_raw_file()

    def verify_hls_structure(self):
        """
        Verify that all HLS files are present and valid

        Returns:
            dict: Validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Check main manifest
        if not os.path.exists(self.get_hls_manifest_path()):
            results['valid'] = False
            results['errors'].append('Main playlist.m3u8 not found')

        # Check quality directories
        base_dir = self.get_hls_directory()
        for quality in ['high', 'med', 'low']:
            quality_dir = os.path.join(base_dir, quality)
            playlist_path = os.path.join(quality_dir, 'playlist.m3u8')

            if not os.path.exists(quality_dir):
                results['warnings'].append(f'{quality} quality directory not found')
            elif not os.path.exists(playlist_path):
                results['warnings'].append(f'{quality} playlist.m3u8 not found')
            else:
                # Count segments
                segments = [f for f in os.listdir(quality_dir) if f.endswith('.ts')]
                if len(segments) == 0:
                    results['errors'].append(f'{quality} has no segments')
                    results['valid'] = False

        # Check metadata
        if not os.path.exists(self.get_hls_metadata_path()):
            results['warnings'].append('metadata.json not found')

        return results

    @staticmethod
    def get_storage_stats():
        """
        Get storage statistics

        Returns:
            dict: Storage usage information
        """
        media_root = settings.MEDIA_ROOT

        def get_dir_size(path):
            """Calculate directory size"""
            total = 0
            try:
                for entry in os.scandir(path):
                    if entry.is_file():
                        total += entry.stat().st_size
                    elif entry.is_dir():
                        total += get_dir_size(entry.path)
            except Exception:
                pass
            return total

        stats = {
            'raw': get_dir_size(os.path.join(media_root, 'raw')),
            'hls': get_dir_size(os.path.join(media_root, 'hls')),
            'images': get_dir_size(os.path.join(media_root, 'images')),
            'failed': get_dir_size(os.path.join(media_root, 'failed')),
        }

        # Convert to MB
        stats = {k: v / (1024 * 1024) for k, v in stats.items()}
        stats['total'] = sum(stats.values())

        return stats