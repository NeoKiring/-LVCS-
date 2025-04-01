import os
import sys
import argparse
from pathlib import Path
from repository import Repository

class CLI:
    """バージョン管理システムのコマンドラインインターフェース"""
    
    def __init__(self):
        """CLIを初期化"""
        self.parser = self._create_parser()
        self.repo = None
    
    def _create_parser(self):
        """コマンドラインパーサーを作成"""
        parser = argparse.ArgumentParser(
            description='ローカルバージョン管理システム（LVCS）',
            prog='lvcs'
        )
        
        subparsers = parser.add_subparsers(dest='command', help='使用可能なコマンド')
        
        # 初期化コマンド
        init_parser = subparsers.add_parser('init', help='新しいリポジトリを初期化')
        
        # 設定コマンド
        config_parser = subparsers.add_parser('config', help='リポジトリの設定を変更')
        config_parser.add_argument('--name', help='ユーザー名を設定')
        config_parser.add_argument('--email', help='メールアドレスを設定')
        config_parser.add_argument('--list', action='store_true', help='現在の設定を表示')
        
        # 追加コマンド
        add_parser = subparsers.add_parser('add', help='ファイルをステージングエリアに追加')
        add_parser.add_argument('path', help='追加するファイルまたはディレクトリのパス')
        
        # コミットコマンド
        commit_parser = subparsers.add_parser('commit', help='ステージングされた変更をコミット')
        commit_parser.add_argument('-m', '--message', required=True, help='コミットメッセージ')
        
        # ステータスコマンド
        status_parser = subparsers.add_parser('status', help='リポジトリの状態を表示')
        
        # ログコマンド
        log_parser = subparsers.add_parser('log', help='コミット履歴を表示')
        log_parser.add_argument('-n', '--count', type=int, default=10, help='表示するコミット数')
        
        # 差分コマンド
        diff_parser = subparsers.add_parser('diff', help='変更の差分を表示')
        diff_parser.add_argument('path', nargs='?', help='差分を表示するファイルのパス（指定しない場合はすべての変更）')
        
        # ブランチコマンド
        branch_parser = subparsers.add_parser('branch', help='ブランチを作成、削除、または一覧表示')
        branch_parser.add_argument('name', nargs='?', help='作成または削除するブランチ名')
        branch_parser.add_argument('-d', '--delete', action='store_true', help='指定されたブランチを削除')
        
        # チェックアウトコマンド
        checkout_parser = subparsers.add_parser('checkout', help='ブランチをチェックアウト')
        checkout_parser.add_argument('branch', help='チェックアウトするブランチ名')
        
        # リセットコマンド
        reset_parser = subparsers.add_parser('reset', help='ファイルをリセットまたはインデックスをクリア')
        reset_parser.add_argument('path', nargs='?', help='リセットするファイルのパス（指定しない場合はすべての変更）')
        reset_parser.add_argument('--hard', action='store_true', help='ハードリセットを実行（ファイルも変更）')
        
        # マージコマンド
        merge_parser = subparsers.add_parser('merge', help='指定したブランチを現在のブランチにマージ')
        merge_parser.add_argument('branch', help='マージするブランチ名')
        
        return parser
    
    def _find_repo_root(self):
        """カレントディレクトリから上位に向かってリポジトリのルートを探す"""
        current_path = Path(os.getcwd())
        
        while current_path != current_path.parent:
            if (current_path / '.lvcs').exists():
                return current_path
            current_path = current_path.parent
            
        return None
    
    def _print_success(self, message):
        """成功メッセージを表示"""
        print(f"\033[92m{message}\033[0m")
    
    def _print_error(self, message):
        """エラーメッセージを表示"""
        print(f"\033[91mエラー: {message}\033[0m")
    
    def _print_info(self, message):
        """情報メッセージを表示"""
        print(f"\033[94m{message}\033[0m")
    
    def _print_warning(self, message):
        """警告メッセージを表示"""
        print(f"\033[93m{message}\033[0m")
    
    def run(self, args=None):
        """CLIを実行"""
        args = self.parser.parse_args(args)
        
        if args.command == 'init':
            # カレントディレクトリで新しいリポジトリを初期化
            self.repo = Repository(os.getcwd())
            success, message = self.repo.init()
            
            if success:
                self._print_success(message)
            else:
                self._print_error(message)
            
            return
        
        # それ以外のコマンドではリポジトリのルートを探す
        repo_root = self._find_repo_root()
        if not repo_root:
            self._print_error("LVCSリポジトリが見つかりません。'lvcs init'を実行して新しいリポジトリを作成してください。")
            sys.exit(1)
            
        self.repo = Repository(repo_root)
        
        # コマンドを実行
        if args.command == 'config':
            self._handle_config(args)
        elif args.command == 'add':
            self._handle_add(args)
        elif args.command == 'commit':
            self._handle_commit(args)
        elif args.command == 'status':
            self._handle_status(args)
        elif args.command == 'log':
            self._handle_log(args)
        elif args.command == 'diff':
            self._handle_diff(args)
        elif args.command == 'branch':
            self._handle_branch(args)
        elif args.command == 'checkout':
            self._handle_checkout(args)
        elif args.command == 'reset':
            self._handle_reset(args)
        elif args.command == 'merge':
            self._handle_merge(args)
        else:
            self.parser.print_help()
    
    def _handle_config(self, args):
        """コンフィグコマンドを処理"""
        config = self.repo.get_config()
        
        if args.list:
            name = config.get('user', {}).get('name', '未設定')
            email = config.get('user', {}).get('email', '未設定')
            
            print("現在の設定:")
            print(f"  user.name: {name}")
            print(f"  user.email: {email}")
            return
        
        if args.name or args.email:
            if 'user' not in config:
                config['user'] = {}
                
            if args.name:
                config['user']['name'] = args.name
                self._print_success(f"user.name を {args.name} に設定しました")
                
            if args.email:
                config['user']['email'] = args.email
                self._print_success(f"user.email を {args.email} に設定しました")
                
            self.repo.set_config(config)
        else:
            self._print_warning("変更する設定項目を指定してください（例: --name 'ユーザー名' --email 'メール'）")
    
    def _handle_add(self, args):
        """追加コマンドを処理"""
        success, message = self.repo.add(args.path)
        
        if success:
            self._print_success(message)
        else:
            self._print_error(message)
    
    def _handle_commit(self, args):
        """コミットコマンドを処理"""
        success, message = self.repo.commit(args.message)
        
        if success:
            self._print_success(message)
        else:
            self._print_error(message)
    
    def _handle_status(self, args):
        """ステータスコマンドを処理"""
        success, status_info = self.repo.status()
        
        if not success:
            self._print_error("リポジトリの状態を取得できませんでした")
            return
        
        branch = status_info['branch'] if status_info['branch'] else '（デタッチドHEAD）'
        print(f"ブランチ: {branch}")
        print()
        
        if status_info['staged_changes']:
            print("コミット予定の変更:")
            for item in status_info['staged_changes']:
                print(f"  {item}")
            print()
        
        if status_info['unstaged_changes']:
            print("未ステージングの変更:")
            for item in status_info['unstaged_changes']:
                print(f"  {item}")
            print()
        
        if status_info['untracked_files']:
            print("未追跡のファイル:")
            for item in status_info['untracked_files']:
                print(f"  {item}")
            print()
            
        if not (status_info['staged_changes'] or status_info['unstaged_changes'] or status_info['untracked_files']):
            print("ワーキングディレクトリはクリーンです")
    
    def _handle_log(self, args):
        """ログコマンドを処理"""
        success, log_entries = self.repo.log(args.count)
        
        if not success:
            self._print_error("コミット履歴を取得できませんでした")
            return
        
        for entry in log_entries:
            print(f"\033[93mコミット: {entry['hash']}\033[0m")
            print(f"作者: {entry['author']}")
            print(f"日付: {entry['date']}")
            print()
            print(f"    {entry['message']}")
            print()
            print("=" * 50)
    
    def _handle_diff(self, args):
        """差分コマンドを処理"""
        success, diff_output = self.repo.diff(args.path)
        
        if not success:
            self._print_error("差分を取得できませんでした")
            return
        
        for line in diff_output:
            if line.startswith('+'):
                print(f"\033[92m{line}\033[0m")
            elif line.startswith('-'):
                print(f"\033[91m{line}\033[0m")
            elif line.startswith('@@'):
                print(f"\033[96m{line}\033[0m")
            elif line.startswith('---') or line.startswith('+++'):
                print(f"\033[94m{line}\033[0m")
            else:
                print(line)
    
    def _handle_branch(self, args):
        """ブランチコマンドを処理"""
        if args.name:
            success, message = self.repo.branch(args.name, args.delete)
            
            if success:
                self._print_success(message)
            else:
                self._print_error(message)
        else:
            success, branch_info = self.repo.branch()
            
            if not success:
                self._print_error("ブランチ情報を取得できませんでした")
                return
            
            for branch in branch_info['branches']:
                if branch == branch_info['current']:
                    print(f"* \033[92m{branch}\033[0m")
                else:
                    print(f"  {branch}")
    
    def _handle_checkout(self, args):
        """チェックアウトコマンドを処理"""
        success, message = self.repo.checkout(args.branch)
        
        if success:
            self._print_success(message)
        else:
            self._print_error(message)
    
    def _handle_reset(self, args):
        """リセットコマンドを処理"""
        success, message = self.repo.reset(args.path, args.hard)
        
        if success:
            self._print_success(message)
        else:
            self._print_error(message)
    
    def _handle_merge(self, args):
        """マージコマンドを処理"""
        success, message = self.repo.merge(args.branch)
        
        if success:
            self._print_success(message)
        else:
            self._print_error(message)


def main():
    """メイン関数"""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
