from django.db import models
from mwonya_apps.authentication.models import User

from django.core.validators import FileExtensionValidator

from mwonya_core import settings
from mwonya_apps.creator.utils.file_handlers import (
    generate_track_path,
    track_cover_path,
    album_cover_path,
    artist_profile_path,
    artist_cover_path,
    podcast_cover_path,
    playlist_cover_path
)
from mwonya_apps.creator.utils.storage import get_storage_backend
import uuid


class Artist(models.Model):
    """Updated Artist model with proper file paths"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='artist_profile', null=True, blank=True)
    stage_name = models.CharField(max_length=255, unique=True, db_index=True)
    bio = models.TextField(blank=True, null=True)

    # Updated image fields with custom upload paths and storage
    profile_image = models.ImageField(
        upload_to=artist_profile_path,
        blank=True,
        null=True,
        storage=get_storage_backend('image'),
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )
    cover_image = models.ImageField(
        upload_to=artist_cover_path,
        blank=True,
        null=True,
        storage=get_storage_backend('image'),
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )

    is_verified = models.BooleanField(default=False)
    monthly_listeners = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-monthly_listeners', 'stage_name']

    def __str__(self):
        return self.stage_name


class Genre(models.Model):
    """Model for music and podcast genres"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='genres/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Track(models.Model):
    """Updated Track model with proper file paths"""
    CONTENT_TYPE_CHOICES = [
        ('music', 'Music'),
        ('podcast', 'Podcast Episode'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('processing', 'Processing (HLS)'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='music')

    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='tracks')
    featured_artists = models.ManyToManyField(Artist, related_name='featured_tracks', blank=True)

    # Audio files with custom storage
    audio_file = models.FileField(
        upload_to=generate_track_path,
        blank=True,
        null=True,
        storage=get_storage_backend('raw'),
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'm4a', 'wav', 'flac', 'aac', 'ogg'])],
        help_text="Original uploaded audio file"
    )

    # HLS manifest path (stored as relative path)
    hls_manifest = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Relative path to HLS manifest file"
    )
    hls_processed = models.BooleanField(default=False)

    duration = models.PositiveIntegerField(help_text="Duration in seconds", null=True, blank=True)
    isrc = models.CharField(max_length=12, blank=True, null=True, unique=True)

    # Cover art with custom storage
    cover_art = models.ImageField(
        upload_to=track_cover_path,
        blank=True,
        null=True,
        storage=get_storage_backend('image'),
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )

    genres = models.ManyToManyField(Genre, related_name='tracks', blank=True)

    play_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    review_notes = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='reviewed_tracks')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    is_explicit = models.BooleanField(default=False)
    release_date = models.DateField(null=True, blank=True)
    is_public = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.artist.stage_name}"

    def get_hls_url(self):
        """Get the URL to the HLS manifest"""
        if self.hls_manifest:
            if settings.USE_S3_STORAGE:
                return f"{settings.MEDIA_URL}{self.hls_manifest}"
            return f"{settings.MEDIA_URL}{self.hls_manifest}"
        return None

    def get_file_manager(self):
        """Get FileManager instance for this track"""
        from utils.file_handlers import FileManager
        return FileManager(self)


class TrackDetail(models.Model):
    """Stores specific details for different release types"""
    RELEASE_TYPE_CHOICES = [
        ('single', 'Single'),
        ('album', 'Album'),
        ('ep', 'EP'),
        ('mixtape', 'Mixtape'),
        ('episode', 'Podcast Episode'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    track = models.OneToOneField(Track, on_delete=models.CASCADE, related_name='detail')
    release_type = models.CharField(max_length=20, choices=RELEASE_TYPE_CHOICES, db_index=True)

    # For albums, EPs, mixtapes
    album_name = models.CharField(max_length=255, blank=True, null=True)
    track_number = models.PositiveIntegerField(null=True, blank=True)
    disc_number = models.PositiveIntegerField(default=1, null=True, blank=True)
    total_tracks = models.PositiveIntegerField(null=True, blank=True)

    # For podcast episodes
    podcast = models.ForeignKey('Podcast', on_delete=models.CASCADE, null=True, blank=True, related_name='episodes')
    episode_number = models.PositiveIntegerField(null=True, blank=True)
    season_number = models.PositiveIntegerField(null=True, blank=True)

    # Additional metadata
    description = models.TextField(blank=True, null=True)
    producer = models.CharField(max_length=255, blank=True, null=True)
    composer = models.CharField(max_length=255, blank=True, null=True)
    label = models.CharField(max_length=255, blank=True, null=True)
    copyright = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['release_type', 'album_name']),
            models.Index(fields=['podcast', 'episode_number']),
        ]

    def __str__(self):
        if self.release_type == 'episode':
            return f"{self.podcast.name if self.podcast else 'Unknown'} - Episode {self.episode_number}"
        return f"{self.track.title} ({self.release_type})"


class Podcast(models.Model):
    """Updated Podcast model with proper file paths"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    slug = models.SlugField(max_length=255, unique=True)
    host = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='podcasts')
    description = models.TextField()

    # Cover image with custom storage
    cover_image = models.ImageField(
        upload_to=podcast_cover_path,
        storage=get_storage_backend('image'),
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )

    language = models.CharField(max_length=10, default='en')
    is_explicit = models.BooleanField(default=False)
    website = models.URLField(blank=True, null=True)
    rss_feed = models.URLField(blank=True, null=True)

    genres = models.ManyToManyField(Genre, related_name='podcasts')

    subscriber_count = models.PositiveIntegerField(default=0)
    total_episodes = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Album(models.Model):
    """Updated Album model with proper file paths"""
    ALBUM_TYPE_CHOICES = [
        ('album', 'Album'),
        ('ep', 'EP'),
        ('mixtape', 'Mixtape'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, blank=True)
    album_type = models.CharField(max_length=20, choices=ALBUM_TYPE_CHOICES, default='album')
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='albums')

    description = models.TextField(blank=True, null=True)

    # Cover art with custom storage
    cover_art = models.ImageField(
        upload_to=album_cover_path,
        storage=get_storage_backend('image'),
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )

    release_date = models.DateField()
    label = models.CharField(max_length=255, blank=True, null=True)
    copyright = models.CharField(max_length=255, blank=True, null=True)
    upc = models.CharField(max_length=13, blank=True, null=True, unique=True)

    genres = models.ManyToManyField(Genre, related_name='albums')

    play_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)

    is_explicit = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-release_date']

    def __str__(self):
        return f"{self.title} - {self.artist.stage_name}"


class Lyric(models.Model):
    """Model for track lyrics in multiple languages"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='lyrics')
    language = models.CharField(max_length=10, db_index=True, help_text="Language code (e.g., 'en', 'es', 'fr')")
    content = models.TextField(help_text="Lyrics content with timestamps if available")
    is_synced = models.BooleanField(default=False, help_text="Whether lyrics have timestamps")

    # Credit
    transcribed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['track', 'language']
        indexes = [
            models.Index(fields=['track', 'language']),
        ]

    def __str__(self):
        return f"{self.track.title} - {self.language}"


class Playlist(models.Model):
    """Updated Playlist model with proper file paths"""
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('unlisted', 'Unlisted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playlists')

    # Cover image with custom storage
    cover_image = models.ImageField(
        upload_to=playlist_cover_path,
        blank=True,
        null=True,
        storage=get_storage_backend('image'),
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )

    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    is_collaborative = models.BooleanField(default=False)
    collaborators = models.ManyToManyField(User, related_name='collaborative_playlists', blank=True)

    follower_count = models.PositiveIntegerField(default=0)
    total_duration = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} by {self.user.name}"


class PlaylistTrack(models.Model):
    """Through model for playlist tracks with ordering"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='playlist_tracks')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='in_playlists')
    position = models.PositiveIntegerField()
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position']
        unique_together = ['playlist', 'track']
        indexes = [
            models.Index(fields=['playlist', 'position']),
        ]

    def __str__(self):
        return f"{self.track.title} in {self.playlist.name}"


class ListeningHistory(models.Model):
    """Model for tracking user listening history"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listening_history')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='history_entries')

    # Listening details
    played_at = models.DateTimeField(auto_now_add=True, db_index=True)
    duration_played = models.PositiveIntegerField(help_text="Duration played in seconds")
    completed = models.BooleanField(default=False, help_text="Whether track was played to completion")

    # Context
    source = models.CharField(max_length=50, blank=True, null=True,
                              help_text="Where track was played from (playlist, album, etc.)")
    device = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-played_at']
        indexes = [
            models.Index(fields=['user', '-played_at']),
            models.Index(fields=['track', '-played_at']),
        ]
        verbose_name_plural = "Listening histories"

    def __str__(self):
        return f"{self.user.name} played {self.track.title}"


class LikedTrack(models.Model):
    """Model for user liked tracks"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liked_tracks')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='likes')
    liked_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ['user', 'track']
        ordering = ['-liked_at']
        indexes = [
            models.Index(fields=['user', '-liked_at']),
        ]

    def __str__(self):
        return f"{self.user.name} likes {self.track.title}"


class LikedAlbum(models.Model):
    """Model for user liked albums"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liked_albums')
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='likes')
    liked_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ['user', 'album']
        ordering = ['-liked_at']
        indexes = [
            models.Index(fields=['user', '-liked_at']),
        ]

    def __str__(self):
        return f"{self.user.name} likes {self.album.title}"


class LikedPodcast(models.Model):
    """Model for user followed/liked podcasts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liked_podcasts')
    podcast = models.ForeignKey(Podcast, on_delete=models.CASCADE, related_name='subscribers')
    subscribed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ['user', 'podcast']
        ordering = ['-subscribed_at']
        indexes = [
            models.Index(fields=['user', '-subscribed_at']),
        ]

    def __str__(self):
        return f"{self.user.name} subscribed to {self.podcast.name}"


class Comment(models.Model):
    """Model for comments on tracks"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='comments')

    # Comment content
    content = models.TextField()
    timestamp = models.PositiveIntegerField(null=True, blank=True,
                                            help_text="Timestamp in track (seconds) for time-based comments")

    # Threading
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    # Stats
    like_count = models.PositiveIntegerField(default=0)
    reply_count = models.PositiveIntegerField(default=0)

    # Moderation
    is_edited = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['track', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['parent', '-created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.user.name} on {self.track.title}"


class CommentLike(models.Model):
    """Model for comment likes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_likes')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'comment']
        indexes = [
            models.Index(fields=['comment', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.name} likes comment by {self.comment.user.name}"


class FollowArtist(models.Model):
    """Model for users following artists"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_artists')
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='followers')
    followed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ['user', 'artist']
        ordering = ['-followed_at']
        indexes = [
            models.Index(fields=['user', '-followed_at']),
        ]

    def __str__(self):
        return f"{self.user.name} follows {self.artist.stage_name}"


class FollowPlaylist(models.Model):
    """Model for users following playlists"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followed_playlists')
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='followers')
    followed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ['user', 'playlist']
        ordering = ['-followed_at']
        indexes = [
            models.Index(fields=['user', '-followed_at']),
        ]

    def __str__(self):
        return f"{self.user.name} follows {self.playlist.name}"