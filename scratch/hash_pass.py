import bcrypt

passwords = {
    'ahmed_m': 'Pass_123',
    'sara_k': 'New_Pass_124',
    'omar_h': 'NewPass_125',
    'admin': 'Admin_Pass_163',
    'nour_a': 'Nour_Pass_723'
}

print("BEGIN;")
for user, pwd in passwords.items():
    hashed = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    print(f"UPDATE users SET password = '{hashed}' WHERE username = '{user}';")
    print(f"-- {user} hash: {hashed}")
print("COMMIT;")
