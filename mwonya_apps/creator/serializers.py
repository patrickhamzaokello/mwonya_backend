from rest_framework import serializers
from .models import (
    Artist, Genre, Track, TrackDetail, Podcast, Album, Lyric,
    Playlist, PlaylistTrack, ListeningHistory, LikedTrack,
    LikedAlbum, LikedPodcast, Comment, CommentLike,
    FollowArtist, FollowPlaylist
)
from django.contrib.auth import get_user_model

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info for nested serializers"""

    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'email']
        read_only_fields = fields


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name', 'slug', 'description', 'image', 'created_at']
        read_only_fields = ['id', 'created_at']


class ArtistMinimalSerializer(serializers.ModelSerializer):
    """Minimal artist info for nested serializers"""

    class Meta:
        model = Artist
        fields = ['id', 'stage_name', 'profile_image', 'is_verified']
        read_only_fields = fields


class ArtistSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    is_following = serializers.SerializerMethodField()
    follower_count = serializers.SerializerMethodField()

    class Meta:
        model = Artist
        fields = [
            'id', 'user', 'stage_name', 'bio', 'profile_image',
            'cover_image', 'is_verified', 'monthly_listeners',
            'is_following', 'follower_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_verified', 'monthly_listeners', 'created_at', 'updated_at']

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return FollowArtist.objects.filter(user=request.user, artist=obj).exists()
        return False

    def get_follower_count(self, obj):
        return obj.followers.count()


class LyricSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lyric
        fields = ['id', 'language', 'content', 'is_synced', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrackDetailSerializer(serializers.ModelSerializer):
    podcast_name = serializers.CharField(source='podcast.name', read_only=True)

    class Meta:
        model = TrackDetail
        fields = [
            'id', 'release_type', 'album_name', 'track_number',
            'disc_number', 'total_tracks', 'podcast', 'podcast_name',
            'episode_number', 'season_number', 'description',
            'producer', 'composer', 'label', 'copyright'
        ]
        read_only_fields = ['id']


class TrackListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for track lists"""
    artist = ArtistMinimalSerializer(read_only=True)
    featured_artists = ArtistMinimalSerializer(many=True, read_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Track
        fields = [
            'id', 'title', 'slug', 'content_type', 'artist',
            'featured_artists', 'cover_art', 'duration', 'genres',
            'play_count', 'like_count', 'is_explicit', 'release_date',
            'is_liked', 'status', 'created_at'
        ]
        read_only_fields = fields

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return LikedTrack.objects.filter(user=request.user, track=obj).exists()
        return False


class TrackDetailedSerializer(serializers.ModelSerializer):
    """Detailed serializer with all track information"""
    artist = ArtistSerializer(read_only=True)
    artist_id = serializers.UUIDField(write_only=True)
    featured_artists = ArtistMinimalSerializer(many=True, read_only=True)
    featured_artist_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    genres = GenreSerializer(many=True, read_only=True)
    genre_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    detail = TrackDetailSerializer(required=False)
    lyrics = LyricSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Track
        fields = [
            'id', 'title', 'slug', 'content_type', 'artist', 'artist_id',
            'featured_artists', 'featured_artist_ids', 'audio_file',
            'hls_manifest', 'hls_processed', 'duration', 'isrc',
            'cover_art', 'genres', 'genre_ids', 'play_count',
            'like_count', 'comment_count', 'status', 'review_notes',
            'is_explicit', 'release_date', 'is_public', 'detail',
            'lyrics', 'is_liked', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'hls_manifest', 'hls_processed', 'play_count',
            'like_count', 'comment_count', 'status', 'created_at', 'updated_at'
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return LikedTrack.objects.filter(user=request.user, track=obj).exists()
        return False

    def create(self, validated_data):
        featured_artist_ids = validated_data.pop('featured_artist_ids', [])
        genre_ids = validated_data.pop('genre_ids', [])
        detail_data = validated_data.pop('detail', None)

        track = Track.objects.create(**validated_data)

        if featured_artist_ids:
            track.featured_artists.set(featured_artist_ids)
        if genre_ids:
            track.genres.set(genre_ids)
        if detail_data:
            TrackDetail.objects.create(track=track, **detail_data)

        return track

    def update(self, instance, validated_data):
        featured_artist_ids = validated_data.pop('featured_artist_ids', None)
        genre_ids = validated_data.pop('genre_ids', None)
        detail_data = validated_data.pop('detail', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if featured_artist_ids is not None:
            instance.featured_artists.set(featured_artist_ids)
        if genre_ids is not None:
            instance.genres.set(genre_ids)
        if detail_data:
            TrackDetail.objects.update_or_create(
                track=instance, defaults=detail_data
            )

        return instance


class PodcastSerializer(serializers.ModelSerializer):
    host = ArtistMinimalSerializer(read_only=True)
    host_id = serializers.UUIDField(write_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    genre_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Podcast
        fields = [
            'id', 'name', 'slug', 'host', 'host_id', 'description',
            'cover_image', 'language', 'is_explicit', 'website',
            'rss_feed', 'genres', 'genre_ids', 'subscriber_count',
            'total_episodes', 'is_active', 'is_subscribed',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'subscriber_count', 'total_episodes',
            'created_at', 'updated_at'
        ]

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return LikedPodcast.objects.filter(user=request.user, podcast=obj).exists()
        return False

    def create(self, validated_data):
        genre_ids = validated_data.pop('genre_ids', [])
        podcast = Podcast.objects.create(**validated_data)
        if genre_ids:
            podcast.genres.set(genre_ids)
        return podcast

    def update(self, instance, validated_data):
        genre_ids = validated_data.pop('genre_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if genre_ids is not None:
            instance.genres.set(genre_ids)
        return instance


class AlbumSerializer(serializers.ModelSerializer):
    artist = ArtistMinimalSerializer(read_only=True)
    artist_id = serializers.UUIDField(write_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    genre_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    tracks = TrackListSerializer(many=True, read_only=True, source='trackdetail_set.track')
    track_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Album
        fields = [
            'id', 'title', 'slug', 'album_type', 'artist', 'artist_id',
            'description', 'cover_art', 'release_date', 'label',
            'copyright', 'upc', 'genres', 'genre_ids', 'play_count',
            'like_count', 'is_explicit', 'is_public', 'tracks',
            'track_count', 'is_liked', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'play_count', 'like_count',
            'created_at', 'updated_at'
        ]

    def get_track_count(self, obj):
        return obj.trackdetail_set.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return LikedAlbum.objects.filter(user=request.user, album=obj).exists()
        return False


class PlaylistTrackSerializer(serializers.ModelSerializer):
    track = TrackListSerializer(read_only=True)
    track_id = serializers.UUIDField(write_only=True)
    added_by = UserMinimalSerializer(read_only=True)

    class Meta:
        model = PlaylistTrack
        fields = ['id', 'track', 'track_id', 'position', 'added_by', 'added_at']
        read_only_fields = ['id', 'added_by', 'added_at']


class PlaylistSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    tracks = PlaylistTrackSerializer(many=True, read_only=True, source='playlist_tracks')
    track_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = [
            'id', 'name', 'slug', 'description', 'user', 'cover_image',
            'privacy', 'is_collaborative', 'collaborators', 'follower_count',
            'total_duration', 'tracks', 'track_count', 'is_following',
            'is_owner', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'user', 'follower_count', 'total_duration',
            'created_at', 'updated_at'
        ]

    def get_track_count(self, obj):
        return obj.playlist_tracks.count()

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return FollowPlaylist.objects.filter(user=request.user, playlist=obj).exists()
        return False

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False


class ListeningHistorySerializer(serializers.ModelSerializer):
    track = TrackListSerializer(read_only=True)
    track_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = ListeningHistory
        fields = [
            'id', 'track', 'track_id', 'played_at', 'duration_played',
            'completed', 'source', 'device'
        ]
        read_only_fields = ['id', 'played_at']


class CommentSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    track = TrackListSerializer(read_only=True)
    track_id = serializers.UUIDField(write_only=True, required=False)
    replies = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'track', 'track_id', 'content', 'timestamp',
            'parent', 'like_count', 'reply_count', 'is_edited',
            'is_pinned', 'is_deleted', 'replies', 'is_liked',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'like_count', 'reply_count', 'is_edited',
            'is_pinned', 'is_deleted', 'created_at', 'updated_at'
        ]

    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(
                obj.replies.filter(is_deleted=False),
                many=True,
                context=self.context
            ).data
        return []

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CommentLike.objects.filter(user=request.user, comment=obj).exists()
        return False


class LikedTrackSerializer(serializers.ModelSerializer):
    track = TrackListSerializer(read_only=True)
    track_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = LikedTrack
        fields = ['id', 'track', 'track_id', 'liked_at']
        read_only_fields = ['id', 'liked_at']


class LikedAlbumSerializer(serializers.ModelSerializer):
    album = AlbumSerializer(read_only=True)
    album_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = LikedAlbum
        fields = ['id', 'album', 'album_id', 'liked_at']
        read_only_fields = ['id', 'liked_at']


class LikedPodcastSerializer(serializers.ModelSerializer):
    podcast = PodcastSerializer(read_only=True)
    podcast_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = LikedPodcast
        fields = ['id', 'podcast', 'podcast_id', 'subscribed_at']
        read_only_fields = ['id', 'subscribed_at']


class FollowArtistSerializer(serializers.ModelSerializer):
    artist = ArtistSerializer(read_only=True)
    artist_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = FollowArtist
        fields = ['id', 'artist', 'artist_id', 'followed_at']
        read_only_fields = ['id', 'followed_at']


class FollowPlaylistSerializer(serializers.ModelSerializer):
    playlist = PlaylistSerializer(read_only=True)
    playlist_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = FollowPlaylist
        fields = ['id', 'playlist', 'playlist_id', 'followed_at']
        read_only_fields = ['id', 'followed_at']