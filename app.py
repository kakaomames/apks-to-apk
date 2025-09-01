from flask import Flask, request
import pdfplumber
import re
import io

app = Flask(__name__)

# HTMLをPythonの文字列として定義
HTML_FORM = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>PDFから単語リストを作成</title>
    <style>
        body { font-family: sans-serif; margin: 2em; line-height: 1.6; }
        .container { max-width: 600px; margin: auto; padding: 2em; border: 1px solid #ccc; border-radius: 8px; }
        input[type="file"] { margin-bottom: 1em; }
        input[type="submit"] { padding: 0.5em 1em; }
        pre { background-color: #f4f4f4; padding: 1em; border-radius: 4px; overflow-x: auto; }
        h1, h2 { color: #333; }
        footer { margin-top: 2em; font-size: 0.8em; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>PDFから単語リストを作成</h1>
        <p>PDFファイルをアップロードすると、単語と日本語訳を抽出して表示します。</p>
        <form action="/" method="post" enctype="multipart/form-data">
            <label for="pdf_file">ファイルを選択してください：</label><br>
            <input type="file" name="pdf_file" id="pdf_file" accept=".pdf"><br>
            <input type="submit" value="ファイルをアップロードして解析">
        </form>
        {% if word_list %}
        <h2>抽出された単語リスト</h2>
        <pre>{{ word_list }}</pre>
        {% endif %}
    </div>
    <footer>&copy; Kakaomame's Web App</footer>
</body>
</html>
"""

def parse_pdf_from_memory(file_stream):
    """
    メモリ上のPDFファイルから単語と日本語訳を抽出し、key=value形式のリストを返します。
    """
    word_list = []
    try:
        with pdfplumber.open(file_stream) as pdf:
            for page in pdf.pages:
                raw_text = page.extract_text()
                if not raw_text:
                    continue
                
                lines = raw_text.split('\n')
                
                word_pattern = re.compile(r'^[a-zA-Z\s\']+$')
                meaning_pattern = re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]+')
                
                english_word = None
                for line in lines:
                    trimmed_line = line.strip()
                    if word_pattern.match(trimmed_line) and not trimmed_line.startswith(('word', 'PAGE')):
                        english_word = trimmed_line
                    elif english_word and meaning_pattern.search(trimmed_line):
                        clean_meaning = re.sub(r'[\u3040-\u309f]+$', '', trimmed_line).strip()
                        word_list.append(f"{english_word}={clean_meaning}")
                        english_word = None # ペアが見つかったのでリセット
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return [f"エラーが発生しました: {e}"]
    return word_list

@app.route('/', methods=['GET', 'POST'])
def upload_and_process_pdf():
    word_list = []
    if request.method == 'POST':
        # PDFファイルがアップロードされたか確認
        if 'pdf_file' not in request.files:
            return HTML_FORM.replace('{% if word_list %}', f"<p style='color:red;'>ファイルが選択されていません。</p>")
        
        pdf_file = request.files['pdf_file']
        if pdf_file.filename == '':
            return HTML_FORM.replace('{% if word_list %}', f"<p style='color:red;'>ファイルが選択されていません。</p>")
        
        if pdf_file and pdf_file.filename.endswith('.pdf'):
            # ファイルの内容をメモリに読み込み、解析関数に渡す
            file_stream = io.BytesIO(pdf_file.read())
            processed_words = parse_pdf_from_memory(file_stream)
            word_list_str = '\n'.join(processed_words)
            return HTML_FORM.replace('{% if word_list %}', f"<pre>{word_list_str}</pre>")
        else:
            return HTML_FORM.replace('{% if word_list %}', f"<p style='color:red;'>PDFファイルのみアップロードできます。</p>")
            
    # GETリクエストの場合、フォームを表示
    return HTML_FORM.replace('{% if word_list %}', '')

if __name__ == '__main__':
    app.run(debug=True)
