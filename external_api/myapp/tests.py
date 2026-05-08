from __future__ import annotations

import json
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from myapp import db_utils


class EndpointTests(TestCase):
	def test_api_signup_returns_created_user(self):
		payload = {
			"username": "alice",
			"email": "alice@example.com",
			"password": "secret123",
			"first_name": "Alice",
			"last_name": "Doe",
		}

		with patch("myapp.views.create_user") as create_user:
			create_user.return_value = {
				"id": 1,
				"username": "alice",
				"email": "alice@example.com",
				"first_name": "Alice",
				"last_name": "Doe",
				"profile_id": 99,
			}

			response = self.client.post(
				"/api/signup/",
				data=json.dumps(payload),
				content_type="application/json",
			)

		self.assertEqual(response.status_code, 201)
		body = response.json()
		self.assertEqual(body["status"], "success")
		self.assertEqual(body["user"]["username"], "alice")
		create_user.assert_called_once()

	def test_api_login_sets_session_cookie(self):
		payload = {"identifier": "alice", "password": "secret123"}

		with patch("myapp.views.authenticate_user") as authenticate_user, patch(
			"myapp.views.create_session"
		) as create_session:
			authenticate_user.return_value = {
				"id": 1,
				"username": "alice",
				"email": "alice@example.com",
				"first_name": "Alice",
				"last_name": "Doe",
			}
			create_session.return_value = "session-key-123"

			response = self.client.post(
				"/api/login/",
				data=json.dumps(payload),
				content_type="application/json",
			)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["status"], "success")
		self.assertIn("sessionid", response.cookies)
		self.assertEqual(response.cookies["sessionid"].value, "session-key-123")

	def test_process_deposit_requires_session(self):
		response = self.client.post(
			"/deposit/process-payment/",
			data=json.dumps({"amount": "25.50", "card_number": "4111111111111111", "cvc": "123"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 401)
		self.assertEqual(response.json()["message"], "Authentication required.")

	def test_process_deposit_succeeds_with_session(self):
		payload = {"amount": "25.50", "card_number": "4111111111111111", "cvc": "123"}

		with patch("myapp.views.get_session_user_id") as get_session_user_id, patch(
			"myapp.views.record_deposit"
		) as record_deposit:
			get_session_user_id.return_value = 1
			record_deposit.return_value = {
				"id": 10,
				"amount": "25.50",
				"status": "completed",
				"date": "2026-05-08T10:00:00Z",
				"balance": "125.50",
			}

			response = self.client.post(
				"/deposit/process-payment/",
				data=json.dumps(payload),
				content_type="application/json",
				HTTP_COOKIE="sessionid=session-key-123",
			)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()["deposit"]["status"], "completed")

	def test_products_requires_api_key(self):
		response = self.client.get("/external_api/api/products/")
		self.assertEqual(response.status_code, 401)

	def test_products_returns_advertised_items(self):
		with patch("myapp.views.get_api_client") as get_api_client, patch(
			"myapp.views.list_advertised_products"
		) as list_advertised_products:
			get_api_client.return_value = {"id": 1, "name": "Test Client"}
			list_advertised_products.return_value = [
				{"id": 1, "name": "Item 1", "price": "9.99"}
			]

			response = self.client.get(
				"/external_api/api/products/",
				HTTP_X_API_KEY="api-key-123",
			)

		self.assertEqual(response.status_code, 200)
		body = response.json()
		self.assertEqual(body["count"], 1)
		self.assertEqual(body["products"][0]["name"], "Item 1")

	def test_create_order_returns_order_payload(self):
		with patch("myapp.views.get_api_client") as get_api_client, patch(
			"myapp.views.create_order"
		) as create_order:
			get_api_client.return_value = {"id": 1, "name": "Test Client"}
			create_order.return_value = {
				"id": 20,
				"buyer_id": 3,
				"seller_id": 4,
				"product_id": 5,
				"quantity": 1,
			}

			response = self.client.post(
				"/external_api/api/create_order/",
				data=json.dumps({"buyer_id": 3, "product_id": 5, "quantity": 1}),
				content_type="application/json",
				HTTP_X_API_KEY="api-key-123",
			)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()["order"]["product_id"], 5)

	def test_inventory_upload_accepts_csv(self):
		csv_file = SimpleUploadedFile(
			"products.csv",
			b"name,price,quantity,advertise,for_sale\nDemo Item,19.99,3,true,true\n",
			content_type="text/csv",
		)

		with patch("myapp.views.get_session_user_id") as get_session_user_id, patch(
			"myapp.views.bulk_upload_items"
		) as bulk_upload_items:
			get_session_user_id.return_value = 1
			bulk_upload_items.return_value = {
				"count": 1,
				"items": [{"id": 1, "name": "Demo Item", "price": "19.99"}],
			}

			response = self.client.post(
				"/inventory/upload/",
				data={"file": csv_file},
				HTTP_COOKIE="sessionid=session-key-123",
			)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()["count"], 1)

	def test_ai_description_returns_text(self):
		with patch("myapp.views.get_session_user_id") as get_session_user_id, patch(
			"myapp.views.generate_description"
		) as generate_description:
			get_session_user_id.return_value = 1
			generate_description.return_value = ("Generated description text.", "fallback")

			response = self.client.post(
				"/inventory/ai-desc/",
				data=json.dumps({"name": "Demo Item", "category": "Accessories"}),
				content_type="application/json",
				HTTP_COOKIE="sessionid=session-key-123",
			)

		self.assertEqual(response.status_code, 200)
		body = response.json()
		self.assertEqual(body["description"], "Generated description text.")
		self.assertEqual(body["source"], "fallback")

	def test_generate_description_uses_gemini_when_available(self):
		with patch("myapp.db_utils.os.getenv") as getenv, patch(
			"myapp.db_utils.genai.Client"
		) as client_class:
			getenv.return_value = "test-api-key"
			client_instance = client_class.return_value
			client_instance.models.generate_content.return_value.text = "Gemini description text."

			description, source = db_utils.generate_description(
				"Demo Item",
				category="Accessories",
				features="lightweight",
				tone="friendly",
			)

		self.assertEqual(source, "gemini")
		self.assertEqual(description, "Gemini description text.")
		client_class.assert_called_once()

	def test_generate_description_falls_back_without_key(self):
		with patch("myapp.db_utils.os.getenv") as getenv:
			getenv.return_value = None
			description, source = db_utils.generate_description("Demo Item")

		self.assertEqual(source, "fallback")
		self.assertIn("Demo Item", description)
