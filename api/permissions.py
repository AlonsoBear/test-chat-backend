from rest_framework import permissions
from users.models import CustomUser
from .models import ChatMember, Chat, FriendsList, Friend

class IsChatMember(permissions.BasePermission):
	def has_permission(self, request, view):
		return True

	def has_object_permission(self, request, view, object):
		try:
			chat_member = ChatMember.objects.get(chat=object, member=request.user)
		except:
			return False
		return True

class IsFriend(permissions.BasePermission):
	message = 'The user is not in your friends list'

	def has_object_permission(self, request, view, object):
		try:
			friend_user = CustomUser.objects.get(username=request.data['friend_name'])
			request_user_fl = FriendsList.objects.get(owner=request.user)
			friend = Friend.objects.get(friends_list=request_user_fl, friend=friend_user)
		except:
			return False
		return True

class IsRequestedUser(permissions.BasePermission):
	message = 'You are not allowed to see this request'

	def has_permission(self, request, view):
		if request.user.is_authenticated:
			return True
		return False

	def has_object_permission(self, request, view, object):
		if request.user != object.user_receiver:
			return False
		return True
