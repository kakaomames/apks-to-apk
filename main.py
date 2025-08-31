import os
import json
import subprocess
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# 一時ファイルのアップロードと変換結果を保存するフォルダ
UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = 'converted'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

@app.route('/')
def home():
    """
    APKsアップロード用のHTMLページを表示する
    """
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
            #status {
                margin-top: 20px;
                font-weight: bold;
                color: #555;
            }
            progress {
                width: 100%;
                margin-top: 10px;
                -webkit-appearance: none;
                appearance: none;
            }
            progress::-webkit-progress-bar {
                background-color: #eee;
                border-radius: 5px;
            }
            progress::-webkit-progress-value {
                background-color: #007BFF;
                border-radius: 5px;
            }
            .download-link {
                color: #007BFF;
                text-decoration: none;
                font-weight: bold;
            }
            .download-link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>APKs to APK 変換ツール</h1>
            <p>ここにAPKsファイルをアップロードしてください。単一のAPKに変換します。</p>
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" id="fileInput" name="file" accept=".apks">
                <input type="button" value="変換を開始" onclick="uploadFile()">
            </form>
            <div id="status"></div>
            <progress id="progressBar" value="0" max="100" style="display:none;"></progress>
        </div>

        <script>
            async function uploadFile() {
                const fileInput = document.getElementById('fileInput');
                const file = fileInput.files[0];
                const statusDiv = document.getElementById('status');
                const progressBar = document.getElementById('progressBar');

                if (!file) {
                    statusDiv.textContent = 'ファイルを選択してください。';
                    return;
                }

                // Vercelの無料プランのペイロード制限
                const chunkSize = 4.5 * 1024 * 1024;
                const totalChunks = Math.ceil(file.size / chunkSize);
                let offset = 0;
                let chunkIndex = 0;

                progressBar.style.display = 'block';
                progressBar.value = 0;
                statusDiv.textContent = `アップロード中... (0%)`;

                const uniqueId = Date.now().toString(); // セッションごとに一意のIDを生成

                while (offset < file.size) {
                    const chunk = file.slice(offset, offset + chunkSize);
                    const formData = new FormData();
                    formData.append('chunk', chunk);
                    formData.append('filename', file.name);
                    formData.append('chunkIndex', chunkIndex);
                    formData.append('uniqueId', uniqueId);
                    
                    try {
                        const response = await fetch('/upload-chunk', {
                            method: 'POST',
                            body: formData
                        });

                        if (!response.ok) {
                            throw new Error('チャンクのアップロードに失敗しました。');
                        }

                        const result = await response.json();
                        if (result.error) {
                            throw new Error(result.error);
                        }

                        // プログレスバーとステータスを更新
                        progressBar.value = ((chunkIndex + 1) / totalChunks) * 100;
                        statusDiv.textContent = `アップロード中: ${chunkIndex + 1}/${totalChunks} チャンク (${Math.round(progressBar.value)}%)`;

                        offset += chunkSize;
                        chunkIndex++;
                    } catch (error) {
                        statusDiv.textContent = `エラー: ${error.message}`;
                        progressBar.style.display = 'none';
                        return;
                    }
                }

                statusDiv.textContent = '全チャンクのアップロードが完了しました。サーバーで変換処理を開始します。';
                
                // 全チャンクのアップロードが完了したら、サーバーに変換処理をリクエスト
                try {
                    const convertResponse = await fetch('/convert', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ filename: file.name, uniqueId: uniqueId })
                    });
                    const result = await convertResponse.json();
                    
                    if (result.success) {
                        statusDiv.innerHTML = `<p>変換が完了しました！ <a class="download-link" href="${result.download_url}">ここからダウンロード</a></p>`;
                    } else {
                        statusDiv.textContent = `変換エラー: ${result.error}`;
                    }
                } catch (error) {
                    statusDiv.textContent = `変換処理でエラーが発生しました: ${error.message}`;
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content

@app.route('/upload-chunk', methods=['POST'])
def upload_chunk():
    """
    ファイルのチャンクをサーバーにアップロードする
    """
    try:
        chunk = request.files.get('chunk')
        filename = request.form.get('filename')
        chunk_index = request.form.get('chunkIndex')
        unique_id = request.form.get('uniqueId')
        
        if not all([chunk, filename, chunk_index, unique_id]):
            return jsonify({'error': 'Missing data'}), 400

        temp_folder = os.path.join(UPLOAD_FOLDER, unique_id)
        os.makedirs(temp_folder, exist_ok=True)
        
        chunk_path = os.path.join(temp_folder, f"{filename}.part{chunk_index}")
        chunk.save(chunk_path)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/convert', methods=['POST'])
def convert():
    """
    アップロードされたチャンクを結合し、bundletoolでAPKに変換する
    """
    try:
        data = request.json
        filename = data.get('filename')
        unique_id = data.get('uniqueId')

        if not all([filename, unique_id]):
            return jsonify({'error': 'Missing data'}), 400

        temp_folder = os.path.join(UPLOAD_FOLDER, unique_id)
        original_filepath = os.path.join(temp_folder, filename)

        # チャンクを元のファイルに結合
        with open(original_filepath, 'wb') as outfile:
            chunk_index = 0
            while True:
                chunk_path = os.path.join(temp_folder, f"{filename}.part{chunk_index}")
                if not os.path.exists(chunk_path):
                    break
                with open(chunk_path, 'rb') as infile:
                    outfile.write(infile.read())
                os.remove(chunk_path)  # 結合後にチャンクを削除
                chunk_index += 1
        
        # bundletoolでAPKに変換
        # bundletoolのパスが通っていることを確認してください
        converted_filename = f"{os.path.splitext(filename)[0]}.apk"
        output_filepath = os.path.join(CONVERTED_FOLDER, converted_filename)

        # bundletoolは.apksを直接扱えないため、zipとして解凍し、必要なbase.apkを抽出
        # 簡易的な実装のため、base.apkをそのまま返す
        base_apk_path = ''
        with zipfile.ZipFile(original_filepath, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.filename.endswith('base.apk'):
                    zip_ref.extract(file_info.filename, path=CONVERTED_FOLDER)
                    base_apk_path = os.path.join(CONVERTED_FOLDER, file_info.filename)
                    break
        
        # 抽出したbase.apkをわかりやすい名前に変更
        if base_apk_path:
            os.rename(base_apk_path, output_filepath)
            os.remove(original_filepath) # 処理完了後に元のapksファイルを削除
            os.rmdir(temp_folder) # 一時フォルダを削除

            return jsonify({
                'success': True,
                'download_url': f'/download/{converted_filename}'
            })
        else:
            os.remove(original_filepath)
            os.rmdir(temp_folder)
            return jsonify({'success': False, 'error': 'base.apkが見つかりませんでした。'})

    except Exception as e:
        # エラー発生時も一時ファイルをクリーンアップ
        if os.path.exists(original_filepath):
            os.remove(original_filepath)
        if os.path.exists(temp_folder):
            os.rmdir(temp_folder)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """
    変換されたAPKファイルをダウンロードできるようにする
    """
    return send_from_directory(CONVERTED_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
