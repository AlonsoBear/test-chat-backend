from django.test import TestCase
from django.urls import reverse

from users.models import CustomUser
from .models import Friend, FriendsList, Chat

# Create your tests here.

class FriendSystemTest(TestCase):
	def setUp(self):
		self.test_user = CustomUser(username="test_user")
		self.test_user.set_password("12345678")
		self.test_user.save()

		self.friend_user = CustomUser(username="friend_user")
		self.friend_user.set_password("12345678")
		self.friend_user.save()

		self.second_friend_user = CustomUser(username="second_friend_user")
		self.second_friend_user.set_password("12345678")
		self.second_friend_user.save()

	def test_add_friend(self):
		response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": "test_user",
				"password": "12345678",
			}
		)
		token = response.data["access"]
		self.assertEqual(response.status_code, 200)

		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "friend_user"
			},
			HTTP_AUTHORIZATION = f'JWT {token}'
		)
		self.assertEqual(response.status_code, 201)
		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "error_user"
			},
			HTTP_AUTHORIZATION = f'JWT {token}'
		)
		self.assertEqual(response.status_code, 422)
		self.assertEqual(response.data, "User not Found")
		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "test_user"
			},
			HTTP_AUTHORIZATION = f'JWT {token}'
		)
		self.assertEqual(response.status_code, 409)
		self.assertEqual(response.data, 'Unable to befriend yourself')

		response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": "friend_user",
				"password": "12345678",
			}
		)
		token = response.data["access"]
		self.assertEqual(response.status_code, 200)
		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "test_user"
			},
			HTTP_AUTHORIZATION = f'JWT {token}'
		)
		self.assertEqual(response.status_code, 409)
		self.assertEqual(response.data, 'test_user has already sent you a friend request')
		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "test_user"
			},
		)
		self.assertEqual(response.status_code, 401)
		response = self.client.get(
			reverse("friend_list"),
			{},
			HTTP_AUTHORIZATION = f'JWT {token}'
		)
		self.assertEqual(response.status_code, 422)


	def test_accept_friend_request(self):
		response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": "test_user",
				"password": "12345678",
			}
		)
		test_token = response.data["access"]
		self.assertEqual(response.status_code, 200)

		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "friend_user"
			},
			HTTP_AUTHORIZATION = f'JWT {test_token}'
		)
		self.assertEqual(response.status_code, 201)

		response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": "second_friend_user",
				"password": "12345678",
			}
		)
		token = response.data["access"]
		self.assertEqual(response.status_code, 200)

		response = self.client.post(
			reverse("friend_list"),
			{
				"friend": "friend_user"
			},
			HTTP_AUTHORIZATION = f'JWT {token}'
		)
		self.assertEqual(response.status_code, 201)

		response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": "friend_user",
				"password": "12345678",
			}
		)
		token = response.data["access"]

		response = self.client.get(
			reverse("friend_request_list"),
			HTTP_AUTHORIZATION = f'JWT {token}',
		)
		self.assertEqual(response.status_code, 200)

		friend_request_id_1 = response.data[0]["id"]
		friend_request_id_2 = response.data[1]["id"]

		response = self.client.post(
			reverse("friend_request", args=(friend_request_id_1,)),
			{
				"accepted": True,
			},
			HTTP_AUTHORIZATION = f'JWT {test_token}',
		)
		self.assertEqual(response.status_code, 403)

		response = self.client.post(
			reverse("friend_request", args=(friend_request_id_1,)),
			{
				"accepted": True,
			},
			HTTP_AUTHORIZATION = f'JWT {token}',
		)
		self.assertEqual(response.status_code, 201)

		response = self.client.post(
			reverse("friend_request", args=(friend_request_id_2,)),
			{
				"accepted": False,
			},
			HTTP_AUTHORIZATION = f'JWT {token}',
		)
		self.assertEqual(response.status_code, 200)
		response = self.client.get(
			reverse("friend_request_list"),
			HTTP_AUTHORIZATION = f'JWT {token}',
		)
		self.assertEqual(response.data, [])
		response = self.client.get(
			reverse("friend_list"),
			HTTP_AUTHORIZATION = f'JWT {token}',
		)
		self.assertContains(response, 'test_user')
		self.assertNotContains(response, 'second_friend_user')


class ChatSystemTest(TestCase):
	def setUp(self):
		self.test_user = CustomUser(username="test_user")
		self.test_user.set_password("12345678")
		self.test_user.save()

		self.friend_user = CustomUser(username="friend_user")
		self.friend_user.set_password("12345678")
		self.friend_user.save()

		self.second_friend_user = CustomUser(username="second_friend_user")
		self.second_friend_user.set_password("12345678")
		self.second_friend_user.save()

		self.test_user_friend_list = FriendsList.objects.create(owner=self.test_user)
		self.friend_user_friends_list = FriendsList.objects.create(owner=self.friend_user)
		self.second_friend_user_friends_list = FriendsList.objects.create(owner=self.second_friend_user)

		Friend.objects.create(friends_list=self.test_user_friend_list, friend=self.friend_user)
		#Friend.objects.create(friends_list=self.test_user_friend_list, friend=self.second_friend_user)

		Friend.objects.create(friends_list=self.friend_user_friends_list, friend=self.test_user)
		Friend.objects.create(friends_list=self.friend_user_friends_list, friend=self.second_friend_user)

		#Friend.objects.create(friends_list=self.second_friend_user_friends_list, friend=self.test_user)
		Friend.objects.create(friends_list=self.second_friend_user_friends_list, friend=self.friend_user)

	def test_chat_creation(self):
		response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": "test_user",
				"password": "12345678"
			}
		)
		test_user_token = response.data["access"]
		response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": "friend_user",
				"password": "12345678"
			}
		)
		friend_user_token = response.data["access"]
		response = self.client.post(
			reverse("token_obtain_pair"),
			{
				"username": "second_friend_user",
				"password": "12345678"
			}
		)
		second_friend_user_token = response.data["access"]

		response = self.client.post(
			reverse("chat_list"),
			{
				"friend_name": "friend_user"
			},
			HTTP_AUTHORIZATION = f"JWT {test_user_token}"
		)
		self.assertEqual(response.status_code, 201)

		response = self.client.post(
			reverse("chat_list"),
			{
				"friend_name": "friend_user"
			},
			HTTP_AUTHORIZATION = f"JWT {test_user_token}"
		)
		self.assertEqual(response.status_code, 409)

		response = self.client.post(
			reverse("chat_list"),
			{
				"friend_name": "second_friend_user"
			},
			HTTP_AUTHORIZATION = f"JWT {test_user_token}"
		)
		self.assertEqual(response.status_code, 403)
