from django.test import TestCase
from django.urls import reverse

from users.models import CustomUser
from .models import Friend, FriendsList, Chat
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APIClient
import uuid

# Create your tests here.
class AuthenticationSystem(TestCase):
	def setUp(self):
		self.test_user = CustomUser(username="test_user")
		self.test_user.set_password("12345678")
		self.test_user.save()
		self.test_user_token = str(RefreshToken.for_user(self.test_user))

	def test_refresh_token(self):
		response = self.client.post(
			reverse("token_refresh"),
			{
				"refresh": self.test_user_token,
			},
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "access")
		self.assertContains(response, "refresh")

	def test_obtain_token(self):
		response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": "test_user",
				"password": "12345678",
			}
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "access")
		self.assertContains(response, "refresh")

	def test_user_signup(self):
		response = self.client.post(
			reverse("create_user"),
			{
				"email": "whatever@whatever.com",
				"username": "whateveruser",
				"password": "whateverpassword",
			}
		)
		user = response.data['username']
		password = 'whateverpassword'
		response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": user,
				"password": password,
			}
		)
		self.assertEqual(response.status_code, 200)


class FriendSystemTest(TestCase):
	def setUp(self):
		self.test_user = CustomUser(username="test_user")
		self.test_user.set_password("12345678")
		self.test_user.save()
		self.test_user_token = RefreshToken.for_user(self.test_user)
		self.test_user_token = str(self.test_user_token.access_token)

		self.friend_user = CustomUser(username="friend_user")
		self.friend_user.set_password("12345678")
		self.friend_user.save()
		self.friend_user_token = RefreshToken.for_user(self.friend_user)
		self.friend_user_token = str(self.friend_user_token.access_token)

		self.second_friend_user = CustomUser(username="second_friend_user")
		self.second_friend_user.set_password("12345678")
		self.second_friend_user.save()
		self.second_friend_user_token = RefreshToken.for_user(self.second_friend_user)
		self.second_friend_user_token = str(self.second_friend_user_token.access_token)

	def test_add_friend(self):
		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "friend_user"
			},
			HTTP_AUTHORIZATION = f'JWT {self.test_user_token}'
		)
		self.assertEqual(response.status_code, 201)

	def test_add_unexisting_friend(self):
		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "error_user"
			},
			HTTP_AUTHORIZATION = f'JWT {self.test_user_token}'
		)
		self.assertEqual(response.status_code, 422)

	def test_add_yourself_friend(self):
		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "test_user"
			},
			HTTP_AUTHORIZATION = f'JWT {self.test_user_token}'
		)
		self.assertEqual(response.status_code, 409)
		self.assertEqual(response.data, 'Unable to befriend yourself')

	def test_add_already_requested_friend(self):
		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "friend_user"
			},
			HTTP_AUTHORIZATION = f'JWT {self.test_user_token}'
		)
		self.assertEqual(response.status_code, 201)
		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "test_user"
			},
			HTTP_AUTHORIZATION = f'JWT {self.friend_user_token}'
		)
		self.assertEqual(response.status_code, 409)
		self.assertEqual(response.data, 'test_user has already sent you a friend request')

	def test_add_friend_without_authentication(self):
		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "test_user"
			},
		)
		self.assertEqual(response.status_code, 401)

	def test_friend_list_without_friends(self):
		response = self.client.get(
			reverse("friend_list"),
			{},
			HTTP_AUTHORIZATION = f'JWT {self.test_user_token}'
		)
		self.assertEqual(response.status_code, 422)

	def test_accept_friend_request(self):
		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "friend_user"
			},
			HTTP_AUTHORIZATION = f'JWT {self.test_user_token}'
		)
		self.assertEqual(response.status_code, 201)
		response = self.client.get(
			reverse("friend_request_list"),
			HTTP_AUTHORIZATION = f'JWT {self.friend_user_token}',
		)
		self.assertEqual(response.status_code, 200)

		friend_request_id = response.data[0]["id"]

		response = self.client.post(
			reverse("friend_request", args=(friend_request_id,)),
			{
				"accepted": True,
			},
			HTTP_AUTHORIZATION = f'JWT {self.test_user_token}',
		)
		self.assertEqual(response.status_code, 403)
		response = self.client.post(
			reverse("friend_request", args=(friend_request_id,)),
			{
				"accepted": True,
			},
			HTTP_AUTHORIZATION = f'JWT {self.friend_user_token}',
		)
		self.assertEqual(response.status_code, 201)

		response = self.client.get(
			reverse("friend_list"),
			HTTP_AUTHORIZATION = f'JWT {self.friend_user_token}',
		)
		self.assertContains(response, 'test_user')



	def test_reject_friend_request(self):
		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "friend_user"
			},
			HTTP_AUTHORIZATION = f'JWT {self.second_friend_user_token}'
		)
		self.assertEqual(response.status_code, 201)

		response = self.client.get(
			reverse("friend_request_list"),
			HTTP_AUTHORIZATION = f'JWT {self.friend_user_token}',
		)
		self.assertEqual(response.status_code, 200)

		friend_request_id = response.data[0]["id"]

		response = self.client.post(
			reverse("friend_request", args=(friend_request_id,)),
			{
				"accepted": False,
			},
			HTTP_AUTHORIZATION = f'JWT {self.friend_user_token}',
		)
		self.assertEqual(response.status_code, 200)

		response = self.client.post(
			reverse("friend_request", args=(uuid.uuid1(),)),
			{
				"accepted": False,
			},
			HTTP_AUTHORIZATION = f'JWT {self.friend_user_token}',
		)
		self.assertEqual(response.status_code, 422)

		response = self.client.get(
			reverse("friend_request_list"),
			HTTP_AUTHORIZATION = f'JWT {self.friend_user_token}',
		)
		self.assertEqual(response.data, [])

		response = self.client.get(
			reverse("friend_list"),
			HTTP_AUTHORIZATION = f'JWT {self.friend_user_token}',
		)
		self.assertEqual(response.status_code, 422)


class ChatSystemTest(TestCase):
	def setUp(self):
		self.test_user = CustomUser(username="test_user")
		self.test_user.set_password("12345678")
		self.test_user.save()
		self.test_user_token = RefreshToken.for_user(self.test_user)
		self.test_user_token = str(self.test_user_token.access_token)

		self.friend_user = CustomUser(username="friend_user")
		self.friend_user.set_password("12345678")
		self.friend_user.save()
		self.friend_user_token = RefreshToken.for_user(self.friend_user)
		self.friend_user_token = str(self.friend_user_token.access_token)

		self.second_friend_user = CustomUser(username="second_friend_user")
		self.second_friend_user.set_password("12345678")
		self.second_friend_user.save()
		self.second_friend_user_token = RefreshToken.for_user(self.second_friend_user)
		self.second_friend_user_token = str(self.second_friend_user_token.access_token)

		self.third_friend_user = CustomUser(username="third_friend_user")
		self.third_friend_user.set_password("12345678")
		self.third_friend_user.save()
		self.third_friend_user_token = RefreshToken.for_user(self.third_friend_user)
		self.third_friend_user_token = str(self.third_friend_user_token.access_token)

		self.test_user_friend_list = FriendsList.objects.create(owner=self.test_user)
		self.friend_user_friends_list = FriendsList.objects.create(owner=self.friend_user)
		self.second_friend_user_friends_list = FriendsList.objects.create(owner=self.second_friend_user)
		self.third_friend_user_friends_list = FriendsList.objects.create(owner=self.third_friend_user)

		Friend.objects.create(friends_list=self.test_user_friend_list, friend=self.friend_user)
		Friend.objects.create(friends_list=self.test_user_friend_list, friend=self.third_friend_user)

		Friend.objects.create(friends_list=self.friend_user_friends_list, friend=self.test_user)
		Friend.objects.create(friends_list=self.friend_user_friends_list, friend=self.second_friend_user)

		Friend.objects.create(friends_list=self.second_friend_user_friends_list, friend=self.friend_user)

		Friend.objects.create(friends_list=self.third_friend_user_friends_list, friend=self.test_user)

	def test_chat_creation(self):
		response = self.client.post(
			reverse("ind_chat"),
			{
				"friend_nae": 1
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 400)

		response = self.client.post(
			reverse("ind_chat"),
			{
				"friend_name": "friend_user"
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 201)

		response = self.client.post(
			reverse("ind_chat"),
			{
				"friend_name": "friend_userr"
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 409)

		response = self.client.post(
			reverse("ind_chat"),
			{
				"friend_name": "friend_user"
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 409)

		response = self.client.post(
			reverse("ind_chat"),
			{
				"friend_name": "second_friend_user"
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 403)

	def test_get_chat_list(self):
		response = self.client.post(
			reverse("ind_chat"),
			{
				"friend_name": "friend_user"
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 201)

		response = self.client.post(
			reverse("ind_chat"),
			{
				"friend_name": "third_friend_user"
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 201)

		response = self.client.post(
			reverse("ind_chat"),
			{
				"friend_name": "second_friend_user"
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 403)

		response = self.client.get(
			reverse("chat_list_create_group"),
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertContains(response, "friend_user")
		self.assertContains(response, "third_friend_user")
		self.assertNotContains(response, "second_friend_user")

	def test_create_group_chat(self):
		response = self.client.post(
			reverse("chat_list_create_group"),
			{
				"group_name": "LOS WACHIKOLEROS",
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 201)

		response = self.client.post(
			reverse("chat_list_create_group"),
			{
				"group_nme": 5,
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 400)

	def test_detail_group_chat(self):
		response = self.client.post(
			reverse("chat_list_create_group"),
			{
				"group_name": "LOS WACHIKOLEROS",
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 201)
		chat_id = response.data["id"]
		response = self.client.get(
			reverse("chat_detail", args=(chat_id,)),
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertContains(response, chat_id)
		self.assertContains(response, "LOS WACHIKOLEROS")

	def test_add_friend_to_chat_group(self):
		client = APIClient()
		response = self.client.post(
			reverse("chat_list_create_group"),
			{
				"group_name": "LOS WACHIKOLEROS",
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		chat_id = response.data["id"]

		response = client.post(
			reverse("chat_detail", args=(chat_id,)),
			{
				"friends": [
					{
						"friend": f"{self.friend_user}"
					},
					{
						"friend": f"{self.third_friend_user}",
					},
				]
			},
			format = 'json',
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 200)
		response = self.client.get(
			reverse("chat_detail", args=(chat_id,)),
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertContains(response, f"{self.friend_user}")
		self.assertContains(response, f"{self.third_friend_user}")

	def test_message_to_chat(self):
		response = self.client.post(
			reverse("ind_chat"),
			{
				"friend_name": "friend_user"
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		chat_id = response.data['chat_id']
		response = self.client.post(
			reverse("message_list", args=(chat_id,)),
			{
				"content": "CHUPACHUPS",
			},
			HTTP_AUTHORIZATION = f"JWT {self.friend_user_token}"
		)
		self.assertEqual(response.status_code, 201)
		response = self.client.post(
			reverse("message_list", args=(chat_id,)),
			{
				"content": "frutilupis",
			},
			HTTP_AUTHORIZATION = f"JWT {self.test_user_token}"
		)
		self.assertEqual(response.status_code, 201)
		response = self.client.post(
			reverse("message_list", args=(chat_id,)),
			{
				"content": "SUPERTOD",
			},
			HTTP_AUTHORIZATION = f"JWT {self.second_friend_user_token}"
		)
		self.assertEqual(response.status_code, 403)
		response = self.client.get(
			reverse("message_list", args=(chat_id,)),
			HTTP_AUTHORIZATION = f'JWT {self.test_user_token}'
		)
		self.assertContains(response, "CHUPACHUPS")
		self.assertContains(response, "frutilupis")
		self.assertNotContains(response, "SUPERTOD")

		response = self.client.get(
			reverse("message_list", args=(chat_id,)),
			HTTP_AUTHORIZATION = f'JWT {self.second_friend_user_token}'
		)
		self.assertEqual(response.status_code, 403)
