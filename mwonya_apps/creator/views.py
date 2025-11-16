from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django.db.models import Q, Count, F
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Artist, Genre, Track, TrackDetail, Podcast, Album, Lyric,
    Playlist, PlaylistTrack, ListeningHistory, LikedTrack,
    LikedAlbum, LikedPodcast, Comment, CommentLike,
    FollowArtist, FollowPlaylist
)
from .serializers import (
    ArtistSerializer, GenreSerializer, TrackListSerializer,
    TrackDetailedSerializer, PodcastSerializer, AlbumSerializer,
    LyricSerializer, PlaylistSerializer, PlaylistTrackSerializer,
    ListeningHistorySerializer, CommentSerializer, LikedTrackSerializer,
    LikedAlbumSerializer, LikedPodcastSerializer, FollowArtistSerializer,
    FollowPlaylistSerializer
)


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for genres - read only"""
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class ArtistViewSet(viewsets.ModelViewSet):
    """ViewSet for artists"""
    queryset = Artist.objects.all().select_related('user')
    serializer_class = ArtistSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['stage_name', 'bio']
    ordering_fields = ['stage_name', 'monthly_listeners', 'created_at']
    ordering = ['-monthly_listeners']

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def follow(self, request, pk=None):
        """Follow an artist"""
        artist = self.get_object()
        follow, created = FollowArtist.objects.get_or_create(
            user=request.user,
            artist=artist
        )
        if created:
            return Response({'status': 'following'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'already following'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk=None):
        """Unfollow an artist"""
        artist = self.get_object()
        deleted, _ = FollowArtist.objects.filter(
            user=request.user,
            artist=artist
        ).delete()
        if deleted:
            return Response({'status': 'unfollowed'}, status=status.HTTP_200_OK)
        return Response({'status': 'not following'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def tracks(self, request, pk=None):
        """Get all tracks by an artist"""
        artist = self.get_object()
        tracks = Track.objects.filter(
            artist=artist,
            status='approved',
            is_public=True
        ).select_related('artist').prefetch_related('genres', 'featured_artists')
        serializer = TrackListSerializer(tracks, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def albums(self, request, pk=None):
        """Get all albums by an artist"""
        artist = self.get_object()
        albums = Album.objects.filter(
            artist=artist,
            is_public=True
        ).select_related('artist').prefetch_related('genres')
        serializer = AlbumSerializer(albums, many=True, context={'request': request})
        return Response(serializer.data)


class TrackViewSet(viewsets.ModelViewSet):
    """ViewSet for tracks"""
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['content_type', 'status', 'is_explicit', 'artist']
    search_fields = ['title', 'artist__stage_name']
    ordering_fields = ['title', 'play_count', 'like_count', 'created_at', 'release_date']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Track.objects.select_related(
            'artist', 'detail', 'detail__podcast'
        ).prefetch_related('genres', 'featured_artists', 'lyrics')

        # Filter by status based on user
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return queryset
        return queryset.filter(status='approved', is_public=True)

    def get_serializer_class(self):
        if self.action == 'list':
            return TrackListSerializer
        return TrackDetailedSerializer

    def perform_create(self, serializer):
        serializer.save(status='pending')

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        """Like a track"""
        track = self.get_object()
        liked, created = LikedTrack.objects.get_or_create(
            user=request.user,
            track=track
        )
        if created:
            track.like_count = F('like_count') + 1
            track.save(update_fields=['like_count'])
            track.refresh_from_db()
            return Response({'status': 'liked', 'like_count': track.like_count}, status=status.HTTP_201_CREATED)
        return Response({'status': 'already liked'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unlike(self, request, pk=None):
        """Unlike a track"""
        track = self.get_object()
        deleted, _ = LikedTrack.objects.filter(
            user=request.user,
            track=track
        ).delete()
        if deleted:
            track.like_count = F('like_count') - 1
            track.save(update_fields=['like_count'])
            track.refresh_from_db()
            return Response({'status': 'unliked', 'like_count': track.like_count}, status=status.HTTP_200_OK)
        return Response({'status': 'not liked'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def play(self, request, pk=None):
        """Record a play/listen"""
        track = self.get_object()
        duration_played = request.data.get('duration_played', 0)
        completed = request.data.get('completed', False)

        ListeningHistory.objects.create(
            user=request.user,
            track=track,
            duration_played=duration_played,
            completed=completed,
            source=request.data.get('source'),
            device=request.data.get('device')
        )

        # Increment play count
        track.play_count = F('play_count') + 1
        track.save(update_fields=['play_count'])
        track.refresh_from_db()

        return Response({'status': 'recorded', 'play_count': track.play_count})

    @action(detail=True, methods=['get'])
    def lyrics(self, request, pk=None):
        """Get lyrics for a track"""
        track = self.get_object()
        lyrics = track.lyrics.all()
        serializer = LyricSerializer(lyrics, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """Get comments for a track"""
        track = self.get_object()
        comments = track.comments.filter(parent=None, is_deleted=False).select_related('user')
        serializer = CommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def pending_review(self, request):
        """Get tracks pending review (admin only)"""
        if not request.user.is_staff:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        tracks = Track.objects.filter(status='pending').select_related('artist')
        serializer = TrackListSerializer(tracks, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve a track (admin only)"""
        if not request.user.is_staff:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        track = self.get_object()
        track.status = 'approved'
        track.reviewed_by = request.user
        track.review_notes = request.data.get('review_notes', '')
        track.save()

        serializer = self.get_serializer(track)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """Reject a track (admin only)"""
        if not request.user.is_staff:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        track = self.get_object()
        track.status = 'rejected'
        track.reviewed_by = request.user
        track.review_notes = request.data.get('review_notes', '')
        track.save()

        serializer = self.get_serializer(track)
        return Response(serializer.data)


class PodcastViewSet(viewsets.ModelViewSet):
    """ViewSet for podcasts"""
    queryset = Podcast.objects.all().select_related('host').prefetch_related('genres')
    serializer_class = PodcastSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'host__stage_name']
    ordering_fields = ['name', 'subscriber_count', 'created_at']
    ordering = ['-subscriber_count']

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def subscribe(self, request, slug=None):
        """Subscribe to a podcast"""
        podcast = self.get_object()
        subscription, created = LikedPodcast.objects.get_or_create(
            user=request.user,
            podcast=podcast
        )
        if created:
            podcast.subscriber_count = F('subscriber_count') + 1
            podcast.save(update_fields=['subscriber_count'])
            podcast.refresh_from_db()
            return Response({'status': 'subscribed'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'already subscribed'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unsubscribe(self, request, slug=None):
        """Unsubscribe from a podcast"""
        podcast = self.get_object()
        deleted, _ = LikedPodcast.objects.filter(
            user=request.user,
            podcast=podcast
        ).delete()
        if deleted:
            podcast.subscriber_count = F('subscriber_count') - 1
            podcast.save(update_fields=['subscriber_count'])
            podcast.refresh_from_db()
            return Response({'status': 'unsubscribed'}, status=status.HTTP_200_OK)
        return Response({'status': 'not subscribed'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def episodes(self, request, slug=None):
        """Get all episodes of a podcast"""
        podcast = self.get_object()
        episodes = Track.objects.filter(
            detail__podcast=podcast,
            status='approved',
            is_public=True
        ).select_related('artist', 'detail').order_by('-detail__episode_number')
        serializer = TrackListSerializer(episodes, many=True, context={'request': request})
        return Response(serializer.data)


class AlbumViewSet(viewsets.ModelViewSet):
    """ViewSet for albums"""
    queryset = Album.objects.all().select_related('artist').prefetch_related('genres')
    serializer_class = AlbumSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['album_type', 'artist']
    search_fields = ['title', 'artist__stage_name']
    ordering_fields = ['title', 'release_date', 'play_count', 'like_count']
    ordering = ['-release_date']

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, slug=None):
        """Like an album"""
        album = self.get_object()
        liked, created = LikedAlbum.objects.get_or_create(
            user=request.user,
            album=album
        )
        if created:
            album.like_count = F('like_count') + 1
            album.save(update_fields=['like_count'])
            album.refresh_from_db()
            return Response({'status': 'liked'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'already liked'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unlike(self, request, slug=None):
        """Unlike an album"""
        album = self.get_object()
        deleted, _ = LikedAlbum.objects.filter(
            user=request.user,
            album=album
        ).delete()
        if deleted:
            album.like_count = F('like_count') - 1
            album.save(update_fields=['like_count'])
            album.refresh_from_db()
            return Response({'status': 'unliked'}, status=status.HTTP_200_OK)
        return Response({'status': 'not liked'}, status=status.HTTP_400_BAD_REQUEST)


class PlaylistViewSet(viewsets.ModelViewSet):
    """ViewSet for playlists"""
    serializer_class = PlaylistSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'user__name']
    ordering_fields = ['name', 'follower_count', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Playlist.objects.filter(
                Q(privacy='public') |
                Q(user=self.request.user) |
                Q(collaborators=self.request.user)
            ).select_related('user').prefetch_related('playlist_tracks__track').distinct()
        return Playlist.objects.filter(privacy='public').select_related('user')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_track(self, request, slug=None):
        """Add a track to playlist"""
        playlist = self.get_object()

        # Check permissions
        if playlist.user != request.user and request.user not in playlist.collaborators.all():
            return Response({'error': 'No permission'}, status=status.HTTP_403_FORBIDDEN)

        track_id = request.data.get('track_id')
        if not track_id:
            return Response({'error': 'track_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            track = Track.objects.get(id=track_id)
        except Track.DoesNotExist:
            return Response({'error': 'Track not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get next position
        last_position = playlist.playlist_tracks.aggregate(
            max_pos=models.Max('position')
        )['max_pos'] or 0

        playlist_track, created = PlaylistTrack.objects.get_or_create(
            playlist=playlist,
            track=track,
            defaults={
                'position': last_position + 1,
                'added_by': request.user
            }
        )

        if created:
            return Response({'status': 'added'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'already in playlist'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def remove_track(self, request, slug=None):
        """Remove a track from playlist"""
        playlist = self.get_object()

        # Check permissions
        if playlist.user != request.user and request.user not in playlist.collaborators.all():
            return Response({'error': 'No permission'}, status=status.HTTP_403_FORBIDDEN)

        track_id = request.data.get('track_id')
        deleted, _ = PlaylistTrack.objects.filter(
            playlist=playlist,
            track_id=track_id
        ).delete()

        if deleted:
            return Response({'status': 'removed'}, status=status.HTTP_200_OK)
        return Response({'error': 'Track not in playlist'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def follow(self, request, slug=None):
        """Follow a playlist"""
        playlist = self.get_object()
        follow, created = FollowPlaylist.objects.get_or_create(
            user=request.user,
            playlist=playlist
        )
        if created:
            playlist.follower_count = F('follower_count') + 1
            playlist.save(update_fields=['follower_count'])
            playlist.refresh_from_db()
            return Response({'status': 'following'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'already following'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unfollow(self, request, slug=None):
        """Unfollow a playlist"""
        playlist = self.get_object()
        deleted, _ = FollowPlaylist.objects.filter(
            user=request.user,
            playlist=playlist
        ).delete()
        if deleted:
            playlist.follower_count = F('follower_count') - 1
            playlist.save(update_fields=['follower_count'])
            playlist.refresh_from_db()
            return Response({'status': 'unfollowed'}, status=status.HTTP_200_OK)
        return Response({'status': 'not following'}, status=status.HTTP_400_BAD_REQUEST)


class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet for comments"""
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'like_count']
    ordering = ['-created_at']

    def get_queryset(self):
        return Comment.objects.filter(
            is_deleted=False
        ).select_related('user', 'track')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        # Increment comment count on track
        track_id = self.request.data.get('track_id')
        if track_id:
            Track.objects.filter(id=track_id).update(
                comment_count=F('comment_count') + 1
            )

    def perform_destroy(self, instance):
        # Soft delete
        instance.is_deleted = True
        instance.save()
        # Decrement comment count
        instance.track.comment_count = F('comment_count') - 1
        instance.track.save(update_fields=['comment_count'])

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        """Like a comment"""
        comment = self.get_object()
        liked, created = CommentLike.objects.get_or_create(
            user=request.user,
            comment=comment
        )
        if created:
            comment.like_count = F('like_count') + 1
            comment.save(update_fields=['like_count'])
            comment.refresh_from_db()
            return Response({'status': 'liked'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'already liked'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unlike(self, request, pk=None):
        """Unlike a comment"""
        comment = self.get_object()
        deleted, _ = CommentLike.objects.filter(
            user=request.user,
            comment=comment
        ).delete()
        if deleted:
            comment.like_count = F('like_count') - 1
            comment.save(update_fields=['like_count'])
            comment.refresh_from_db()
            return Response({'status': 'unliked'}, status=status.HTTP_200_OK)
        return Response({'status': 'not liked'}, status=status.HTTP_400_BAD_REQUEST)


class UserLibraryViewSet(viewsets.ViewSet):
    """ViewSet for user library endpoints"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def liked_tracks(self, request):
        """Get user's liked tracks"""
        liked = LikedTrack.objects.filter(
            user=request.user
        ).select_related('track__artist').prefetch_related('track__genres')
        serializer = LikedTrackSerializer(liked, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def liked_albums(self, request):
        """Get user's liked albums"""
        liked = LikedAlbum.objects.filter(
            user=request.user
        ).select_related('album__artist')
        serializer = LikedAlbumSerializer(liked, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def subscribed_podcasts(self, request):
        """Get user's subscribed podcasts"""
        subscriptions = LikedPodcast.objects.filter(
            user=request.user
        ).select_related('podcast__host')
        serializer = LikedPodcastSerializer(subscriptions, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def following_artists(self, request):
        """Get artists user is following"""
        following = FollowArtist.objects.filter(
            user=request.user
        ).select_related('artist')
        serializer = FollowArtistSerializer(following, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get user's listening history"""
        history = ListeningHistory.objects.filter(
            user=request.user
        ).select_related('track__artist')[:50]
        serializer = ListeningHistorySerializer(history, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def playlists(self, request):
        """Get user's playlists"""
        playlists = Playlist.objects.filter(user=request.user)
        serializer = PlaylistSerializer(playlists, many=True, context={'request': request})
        return Response(serializer.data)