# =================================================================
# Management command to migrate files
# management/commands/migrate_to_s3.py
# =================================================================

from django.core.management.base import BaseCommand
from django.conf import settings
from mwonya_apps.creator.models import Track, Artist, Album, Podcast, Playlist
from mwonya_apps.creator.utils.file_handlers import FileManager
import os
import boto3
from pathlib import Path


class Command(BaseCommand):
    help = 'Migrate files from local storage to S3'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate migration without actually moving files',
        )
        parser.add_argument(
            '--file-type',
            type=str,
            choices=['all', 'audio', 'images'],
            default='all',
            help='Type of files to migrate',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        file_type = options['file_type']

        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode - no files will be moved'))

        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        if file_type in ['all', 'audio']:
            self.migrate_audio_files(s3_client, bucket_name, dry_run)

        if file_type in ['all', 'images']:
            self.migrate_image_files(s3_client, bucket_name, dry_run)

        self.stdout.write(self.style.SUCCESS('Migration completed!'))

    def migrate_audio_files(self, s3_client, bucket_name, dry_run):
        """Migrate audio files to S3"""
        self.stdout.write('Migrating audio files...')

        tracks = Track.objects.filter(hls_processed=True)
        total = tracks.count()

        for index, track in enumerate(tracks, 1):
            self.stdout.write(f'Processing track {index}/{total}: {track.title}')

            file_manager = FileManager(track)
            hls_dir = file_manager.get_hls_directory()

            if not os.path.exists(hls_dir):
                self.stdout.write(self.style.WARNING(f'  HLS directory not found: {hls_dir}'))
                continue

            # Upload all HLS files
            for root, dirs, files in os.walk(hls_dir):
                for file in files:
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, settings.MEDIA_ROOT)
                    s3_key = relative_path.replace('\\', '/')

                    if not dry_run:
                        try:
                            s3_client.upload_file(
                                local_path,
                                bucket_name,
                                s3_key,
                                ExtraArgs={'ContentType': self.get_content_type(file)}
                            )
                            self.stdout.write(f'  Uploaded: {s3_key}')
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'  Error uploading {s3_key}: {e}'))
                    else:
                        self.stdout.write(f'  Would upload: {s3_key}')

    def migrate_image_files(self, s3_client, bucket_name, dry_run):
        """Migrate image files to S3"""
        self.stdout.write('Migrating image files...')

        # Collect all image fields
        image_fields = [
            (Track, 'cover_art'),
            (Artist, 'profile_image'),
            (Artist, 'cover_image'),
            (Album, 'cover_art'),
            (Podcast, 'cover_image'),
            (Playlist, 'cover_image'),
        ]

        for model, field_name in image_fields:
            self.stdout.write(f'Processing {model.__name__}.{field_name}...')

            queryset = model.objects.exclude(**{field_name: ''})

            for obj in queryset:
                image_field = getattr(obj, field_name)

                if image_field and hasattr(image_field, 'path'):
                    local_path = image_field.path

                    if os.path.exists(local_path):
                        relative_path = os.path.relpath(local_path, settings.MEDIA_ROOT)
                        s3_key = relative_path.replace('\\', '/')

                        if not dry_run:
                            try:
                                s3_client.upload_file(
                                    local_path,
                                    bucket_name,
                                    s3_key,
                                    ExtraArgs={'ContentType': self.get_content_type(local_path)}
                                )
                                self.stdout.write(f'  Uploaded: {s3_key}')
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f'  Error: {e}'))
                        else:
                            self.stdout.write(f'  Would upload: {s3_key}')

    def get_content_type(self, filename):
        """Get content type based on file extension"""
        ext = filename.split('.')[-1].lower()
        content_types = {
            'm3u8': 'application/vnd.apple.mpegurl',
            'ts': 'video/mp2t',
            'm4a': 'audio/mp4',
            'mp3': 'audio/mpeg',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'webp': 'image/webp',
            'json': 'application/json',
        }
        return content_types.get(ext, 'application/octet-stream')