import bcrypt

password = "Pass_123"
hashed = "$2a$18$H.vv1GNoiMoSZcT0.83w8OV0P9pCTnlGN1.S0hNIUVTjIgyIR2uj2"

try:
    match = bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    print(f"Match: {match}")
except Exception as e:
    print(f"Error: {e}")
