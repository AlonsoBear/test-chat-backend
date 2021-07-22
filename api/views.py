import json

from django.shortcuts import render

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from users.models import CustomUser
from .permissions import IsChatMember, IsFriend, IsRequestedUser
from .models import Friend, Message, Chat, FriendsList, ChatMember, FriendRequest
from .serializers import  AddFriendSerializer, MessageSerializer, ChatSerializer, IndividualChatSerializer, GroupChatSerializer,\
 						  AddMemberSerializer, FriendRequestSerializer, AcceptFriendRequestSerializer, CustomUserSerializer, \
						  MyTokenObtainPairSerializer, ProfilePictureSerializer, RemoveGroupSerializer

# ADD FRIEND AND GET A FRIENDS LIST FOR EACH USER
class FriendListView(generics.ListCreateAPIView):

	# SET THE QUERY SET TO BE DISPLAY AND THE SERIALIZER FOR THE DATA
	queryset = Friend.objects.all()
	serializer_class = AddFriendSerializer

	# GET METHOD TO RETRIEVE FRIENDS LIST FOR EACH USER
	def get(self, request):
		# GETS REQUEST USERS FRIENDS LIST OR 422 RESPONSE
		try:
			friends_list = FriendsList.objects.get(owner=request.user)
		except:
			return Response("Not Found", status=status.HTTP_422_UNPROCESSABLE_ENTITY)

		# RETRIEVES THE LIST OF FRIEND MODELS LINKES TO THE USERS FRIENDSLIST
		friends = Friend.objects.filter(friends_list=friends_list)

		# SPLITS THE DATA ONLY TO SHOW FRIEND NAME
		friends = [{"name":friend.friend.username} for friend in friends]
		return Response(data=friends, status=status.HTTP_200_OK)

	# ******* THERE IS NO SERIALIZER VALIDATION *******
	# CREATE METHOD TO ADD A FRIEND TO A USERS FRIENDS LIST
	def create(self, request):
		# CHECKS WHETHER THERE IS A USER WITH THE NAME IN THE DATA OR NOT, 422 IF NOT FOUND
		channel_layer = get_channel_layer()
		try:
			friend_requested = CustomUser.objects.get(username=request.data["friend"])
		except:
			return Response("User not Found", status=status.HTTP_422_UNPROCESSABLE_ENTITY)
		# FUNCTION THAT CHECKS IF THERE IS ALREADY A FRIEND REQUEST IN PROGRESS, IF THERE IS 409 CONFLICT RESPONSE
		if self.check_friend_request(request.user, friend_requested):
			return Response(f"{friend_requested.username} has already sent you a friend request", status=status.HTTP_409_CONFLICT)
		# CREATES THE FRIEND REQUEST OBJECT, 409 CONFLICT IF THERE IS AN ISSUE
		try:
			friend_request = FriendRequest(user_sender=request.user, user_receiver=friend_requested)
			friend_request.save()
			async_to_sync(channel_layer.group_send)(f"{friend_requested.id}", {"type": "friend.request", "request_id":f"{friend_request.id}","user_sender":request.user.username})
		except Exception as e:
			return Response(str(e), status=status.HTTP_409_CONFLICT)
		# RESPONSE 201 IF EVERYTHING WENT AS EXPECTED
		return Response("Request sent", status=status.HTTP_201_CREATED)

	# FUNCTION THAT CHECKS IF THERE IS ALREADY A FRIEND REQUEST
	def check_friend_request(self, sender, receiver):
		# RETRIEVES A FRIEND_REQUEST OBJECT WITH THE SPECITY DATA
		friend_request = FriendRequest.objects.filter(user_sender=receiver, user_receiver=sender).first()
		# IF THE OBJECT EXISTS RETURNS TRUE, OTHERWISE RETURNS FALSE
		if friend_request:
			return True
		return False


# GENERATES A LIST OF ALL THE FRIEND REQUESTS THE USER HAS
class FriendRequestListView(generics.ListAPIView):
	serializer_class = FriendRequestSerializer

	# ALLOWS TO SET A QUERYSET WITH THE GIVEN REQUEST AT THE MOMENT
	def get_queryset(self):
		return FriendRequest.objects.filter(user_receiver=self.request.user)


# GETS THE DATA FOR A SPECIFIC FRIEND REQUEST (GET), ALLOWS YOU TO ACCEPT OR REJECT A SPECIFIC REQUEST (POST)
class FriendRequestDetailView(generics.RetrieveAPIView):
	permission_classes = (IsRequestedUser,)
	queryset = FriendRequest.objects.all()

	# IN THIS CASE THE FUNCTION ALLOWS TO USE DIFFERENT SERIALIZERS FOR DIFFERENT HTTP METHODS
	def get_serializer_class(self):
		# USES FRIENDREQUEST SERIALIZER IF THE METHOD IS GET, ACCEPTFRIENDREQUESTSERIALIZER FOR ANY OTHER METHOD
		if self.request.method == 'GET':
			return FriendRequestSerializer
		return AcceptFriendRequestSerializer

	# LETS THE USER ACCEPT OR REJECT A FRIEND REQUEST
	def post(self, request, pk):
		serializer = AcceptFriendRequestSerializer(data=request.data)
		channel_layer = get_channel_layer()
		# VALIDATES SERIALIZER DATA
		if serializer.is_valid():
			# CHECKS IF THE GIVEN FRIEND REQUEST EXISTS. 422 IF NOT
			try:
				friend_request = FriendRequest.objects.get(id=pk)
			except:
				return Response("Friend Request not found", status=status.HTTP_422_UNPROCESSABLE_ENTITY)
			self.check_object_permissions(request, friend_request)
			if serializer.data["accepted"] == True:
				# SETS THE OBJECT TO BE CREATED DATA
				sender = friend_request.user_sender
				receiver = friend_request.user_receiver
				fl_sender = FriendsList.objects.filter(owner=sender).first()
				# IF A FRIENDS LIST DOES NOT EXIST CREATES ONE FOR THE SENDER
				if not fl_sender:
					fl_sender = FriendsList.objects.create(owner=sender)
				fl_receiver = FriendsList.objects.filter(owner=receiver).first()
				# IF A FRIENDS LIST DOES NOT EXIST CREATES ONE FOR THE RECEIVER
				if not fl_receiver:
					fl_receiver = FriendsList.objects.create(owner=receiver)
				# CREATES THE TWO FRIEND OBJECTS FOR THE 2 USERS
				try:
					add_friend_receiver = Friend(friends_list=fl_sender, friend=receiver)
					add_friend_sender = Friend(friends_list=fl_receiver, friend=sender)
				except:
					return Response("Friend could not be added", status=status.HTTP_409_CONFLICT)
				add_friend_receiver.save()
				add_friend_sender.save()
				async_to_sync(channel_layer.group_send)(f"{sender.id}", {"type": "request.accepted", "name":f"{receiver.username}"})
				async_to_sync(channel_layer.group_send)(f"{receiver.id}", {"type": "request.accepted", "name":f"{sender.username}"})
				# DELETES THE REQUEST IF ACCEPTED
				friend_request.delete()
				return Response("Request: Accepted", status=status.HTTP_201_CREATED)
			# DELETES THE REQUEST IF REJECTED
			friend_request.delete()
			return Response("Request: Rejected", status=status.HTTP_200_OK)
		return Response(serializer.error, status=status.HTTP_400_BAD_REQUEST)

# ******* THERE IS NO SERIALIZER VALIDATION *******
# GENERATES A LIST OF MESSAGES FROM AN SPECIFIC CHAT AND LETS YOU ADD MESSAGES TO SAID CHAT
class MessageListView(APIView):
	permission_classes = (IsChatMember, IsAuthenticated)
	serializer_class = MessageSerializer

	# GET METHOD, SHOWS THE MESSAGES OF A SPECIFIC CHAT
	def get(self, request, pk):
		# CHECKS WHETHER THE CHAT EXISTS OR NOT, 422 IF NOT
		try:
			chat = Chat.objects.get(id=pk)
		except:
			return Response("Chat does not exist", status=status.HTTP_422_UNPROCESSABLE_ENTITY)
		# PERMISSION THAT CHECKS IF THE USER IS A CHATMEMBER
		self.check_object_permissions(request, chat)
		# IF THE CHAT EXISTS SETS THE DATA THAT IS GOING TO SEND
		if chat:
			messages = Message.objects.filter(chat=chat)
			messages = [{'author':message.author.username, 'content':message.content, 'date_sent':message.date_sent} for message in messages]
			return Response(data=messages, status=status.HTTP_200_OK)

		return Response("Chat does not exist", status=status.HTTP_400_BAD_REQUEST)

	# POST METHOD, CREATES MESSAGES FOR A SPECIFIC CHAT
	def post(self, request, pk):
		serializer = self.serializer_class(data=request.data)

		# CHECKS IF THE DATA IS VALID
		if serializer.is_valid():
			# CHECKS IF THE GIVEN CHAT EXISTS, 422 IF NOT
			try:
				chat = Chat.objects.get(id=pk)
			except:
				return Response("Chat does not exist", status=status.HTTP_422_UNPROCESSABLE_ENTITY)

			# CHECKS IF THE USER IS A CHAT MEMBER
			self.check_object_permissions(request, chat)
			# SERIALIZES THE DATA
			serializer.save(request.user, chat)
			return Response('Message received', status=status.HTTP_201_CREATED)
		return Response({'Bad Request': 'Invalid data...'}, status=status.HTTP_400_BAD_REQUEST)

# GENERATES THE DATA OF A SPECIFIC CHAT, LETS YOU ADD MEMBERS TO GROUP CHATS
class ChatDetailAddMemberView(APIView):
	permission_classes = (IsChatMember, IsAuthenticated)
	serializer_class = AddMemberSerializer
	# GET METHOD, SHOWS THE DATA OF A SPECIFIC CHAT
	def get(self, request, pk):
		# CHEKS IF THE CHAT EXISTS, IF IT DOES, GETS THE CHAT MAMBERS OF SAID CHAT
		try:
			chat = Chat.objects.get(id=pk)
			chat_members = chat.chat_for_member.all()
			# MAKES A LIST OF THE MEMBER USERNAMES
			chat_members = [chat_member.member.username for chat_member in chat_members]
		except:
			return Response("Chat not found", status=status.HTTP_409_CONFLICT)
		self.check_object_permissions(request, chat)
		return Response(data = {
			"id":chat.id,
			"name":chat.name,
			"members":chat_members,
		}, status=status.HTTP_200_OK)

	# POST METHOD, ALLOWS YOU TO ADD A MEMBER TO A CHAT
	def post(self, request, pk):
		# SERIALIZES THE REQUEST DATA
		serializer = self.serializer_class(data=request.data)
		# VALIDATES THE SERIALIZED DATA
		if serializer.is_valid():
			# CHECKS IF THE CHAT EXISTS, 409 IF NOT
			chat = Chat.objects.filter(id=pk).first()
			if not chat:
				return Response("Not found: Chat does not exist", status=status.HTTP_422_UNPROCESSABLE_ENTITY)
			# EXTRACTS THE FRIEND LIST TO BE ADDED
			friends_names = serializer.data.get("friends")
			count=0
			for friend in friends_names:
				try:
					user = CustomUser.objects.get(username=friend["friend"])
					member = ChatMember(member=user)
					chat.add_member(member)
				except:
					count += 1
			if count != 0:
				if count == len(friends_names):
					return Response("No friend could be added", status=status.HTTP_422_UNPROCESSABLE_ENTITY)
				return Response(f"{count} friends could not be added", status=status.HTTP_200_OK)
			return Response("Members added", status=status.HTTP_200_OK)
		return Response({serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

	def delete(self, request, pk):
		try:
			chat_member = ChatMember.objects.get(member=request.user, chat=pk)
		except:
			return Response("You are not a member of the chat", status=status.HTTP_409_CONFLICT)
		chat_member.delete()
		return Response("You are no longer a member of this chat", status=status.HTTP_200_OK)

# CREATE GROUP CHAT AND LIST OF ALL THE CHATS OF A USER
class ChatListCreateView(APIView):
	permission_classes = (IsAuthenticated,)
	serializer_class = GroupChatSerializer

	def get(self, request):
		data = []

		# GET CHAT LIST OF A SPECIFIC USER
		chat_list = ChatMember.objects.filter(member=request.user)
		chat_list = [chat_member.chat for chat_member in chat_list]

		# CHECKS AND ASSIGNS THE NAME OF THE CHATS
		for chat in chat_list:
			try:
				# GETS THE LAST MESSAGE THAT WAS SAVED IN THE CHAT
				message = Message.objects.filter(chat=chat).order_by('-date_sent')[0]
			except:
				message = "No messages yet"
				modified_at = False
			# IF THE CHAT NAME IS NOT THE DATABASE DEFAULT FOR INDIVIDUAL CHAT IT SETS THE CHAT TO GROUP CHAT
			if chat.name != "not_assigned":
				is_group = True
				# SETS THE DATA TO BE SEND WHETHER THERE IS A MESSAGE OR NOT
				if message != "No messages yet":
					modified_at = message.date_sent
					message = f'{message.author}: {message.content}'
				data.append({"id":chat.id, "name":chat.name, "last_message":message, "modified_at":modified_at ,"is_group": is_group})
			# IF THE CHAT NAME IS THE DATABASE DEFAULT SETS THE CHAT AS INDIVIDUAL
			else:
				is_group = False
				# SETS THE DATA TO BE SEND WHETHER THERE IS A MESSAGE OR NOT
				if message != "No messages yet":
					modified_at = message.date_sent
					message = f'{message.content}'
				# GETS THE NAME OF THE ONLY OTHER MEMBER IN THE CHAT BESIDES THE USER THAT MADE THE REQUEST
				friend_name = chat.chat_for_member.all().exclude(member=request.user)[0].member.username
				profile_pic = chat.chat_for_member.all().exclude(member=request.user)[0].member.profile_picture
				if not profile_pic:
					profile_pic = None
				else:
					profile_pic = profile_pic.url
				data.append({"id":chat.id, "name":friend_name, "profile_picture":profile_pic, "last_message":message, "modified_at": modified_at, "is_group": is_group})
		return Response(data, status=status.HTTP_200_OK)

	def post(self, request):

		# SERIALIZES AND VALIDATES DATA
		chat_serializer = self.serializer_class(data=request.data)
		if chat_serializer.is_valid():

			# SAVES SERIALIZER BY CREATING A CHAT
			chat = chat_serializer.save()
			try:
				# ASSIGNS NAME TO CHAT
				chat.name = request.data["group_name"]
			except:
				# IF THERE IS A PROBLEM THE CHAT IS DELETED AND RETURN IS 400
				chat.delete()
				return Response({'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
			chat.save()

			# ESTABLISH THE CREATOR OF THE CHAT AS A MEMBER OF IT
			chat_member = ChatMember(member=request.user)
			chat.add_member(chat_member)

			return Response(data={"id": chat.id, "name": chat.name}, status=status.HTTP_201_CREATED)
		return Response({'Bad Request': 'Invalid data...'}, status=status.HTTP_400_BAD_REQUEST)


# CREATE INDICIDUAL CHAT AND CHATMEMBERS VIEW
class IndChatView(APIView):
	permission_classes = (IsFriend, IsAuthenticated)
	serializer_class = IndividualChatSerializer

	# POST METHOD TO CREATE AN INDIVIDUAL CHAT WITH A FRIEND
	def post(self, request):
		# SERIALIZES, VALIDATES AND SAVES (CREATES CHAT OBJECT) THE DATA
		chat_serializer = self.serializer_class(data=request.data)
		if not chat_serializer.is_valid():
			return Response({'Bad Request': 'Invalid data...'}, status=status.HTTP_400_BAD_REQUEST)

		# QUERY TO LOOK FOR FRIEND AND ADD IT TO CHAT, NO RESULT EQUALS CONFLICT STATUS
		try:
			friend_member = CustomUser.objects.get(username=request.data['friend_name'])
		except Exception as e:
			return Response(str(e), status=status.HTTP_409_CONFLICT)

		self.check_object_permissions(request, friend_member)

		# CHECK IF THERE IS ALREADY AN EXISTING CHAT
		if check_matching_column(request.user, friend_member):
			return Response("A chat already exists", status=status.HTTP_409_CONFLICT)

		chat = chat_serializer.save()

		# ADDS FRIEND TO CHAT
		chat_member = ChatMember(member=friend_member)
		chat.add_member(chat_member)

		# ADDS CHAT CREATOR TO CHAT
		chat_member = ChatMember(member=request.user)
		chat.add_member(chat_member)

		channel_layer = get_channel_layer()
		async_to_sync(channel_layer.group_send)(f"{friend_member.id}", {"type": "new.chat", "chat_id":f"{chat.id}"})

		return Response(data={"chat_id":chat.id}, status=status.HTTP_201_CREATED)

# METHOD THAT CHECKS IF A CHAT ALREADY EXITS
def check_matching_column(user, friend):
	# GETS ALL CHAT_MEMBER OBJECTS FOR THE TWO USERS
	queryset_1 = ChatMember.objects.filter(member=user)
	queryset_2 = ChatMember.objects.filter(member=friend)

	# MAKES A LIST OF THE CHATS BASED ON THE FIRST QUERYSET
	chats = [chat_member.chat for chat_member in queryset_1]
	for chat in chats:
		# CHECKS IF ANY CHAT IN THE CHATS VIEW EXISTS IN THE SECOND QUERYSET
		exact_chat = queryset_2.filter(chat=chat)
		# TRUE IF A CHAT EXISTS
		if exact_chat:
			return exact_chat[0]
	return None

# SIGNUP VIEW FOR USERS
class CustomUserCreate(APIView):
    permission_classes = (AllowAny,)
    serializer_class = CustomUserSerializer

	# POST METHOD, ALLOWS TO ADD USERS
    def post(self, request, format='json'):
		# SERIALIZES THE REQUEST DATA
        serializer = self.serializer_class(data=request.data)
		# VALIDATES THE SERIALIZED DATA
        if serializer.is_valid():
			# CREATES THE USER
            user = serializer.save()
            if user:
                json = serializer.data
                return Response(json, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# VIEW THAT USES A JWT WITH A USER_NAME PAYLOAD
class ObtainTokenPairWithColorView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = MyTokenObtainPairSerializer

class UploadProfilePictureView(APIView):
	serializer_class = ProfilePictureSerializer

	def put(self, request):
		serializer = self.serializer_class(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

		user = request.user
		user.profile_picture=request.FILES['profile_pic']
		user.save()
		return Response("", status=status.HTTP_200_OK)
