from core.auth.auth import authenticate_user

user = authenticate_user('ahmed_m', 'Pass_123')
if user:
    print(f"Login successful for {user['username']}")
else:
    print("Login failed")
