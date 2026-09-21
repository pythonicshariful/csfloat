# CSFloat Dashboard & Launcher - How To Use

This dashboard allows you to quickly launch multiple isolated Chrome profiles, each opening specific tabs to `https://csfloat.com/db`. Because it uses persistent Chrome profiles, you only need to log in to your accounts once, and it will remember your session for all future launches!

## 1. Starting the Dashboard
1. Open a terminal in this folder (`G:\Personal\fver\csfloat`).
2. Run the application:
   ```powershell
   python app.py
   ```
3. Open your browser and go to `http://127.0.0.1:5000`.

## 2. Setting Up Your Accounts (First-Time Login)
Steam requires a manual login the very first time so you can pass the 2FA (Steam Guard) check. You only need to do this **once per profile**.

1. In the dashboard, set **Chrome Profiles** to `1` and **Tabs** to `1`.
2. Click **Launch**. This will open "Profile 1".
3. In the new Chrome window, go to `https://csfloat.com` and click **Sign in** (this will redirect you to Steam).
4. Enter your Username and Password for your first account.
5. When asked for the **Steam Guard Mobile Authenticator code**, open a new terminal in this folder and use the included 2FA script with your account's `shared_secret`:
   ```powershell
   # Replace YOUR_SHARED_SECRET with the actual shared secret for this account
   python get_2fa.py YOUR_SHARED_SECRET
   ```
6. The script will print a 5-character code. Enter it into Steam to finish logging in.
7. Close the Chrome window.

**Repeat this process** by launching Profile 2, Profile 3, etc., until you have logged into all your accounts. 

## 3. Daily Usage
Once you have logged into your profiles:
1. Open the dashboard.
2. Set the number of **Profiles** you want to launch (e.g., 3).
3. Set the number of **Tabs** you want each profile to open (e.g., 2).
4. Click **Launch**.
5. The script will launch all your profiles simultaneously. Because you already logged in during Step 2, they will all automatically be signed in and ready to use!

## 4. Closing Everything
When you are done, simply click the **Close All** button on the dashboard to safely close all automated Chrome instances at once.
