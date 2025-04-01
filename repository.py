import os
import hashlib
import json
import time
import shutil
import difflib
import zlib
from pathlib import Path
from datetime import datetime

class Repository:
    """バージョン管理操作を処理するメインリポジトリクラス"""
    
    def __init__(self, repo_path):
        """リポジトリを初期化する"""
        self.repo_path = Path(repo_path)
        self.vcs_dir = self.repo_path / '.lvcs'
        self.objects_dir = self.vcs_dir / 'objects'
        self.refs_dir = self.vcs_dir / 'refs'
        self.branches_dir = self.refs_dir / 'heads'
        self.head_file = self.vcs_dir / 'HEAD'
        self.index_file = self.vcs_dir / 'index'
        self.config_file = self.vcs_dir / 'config'
        
    def init(self):
        """新しいリポジトリを初期化する"""
        if self.vcs_dir.exists():
            return False, "リポジトリはすでに初期化されています"
        
        # ディレクトリ構造を作成
        self.vcs_dir.mkdir()
        self.objects_dir.mkdir()
        self.refs_dir.mkdir()
        self.branches_dir.mkdir()
        
        # masterブランチを指すデフォルトのHEADを作成
        with open(self.head_file, 'w') as f:
            f.write("ref: refs/heads/master")
        
        # 空のインデックスを作成
        with open(self.index_file, 'w') as f:
            json.dump({}, f)
        
        # デフォルト設定を作成
        with open(self.config_file, 'w') as f:
            config = {
                "core": {
                    "repositoryformatversion": 0,
                    "filemode": False,
                    "bare": False
                },
                "user": {
                    "name": "",
                    "email": ""
                }
            }
            json.dump(config, f, indent=4)
        
        return True, "空のリポジトリを初期化しました"
    
    def get_config(self):
        """リポジトリの設定を読み込む"""
        if not self.config_file.exists():
            return {}
        
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    def set_config(self, config):
        """リポジトリの設定を更新する"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
    
    def hash_object(self, data, obj_type='blob'):
        """データをリポジトリに保存し、そのハッシュを返す"""
        header = f"{obj_type} {len(data)}\0"
        full_data = header.encode() + data
        
        # SHA-1ハッシュを計算
        sha1 = hashlib.sha1(full_data).hexdigest()
        
        # オブジェクトを圧縮して保存
        compressed_data = zlib.compress(full_data)
        object_path = self.objects_dir / sha1[:2] / sha1[2:]
        
        if not object_path.parent.exists():
            object_path.parent.mkdir()
        
        with open(object_path, 'wb') as f:
            f.write(compressed_data)
        
        return sha1
    
    def get_object(self, sha1, expected_type=None):
        """リポジトリからオブジェクトを取得して解凍する"""
        object_path = self.objects_dir / sha1[:2] / sha1[2:]
        
        if not object_path.exists():
            return None, None
        
        with open(object_path, 'rb') as f:
            compressed_data = f.read()
        
        # データを解凍
        data = zlib.decompress(compressed_data)
        
        # ヘッダーを解析
        null_index = data.find(b'\0')
        header = data[:null_index].decode()
        obj_type, size = header.split()
        
        # 期待されるタイプが提供されている場合はチェック
        if expected_type and obj_type != expected_type:
            raise ValueError(f"期待される型は {expected_type} ですが、{obj_type} が見つかりました")
        
        # 実際のデータを返す
        return obj_type, data[null_index+1:]
    
    def get_index(self):
        """インデックスファイルを読み込む"""
        if not self.index_file.exists():
            return {}
        
        with open(self.index_file, 'r') as f:
            return json.load(f)
    
    def update_index(self, index):
        """インデックスファイルを更新する"""
        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=4)
    
    def _get_file_hash(self, file_path):
        """ファイルのハッシュを計算する"""
        with open(file_path, 'rb') as f:
            data = f.read()
        return self.hash_object(data)
    
    def add(self, path_pattern):
        """ファイルをステージングエリアに追加する"""
        # レポジトリのルートを基準に相対パスを解決
        full_path = (self.repo_path / path_pattern).resolve()
        
        try:
            rel_path = full_path.relative_to(self.repo_path.resolve())
        except ValueError:
            return False, f"パス {path_pattern} はリポジトリ内にありません"
        
        # 現在のインデックスを取得
        index = self.get_index()
        
        # ディレクトリとファイルの処理を分ける
        if full_path.is_dir():
            # ディレクトリ内のすべてのファイルを追加
            added_files = []
            for file_path in full_path.glob('**/*'):
                if file_path.is_file() and '.lvcs' not in str(file_path):
                    try:
                        file_rel_path = str(file_path.relative_to(self.repo_path.resolve()))
                        file_hash = self._get_file_hash(file_path)
                        index[file_rel_path] = {
                            'hash': file_hash,
                            'timestamp': datetime.now().timestamp()
                        }
                        added_files.append(file_rel_path)
                    except Exception as e:
                        return False, f"ファイル {file_path} の追加中にエラーが発生しました: {str(e)}"
            
            self.update_index(index)
            return True, f"{len(added_files)} 個のファイルを追加しました"
        elif full_path.is_file():
            # 単一ファイルを追加
            file_rel_path = str(rel_path)
            try:
                file_hash = self._get_file_hash(full_path)
                
                index[file_rel_path] = {
                    'hash': file_hash,
                    'timestamp': datetime.now().timestamp()
                }
                
                self.update_index(index)
                return True, f"{file_rel_path} を追加しました"
            except Exception as e:
                return False, f"ファイル {full_path} の追加中にエラーが発生しました: {str(e)}"
        else:
            return False, f"パスが見つかりません: {path_pattern}"
    
    def create_tree(self):
        """現在のインデックスからツリーオブジェクトを作成する"""
        index = self.get_index()
        tree_entries = {}
        
        for path, info in index.items():
            parts = path.split('/')
            current = tree_entries
            
            # ツリー構造をナビゲート/作成する
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # ファイルエントリを追加
            current[parts[-1]] = info['hash']
        
        # ツリーをシリアル化して保存
        return self._store_tree(tree_entries)
    
    def _store_tree(self, tree_dict):
        """ツリー構造を再帰的に保存する"""
        tree_content = []
        
        for name, value in sorted(tree_dict.items()):
            if isinstance(value, dict):
                # これはディレクトリ/サブツリー
                mode = "40000"  # ディレクトリモード
                subtree_hash = self._store_tree(value)
                obj_type = "tree"
                tree_content.append(f"{mode} {obj_type} {subtree_hash}\t{name}")
            else:
                # これはファイル
                mode = "100644"  # 通常ファイルモード
                obj_type = "blob"
                tree_content.append(f"{mode} {obj_type} {value}\t{name}")
        
        # すべてのエントリを結合してツリーオブジェクトを作成
        tree_str = "\n".join(tree_content)
        return self.hash_object(tree_str.encode(), 'tree')
    
    def get_current_branch(self):
        """現在のブランチ名を取得する"""
        if not self.head_file.exists():
            return None
        
        with open(self.head_file, 'r') as f:
            head_content = f.read().strip()
        
        if head_content.startswith('ref: '):
            ref_path = head_content[5:]  # 'ref: ' プレフィックスをスキップ
            branch = ref_path.split('/')[-1]
            return branch
        else:
            # デタッチドHEAD状態
            return None
    
    def get_branch_commit(self, branch_name):
        """ブランチが指すコミットハッシュを取得する"""
        branch_file = self.branches_dir / branch_name
        
        if not branch_file.exists():
            return None
        
        with open(branch_file, 'r') as f:
            return f.read().strip()
    
    def commit(self, message):
        """新しいコミットオブジェクトを作成する"""
        # ステージングされた変更があるかチェック
        index = self.get_index()
        if not index:
            return False, "コミットするためのステージングされた変更はありません"
        
        # インデックスからツリーを作成
        tree_hash = self.create_tree()
        
        # 設定から作者情報を取得
        config = self.get_config()
        author_name = config.get('user', {}).get('name', '不明')
        author_email = config.get('user', {}).get('email', 'unknown@example.com')
        
        # 親コミットを取得
        parents = []
        branch = self.get_current_branch()
        if branch:
            parent_hash = self.get_branch_commit(branch)
            if parent_hash:
                parents.append(parent_hash)
        
        # コミットコンテンツを作成
        commit_items = [
            f"tree {tree_hash}",
        ]
        
        for parent in parents:
            commit_items.append(f"parent {parent}")
        
        timestamp = int(time.time())
        timezone = time.strftime("%z")
        
        commit_items.extend([
            f"author {author_name} <{author_email}> {timestamp} {timezone}",
            f"committer {author_name} <{author_email}> {timestamp} {timezone}",
            "",
            message
        ])
        
        commit_content = "\n".join(commit_items)
        
        # コミットをハッシュして保存
        commit_hash = self.hash_object(commit_content.encode(), 'commit')
        
        # ブランチ参照を更新
        if branch:
            branch_file = self.branches_dir / branch
            with open(branch_file, 'w') as f:
                f.write(commit_hash)
        else:
            # デタッチドHEAD状態 - HEADを直接更新
            with open(self.head_file, 'w') as f:
                f.write(commit_hash)
        
        return True, f"コミット {commit_hash[:8]} を作成しました"
    
    def log(self, count=10):
        """コミットログを表示する"""
        branch = self.get_current_branch()
        if not branch:
            with open(self.head_file, 'r') as f:
                current_commit = f.read().strip()
        else:
            current_commit = self.get_branch_commit(branch)
        
        if not current_commit:
            return False, "まだコミットがありません"
        
        log_entries = []
        commit_hash = current_commit
        
        while commit_hash and len(log_entries) < count:
            obj_type, commit_data = self.get_object(commit_hash, 'commit')
            if not commit_data:
                break
                
            commit_content = commit_data.decode()
            commit_lines = commit_content.split('\n')
            
            # コミットデータを解析
            commit_info = {
                'hash': commit_hash,
                'tree': None,
                'parents': [],
                'author': None,
                'committer': None,
                'message': []
            }
            
            message_start = False
            for line in commit_lines:
                if not line.strip() and not message_start:
                    message_start = True
                    continue
                
                if message_start:
                    commit_info['message'].append(line)
                elif line.startswith('tree '):
                    commit_info['tree'] = line[5:]
                elif line.startswith('parent '):
                    commit_info['parents'].append(line[7:])
                elif line.startswith('author '):
                    commit_info['author'] = line[7:]
                elif line.startswith('committer '):
                    commit_info['committer'] = line[10:]
            
            # ログエントリをフォーマット
            author_parts = commit_info['author'].split()
            author_name = ' '.join(author_parts[:-2])
            timestamp = int(author_parts[-2])
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            log_entry = {
                'hash': commit_hash,
                'author': author_name,
                'date': date_str,
                'message': '\n'.join(commit_info['message'])
            }
            
            log_entries.append(log_entry)
            
            # 親コミットに移動
            if commit_info['parents']:
                commit_hash = commit_info['parents'][0]
            else:
                break
        
        return True, log_entries
    
    def status(self):
        """リポジトリの状態を表示する"""
        status_info = {
            'branch': self.get_current_branch(),
            'staged_changes': [],
            'unstaged_changes': [],
            'untracked_files': []
        }
        
        # 現在のインデックスを取得
        index = self.get_index()
        
        # ワーキングディレクトリ内のすべてのファイルをチェック
        for file_path in self.repo_path.glob('**/*'):
            if file_path.is_file() and '.lvcs' not in str(file_path):
                try:
                    rel_path = str(file_path.relative_to(self.repo_path))
                    
                    if rel_path in index:
                        # ファイルが変更されたかチェック
                        current_hash = self._get_file_hash(file_path)
                        if current_hash != index[rel_path]['hash']:
                            status_info['unstaged_changes'].append(rel_path)
                    else:
                        # 未追跡ファイル
                        status_info['untracked_files'].append(rel_path)
                except Exception:
                    # 例外を無視して続行
                    continue
        
        # ステージングされた変更をチェック
        branch = self.get_current_branch()
        if branch:
            commit_hash = self.get_branch_commit(branch)
            if commit_hash:
                # 最後のコミットからツリーを取得
                obj_type, commit_data = self.get_object(commit_hash, 'commit')
                commit_lines = commit_data.decode().split('\n')
                tree_hash = None
                
                for line in commit_lines:
                    if line.startswith('tree '):
                        tree_hash = line[5:]
                        break
                
                if tree_hash:
                    # インデックスとコミットの内容を比較
                    staged_dict = {}
                    for path, info in index.items():
                        staged_dict[path] = info['hash']
                    
                    # 最後のコミットのファイルリストと比較
                    for file_path, file_hash in staged_dict.items():
                        # コミットされたバージョンのハッシュを取得するには、ツリーを再帰的に辿る必要があります
                        # 簡略化のため、ここではステージングされたファイルはすべて変更としてマークします
                        if file_path not in status_info['unstaged_changes']:
                            status_info['staged_changes'].append(file_path)
        
        return True, status_info
    
    def checkout(self, branch_name):
        """指定されたブランチにチェックアウトする"""
        # ブランチが存在するか確認
        branch_file = self.branches_dir / branch_name
        
        if not branch_file.exists():
            return False, f"ブランチ '{branch_name}' は存在しません"
        
        # ブランチが指すコミットを取得
        with open(branch_file, 'r') as f:
            commit_hash = f.read().strip()
        
        # HEADファイルを更新
        with open(self.head_file, 'w') as f:
            f.write(f"ref: refs/heads/{branch_name}")
        
        # ワーキングディレクトリを更新
        return self._update_working_directory(commit_hash)
    
    def _update_working_directory(self, commit_hash):
        """指定されたコミットでワーキングディレクトリを更新する"""
        # コミットからツリーハッシュを取得
        obj_type, commit_data = self.get_object(commit_hash, 'commit')
        commit_lines = commit_data.decode().split('\n')
        tree_hash = None
        
        for line in commit_lines:
            if line.startswith('tree '):
                tree_hash = line[5:]
                break
        
        if not tree_hash:
            return False, "コミットからツリーハッシュを取得できませんでした"
        
        # 現在のインデックスをバックアップ
        index_backup = self.get_index()
        
        try:
            # ファイルを取得して更新
            new_index = {}
            success, message = self._checkout_tree(tree_hash, self.repo_path, '', new_index)
            
            if not success:
                # 失敗した場合はバックアップを復元
                self.update_index(index_backup)
                return False, message
            
            # インデックスを更新
            self.update_index(new_index)
            return True, f"ブランチに正常にチェックアウトしました（コミット {commit_hash[:8]}）"
        except Exception as e:
            # エラーの場合はバックアップを復元
            self.update_index(index_backup)
            return False, f"チェックアウト中にエラーが発生しました: {str(e)}"
    
    def _checkout_tree(self, tree_hash, dir_path, prefix, index):
        """ツリーオブジェクトを再帰的に展開してワーキングディレクトリを更新する"""
        obj_type, tree_data = self.get_object(tree_hash, 'tree')
        tree_content = tree_data.decode()
        
        # 各ツリーエントリを処理
        for line in tree_content.split('\n'):
            if not line.strip():
                continue
            
            # 行を解析して、モード、型、ハッシュ、名前を取得
            parts = line.split('\t')
            if len(parts) != 2:
                continue
                
            mode_type_hash = parts[0].split()
            if len(mode_type_hash) != 3:
                continue
                
            mode, obj_type, obj_hash = mode_type_hash
            name = parts[1]
            
            # ファイルパスを構築
            file_path = dir_path / name
            rel_path = prefix + name if not prefix else prefix + '/' + name
            
            if obj_type == 'tree':
                # ディレクトリの場合は再帰的に処理
                file_path.mkdir(exist_ok=True)
                success, message = self._checkout_tree(obj_hash, file_path, rel_path, index)
                if not success:
                    return False, message
            elif obj_type == 'blob':
                # ファイルの場合はコンテンツを取得して書き込む
                _, blob_data = self.get_object(obj_hash, 'blob')
                
                # 親ディレクトリが存在することを確認
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'wb') as f:
                    f.write(blob_data)
                
                # インデックスを更新
                index[rel_path] = {
                    'hash': obj_hash,
                    'timestamp': datetime.now().timestamp()
                }
        
        return True, "成功"
    
    def branch(self, branch_name=None, delete=False):
        """新しいブランチを作成または既存のブランチを削除する"""
        if branch_name is None:
            # すべてのブランチを一覧表示
            branches = [path.name for path in self.branches_dir.glob('*')]
            current_branch = self.get_current_branch()
            
            return True, {
                'branches': branches,
                'current': current_branch
            }
        
        branch_file = self.branches_dir / branch_name
        
        if delete:
            # ブランチを削除
            if not branch_file.exists():
                return False, f"ブランチ '{branch_name}' は存在しません"
            
            # 現在のブランチは削除できない
            current_branch = self.get_current_branch()
            if current_branch == branch_name:
                return False, f"ブランチ '{branch_name}' はHEADが指しているため削除できません"
            
            branch_file.unlink()
            return True, f"ブランチ '{branch_name}' を削除しました"
        else:
            # ブランチを作成
            if branch_file.exists():
                return False, f"ブランチ '{branch_name}' はすでに存在します"
            
            # 現在のHEADコミットを取得
            current_branch = self.get_current_branch()
            if current_branch:
                current_commit = self.get_branch_commit(current_branch)
            else:
                with open(self.head_file, 'r') as f:
                    current_commit = f.read().strip()
            
            if not current_commit:
                return False, "ブランチを作成するためのコミットがありません"
            
            # 新しいブランチを作成
            with open(branch_file, 'w') as f:
                f.write(current_commit)
                
            return True, f"ブランチ '{branch_name}' を作成しました"
    
    def diff(self, path=None):
        """インデックスとワーキングディレクトリ間の差分を表示する"""
        index = self.get_index()
        diff_output = []
        
        if path:
            # 特定のファイルの差分
            full_path = (self.repo_path / path).resolve()
            try:
                rel_path = str(full_path.relative_to(self.repo_path.resolve()))
                
                if rel_path in index:
                    # インデックスからファイルのコンテンツを取得
                    obj_type, staged_data = self.get_object(index[rel_path]['hash'], 'blob')
                    staged_content = staged_data.decode('utf-8', errors='replace').splitlines()
                    
                    # 現在のファイルコンテンツを取得
                    if full_path.exists():
                        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                            current_content = f.read().splitlines()
                    else:
                        current_content = []
                    
                    # 差分を計算
                    diff = list(difflib.unified_diff(
                        staged_content, current_content,
                        f'a/{rel_path}', f'b/{rel_path}',
                        lineterm=''
                    ))
                    
                    if diff:
                        diff_output.extend(diff)
                    
                elif full_path.exists():
                    # 未追跡のファイル
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                        current_content = f.read().splitlines()
                    
                    diff = list(difflib.unified_diff(
                        [], current_content,
                        f'/dev/null', f'b/{rel_path}',
                        lineterm=''
                    ))
                    
                    if diff:
                        diff_output.extend(diff)
            
            except Exception as e:
                return False, f"差分の取得中にエラーが発生しました: {str(e)}"
        else:
            # すべての変更ファイルの差分
            status_success, status_info = self.status()
            if not status_success:
                return False, "ステータス情報を取得できませんでした"
            
            # 未ステージングの変更を処理
            for file_path in status_info['unstaged_changes']:
                sub_success, sub_diff = self.diff(file_path)
                if sub_success and sub_diff:
                    diff_output.append(f"--- {file_path} ---")
                    diff_output.extend(sub_diff)
                    diff_output.append("")  # 空行を追加
            
            # 未追跡ファイルを処理
            for file_path in status_info['untracked_files']:
                sub_success, sub_diff = self.diff(file_path)
                if sub_success and sub_diff:
                    diff_output.append(f"--- {file_path} (新規) ---")
                    diff_output.extend(sub_diff)
                    diff_output.append("")  # 空行を追加
        
        return True, diff_output
    
    def reset(self, path=None, hard=False):
        """インデックスまたはワーキングディレクトリをリセットする"""
        if path:
            # 特定のファイルをリセット
            full_path = (self.repo_path / path).resolve()
            try:
                rel_path = str(full_path.relative_to(self.repo_path.resolve()))
                
                # インデックスを取得して更新
                index = self.get_index()
                
                if rel_path in index:
                    if hard:
                        # ハードリセット：ファイルをインデックスバージョンに復元
                        obj_type, file_data = self.get_object(index[rel_path]['hash'], 'blob')
                        with open(full_path, 'wb') as f:
                            f.write(file_data)
                    
                    # インデックスからファイルを削除
                    del index[rel_path]
                    self.update_index(index)
                    
                    return True, f"{rel_path} をリセットしました"
                else:
                    return False, f"{rel_path} はインデックスに存在しません"
            
            except Exception as e:
                return False, f"リセット中にエラーが発生しました: {str(e)}"
        else:
            # 完全リセット
            if hard:
                # ハードリセット：現在のブランチの最後のコミットに戻る
                branch = self.get_current_branch()
                if branch:
                    commit_hash = self.get_branch_commit(branch)
                    if commit_hash:
                        return self._update_working_directory(commit_hash)
                    else:
                        return False, "ブランチにコミットがありません"
                else:
                    return False, "ブランチがありません"
            else:
                # ソフトリセット：インデックスをクリア
                self.update_index({})
                return True, "インデックスをリセットしました"
    
    def merge(self, branch_name):
        """指定されたブランチを現在のブランチにマージする"""
        # 現在のブランチを取得
        current_branch = self.get_current_branch()
        if not current_branch:
            return False, "現在デタッチドHEAD状態です。マージするにはブランチにチェックアウトしてください"
        
        # ターゲットブランチが存在するか確認
        branch_file = self.branches_dir / branch_name
        if not branch_file.exists():
            return False, f"ブランチ '{branch_name}' は存在しません"
        
        # 両方のブランチの最新コミットを取得
        current_commit = self.get_branch_commit(current_branch)
        target_commit = self.get_branch_commit(branch_name)
        
        if current_commit == target_commit:
            return True, "既に最新です。マージする必要はありません"
        
        # 共通の祖先を見つける（簡易版）
        # 本格的な実装では共通祖先を見つけるための複雑なアルゴリズムが必要ですが、
        # 簡易版では単に片方のコミットを採用します（fast-forwardマージのような動作）
        
        # ターゲットコミットをワーキングディレクトリにチェックアウト
        success, message = self._update_working_directory(target_commit)
        if not success:
            return False, f"マージ中にエラーが発生しました: {message}"
        
        # 現在のブランチを更新
        with open(branch_file, 'r') as f:
            target_commit = f.read().strip()
            
        current_branch_file = self.branches_dir / current_branch
        with open(current_branch_file, 'w') as f:
            f.write(target_commit)
            
        return True, f"ブランチ '{branch_name}' を '{current_branch}' にマージしました"
