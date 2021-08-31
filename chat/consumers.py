from django.conf import settings
from django.contrib.auth import get_user_model

from users.models import CustomUser
from api.models import Chat, ChatMember, Message
from asgiref.sync import sync_to_async, async_to_sync

import jwt
import json
import requests_async as arequests

from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
	responde = {}
	key = settings.SECRET_KEY
	user = None
	token = ""

	@sync_to_async
	def get_user_id_from_token(self, token):
		decoded_data = jwt.decode(token, self.key, algorithms='HS256')
		user = CustomUser.objects.filter(id=decoded_data["user_id"]).first()
		return user

	@sync_to_async
	def get_user_chats(self, id):
		user_chat_members = ChatMember.objects.filter(member=id)
		chats = [chat_member.chat for chat_member in user_chat_members]
		return chats

	@sync_to_async
	def get_user_specific_chat(self, id):
		chat = Chat.objects.filter(id=id).first()
		return chat, chat.name

	@sync_to_async
	def create_message(self, data):
		record = Message(chat=data['chat'], author=self.user, content=data['message'])
		record.save()
		return record

	async def connect(self):
		dict_keys = list(self.scope["cookies"])
		token_count = dict_keys.count("token")
		if token_count:
			try:
				self.user = await self.get_user_id_from_token(self.scope['cookies']['token'])
				self.token = self.scope['cookies']['token']
				chats = await self.get_user_chats(self.user.id)
				chats_ids = [chat.id for chat in chats]
				for id in chats_ids:
					await self.channel_layer.group_add(f'{id}', self.channel_name)
				await self.channel_layer.group_add(f"{self.user.id}", self.channel_name)
				await self.accept()
			except Exception as e:
				print("entrando 1")
				await self.accept()
				await self.close()
		else:
			print("entrando 2")
			await self.accept()
			await self.close()

	async def disconnect(self, close_code):
		if not self.user:
			pass
		else:
			chats = await self.get_user_chats(self.user.id)
			chats_ids = [chat.id for chat in chats]
			for id in chats_ids:
				await self.channel_layer.group_discard(f'{id}', self.channel_name)

	async def friend_request(self, event):
		await self.send(text_data=json.dumps({
			'event': 'new_friend_request',
			'id': event["request_id"],
			'user_sender': event["user_sender"],
		}))

	async def new_chat(self, event):
		await self.channel_layer.group_add(f'{event["chat_id"]}', self.channel_name)

	async def remove_chat(self, event):
		await self.channel_layer.group_discard(f'{event["chat_id"]}', self.channel_name)

	async def request_accepted(self, event):
		await self.send(text_data=json.dumps({
			'event': 'friend_request_accepted',
			'name': event["name"],
		}))

	async def send_message(self, res):
		#print(res)
		await self.send(text_data=json.dumps({
			'event': 'new_message',
			'chat_id': res["chat_id"],
			'is_group': res["is_group"],
			'name': res["name"],
			'author': res["author"],
            "content": res["message"],
        }))

	async def receive(self, text_data):
		text_data_json = json.loads(text_data)
		message = text_data_json['message']
		chat_id = text_data_json['chat_id']
		is_group = text_data_json['is_group']

		chat, group_name = await self.get_user_specific_chat(chat_id)

		try:
			data = {"chat":chat, "message":message}
			record = await self.create_message(data)
			print(record)
			if is_group:
				await self.channel_layer.group_send(str(chat_id), {
				'type': "send_message",
				'chat_id': chat_id,
				'is_group': True,
				'name': group_name,
				'author': self.user.username,
				'message':message,
				})
			else:
				await self.channel_layer.group_send(str(chat_id), {
				'type': "send_message",
				'chat_id': chat_id,
				'is_group': False,
				'name': self.user.username,
				'author': self.user.username,
				'message':message,
				})
		except Exception as e:
			print(e)
			await self.send(text_data=json.dumps({
				'type': "error",
	            "message": "Message could not be sent",
	        }))
