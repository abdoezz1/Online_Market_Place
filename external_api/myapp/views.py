from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .db_utils import (
	authenticate_user,
	bulk_upload_items,
	create_order,
	create_session,
	create_user,
	generate_description,
	get_api_client,
	get_session_user_id,
	list_advertised_products,
	process_deposit as record_deposit,
)


def _json_body(request):
	if request.body:
		try:
			decoded = request.body.decode("utf-8").strip()
			if decoded:
				return json.loads(decoded)
		except Exception:
			pass
	if request.POST:
		return request.POST.dict()
	return {}


def _api_key_from_request(request):
	header_key = request.headers.get("X-API-KEY") or request.headers.get("X-Api-Key")
	if header_key:
		return header_key.strip()

	authorization = request.headers.get("Authorization", "").strip()
	if not authorization:
		return ""
	if authorization.lower().startswith("api-key "):
		return authorization.split(None, 1)[1].strip()
	if authorization.lower().startswith("bearer "):
		return authorization.split(None, 1)[1].strip()
	return authorization


def _session_user_id(request):
	session_key = request.COOKIES.get("sessionid")
	if not session_key:
		return None
	return get_session_user_id(session_key)


def _error(message, status=400, **extra):
	payload = {"status": "error", "message": message}
	payload.update(extra)
	return JsonResponse(payload, status=status)


def index(request):
	return HttpResponse(
		"<h1>External API is running</h1><p>Visit <a href='/health/'>/health/</a> for a status check.</p>"
	)


def health(request):
	return JsonResponse({"status": "ok"})


def store(request):
	return JsonResponse({"status": "store"})


@csrf_exempt
def api_signup(request):
	if request.method != "POST":
		return _error("Method not allowed.", status=405)

	data = _json_body(request)
	username = str(data.get("username", "")).strip()
	email = str(data.get("email", "")).strip()
	password = str(data.get("password", "")).strip()
	first_name = str(data.get("first_name", "")).strip()
	last_name = str(data.get("last_name", "")).strip()

	if not all([username, email, password, first_name, last_name]):
		return _error("All fields are required.")

	try:
		user = create_user(username, email, password, first_name, last_name)
	except ValueError as exc:
		return _error(str(exc), status=409)
	except Exception as exc:
		return _error(f"Unable to create user: {exc}", status=500)

	return JsonResponse(
		{
			"status": "success",
			"message": "User registered successfully.",
			"user": {
				"id": user["id"],
				"username": user["username"],
				"email": user["email"],
				"first_name": user["first_name"],
				"last_name": user["last_name"],
				"profile_id": user["profile_id"],
			},
		},
		status=201,
	)


@csrf_exempt
def api_login(request):
	if request.method != "POST":
		return _error("Method not allowed.", status=405)

	data = _json_body(request)
	identifier = str(data.get("identifier", "")).strip()
	password = str(data.get("password", "")).strip()

	if not identifier or not password:
		return _error("Identifier and password are required.")

	try:
		user = authenticate_user(identifier, password)
		if not user:
			return _error("Invalid credentials.", status=401)
		session_key = create_session(user["id"])
	except Exception as exc:
		return _error(f"Login failed: {exc}", status=500)

	response = JsonResponse(
		{
			"status": "success",
			"message": "Login successful.",
			"user": user,
		}
	)
	response.set_cookie(
		"sessionid",
		session_key,
		httponly=True,
		samesite="Lax",
		max_age=60 * 60 * 24 * 7,
		path="/",
	)
	return response


@csrf_exempt
def process_deposit(request):
	if request.method != "POST":
		return _error("Method not allowed.", status=405)

	user_id = _session_user_id(request)
	if not user_id:
		return _error("Authentication required.", status=401)

	data = _json_body(request)
	amount_raw = str(data.get("amount", "")).strip()
	card_number = str(data.get("card_number", data.get("card", ""))).strip()
	cvc = str(data.get("cvc", data.get("cvv", ""))).strip()

	try:
		amount = Decimal(amount_raw)
	except (InvalidOperation, TypeError):
		return _error("Amount must be a valid number.")

	if amount < Decimal("10") or amount > Decimal("10000"):
		return _error("Amount must be between 10 and 10,000.")

	if len(card_number) != 16 or not card_number.isdigit() or card_number[0] not in {"4", "5"}:
		return _error("Card number must be exactly 16 digits and start with 4 or 5.")

	if len(cvc) != 3 or not cvc.isdigit():
		return _error("CVC must be exactly 3 digits.")

	try:
		deposit = record_deposit(user_id, amount)
	except ValueError as exc:
		return _error(str(exc), status=400)
	except Exception as exc:
		return _error(f"Deposit failed: {exc}", status=500)

	return JsonResponse(
		{
			"status": "success",
			"message": "Deposit processed successfully.",
			"deposit": deposit,
		},
		status=201,
	)


def products(request):
	if request.method != "GET":
		return _error("Method not allowed.", status=405)

	api_key = _api_key_from_request(request)
	if not api_key:
		return _error("API key is required.", status=401)

	client = get_api_client(api_key)
	if not client:
		return _error("Invalid API key.", status=401)

	try:
		rows = list_advertised_products()
	except Exception as exc:
		return _error(f"Unable to load products: {exc}", status=500)

	return JsonResponse(
		{
			"status": "success",
			"client": {"id": client["id"], "name": client["name"]},
			"count": len(rows),
			"products": rows,
		}
	)


@csrf_exempt
def create_order_view(request):
	if request.method != "POST":
		return _error("Method not allowed.", status=405)

	api_key = _api_key_from_request(request)
	if not api_key:
		return _error("API key is required.", status=401)

	client = get_api_client(api_key)
	if not client:
		return _error("Invalid API key.", status=401)

	data = _json_body(request)
	buyer_id_raw = data.get("buyer_id")
	product_id_raw = data.get("product_id")
	quantity_raw = data.get("quantity", 1)

	try:
		buyer_id = int(buyer_id_raw)
		product_id = int(product_id_raw)
		quantity = int(quantity_raw)
	except (TypeError, ValueError):
		return _error("buyer_id, product_id, and quantity must be integers.")

	try:
		order = create_order(buyer_id, product_id, quantity)
	except ValueError as exc:
		return _error(str(exc), status=400)
	except Exception as exc:
		return _error(f"Unable to create order: {exc}", status=500)

	return JsonResponse(
		{
			"status": "success",
			"message": "Order created successfully.",
			"client": {"id": client["id"], "name": client["name"]},
			"order": order,
		},
		status=201,
	)


@csrf_exempt
def inventory_upload(request):
	if request.method != "POST":
		return _error("Method not allowed.", status=405)

	user_id = _session_user_id(request)
	if not user_id:
		return _error("Authentication required.", status=401)

	uploaded_file = request.FILES.get("file") or request.FILES.get("csv_file")
	if not uploaded_file:
		return _error("Upload a CSV file using the file or csv_file field.")

	try:
		result = bulk_upload_items(user_id, uploaded_file)
	except ValueError as exc:
		return _error(str(exc), status=400)
	except Exception as exc:
		return _error(f"CSV upload failed: {exc}", status=500)

	return JsonResponse(
		{
			"status": "success",
			"message": "CSV imported successfully.",
			"count": result["count"],
			"items": result["items"],
		},
		status=201,
	)


@csrf_exempt
def ai_description(request):
	if request.method != "POST":
		return _error("Method not allowed.", status=405)

	user_id = _session_user_id(request)
	if not user_id:
		return _error("Authentication required.", status=401)

	data = _json_body(request)
	name = str(data.get("name", data.get("product_name", ""))).strip()
	category = str(data.get("category", "")).strip()
	features = str(data.get("features", data.get("keywords", ""))).strip()
	tone = str(data.get("tone", "")).strip()

	if not name:
		return _error("Product name is required.")

	try:
		description, source = generate_description(name, category=category, features=features, tone=tone)
	except Exception as exc:
		return _error(f"Unable to generate description: {exc}", status=500)

	return JsonResponse(
		{
			"status": "success",
			"description": description,
			"source": source,
		}
	)

