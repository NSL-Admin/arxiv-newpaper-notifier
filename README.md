# arxiv-newpaper-notifier: Slack Bot that sends notification of the latest papers published on arXiv.

## 概要

arXiv上にアップロードされた新着論文を取得し、LLMによってその要点をまとめた上でSlackに送るツールです。
arXivから特定カテゴリの論文を取得するスクリプトと、そのデータをSlackに送信するスクリプトを別々に用意しています。

## セットアップ

1. requirements.txt に列挙されたパッケージを全てインストールしてください。

> [!IMPORTANT]
> GPUを使用してLLMを高速化したい場合、 `llama-cpp-python` のGPU対応バイナリを以下のコマンドによってインストールしてください。ご使用中の環境のCUDAのバージョンに応じて `cu121` の部分を変更してください。使用しているCUDAのバージョンが古いなどの原因で既存のバイナリが存在しない場合、[公式ドキュメント](https://github.com/abetlen/llama-cpp-python?tab=readme-ov-file#installation-configuration)に従ってビルドしてください。
> ```bash
> pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121 --upgrade --force-reinstall --no-cache-dir
> ```

2. .env.template のファイル名を .env に変更し、`SLACK_API_TOKEN=` の後ろに **chat:write** と **files:write** のOAuthスコープを持ったBot User OAuth Tokenを書き込んでください。

## 使い方

1. fetch_paper_info.py を使ってarXivから論文情報を取得します。[]で囲まれた引数は省略可能です。特に `--date` を省略した場合、一昨日の1日の間に公開された論文を取得します。（投稿された論文の情報がAPIに反映されるまで少々時間がかかるためデフォルト値が一昨日になっています）

```bash
python fetch_paper_info.py --category 新着論文を探すカテゴリ [--date 論文の出版日(UTC) (YYYY-mm-dd 形式)] [--data-dir データ保存用ディレクトリへのパス] [--max-papers 取得する論文の最大数] [--gpu-index 使用したいGPUのインデックス (0-indexed)] [--verbose]
```

2. send_to_slack.py を使って取得した論文情報をSlackに送信します。[]で囲まれた引数は省略可能です。

> [!WARNING]
> --channel-id に指定したチャンネルの中に、このツールに設定したBotトークンに対応するアプリケーションが存在する必要があります。

```bash
python send_to_slack.py --category Slackに送信する論文情報のカテゴリ --channel-id 論文情報を送る先のチャンネルID [--data-dir データ保存用ディレクトリへのパス] [--verbose]
```

## Tips

- このスクリプトを毎日実行する場合、arXivの[Announcement Schedule](https://info.arxiv.org/help/availability.html)により新着論文が1件も取得されない日があります。