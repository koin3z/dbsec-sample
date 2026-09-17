# Oracle Deep Data Security デモ

Oracle Database の Deep Data Security を、Python / marimo / python-oracledb から確認するためのデモです。Phase 1 ではローカルのエンドユーザーへ直接ログオンして、同じ SELECT が Data Grant によって異なる結果になることを見せます。Phase 2 では Identity Domain / OAuth client credentials と Oracle Deep Data Security の application-mediated 構成を扱います。Phase 2 の SQL は DB 側の application identity、Data Role、Data Grant を設定し、Python 側は公式 DDS provider が有効になるまで fail-closed にします。

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
- Phase 2 の application-mediated 方式は `notebooks/demo_app_mediated.py` と `sql/07` 以降に分離しています。Python 側で DDS を模倣せず、Identity Domain 連携と Data Grant は DB 側で扱います。

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

Phase 2 は direct logon とは別の guarded design target です。Identity Domain の OAuth client credentials で database-access token を取得し、python-oracledb の公式 DDS API で end-user security context payload を attach します。DB 側では OAuth client ID を直接 Data Grant の grantee にせず、`APPLICATION IDENTITY -> DATA ROLE -> DATA GRANT` の順に権限を束ねます。

```bash
uv run marimo edit notebooks/demo_app_mediated.py
```

Phase 2 の `.env` で整理する値は次の通りです。client secret、access token、秘密鍵、wallet material は実値をコミットしません。

- Identity Domain: `IDENTITY_DOMAIN_URL`
- DB application registration: `IDENTITY_DOMAIN_DATABASE_APP_ID`、`IDENTITY_DOMAIN_DATABASE_AUDIENCE`、`IDENTITY_DOMAIN_DATABASE_SCOPE_NAME`、`IDENTITY_DOMAIN_DATABASE_SCOPE`、`IDENTITY_DOMAIN_DATABASE_CLIENT_ID`、`IDENTITY_DOMAIN_DATABASE_CLIENT_SECRET`
- Demo application registration: `DEMO_APP_ID`、`DEMO_APP_CLIENT_ID`、`DEMO_APP_CLIENT_SECRET`、`DEMO_APP_GRANT_TYPES=client_credentials`、`DEMO_APP_DATABASE_SCOPE`、必要なら `DEMO_APP_TOKEN_URL`
- DB-side DDS names: `PHASE2_APP_IDENTITY`、`PHASE2_APP_DIRECTORY_DATA_ROLE`、`PHASE2_APP_SENSITIVE_DATA_ROLE`
- Runtime: `APP_DB_AUTH_MODE=client_credentials`、`APP_DB_USERNAME=DEEPSEC_APP`、`APP_SECURITY_CONTEXT_MODE=identity_domain_client_credentials`、`APP_END_USER_CONTEXT_KEY`、`APP_DATA_ROLES`、`APP_CONTEXT_ATTRIBUTES_JSON`、`APP_TOKEN_REQUEST_TIMEOUT`
- Connectivity: `ORACLE_PROTOCOL=tcps`、wallet/config directory、service name、target DB が Oracle AI Database か Autonomous AI Database か
Phase 2 の `APP_DB_AUTH_MODE=client_credentials` と `APP_SECURITY_CONTEXT_MODE=identity_domain_client_credentials` は TCPS 前提です。`ORACLE_PROTOCOL=tcp` のままだと、python-oracledb が `DPY-3001: bequeath is only supported in python-oracledb thick mode` のような紛らわしいエラーを返すことがあります。TCPS 用の port、wallet/config directory、証明書設定を対象 DB に合わせてください。

`APP_DB_AUTH_MODE=client_credentials` は、`DEMO_APP_*` から取得した token を `oracledb.connect(access_token=...)` に渡します。対象 DB 側では、その OAuth client が共有 DB ユーザー `DEEPSEC_APP` に解決される global user mapping が必要です。`APP_SECURITY_CONTEXT_MODE=identity_domain_client_credentials` は、同じ Identity Domain token を `create_end_user_security_context()` の `database_access_token` に渡し、`APP_END_USER_CONTEXT_KEY` と選択ペルソナで local end-user identity tuple を作ります。

Phase 2 SQL は Phase 1 の direct-logon SQL とは別に実行します。Identity Domain の有効化は対象 DB 種別でファイルが異なるため、どちらか一方だけを選びます。

```bash
# Oracle AI Database の場合
uv run python scripts/run_sql.py --file sql/07_configure_identity_domain.sql --dry-run
uv run python scripts/run_sql.py --file sql/07_configure_identity_domain.sql

# Autonomous AI Database の場合
uv run python scripts/run_sql.py --file sql/07_configure_identity_domain_autonomous.sql --dry-run
uv run python scripts/run_sql.py --file sql/07_configure_identity_domain_autonomous.sql
```

続いて、application identity と Phase 2 用 Data Role / Data Grant を作成します。

```bash
uv run python scripts/run_sql.py --file sql/08_create_application_identity.sql
uv run python scripts/run_sql.py --file sql/09_create_phase2_data_roles.sql
uv run python scripts/run_sql.py --file sql/10_create_phase2_data_grants.sql
uv run python scripts/run_sql.py --file sql/11_validate_phase2.sql
```

`sql/11_validate_phase2.sql` は、DDS 関連 dictionary view の列名が Oracle 26ai のビルドやパッチで変わっても確認できるよう、まず `ALL_TAB_COLUMNS` で列一覧を表示し、その後 `SELECT *` で metadata を表示します。

`sql/10_create_phase2_data_grants.sql` は、アクティブ従業員の directory lookup を application-scoped role に許可し、機微列の lookup は `ORA_END_USER_CONTEXT.username` が検証されたときだけ自分の行に一致するようにしています。Python 側で行フィルタや列マスクは実装しません。通常の `GRANT SELECT ON DEMO_HR.EMPLOYEES` も付与しません。

`sql/07_create_shared_app_user.sql` は、DB logon token 用の global user mapping を DB 側で作る optional file です。`APP_IAM_MAPPING` はこの SQL の `IDENTIFIED GLOBALLY AS ...` に埋め込む descriptor で、Data Grant や application identity の grantee には使いません。対象環境ですでに `DEEPSEC_APP` の mapping がある場合、この SQL は不要です。

```bash
uv run python scripts/phase2_status.py
```

この確認は設定済みの DB auth mode で共有 DB ユーザーに接続し、`SESSION_USER`、`CURRENT_USER`、`ORA_END_USER_CONTEXT.username` の状態を表示します。provider が未検証の場合、protected query は実行されません。notebook の protected query は `ORA_END_USER_CONTEXT.username` が選択ペルソナと一致することを確認してから実行し、`finally` で context を clear します。

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
