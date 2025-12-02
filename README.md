# Gemini + Veo マルチセグメント動画ジェネレーター

Geminiテキストモデルのフレームプロンプト、Gemini 2.5 Flash Imageの絵コンテ（ストーリーボード）画像、Veo 3.1の短尺クリップ、`ffmpeg` の結合を組み合わせて、単一クリップより長い動画を生成するStreamlitアプリ兼Pythonパイプラインです。キャラクター・スタイル・カメラ・世界観の一貫性を重視し、オフライン安全なフェイククライアントも備えています。

## 特長
- タブ分割されたUIで「テーマと設定」→「絵コンテ確認・再生成」→「動画生成」の3ステップをガイド。
- 生成済みの絵コンテを確認し、プロンプトを編集した上で個別フレームを再生成可能。
- Veo 3.1のフレーム間補間で各セグメントを作り、`ffmpeg` concatデマルチプレクサで1本のMP4に結合。
- `ENABLE_REAL_GENAI=1` を明示した場合のみ実APIを使用。`USE_FAKE_GENAI=1` で完全オフラインのフェイク出力を強制でき、UIからも切り替え可能。

## インストールと前提条件
- Python 3.10+ 推奨。
- PATH に `ffmpeg` があること（実行環境でのクリップ結合に必要）。
- 依存関係: `pip install -r requirements.txt`

## APIモードと環境変数
- **REAL**: `ENABLE_REAL_GENAI=1` と `GEMINI_API_KEY`（または `GOOGLE_API_KEY`）を設定。オプションで Vertex AI 用に `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` を指定。
- **FAKE**: `USE_FAKE_GENAI=1` を設定すると `google-genai` 非依存のフェイククライアントで安全に動作。Streamlit UI ではチェックボックスで同じモードを選択できます。
- **DISABLED**: 上記いずれも未設定の場合、`get_genai_client()` は誤用防止のため例外を送出します。

## クイックスタート（Streamlit UI）
```bash
# リポジトリ直下で
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# オフラインデモの場合
export USE_FAKE_GENAI=1
# 実APIを使う場合は代わりに
# export ENABLE_REAL_GENAI=1
# export GEMINI_API_KEY=your_key_here

streamlit run app.py
```
UIのフロー:
1. 「テーマと設定」でテーマ、絵コンテ（フレーム）数（最小2）、動きのヒント、参考画像（任意）を入力して絵コンテを生成。
2. 「絵コンテ確認・再生成」で生成結果を確認し、プロンプトを編集して選択したフレームだけ再生成。
3. 「動画生成」でレビュー済みフレームからセグメントを作成し、連結済みMP4を再生・ダウンロードします。出力は `outputs/run_<timestamp>/` 配下に保存されます。

## パイプラインのコード利用例
`USE_FAKE_GENAI=1` または `ENABLE_REAL_GENAI=1` を設定した上で、Python から直接呼び出せます。
```python
from video_pipeline.run_pipeline import run_pipeline

final_path = run_pipeline(
    theme="夜のネオン屋上を歩く光る妖精",
    num_frames=3,
    ref_image_path=None,           # または PNG/JPEG への Path
    motion_hint="前方へゆっくり進む動き",
)
print("Video at:", final_path)
```
絵コンテだけを再生成したい場合は `video_pipeline.images.regenerate_storyboard_images` を直接使えます。

## 出力とファイル構成
- `app.py` — Streamlit UI のエントリポイント（フェイクモード切替、3ステップ構成、再生成UI）。
- `video_pipeline/`
  - `config.py` — パイプライン設定、APIモード判定、実行ディレクトリ作成。
  - `prompts.py` — フレームプロンプト生成（参照画像・モーションヒント対応）。
  - `images.py` — 参照画像と累積生成画像をギャラリーとして連鎖させる絵コンテ生成・再生成。
  - `videos.py` — フレーム間のVeo 3.1セグメント生成と最終フレーム抽出。
  - `ffmpeg_utils.py` — `ffmpeg` によるクリップ連結と終端フレーム抽出ヘルパー。
  - `run_pipeline.py` — プロンプト→フレーム→セグメント→最終MP4のオーケストレーション。
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
