from steam.guard import generate_twofactor_code

shared_secret = "UbOqdqmTmCh0z5eAfVLi/3JVFlU="
# The function expects the base64 string as bytes
code = generate_twofactor_code(shared_secret.encode('utf-8'))

print(f"Your Steam Guard Code is: {code}")
