# =================================================================
# Signal handlers for file cleanup
# signals.py
# =================================================================

from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from .models import Track, Artist, Album, Podcast, Playlist


@receiver(pre_delete, sender=Track)
def delete_track_files(sender, instance, **kwargs):
    """Delete all files associated with a track before deleting the track"""
    file_manager = instance.get_file_manager()
    file_manager.cleanup_all_files()


@receiver(post_delete, sender=Artist)
def delete_artist_images(sender, instance, **kwargs):
    """Delete artist images when artist is deleted"""
    if instance.profile_image:
        instance.profile_image.delete(save=False)
    if instance.cover_image:
        instance.cover_image.delete(save=False)


@receiver(post_delete, sender=Album)
def delete_album_cover(sender, instance, **kwargs):
    """Delete album cover when album is deleted"""
    if instance.cover_art:
        instance.cover_art.delete(save=False)


@receiver(post_delete, sender=Podcast)
def delete_podcast_cover(sender, instance, **kwargs):
    """Delete podcast cover when podcast is deleted"""
    if instance.cover_image:
        instance.cover_image.delete(save=False)


@receiver(post_delete, sender=Playlist)
def delete_playlist_cover(sender, instance, **kwargs):
    """Delete playlist cover when playlist is deleted"""
    if instance.cover_image:
        instance.cover_image.delete(save=False)