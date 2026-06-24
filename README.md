# Oracle Deep Data Security デモ

Oracle Database の Deep Data Security を、Python / marimo / python-oracledb から確認するためのデモです。Phase 1 ではローカルのエンドユーザーへ直接ログオンして、同じ SELECT が Data Grant によって異なる結果になることを見せます。Phase 2 では共有アプリケーション DB ユーザーで接続し、選択したエンドユーザーの security context を問い合わせ前に付与して、実行後に必ず解除する流れを別 notebook で示します。

```text
marimo UI
  -> 選択したペルソナで direct logon
  -> Oracle Database
  -> Deep Data Security Data Grant が行・列・セルを制御
  -> pandas / marimo で結果を表示
```

## Phase 1 の範囲

- 対象ペルソナは `staff_tokyo`、`manager_tokyo`、`manager_japan`、`ai_assistant` です。
- Python 側では Deep Data Security の挙動を再現しません。
- 行・列・セルの制御は DB 側の Data Grant が強制する前提です。
- Phase 2 の application-mediated 方式は `notebooks/demo_app_mediated.py` に分離しています。OAuth、外部 IAM、AI エージェント本体は実装対象外です。

## 前提

- uv
- Python 3.13
- Oracle Database
- Deep Data Security を利用できる権限
- Oracle Database へ接続できるネットワーク


## クイックスタート

Phase 1 direct logon デモの最短手順です。`.env` の値は環境に合わせて編集してください。コマンドはリポジトリ直下 `/home/ubuntu/workspaces/dbsec-samples` で実行します。

```bash
uv sync
cp .env.example .env
# .env を編集して Oracle 接続先、管理ユーザー、デモ用パスワードを設定
uv run python scripts/run_sql.py --file sql/00_reset.sql
uv run python scripts/run_sql.py --file sql/01_create_schema.sql
uv run python scripts/run_sql.py --file sql/02_create_sample_data.sql
uv run python scripts/run_sql.py --file sql/03_create_end_users.sql
uv run python scripts/run_sql.py --file sql/04_create_data_roles.sql
uv run python scripts/run_sql.py --file sql/05_create_data_grants.sql
uv run python scripts/run_sql.py --file sql/06_validate.sql
uv run pytest
uv run marimo edit notebooks/demo_direct_logon.py
```

DB 上の挙動確認をまとめて行う場合は、SQL セットアップ後に次を実行します。

```bash
uv run python scripts/smoke_test.py --all-personas --sql canonical
```

## セットアップ

```bash
uv sync
cp .env.example .env
```

`.env` の接続先、管理ユーザー、デモ用パスワードを環境に合わせて変更してください。`.env.example` の `change_me` はローカルデモ用のプレースホルダーです。共有環境や永続環境ではそのまま使わないでください。

接続先が Native Network Encryption または Data Integrity を要求して `DPY-3001` が出る場合は、python-oracledb を Thick mode で使います。Oracle Instant Client などの Oracle Client libraries をインストールし、Linux では `ldconfig` または `LD_LIBRARY_PATH` でライブラリ検索パスを設定したうえで、`.env` を次のように変更してください。

```bash
ORACLE_DRIVER_MODE=thick
# Linux では通常、lib_dir を指定せず OS のライブラリ検索パスを使います。
ORACLE_CLIENT_LIB_DIR=
# tnsnames.ora / sqlnet.ora / wallet などを置く場合だけ指定します。
ORACLE_CLIENT_CONFIG_DIR=
```

Windows / macOS では `ORACLE_CLIENT_LIB_DIR` に Instant Client のディレクトリを指定できます。Thick mode はプロセス内で最初の接続前に初期化する必要があるため、設定変更後は marimo や SQL 実行コマンドを再起動してください。

## SQL 実行順

DB で実行する内容は `sql/` 配下に分割しています。Python から DB オブジェクトを暗黙に作成しません。

事前に、レンダリング後のステートメントを確認できます。パスワードは表示時に伏せます。

```bash
uv run python scripts/run_sql.py --file sql/01_create_schema.sql --dry-run
uv run python scripts/run_sql.py --file sql/02_create_sample_data.sql --dry-run
uv run python scripts/run_sql.py --file sql/03_create_end_users.sql --dry-run
```

実行順は次の通りです。

```bash
uv run python scripts/run_sql.py --file sql/00_reset.sql
uv run python scripts/run_sql.py --file sql/01_create_schema.sql
uv run python scripts/run_sql.py --file sql/02_create_sample_data.sql
uv run python scripts/run_sql.py --file sql/03_create_end_users.sql
uv run python scripts/run_sql.py --file sql/04_create_data_roles.sql
uv run python scripts/run_sql.py --file sql/05_create_data_grants.sql
uv run python scripts/run_sql.py --file sql/06_validate.sql
```

`00_reset.sql` は `DEMO_HR`、quoted lowercase ローカル・エンドユーザー、Data Role、`deepsec_demo_session_role` を DROP する破壊的スクリプトです。初期版で作成した uppercase DB ユーザーも cleanup 対象に含めています。共有 DB では対象が本当にデモ用であることを確認してから実行してください。

`04_create_data_roles.sql` と `05_create_data_grants.sql` は Oracle Deep Data Security Guide 26ai の公開構文に照らして確認済みの実行 SQL です。`CREATE DATA ROLE`、`GRANT DATA ROLE`、`CREATE DATA GRANT` を使用します。direct logon 方式では、quoted lowercase のローカル・エンドユーザー（例: `"staff_tokyo"`）を作成し、`CREATE SESSION` を持つ通常の DB ロール `deepsec_demo_session_role` を Data Role に付与します。通常の `GRANT SELECT ON DEMO_HR.EMPLOYEES` はこのデモでは付与しません。行・列・セルの制御は DB 側の Deep Data Security Data Grant で強制します。

既に古い版の `00` から `03` までを実行済みの場合は、更新後の `00_reset.sql` から順に再実行してください。古い uppercase DB ユーザーと、新しい quoted lowercase ローカル・エンドユーザーの両方を reset 対象にしています。

## marimo の起動

```bash
uv run marimo edit notebooks/demo_direct_logon.py
```

このコマンドはリポジトリ直下で実行してください。notebook にはローカルパッケージ `deepsec_demo` を解決するための repo root bootstrap を入れています。

UI でペルソナを選び、同じ canonical SELECT を実行します。期待される差分は次の通りです。

- `staff_tokyo`: quoted lowercase ローカル・エンドユーザー `"staff_tokyo"` として接続し、自分の employee_id `1001` のみを表示。
- `manager_tokyo`: 自分の行と直属部下を表示し、直属部下の `personal_id` は NULL。
- `manager_japan`: 日本の Sales スコープを広く表示し、Data Grant 外の機微列は NULL。
- `ai_assistant`: アクティブ従業員のディレクトリ相当列のみを表示。


## Phase 2: application-mediated デモ

Phase 2 は direct logon とは別の notebook です。共有アプリケーション DB ユーザーで Oracle Database に接続し、問い合わせ直前に選択したローカル・エンドユーザーの security context を付与し、`finally` で必ず `clear_end_user_security_context()` を呼びます。接続を再利用する構成で前のユーザーの context を残さないことが主眼です。

```bash
uv run marimo edit notebooks/demo_app_mediated.py
```

Phase 2 を実行する前提は次の通りです。

- Phase 1 の `00_reset.sql` から `06_validate.sql` までが成功していること。
- `.env` に `APP_DB_USERNAME`、`APP_DB_PASSWORD`、`APP_SECURITY_CONTEXT_MODE=local` を設定すること。
- `APP_DATABASE_ACCESS_TOKEN` と `APP_END_USER_CONTEXT_KEY` は対象環境の Oracle Deep Data Security / security context provider の公式手順で取得した値を設定すること。このリポジトリでは実在しない token や IAM 登録手順を生成しません。
- この notebook が使う python-oracledb の end-user security context payload API は Thin mode を前提にしています。`ORACLE_DRIVER_MODE=thin` で実行してください。接続先が Native Network Encryption などにより Thick mode を必須にする場合は、Phase 2 用に Thin mode で接続できるサービスまたは Oracle 公式手順に沿った別構成が必要です。

共有アプリ DB ユーザー作成や追加権限は、対象 Oracle Database の Deep Data Security / IAM 構成に依存します。実行が必要な DDL は、公式手順に基づく SQL ファイルとして追加してから `scripts/run_sql.py` で実行してください。このデモでは Phase 1 と同じく、アプリ側で行・列・セルをフィルタせず、通常の `GRANT SELECT ON DEMO_HR.EMPLOYEES` で制御を迂回する構成も追加しません。

## 検証

非 DB テスト:

```bash
uv run pytest
```

DB 接続を含むスモークテスト:

```bash
uv run python scripts/smoke_test.py --all-personas --sql canonical
```

スモークテストは選択したペルソナで direct logon し、canonical SELECT の行数、employee_id、機微列の NULL 状態を確認します。対象 Oracle バージョンで未許可列が NULL ではなく列自体を返さない場合は、警告として表示します。

## トラブルシューティング

- marimo 起動時に `deepsec-demo` が missing package と表示される場合は、リポジトリ直下で実行していることを確認してください。まだ解決しない場合は `PYTHONPATH=. uv run marimo edit notebooks/demo_direct_logon.py` で起動してください。
- `DPY-3001` が出る場合は、接続先が Native Network Encryption / Data Integrity を要求しています。`ORACLE_DRIVER_MODE=thick` を設定し、Oracle Client libraries を利用できる状態にしてください。
- `DPI-1047` が出る場合は、Thick mode 用の Oracle Client libraries を読み込めていません。Instant Client のインストール、`LD_LIBRARY_PATH` / `ldconfig`、`ORACLE_CLIENT_LIB_DIR` を確認してください。
- `DPI-` または `ORA-` で接続に失敗する場合は、`.env` の `ORACLE_HOST`、`ORACLE_PORT`、`ORACLE_SERVICE_NAME`、ウォレット設定を確認してください。
- ペルソナで接続できない場合は、`sql/03_create_end_users.sql` が実行済みか確認してください。
- 全ペルソナで同じ結果が出る場合は、Data Grant が作成されているか、対象ユーザーへ Data Role が付与されているか確認してください。
- Python 側のテストが成功しても、Deep Data Security の有効性は証明されません。必ず Oracle Database 上でスモークテストまたは手動 SELECT を確認してください。

## 注意

このリポジトリのサンプル認証情報、サンプル PII、電話番号はデモ専用の合成値です。実在人物、実在識別子、実パスワードをコミットしないでください。
