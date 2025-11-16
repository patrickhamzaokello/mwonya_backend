from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GenreViewSet, ArtistViewSet, TrackViewSet, PodcastViewSet,
    AlbumViewSet, PlaylistViewSet, CommentViewSet, UserLibraryViewSet
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'genres', GenreViewSet, basename='genre')
router.register(r'artists', ArtistViewSet, basename='artist')
router.register(r'tracks', TrackViewSet, basename='track')
router.register(r'podcasts', PodcastViewSet, basename='podcast')
router.register(r'albums', AlbumViewSet, basename='album')
router.register(r'playlists', PlaylistViewSet, basename='playlist')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'library', UserLibraryViewSet, basename='library')

urlpatterns = [
    path('', include(router.urls)),
]

"""
API Endpoints Generated:

GENRES:
GET     /api/genres/                    - List all genres
GET     /api/genres/{slug}/             - Retrieve a genre

ARTISTS:
GET     /api/artists/                   - List all artists
POST    /api/artists/                   - Create an artist
GET     /api/artists/{id}/              - Retrieve an artist
PUT     /api/artists/{id}/              - Update an artist
PATCH   /api/artists/{id}/              - Partial update an artist
DELETE  /api/artists/{id}/              - Delete an artist
POST    /api/artists/{id}/follow/       - Follow an artist
POST    /api/artists/{id}/unfollow/     - Unfollow an artist
GET     /api/artists/{id}/tracks/       - Get artist's tracks
GET     /api/artists/{id}/albums/       - Get artist's albums

TRACKS:
GET     /api/tracks/                    - List all tracks
POST    /api/tracks/                    - Create a track
GET     /api/tracks/{id}/               - Retrieve a track
PUT     /api/tracks/{id}/               - Update a track
PATCH   /api/tracks/{id}/               - Partial update a track
DELETE  /api/tracks/{id}/               - Delete a track
POST    /api/tracks/{id}/like/          - Like a track
POST    /api/tracks/{id}/unlike/        - Unlike a track
POST    /api/tracks/{id}/play/          - Record a play
GET     /api/tracks/{id}/lyrics/        - Get track lyrics
GET     /api/tracks/{id}/comments/      - Get track comments
GET     /api/tracks/pending_review/     - Get pending tracks (admin)
POST    /api/tracks/{id}/approve/       - Approve track (admin)
POST    /api/tracks/{id}/reject/        - Reject track (admin)

PODCASTS:
GET     /api/podcasts/                  - List all podcasts
POST    /api/podcasts/                  - Create a podcast
GET     /api/podcasts/{slug}/           - Retrieve a podcast
PUT     /api/podcasts/{slug}/           - Update a podcast
PATCH   /api/podcasts/{slug}/           - Partial update a podcast
DELETE  /api/podcasts/{slug}/           - Delete a podcast
POST    /api/podcasts/{slug}/subscribe/ - Subscribe to podcast
POST    /api/podcasts/{slug}/unsubscribe/ - Unsubscribe from podcast
GET     /api/podcasts/{slug}/episodes/  - Get podcast episodes

ALBUMS:
GET     /api/albums/                    - List all albums
POST    /api/albums/                    - Create an album
GET     /api/albums/{slug}/             - Retrieve an album
PUT     /api/albums/{slug}/             - Update an album
PATCH   /api/albums/{slug}/             - Partial update an album
DELETE  /api/albums/{slug}/             - Delete an album
POST    /api/albums/{slug}/like/        - Like an album
POST    /api/albums/{slug}/unlike/      - Unlike an album

PLAYLISTS:
GET     /api/playlists/                 - List all playlists
POST    /api/playlists/                 - Create a playlist
GET     /api/playlists/{slug}/          - Retrieve a playlist
PUT     /api/playlists/{slug}/          - Update a playlist
PATCH   /api/playlists/{slug}/          - Partial update a playlist
DELETE  /api/playlists/{slug}/          - Delete a playlist
POST    /api/playlists/{slug}/add_track/ - Add track to playlist
POST    /api/playlists/{slug}/remove_track/ - Remove track from playlist
POST    /api/playlists/{slug}/follow/   - Follow a playlist
POST    /api/playlists/{slug}/unfollow/ - Unfollow a playlist

COMMENTS:
GET     /api/comments/                  - List all comments
POST    /api/comments/                  - Create a comment
GET     /api/comments/{id}/             - Retrieve a comment
PUT     /api/comments/{id}/             - Update a comment
PATCH   /api/comments/{id}/             - Partial update a comment
DELETE  /api/comments/{id}/             - Delete a comment (soft)
POST    /api/comments/{id}/like/        - Like a comment
POST    /api/comments/{id}/unlike/      - Unlike a comment

USER LIBRARY:
GET     /api/library/liked_tracks/      - Get user's liked tracks
GET     /api/library/liked_albums/      - Get user's liked albums
GET     /api/library/subscribed_podcasts/ - Get user's subscribed podcasts
GET     /api/library/following_artists/ - Get artists user follows
GET     /api/library/history/           - Get user's listening history
GET     /api/library/playlists/         - Get user's playlists

QUERY PARAMETERS:
- search: Search across relevant fields
- ordering: Order results (prefix with - for descending)
- page: Page number for pagination
- page_size: Number of results per page

FILTERING (where applicable):
- content_type: Filter tracks by type (music/podcast)
- status: Filter by status (pending/processing/approved/rejected)
- album_type: Filter albums by type (album/ep/mixtape)
- artist: Filter by artist ID

EXAMPLE REQUESTS:

# Search for tracks
GET /api/tracks/?search=love&ordering=-play_count

# Get artist's tracks
GET /api/artists/123e4567-e89b-12d3-a456-426614174000/tracks/

# Like a track
POST /api/tracks/123e4567-e89b-12d3-a456-426614174000/like/

# Add track to playlist
POST /api/playlists/my-favorite-songs/add_track/
Body: {"track_id": "123e4567-e89b-12d3-a456-426614174000"}

# Record a play
POST /api/tracks/123e4567-e89b-12d3-a456-426614174000/play/
Body: {
    "duration_played": 180,
    "completed": true,
    "source": "playlist",
    "device": "web"
}

# Create a comment
POST /api/comments/
Body: {
    "track_id": "123e4567-e89b-12d3-a456-426614174000",
    "content": "Great track!",
    "timestamp": 45
}

# Get user's listening history
GET /api/library/history/
"""