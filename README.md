# Gemini + Veo マルチセグメント動画ジェネレーター

Geminiプロンプト、Gemini 2.5 Flash Imageのキーフレーム、Veo 3.1の短尺クリップ、ffmpeg結合を組み合わせて、単一クリップより長い動画を生成するStreamlitアプリ兼Pythonパイプラインです。キャラクター・スタイル・カメラ・世界観の一貫性を重視します。

## 特長
- グローバルなスタイルを共有しつつ、フレームごとに小さな動きを付けたプロンプトを生成。
- 参照画像を連鎖させてキーフレーム間の見た目やカメラ位置を維持。
- 連続フレーム間をVeo 3.1で短尺クリップ化し、ffmpegで1本のMP4に連結。
- テーマ入力、キーフレーム数、参照画像アップロード、動きのヒントを備えたStreamlit UI。
- デフォルトはオフライン安全: `ENABLE_REAL_GENAI` を明示しない限り実API呼び出しを拒否。

## 必要環境
- Python 3.10+ 推奨（テストは3.9で実行済み、互換インポート維持）。
- PATHにffmpegがあること。
- 依存関係: `pip install -r requirements.txt`

## 環境変数
- `ENABLE_REAL_GENAI=1` — 実際のGemini/Veo呼び出しを許可するために必須。未設定の場合、`get_genai_client()` はクォータ保護のため例外を送出。
- `GEMINI_API_KEY` または `GOOGLE_API_KEY` — Gemini Developer API用。
- オプション（Vertex AIを使う場合）: `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`

## クイックスタート（Streamlit UI）
```bash
# リポジトリ直下で
python -m venv .venv && .\.venv\Scripts\activate  # シェルに合わせて調整
pip install -r requirements.txt
set ENABLE_REAL_GENAI=1
set GEMINI_API_KEY=your_key_here
streamlit run app.py
```
ブラウザでテーマを入力し、キーフレーム数（最小2）、必要なら参照画像をアップロードして「動画を生成」をクリック。生成されたMP4は `outputs/run_<timestamp>/final.mp4` に保存されます。

## パイプラインのコード利用例
```python
from video_pipeline.run_pipeline import run_pipeline

final_path = run_pipeline(
    theme="夜のネオン屋上を歩く光る妖精",
    num_frames=3,
    ref_image_path=None,           # または PNG/JPEG への Path
    motion_hint="前方へゆっくり進む動き"
)
print("Video at:", final_path)
```

## テスト
実APIを呼ばないオフライン安全なユニットテスト:
```bash
python -m pytest
```

## プロジェクト構成
- `app.py` — Streamlit UIのエントリポイント。
- `video_pipeline/`
  - `config.py` — 共有設定、ENABLE_REAL_GENAIのゲート、実行ディレクトリ作成。
  - `prompts.py` — グローバルスタイルと各フレーム説明を返すGeminiテキストプロンプト生成。
  - `images.py` — 参照画像を連鎖させるGemini 2.5 Flash Imageキーフレーム生成。
  - `videos.py` — フレーム間のVeo 3.1セグメント生成。
  - `ffmpeg_utils.py` — ffmpeg concatデマルチプレクサでの連結ヘルパー。
  - `run_pipeline.py` — プロンプト→フレーム→セグメント→最終MP4のオーケストレーション。
- `tests/` — プロンプト解析やffmpeg結合のオフラインテスト。

## 安全性とコスト管理
- 既定で実ネットワーククライアントは拒否。手動検証などで実APIを使いたい場合のみ `ENABLE_REAL_GENAI=1` を設定。自動テストでは設定しないでください。
- ffmpegが導入済みで、結合するクリップのフォーマットが揃っていることを確認してください。

## トラブルシューティング
- `google.genai` の ImportError: `pip install -r requirements.txt` を実行。
- RuntimeError で ENABLE_REAL_GENAI を要求された: 実APIを叩く場合は `ENABLE_REAL_GENAI=1` を設定。
- ffmpeg結合エラー: クリップのパスとコーデックを確認し、修正後に再度concatを実行。
