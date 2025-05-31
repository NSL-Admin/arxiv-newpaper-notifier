# arxiv-newpaper-notifier: Slack Bot that sends notification of the latest papers published on arXiv.

## 概要

arXiv上にアップロードされた新着論文を取得し、LLMによってその要点をまとめた上でSlackに送るツールです。
arXivから特定カテゴリの論文を取得して要約を生成するスクリプトと、そのデータをSlackに送信するスクリプトを別々に用意しています。

## セットアップ

1. [uv](https://docs.astral.sh/uv/getting-started/installation/) (Pythonのパッケージマネージャ) をインストールしてください。
2. [Ollama](https://ollama.com/) (LLM Runner) をインストールしてください。Ollamaをインストールするホストが本ツールを実行するホストと異なる場合、それらのホストは同一ネットワーク内に存在する必要があります。
3. `ollama pull qwen3:8b` と `ollama pull gemma3:4b` を実行し、論文を要約するためのLLMとそれをJSONにフォーマットするためのLLMをそれぞれダウンロードしてください。
4. .env.template のファイル名を .env に変更し、`SLACK_API_TOKEN=` の後ろに **chat:write** と **files:write** のOAuthスコープを持ったBot User OAuth Tokenを書き込んでください。

## 使い方

1. fetch_paper_info.py を使ってarXivから論文情報を取得します。[ ]で囲まれた引数は省略可能です。特に `--date` を省略した場合、一昨日の1日の間に公開された論文を取得します。（投稿された論文の情報がAPIに反映されるまで少々時間がかかるためデフォルト値が一昨日になっています）

    ```bash
    uv run fetch_paper_info.py \
        --category 新着論文を探すカテゴリ \
        [--date 論文の出版日(UTC) (YYYY-mm-dd 形式)] \
        [--data-dir データ保存用ディレクトリへのパス] \
        [--max-papers 取得する論文の最大数] \
        [--ollama-api-base-url OLLAMAが動作しているホストへのURL (Default: http://127.0.0.1:11434)] \
        [--summarizer-as-agent 論文要約用LLMをWeb検索ツールを備えたAgentとして動作させる] \
        [--verbose]
    ```

2. send_to_slack.py を使って取得した論文情報をSlackに送信します。[ ]で囲まれた引数は省略可能です。

    ```bash
    uv run send_to_slack.py \
        --category Slackに送信する論文情報のカテゴリ \
        --channel-id 論文情報を送る先のチャンネルID \
        [--data-dir データ保存用ディレクトリへのパス] \
        [--verbose]
    ```

    > [!WARNING]
    > `--channel-id` に指定したチャンネルの中に、このツールに設定したBotトークンに対応するアプリケーションが存在する必要があります。

## Tips

- それぞれのスクリプトに `--help` をつけて実行するとデフォルト値を確認することができます。
- 論文要約用のLLMのモデル名は `--summarizer-llm-name` で、要約をJSON形式にフォーマットするLLMは `--formatter-llm-name` で指定することができます。
- `--summarizer-as-agent` を使用する場合、 `--summarizer-llm-name` で指定されたLLMは[Tool Useに対応したモデル](https://ollama.com/search?c=tools)である必要があります。
- 別のホストで動作しているOllamaを使用する場合、当該ホストの `OLLMA_HOST` 環境変数を適切に設定する必要があります。
- このスクリプトを毎日実行する場合、arXivの[Announcement Schedule](https://info.arxiv.org/help/availability.html)により新着論文が1件も取得されない日があります。