from core.auth.auth import hash_password
import bcrypt

hashed = hash_password("testpassword")
print(f"Hashed: {hashed}")
rounds = hashed.split('$')[2]
print(f"Rounds: {rounds}")
