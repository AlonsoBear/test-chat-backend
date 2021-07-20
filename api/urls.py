from django.urls import path, include
from .views import FriendListView, MessageListView, IndChatView, ChatListCreateView, ChatDetailAddMemberView, \
				   FriendRequestListView, FriendRequestDetailView, CustomUserCreate, ObtainTokenPairWithColorView, \
				   UploadProfilePictureView
from rest_framework_simplejwt import views as jwt_views

urlpatterns = [
	path('friends/', FriendListView.as_view(), name='friend_list'),
	path('messages/<uuid:pk>/', MessageListView.as_view(), name='message_list'),
	path('chats/', IndChatView.as_view(), name='chat_list'),
	path('chats/list/', ChatListCreateView.as_view(), name='chat_list_create_group'),
	path('chats/<uuid:pk>/', ChatDetailAddMemberView.as_view(), name='chat_detail'),
	path('user/signup/', CustomUserCreate.as_view(), name="create_user"),
	path('token/', ObtainTokenPairWithColorView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
	path('friend-request/', FriendRequestListView.as_view(), name='friend_request_list'),
	path('friend-request/<uuid:pk>/', FriendRequestDetailView.as_view(), name='friend_request'),
	path('profile-picture/', UploadProfilePictureView.as_view(), name='upload_profile_pic'),
]
