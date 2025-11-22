# tasks.py - Celery tasks for audio processing
# =================================================================

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import Track
from .utils.file_handlers import FileManager
import subprocess
import os
import json
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_track_to_hls(self, track_id):
    """
    Process an audio track to HLS format with multiple quality levels

    Args:
        track_id: UUID of the track to process
    """
    try:
        track = Track.objects.get(id=track_id)
        logger.info(f"Starting HLS processing for track: {track.title} ({track_id})")

        # Update status
        track.status = 'processing'
        track.save(update_fields=['status'])

        # Initialize file manager
        file_manager = FileManager(track)

        # Check if raw file exists
        raw_file_path = file_manager.get_raw_file_path()
        if not raw_file_path or not os.path.exists(raw_file_path):
            raise FileNotFoundError(f"Raw audio file not found: {raw_file_path}")

        # Create directory structure
        directories = file_manager.create_hls_directory_structure()

        # Extract audio metadata
        metadata = extract_audio_metadata(raw_file_path)

        # Process each quality level
        qualities = settings.HLS_QUALITIES

        for quality_name, quality_settings in qualities.items():
            logger.info(f"Processing {quality_name} quality...")

            success = process_quality_level(
                input_file=raw_file_path,
                output_dir=directories[quality_name],
                bitrate=quality_settings['bitrate'],
                sample_rate=quality_settings['sample_rate']
            )

            if not success:
                raise Exception(f"Failed to process {quality_name} quality")

        # Create master playlist
        create_master_playlist(directories['base'])

        # Copy original file to HLS directory
        original_copy_path = os.path.join(directories['base'], f"{track_id}.m4a")
        subprocess.run([
            'ffmpeg', '-i', raw_file_path,
            '-c:a', 'aac', '-b:a', '320k',
            original_copy_path
        ], check=True)

        # Save metadata
        metadata.update({
            'track_id': str(track_id),
            'track_title': track.title,
            'artist': track.artist.stage_name,
            'processed_at': str(timezone.now()),
            'qualities': list(qualities.keys())
        })
        file_manager.save_metadata(metadata)

        # Update track in database
        track.hls_manifest = f"hls/{track_id}/playlist.m3u8"
        track.hls_processed = True
        track.status = 'approved'
        track.duration = int(float(metadata.get('duration', 0)))
        track.save(update_fields=['hls_manifest', 'hls_processed', 'status', 'duration'])

        # Verify HLS structure
        verification = file_manager.verify_hls_structure()
        if not verification['valid']:
            raise Exception(f"HLS verification failed: {verification['errors']}")

        # Optionally delete raw file to save space
        # file_manager.cleanup_raw_file()

        logger.info(f"Successfully processed track: {track.title}")
        return {
            'status': 'success',
            'track_id': str(track_id),
            'manifest_url': track.get_hls_url()
        }

    except Track.DoesNotExist:
        logger.error(f"Track not found: {track_id}")
        return {'status': 'error', 'message': 'Track not found'}

    except Exception as e:
        logger.error(f"Error processing track {track_id}: {str(e)}")

        # Move to failed directory
        try:
            track = Track.objects.get(id=track_id)
            file_manager = FileManager(track)
            file_manager.move_to_failed(reason=str(e))

            track.status = 'rejected'
            track.review_notes = f"Processing failed: {str(e)}"
            track.save(update_fields=['status', 'review_notes'])
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {str(cleanup_error)}")

        # Retry task
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


def extract_audio_metadata(audio_file):
    """
    Extract metadata from audio file using ffprobe

    Args:
        audio_file: Path to audio file

    Returns:
        dict: Audio metadata
    """
    try:
        result = subprocess.run([
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            audio_file
        ], capture_output=True, text=True, check=True)

        data = json.loads(result.stdout)

        format_info = data.get('format', {})
        audio_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), {})

        return {
            'duration': format_info.get('duration', '0'),
            'bitrate': format_info.get('bit_rate', '0'),
            'sample_rate': audio_stream.get('sample_rate', '0'),
            'channels': audio_stream.get('channels', 2),
            'codec': audio_stream.get('codec_name', 'unknown'),
            'format': format_info.get('format_name', 'unknown')
        }

    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        return {}


def process_quality_level(input_file, output_dir, bitrate, sample_rate):
    """
    Process audio file to specific quality level

    Args:
        input_file: Path to input audio file
        output_dir: Directory for output files
        bitrate: Target bitrate (e.g., '320k')
        sample_rate: Target sample rate (e.g., '48000')

    Returns:
        bool: Success status
    """
    try:
        playlist_path = os.path.join(output_dir, 'playlist.m3u8')
        segment_pattern = os.path.join(output_dir, 'segment_%03d.ts')

        # FFmpeg command for HLS conversion
        command = [
            'ffmpeg',
            '-i', input_file,
            '-c:a', 'aac',
            '-b:a', bitrate,
            '-ar', sample_rate,
            '-f', 'hls',
            '-hls_time', str(settings.HLS_SEGMENT_DURATION),
            '-hls_playlist_type', 'vod',
            '-hls_segment_filename', segment_pattern,
            playlist_path
        ]

        # Run FFmpeg
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        logger.info(f"Successfully created HLS files in {output_dir}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error processing quality level: {e}")
        return False


def create_master_playlist(base_dir):
    """
    Create master HLS playlist that references all quality levels

    Args:
        base_dir: Base directory containing quality subdirectories
    """
    master_playlist_path = os.path.join(base_dir, 'playlist.m3u8')

    qualities_config = {
        'high': {'bandwidth': 320000, 'name': 'High Quality'},
        'med': {'bandwidth': 192000, 'name': 'Medium Quality'},
        'low': {'bandwidth': 128000, 'name': 'Low Quality'},
    }

    with open(master_playlist_path, 'w') as f:
        f.write('#EXTM3U\n')
        f.write('#EXT-X-VERSION:3\n\n')

        for quality, config in qualities_config.items():
            quality_dir = os.path.join(base_dir, quality)
            quality_playlist = os.path.join(quality_dir, 'playlist.m3u8')

            if os.path.exists(quality_playlist):
                f.write(f'#EXT-X-STREAM-INF:BANDWIDTH={config["bandwidth"]},NAME="{config["name"]}"\n')
                f.write(f'{quality}/playlist.m3u8\n\n')

    logger.info(f"Created master playlist: {master_playlist_path}")


@shared_task
def cleanup_old_failed_files():
    """
    Cleanup old failed files (older than 30 days)
    Run this as a periodic task
    """
    import shutil
    from datetime import timedelta

    failed_dir = os.path.join(settings.MEDIA_ROOT, 'failed')

    if not os.path.exists(failed_dir):
        return

    cutoff_date = timezone.now() - timedelta(days=30)

    for item in os.listdir(failed_dir):
        item_path = os.path.join(failed_dir, item)

        if os.path.isdir(item_path):
            # Check failure_log.json for timestamp
            log_path = os.path.join(item_path, 'failure_log.json')

            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r') as f:
                        log_data = json.load(f)

                    timestamp = timezone.datetime.fromisoformat(log_data['timestamp'])

                    if timestamp < cutoff_date:
                        shutil.rmtree(item_path)
                        logger.info(f"Deleted old failed directory: {item_path}")

                except Exception as e:
                    logger.error(f"Error processing failed directory {item_path}: {e}")


@shared_task
def generate_waveform_data(track_id):
    """
    Generate waveform data for audio visualization

    Args:
        track_id: UUID of the track
    """
    try:
        track = Track.objects.get(id=track_id)
        file_manager = FileManager(track)

        audio_file = file_manager.get_raw_file_path()
        if not audio_file or not os.path.exists(audio_file):
            logger.error(f"Audio file not found for track {track_id}")
            return

        output_file = os.path.join(file_manager.get_hls_directory(), 'waveform.json')

        # Generate waveform using ffmpeg
        command = [
            'ffmpeg',
            '-i', audio_file,
            '-af', 'aformat=channel_layouts=mono,compand,showwavespic=s=1920x200:colors=0099ff',
            '-frames:v', '1',
            '-f', 'null',
            '-'
        ]

        # For now, create a simple placeholder
        # In production, use a proper waveform generation library
        waveform_data = {
            'track_id': str(track_id),
            'samples': [],  # Add actual waveform samples here
            'generated_at': str(timezone.now())
        }

        with open(output_file, 'w') as f:
            json.dump(waveform_data, f)

        logger.info(f"Generated waveform for track {track_id}")

    except Track.DoesNotExist:
        logger.error(f"Track not found: {track_id}")
    except Exception as e:
        logger.error(f"Error generating waveform for track {track_id}: {e}")
