from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum
from django.utils.safestring import mark_safe
from .models import (
    Artist, Genre, Track, TrackDetail, Podcast, Album, Lyric,
    Playlist, PlaylistTrack, ListeningHistory, LikedTrack,
    LikedAlbum, LikedPodcast, Comment, CommentLike,
    FollowArtist, FollowPlaylist
)


class TrackDetailInline(admin.StackedInline):
    """Inline for track details"""
    model = TrackDetail
    extra = 0
    fields = (
        'release_type', 'album_name', 'track_number', 'disc_number',
        'total_tracks', 'podcast', 'episode_number', 'season_number',
        'description', 'producer', 'composer', 'label', 'copyright'
    )


class LyricInline(admin.TabularInline):
    """Inline for track lyrics"""
    model = Lyric
    extra = 0
    fields = ('language', 'is_synced', 'transcribed_by')
    readonly_fields = ('transcribed_by',)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'track_count', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at',)
    list_per_page = 50

    def track_count(self, obj):
        return obj.tracks.count()

    track_count.short_description = 'Tracks'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(track_count=Count('tracks'))


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = (
        'stage_name', 'user_link', 'is_verified', 'monthly_listeners',
        'track_count', 'follower_count', 'created_at'
    )
    list_filter = ('is_verified', 'created_at')
    search_fields = ('stage_name', 'user__name', 'user__email')
    readonly_fields = ('monthly_listeners', 'created_at', 'updated_at', 'profile_image_preview', 'cover_image_preview')
    list_per_page = 50

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'stage_name', 'bio')
        }),
        ('Images', {
            'fields': ('profile_image', 'profile_image_preview', 'cover_image', 'cover_image_preview')
        }),
        ('Status & Stats', {
            'fields': ('is_verified', 'monthly_listeners')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['verify_artists', 'unverify_artists']

    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:accounts_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.name)
        return '-'

    user_link.short_description = 'User'

    def track_count(self, obj):
        return obj.tracks.count()

    track_count.short_description = 'Tracks'

    def follower_count(self, obj):
        return obj.followers.count()

    follower_count.short_description = 'Followers'

    def profile_image_preview(self, obj):
        if obj.profile_image:
            return mark_safe(f'<img src="{obj.profile_image.url}" width="150" height="150" />')
        return 'No image'

    profile_image_preview.short_description = 'Profile Preview'

    def cover_image_preview(self, obj):
        if obj.cover_image:
            return mark_safe(f'<img src="{obj.cover_image.url}" width="300" height="150" />')
        return 'No image'

    cover_image_preview.short_description = 'Cover Preview'

    def verify_artists(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} artist(s) verified successfully.')

    verify_artists.short_description = 'Verify selected artists'

    def unverify_artists(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} artist(s) unverified.')

    unverify_artists.short_description = 'Unverify selected artists'


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'artist_link', 'content_type', 'status_badge',
        'play_count', 'like_count', 'comment_count', 'duration_display',
        'is_explicit', 'hls_processed', 'created_at'
    )
    list_filter = (
        'content_type', 'status', 'is_explicit', 'hls_processed',
        'is_public', 'created_at', 'release_date'
    )
    search_fields = ('title', 'artist__stage_name', 'isrc')
    readonly_fields = (
        'play_count', 'like_count', 'comment_count', 'slug',
        'created_at', 'updated_at', 'reviewed_by', 'reviewed_at',
        'cover_art_preview'
    )
    list_per_page = 50
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'content_type', 'artist', 'featured_artists')
        }),
        ('Audio Files', {
            'fields': ('audio_file', 'hls_manifest', 'hls_processed')
        }),
        ('Metadata', {
            'fields': ('duration', 'isrc', 'cover_art', 'cover_art_preview', 'genres')
        }),
        ('Stats', {
            'fields': ('play_count', 'like_count', 'comment_count')
        }),
        ('Review & Status', {
            'fields': ('status', 'review_notes', 'reviewed_by', 'reviewed_at')
        }),
        ('Release Settings', {
            'fields': ('is_explicit', 'release_date', 'is_public')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ('featured_artists', 'genres')
    inlines = [TrackDetailInline, LyricInline]
    actions = ['approve_tracks', 'reject_tracks', 'mark_as_processing']

    def artist_link(self, obj):
        url = reverse('admin:music_artist_change', args=[obj.artist.id])
        return format_html('<a href="{}">{}</a>', url, obj.artist.stage_name)

    artist_link.short_description = 'Artist'

    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'approved': '#28a745',
            'rejected': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )

    status_badge.short_description = 'Status'

    def duration_display(self, obj):
        if obj.duration:
            minutes, seconds = divmod(obj.duration, 60)
            return f'{int(minutes)}:{int(seconds):02d}'
        return '-'

    duration_display.short_description = 'Duration'

    def cover_art_preview(self, obj):
        if obj.cover_art:
            return mark_safe(f'<img src="{obj.cover_art.url}" width="200" height="200" />')
        return 'No cover art'

    cover_art_preview.short_description = 'Cover Art Preview'

    def approve_tracks(self, request, queryset):
        updated = queryset.update(status='approved', reviewed_by=request.user)
        self.message_user(request, f'{updated} track(s) approved successfully.')

    approve_tracks.short_description = 'Approve selected tracks'

    def reject_tracks(self, request, queryset):
        updated = queryset.update(status='rejected', reviewed_by=request.user)
        self.message_user(request, f'{updated} track(s) rejected.')

    reject_tracks.short_description = 'Reject selected tracks'

    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status='processing')
        self.message_user(request, f'{updated} track(s) marked as processing.')

    mark_as_processing.short_description = 'Mark as processing (HLS)'


@admin.register(TrackDetail)
class TrackDetailAdmin(admin.ModelAdmin):
    list_display = ('track_link', 'release_type', 'album_name', 'track_number', 'podcast_link')
    list_filter = ('release_type',)
    search_fields = ('track__title', 'album_name', 'podcast__name')
    readonly_fields = ('created_at', 'updated_at')

    def track_link(self, obj):
        url = reverse('admin:music_track_change', args=[obj.track.id])
        return format_html('<a href="{}">{}</a>', url, obj.track.title)

    track_link.short_description = 'Track'

    def podcast_link(self, obj):
        if obj.podcast:
            url = reverse('admin:music_podcast_change', args=[obj.podcast.id])
            return format_html('<a href="{}">{}</a>', url, obj.podcast.name)
        return '-'

    podcast_link.short_description = 'Podcast'


@admin.register(Podcast)
class PodcastAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'host_link', 'language', 'is_explicit',
        'is_active', 'subscriber_count', 'total_episodes', 'created_at'
    )
    list_filter = ('is_explicit', 'is_active', 'language', 'created_at')
    search_fields = ('name', 'host__stage_name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('subscriber_count', 'total_episodes', 'created_at', 'updated_at', 'cover_image_preview')
    filter_horizontal = ('genres',)
    list_per_page = 50

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'host', 'description')
        }),
        ('Cover Image', {
            'fields': ('cover_image', 'cover_image_preview')
        }),
        ('Podcast Settings', {
            'fields': ('language', 'is_explicit', 'website', 'rss_feed', 'genres')
        }),
        ('Stats', {
            'fields': ('subscriber_count', 'total_episodes')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def host_link(self, obj):
        url = reverse('admin:music_artist_change', args=[obj.host.id])
        return format_html('<a href="{}">{}</a>', url, obj.host.stage_name)

    host_link.short_description = 'Host'

    def cover_image_preview(self, obj):
        if obj.cover_image:
            return mark_safe(f'<img src="{obj.cover_image.url}" width="200" height="200" />')
        return 'No cover image'

    cover_image_preview.short_description = 'Cover Preview'


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'artist_link', 'album_type', 'release_date',
        'track_count', 'play_count', 'like_count', 'is_explicit', 'is_public'
    )
    list_filter = ('album_type', 'is_explicit', 'is_public', 'release_date')
    search_fields = ('title', 'artist__stage_name', 'upc')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('play_count', 'like_count', 'created_at', 'updated_at', 'cover_art_preview')
    filter_horizontal = ('genres',)
    date_hierarchy = 'release_date'
    list_per_page = 50

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'album_type', 'artist', 'description')
        }),
        ('Cover Art', {
            'fields': ('cover_art', 'cover_art_preview')
        }),
        ('Release Information', {
            'fields': ('release_date', 'label', 'copyright', 'upc')
        }),
        ('Categorization', {
            'fields': ('genres',)
        }),
        ('Stats', {
            'fields': ('play_count', 'like_count')
        }),
        ('Settings', {
            'fields': ('is_explicit', 'is_public')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def artist_link(self, obj):
        url = reverse('admin:music_artist_change', args=[obj.artist.id])
        return format_html('<a href="{}">{}</a>', url, obj.artist.stage_name)

    artist_link.short_description = 'Artist'

    def track_count(self, obj):
        return obj.trackdetail_set.count()

    track_count.short_description = 'Tracks'

    def cover_art_preview(self, obj):
        if obj.cover_art:
            return mark_safe(f'<img src="{obj.cover_art.url}" width="200" height="200" />')
        return 'No cover art'

    cover_art_preview.short_description = 'Cover Preview'


@admin.register(Lyric)
class LyricAdmin(admin.ModelAdmin):
    list_display = ('track_link', 'language', 'is_synced', 'transcribed_by_link', 'created_at')
    list_filter = ('language', 'is_synced', 'created_at')
    search_fields = ('track__title', 'language', 'content')
    readonly_fields = ('created_at', 'updated_at')

    def track_link(self, obj):
        url = reverse('admin:music_track_change', args=[obj.track.id])
        return format_html('<a href="{}">{}</a>', url, obj.track.title)

    track_link.short_description = 'Track'

    def transcribed_by_link(self, obj):
        if obj.transcribed_by:
            url = reverse('admin:accounts_user_change', args=[obj.transcribed_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.transcribed_by.name)
        return '-'

    transcribed_by_link.short_description = 'Transcribed By'


class PlaylistTrackInline(admin.TabularInline):
    """Inline for playlist tracks"""
    model = PlaylistTrack
    extra = 0
    fields = ('track', 'position', 'added_by', 'added_at')
    readonly_fields = ('added_by', 'added_at')
    ordering = ('position',)


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'user_link', 'privacy', 'is_collaborative',
        'track_count', 'follower_count', 'created_at'
    )
    list_filter = ('privacy', 'is_collaborative', 'created_at')
    search_fields = ('name', 'user__name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('follower_count', 'total_duration', 'created_at', 'updated_at', 'cover_image_preview')
    filter_horizontal = ('collaborators',)
    inlines = [PlaylistTrackInline]
    list_per_page = 50

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'user')
        }),
        ('Cover Image', {
            'fields': ('cover_image', 'cover_image_preview')
        }),
        ('Settings', {
            'fields': ('privacy', 'is_collaborative', 'collaborators')
        }),
        ('Stats', {
            'fields': ('follower_count', 'total_duration')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = 'Owner'

    def track_count(self, obj):
        return obj.playlist_tracks.count()

    track_count.short_description = 'Tracks'

    def cover_image_preview(self, obj):
        if obj.cover_image:
            return mark_safe(f'<img src="{obj.cover_image.url}" width="200" height="200" />')
        return 'No cover image'

    cover_image_preview.short_description = 'Cover Preview'


@admin.register(PlaylistTrack)
class PlaylistTrackAdmin(admin.ModelAdmin):
    list_display = ('playlist_link', 'track_link', 'position', 'added_by_link', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('playlist__name', 'track__title')
    readonly_fields = ('added_by', 'added_at')

    def playlist_link(self, obj):
        url = reverse('admin:music_playlist_change', args=[obj.playlist.id])
        return format_html('<a href="{}">{}</a>', url, obj.playlist.name)

    playlist_link.short_description = 'Playlist'

    def track_link(self, obj):
        url = reverse('admin:music_track_change', args=[obj.track.id])
        return format_html('<a href="{}">{}</a>', url, obj.track.title)

    track_link.short_description = 'Track'

    def added_by_link(self, obj):
        if obj.added_by:
            url = reverse('admin:accounts_user_change', args=[obj.added_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.added_by.name)
        return '-'

    added_by_link.short_description = 'Added By'


@admin.register(ListeningHistory)
class ListeningHistoryAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'track_link', 'played_at', 'duration_display', 'completed', 'source')
    list_filter = ('completed', 'source', 'played_at')
    search_fields = ('user__name', 'track__title')
    readonly_fields = ('played_at',)
    date_hierarchy = 'played_at'
    list_per_page = 100

    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = 'User'

    def track_link(self, obj):
        url = reverse('admin:music_track_change', args=[obj.track.id])
        return format_html('<a href="{}">{}</a>', url, obj.track.title)

    track_link.short_description = 'Track'

    def duration_display(self, obj):
        minutes, seconds = divmod(obj.duration_played, 60)
        return f'{int(minutes)}:{int(seconds):02d}'

    duration_display.short_description = 'Duration Played'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        'user_link', 'track_link', 'content_preview',
        'timestamp_display', 'like_count', 'reply_count',
        'is_pinned', 'is_deleted', 'created_at'
    )
    list_filter = ('is_pinned', 'is_deleted', 'created_at')
    search_fields = ('user__name', 'track__title', 'content')
    readonly_fields = ('like_count', 'reply_count', 'is_edited', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    list_per_page = 50

    fieldsets = (
        ('Comment Information', {
            'fields': ('user', 'track', 'content', 'timestamp', 'parent')
        }),
        ('Stats', {
            'fields': ('like_count', 'reply_count')
        }),
        ('Status', {
            'fields': ('is_edited', 'is_pinned', 'is_deleted')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['pin_comments', 'unpin_comments', 'delete_comments']

    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = 'User'

    def track_link(self, obj):
        url = reverse('admin:music_track_change', args=[obj.track.id])
        return format_html('<a href="{}">{}</a>', url, obj.track.title)

    track_link.short_description = 'Track'

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

    content_preview.short_description = 'Content'

    def timestamp_display(self, obj):
        if obj.timestamp:
            minutes, seconds = divmod(obj.timestamp, 60)
            return f'{int(minutes)}:{int(seconds):02d}'
        return '-'

    timestamp_display.short_description = 'At Time'

    def pin_comments(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f'{updated} comment(s) pinned.')

    pin_comments.short_description = 'Pin selected comments'

    def unpin_comments(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f'{updated} comment(s) unpinned.')

    unpin_comments.short_description = 'Unpin selected comments'

    def delete_comments(self, request, queryset):
        updated = queryset.update(is_deleted=True)
        self.message_user(request, f'{updated} comment(s) deleted.')

    delete_comments.short_description = 'Delete selected comments'


@admin.register(LikedTrack)
class LikedTrackAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'track_link', 'liked_at')
    list_filter = ('liked_at',)
    search_fields = ('user__name', 'track__title')
    readonly_fields = ('liked_at',)
    date_hierarchy = 'liked_at'
    list_per_page = 100

    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = 'User'

    def track_link(self, obj):
        url = reverse('admin:music_track_change', args=[obj.track.id])
        return format_html('<a href="{}">{}</a>', url, obj.track.title)

    track_link.short_description = 'Track'


@admin.register(LikedAlbum)
class LikedAlbumAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'album_link', 'liked_at')
    list_filter = ('liked_at',)
    search_fields = ('user__name', 'album__title')
    readonly_fields = ('liked_at',)
    date_hierarchy = 'liked_at'
    list_per_page = 100

    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = 'User'

    def album_link(self, obj):
        url = reverse('admin:music_album_change', args=[obj.album.id])
        return format_html('<a href="{}">{}</a>', url, obj.album.title)

    album_link.short_description = 'Album'


@admin.register(LikedPodcast)
class LikedPodcastAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'podcast_link', 'subscribed_at')
    list_filter = ('subscribed_at',)
    search_fields = ('user__name', 'podcast__name')
    readonly_fields = ('subscribed_at',)
    date_hierarchy = 'subscribed_at'
    list_per_page = 100

    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = 'User'

    def podcast_link(self, obj):
        url = reverse('admin:music_podcast_change', args=[obj.podcast.id])
        return format_html('<a href="{}">{}</a>', url, obj.podcast.name)

    podcast_link.short_description = 'Podcast'


@admin.register(FollowArtist)
class FollowArtistAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'artist_link', 'followed_at')
    list_filter = ('followed_at',)
    search_fields = ('user__name', 'artist__stage_name')
    readonly_fields = ('followed_at',)
    date_hierarchy = 'followed_at'
    list_per_page = 100

    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = 'User'

    def artist_link(self, obj):
        url = reverse('admin:music_artist_change', args=[obj.artist.id])
        return format_html('<a href="{}">{}</a>', url, obj.artist.stage_name)

    artist_link.short_description = 'Artist'


@admin.register(FollowPlaylist)
class FollowPlaylistAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'playlist_link', 'followed_at')
    list_filter = ('followed_at',)
    search_fields = ('user__name', 'playlist__name')
    readonly_fields = ('followed_at',)
    date_hierarchy = 'followed_at'
    list_per_page = 100

    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = 'User'

    def playlist_link(self, obj):
        url = reverse('admin:music_playlist_change', args=[obj.playlist.id])
        return format_html('<a href="{}">{}</a>', url, obj.playlist.name)

    playlist_link.short_description = 'Playlist'


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'comment_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__name', 'comment__content')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 100

    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = 'User'

    def comment_preview(self, obj):
        preview = obj.comment.content[:30] + '...' if len(obj.comment.content) > 30 else obj.comment.content
        url = reverse('admin:music_comment_change', args=[obj.comment.id])
        return format_html('<a href="{}">{}</a>', url, preview)

    comment_preview.short_description = 'Comment'


# Customize admin site
admin.site.site_header = 'Music Streaming Admin'
admin.site.site_title = 'Music Streaming Admin Portal'
admin.site.index_title = 'Welcome to Music Streaming Administration'