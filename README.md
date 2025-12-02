# Gemini + Veo マルチセグメント動画ジェネレーター

Geminiテキストモデルのフレームプロンプト、Gemini 2.5 Flash Imageの絵コンテ（ストーリーボード）画像、Veo 3.1の短尺クリップ、`ffmpeg` の結合を組み合わせて、単一クリップより長い動画を生成するStreamlitアプリ兼Pythonパイプラインです。キャラクター・スタイル・カメラ・世界観の一貫性を重視し、オフライン安全なフェイククライアントも備えています。

## 特長
- 単一タブでフレームを追加・挿入しつつ、1フレームずつ生成/再生成をプレビューしながら進行。
- 生成済みの絵コンテを確認し、内容を編集して即再生成可能。途中でフレーム数を増減・挿入できる。
- Veo 3.1のフレーム間補間で各セグメントを作り、`ffmpeg` concatデマルチプレクサで1本のMP4に結合。
- `ENABLE_REAL_GENAI=1` を明示した場合のみ実APIを使用。`USE_FAKE_GENAI=1` で完全オフラインのフェイク出力を強制でき、UIからも切り替え可能。

## インストールと前提条件
- Python 3.10+ 推奨。
- PATH に `ffmpeg` があること（実行環境でのクリップ結合に必要）。
- 依存関係: `pip install -r requirements.txt`

## APIモードと環境変数
- `.env` をリポジトリ直下に配置すると、`video_pipeline/config.py` 読み込み時と `app.py` 起動時に自動で読み込まれます（`python-dotenv` の `load_dotenv()` を使用）。
- **REAL**: `.env` に `ENABLE_REAL_GENAI=1` と `GEMINI_API_KEY`（または `GOOGLE_API_KEY`）を設定。オプションで Vertex AI 用に `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` を指定。
- **FAKE**: `.env` で `USE_FAKE_GENAI=1` を設定すると `google-genai` 非依存のフェイククライアントで安全に動作。Streamlit UI ではチェックボックスで同じモードを選択できます。
- **DISABLED**: 上記いずれも未設定の場合、`get_genai_client()` は誤用防止のため例外を送出します。

## クイックスタート（Streamlit UI）
```bash
# リポジトリ直下で
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# `.env.example` をコピーして環境変数を設定
cp .env.example .env
# オフラインデモの場合は .env に USE_FAKE_GENAI=1 を残す
# 実APIを使う場合は .env で ENABLE_REAL_GENAI=1 と GEMINI_API_KEY を設定

streamlit run app.py
```
UIの流れ（単一タブ）:
1. フレームの説明を入力して末尾追加/途中挿入する（最低2フレーム）。
2. 各フレームカードで「生成/再生成」を押し、画像を確認しながら必要なフレームだけ更新。
3. 「すべてのフレームを一括生成」で未生成分をまとめて作成も可能。
4. 「現在のフレームで動画を生成」でセグメントを結合し、連結済みMP4を再生・ダウンロード。出力は `outputs/run_<timestamp>/` 配下に保存されます。

## パイプラインのコード利用例
`USE_FAKE_GENAI=1` または `ENABLE_REAL_GENAI=1` を設定した上で、Python から直接呼び出せます。
```python
from video_pipeline.run_pipeline import run_pipeline

final_path = run_pipeline(
    frames=[
        {"id": "A", "prompt": "夜のネオン屋上で主人公が立つワイドショット"},
        {"id": "B", "prompt": "主人公がカメラに向かって歩き出す"},
        {"id": "C", "prompt": "カメラが寄り、風で髪がなびくクローズアップ"},
    ],
    ref_image_path=None,           # または PNG/JPEG への Path
)
print("Video at:", final_path)
```
絵コンテだけを再生成したい場合は `video_pipeline.images.regenerate_storyboard_images` を直接使えます。

## 出力とファイル構成
- `app.py` — Streamlit UI のエントリポイント（フェイクモード切替、逐次生成UI）。
- `video_pipeline/`
  - `config.py` — パイプライン設定、APIモード判定、実行ディレクトリ作成。
  - `images.py` — 参照画像と累積生成画像をギャラリーとして連鎖させる絵コンテ生成・再生成。
  - `videos.py` — フレーム間のVeo 3.1セグメント生成と最終フレーム抽出。
  - `ffmpeg_utils.py` — `ffmpeg` によるクリップ連結と終端フレーム抽出ヘルパー。
  - `run_pipeline.py` — フレーム→セグメント→最終MP4のオーケストレーション。
- `tests/` — フェイククライアントと`ffmpeg`コマンドのオフラインテスト。

## テスト
実APIを呼ばないユニットテスト:
```bash
python -m pytest
```

## トラブルシューティング
- `google.genai` の ImportError: `pip install -r requirements.txt` を実行（REALモードのみ必要）。
- RuntimeError でクライアント作成に失敗: REAL モードなら `ENABLE_REAL_GENAI=1`、FAKE モードなら `USE_FAKE_GENAI=1` を設定してください。
- `ffmpeg` 関連エラー: PATH を確認し、クリップパスが存在することを確かめたうえで再実行。
