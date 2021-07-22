from django.conf import settings
from django.contrib.auth import get_user_model

from api.models import Chat, ChatMember
from asgiref.sync import sync_to_async, async_to_sync

import jwt
import json
import requests_async as arequests

from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
	responde = {}
	key = settings.SECRET_KEY
	user_id = ""
	user_name = ""
	token = ""

	async def get_user_id_from_token(self, token):
		decoded_data = jwt.decode(token, self.key, algorithms='HS256')
		self.user_name = decoded_data["name"]
		return decoded_data["user_id"]

	@sync_to_async
	def get_user_chats(self, id):
		user_chat_members = ChatMember.objects.filter(member=id)
		chats = [chat_member.chat for chat_member in user_chat_members]
		return chats


	async def connect(self):
		#print(self.scope['cookies']['token'])
		#print(self.scope['url_route']['kwargs']['pk'])
		self.user_id = await self.get_user_id_from_token(self.scope['cookies']['token'])
		self.token = self.scope['cookies']['token']
		#if user_id == self.scope['url_route']['kwargs']['pk']:
		#print(user_id)
		#print(self.scope['url_route']['kwargs']['pk'])
		chats = await self.get_user_chats(self.user_id)
		chats_ids = [chat.id for chat in chats]
		for id in chats_ids:
			await self.channel_layer.group_add(f'{id}', self.channel_name)
		await self.channel_layer.group_add(f"{self.user_id}", self.channel_name)
		await self.accept()

	async def disconnect(self, close_code):
		chats = await self.get_user_chats(self.user_id)
		chats_ids = [chat.id for chat in chats]
		for id in chats_ids:
			await self.channel_layer.group_discard(f'{id}', self.channel_name)

	async def friend_request(self, event):
		await self.send(text_data=json.dumps({
			'event': 'new_friend_request',
			'request_id': event["request_id"],
			'user_sender': event["user_sender"],
		}))

	async def new_chat(self, event):
		await self.channel_layer.group_add(f'{event["chat_id"]}', self.channel_name)

	async def request_accepted(self, event):
		await self.send(text_data=json.dumps({
			'event': 'friend_request_accepted',
			'name': event["name"],
		}))

	async def send_message(self, res):
		await self.send(text_data=json.dumps({
			'event': 'new_message',
			'chat_id': res["chat_id"],
			'author': res["author"],
            "message": res["message"],
        }))

	async def receive(self, text_data):
		text_data_json = json.loads(text_data)
		message = text_data_json['message']
		chat_id = text_data_json['chat_id']
		URL = f"http://127.0.0.1:8000/api/messages/{text_data_json['chat_id']}/"

		my_headers = {"Authorization": f"JWT {self.token}"}
		response = await arequests.post(url=URL, headers=my_headers, data={'content': text_data_json['message']})

		if response.status_code == 201:
			await self.channel_layer.group_send(str(chat_id), {
			'type': "send_message",
			'chat_id': chat_id,
			'author': self.user_name,
			'message':message,
			})
		else:
			await self.send(text_data=json.dumps({
				'chat_id': chat_id,
				'author': self.user_name,
	            "message": "Message could not be sent",
	        }))
