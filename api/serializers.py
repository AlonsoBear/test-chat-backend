from rest_framework import serializers
from .models import  Message, Friend, Chat, ChatMember, FriendRequest
from users.models import CustomUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class AddFriendSerializer(serializers.Serializer):
	friend = serializers.CharField()

class MessageSerializer(serializers.ModelSerializer):
	class Meta:
		model = Message
		fields = ('content',)

	def save(self, author, chat):
		message = Message.objects.create(
			chat=chat,
			content=self.validated_data["content"],
			author=author,
			)

class ChatSerializer(serializers.ModelSerializer):
	class Meta:
		model = Chat
		fields = '__all__'

class IndividualChatSerializer(serializers.Serializer):
	friend_name = serializers.CharField()

	def save(self):
		chat = Chat.objects.create(group_chat=False)
		return chat

class GroupChatSerializer(serializers.Serializer):
	group_name = serializers.CharField()

	def save(self):
		chat = Chat.objects.create(group_chat=True)
		return chat

class StringListField(serializers.Serializer):
	friend = serializers.CharField()

class AddMemberSerializer(serializers.Serializer):
	friends = StringListField(many=True)

class FriendRequestSerializer(serializers.Serializer):
	id = serializers.UUIDField(format='hex_verbose')
	date_sent = serializers.DateTimeField()
	user_sender = serializers.CharField()


class AcceptFriendRequestSerializer(serializers.Serializer):
	accepted = serializers.BooleanField(required=True)

class CustomUserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    username = serializers.CharField()
    password = serializers.CharField(min_length=8, write_only=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)  # as long as the fields are the same, we can just use this
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super(MyTokenObtainPairSerializer, cls).get_token(user)

        token['name'] = user.username
        return token

class ProfilePictureSerializer(serializers.Serializer):
	profile_pic = serializers.ImageField()

class RemoveGroupSerializer(serializers.Serializer):
	group_id = serializers.UUIDField(format='hex_verbose') 
