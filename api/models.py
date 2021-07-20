from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

class Chat(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	group_chat = models.BooleanField(default=False)
	name = models.CharField(max_length=24, default="not_assigned")

	def add_member(self, member):
		if self.chat_for_member.count() >= 2 and not self.group_chat:
			raise Exception("Too many members in this chat")
		self.chat_for_member.add(member, bulk=False)

class ChatMember(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='chat_for_member')
	member = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='chat_member')

	class Meta:
		unique_together = [['chat', 'member']]

	def __str__(self):
		return self.member.username


class FriendsList(models.Model):
	owner = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, primary_key=True)

	def __str__(self):
		return self.owner.username


class Friend(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	friends_list = models.ForeignKey(FriendsList, on_delete=models.CASCADE, related_name='friends_list')
	friend = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='friend')

	class Meta:
		unique_together = [['friends_list', 'friend']]

	def __str__(self):
		return self.friend.username

class Message(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='chat')
	author = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, related_name='author')
	content = models.TextField()
	date_sent = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.content

class FriendRequest(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	user_sender = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="sent_by")
	user_receiver = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="sent_to")
	date_sent = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = [['user_sender', 'user_receiver']]

	def save(self, *args, **kwargs):
		if self.user_sender == self.user_receiver:
			raise Exception("Unable to befriend yourself")
		super(FriendRequest, self).save(*args, **kwargs)

	def __str__(self):
		return f'{self.user_sender} to {self.user_receiver}'
