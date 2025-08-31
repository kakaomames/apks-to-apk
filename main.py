from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    # ここにHTML文字列を埋め込む
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>APKs to APK Converter</title>
        <style>
            body {
                font-family: sans-serif;
                margin: 20px;
                background-color: #f4f4f4;
            }
            .container {
                max-width: 600px;
                margin: auto;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
            }
            input[type="file"] {
                display: block;
                margin: 20px 0;
            }
            input[type="submit"] {
                background-color: #007BFF;
                color: white;
                padding: 10px 15px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            input[type="submit"]:hover {
                background-color: #0056b3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>APKsファイルをアップロード</h1>
            <p>ここにAPKsファイルをアップロードしてください。単一のAPKに変換します。</p>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept=".apks">
                <input type="submit" value="変換">
            </form>
        </div>
    </body>
    </html>
    """
    return html_content

if __name__ == '__main__':
    app.run(debug=True)

