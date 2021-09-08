"""
ASGI config for test_chat project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os
import django
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat.routing


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_chat.settings')

application = ProtocolTypeRouter({
	'http': get_asgi_application(),
	'websocket': AuthMiddlewareStack(
		URLRouter(
			chat.routing.websocket_urlpatterns,
		)
	),
})
