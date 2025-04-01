import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import queue
from repository import Repository

class GUI:
    """バージョン管理システムのグラフィカルユーザーインターフェース"""
    
    def __init__(self, root):
        """GUIを初期化"""
        self.root = root
        self.root.title("ローカルバージョン管理システム (LVCS)")
        self.root.geometry("900x600")
        
        self.repo = None
        self.repo_path = None
        self.current_branch = None
        
        # スタイル設定
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TButton', font=('Arial', 10))
        self.style.configure('TLabel', font=('Arial', 10), background='#f0f0f0')
        self.style.configure('Header.TLabel', font=('Arial', 12, 'bold'), background='#f0f0f0')
        
        # メインフレーム
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # リポジトリ選択部分
        self.setup_repo_selection()
        
        # コンテンツ部分（初期状態では非表示）
        self.content_frame = ttk.Frame(self.main_frame)
        
        # タスクキュー
        self.task_queue = queue.Queue()
        self.root.after(100, self.process_queue)
    
    def setup_repo_selection(self):
        """リポジトリ選択部分をセットアップ"""
        self.repo_frame = ttk.Frame(self.main_frame, padding="10")
        self.repo_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(self.repo_frame, text="リポジトリを選択または初期化してください", style='Header.TLabel').pack(pady=10)
        
        button_frame = ttk.Frame(self.repo_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="既存のリポジトリを開く", command=self.open_repo).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="新しいリポジトリを初期化", command=self.init_repo).pack(side=tk.LEFT, padx=5)
    
    def setup_content(self):
        """リポジトリが選択または初期化された後のコンテンツをセットアップ"""
        # 古いコンテンツをクリア
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # タブ構造を作成
        self.tab_control = ttk.Notebook(self.content_frame)
        self.tab_control.pack(fill=tk.BOTH, expand=True)
        
        # タブページを作成
        self.status_tab = ttk.Frame(self.tab_control)
        self.commit_tab = ttk.Frame(self.tab_control)
        self.history_tab = ttk.Frame(self.tab_control)
        self.branch_tab = ttk.Frame(self.tab_control)
        
        self.tab_control.add(self.status_tab, text="ステータス")
        self.tab_control.add(self.commit_tab, text="コミット")
        self.tab_control.add(self.history_tab, text="履歴")
        self.tab_control.add(self.branch_tab, text="ブランチ")
        
        # 各タブの内容をセットアップ
        self.setup_status_tab()
        self.setup_commit_tab()
        self.setup_history_tab()
        self.setup_branch_tab()
        
        # リポジトリ情報を表示
        self.repo_info_frame = ttk.Frame(self.content_frame, padding="5")
        self.repo_info_frame.pack(fill=tk.X)
        
        self.repo_path_label = ttk.Label(self.repo_info_frame, text=f"リポジトリ: {self.repo_path}")
        self.repo_path_label.pack(side=tk.LEFT)
        
        self.branch_label = ttk.Label(self.repo_info_frame, text="")
        self.branch_label.pack(side=tk.RIGHT)
        
        # ステータス更新
        self.update_repo_status()
    
    def setup_status_tab(self):
        """ステータスタブの内容をセットアップ"""
        status_frame = ttk.Frame(self.status_tab, padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        # ファイルリストとステータス
        list_frame = ttk.Frame(status_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(list_frame, text="変更されたファイル:", style='Header.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        # ツリービュー
        self.files_tree = ttk.Treeview(list_frame, columns=("status",), height=15)
        self.files_tree.heading("#0", text="ファイル")
        self.files_tree.heading("status", text="ステータス")
        self.files_tree.column("#0", width=300)
        self.files_tree.column("status", width=100)
        self.files_tree.pack(fill=tk.BOTH, expand=True)
        
        # コンテキストメニュー
        self.file_menu = tk.Menu(self.root, tearoff=0)
        self.file_menu.add_command(label="追加", command=self.add_selected_file)
        self.file_menu.add_command(label="差分を表示", command=self.show_selected_diff)
        self.file_menu.add_command(label="リセット", command=self.reset_selected_file)
        
        self.files_tree.bind("<Button-3>", self.show_file_menu)
        self.files_tree.bind("<Double-1>", lambda e: self.show_selected_diff())
        
        # 差分表示エリア
        diff_frame = ttk.Frame(status_frame)
        diff_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        ttk.Label(diff_frame, text="差分:", style='Header.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        self.diff_text = scrolledtext.ScrolledText(diff_frame, wrap=tk.WORD, height=15, width=50)
        self.diff_text.pack(fill=tk.BOTH, expand=True)
        
        # タグを設定（差分の色分け用）
        self.diff_text.tag_configure("add", foreground="green")
        self.diff_text.tag_configure("remove", foreground="red")
        self.diff_text.tag_configure("info", foreground="blue")
        self.diff_text.tag_configure("hunk", foreground="purple")
        
        # ボタンエリア
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="更新", command=self.update_repo_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="すべて追加", command=self.add_all_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="差分を表示", command=self.show_selected_diff).pack(side=tk.LEFT, padx=5)
    
    def setup_commit_tab(self):
        """コミットタブの内容をセットアップ"""
        commit_frame = ttk.Frame(self.commit_tab, padding="10")
        commit_frame.pack(fill=tk.BOTH, expand=True)
        
        # ステージングされたファイル
        ttk.Label(commit_frame, text="コミット予定の変更:", style='Header.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        # リストボックス
        self.staged_listbox = tk.Listbox(commit_frame, height=10)
        self.staged_listbox.pack(fill=tk.X, expand=False)
        
        # コミットメッセージ
        ttk.Label(commit_frame, text="コミットメッセージ:", style='Header.TLabel').pack(anchor=tk.W, pady=(10, 5))
        
        self.commit_message = scrolledtext.ScrolledText(commit_frame, wrap=tk.WORD, height=5)
        self.commit_message.pack(fill=tk.X, expand=False)
        
        # ユーザー情報
        user_frame = ttk.Frame(commit_frame)
        user_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(user_frame, text="ユーザー名:").pack(side=tk.LEFT)
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(user_frame, textvariable=self.username_var, width=20)
        self.username_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(user_frame, text="メールアドレス:").pack(side=tk.LEFT, padx=(10, 0))
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(user_frame, textvariable=self.email_var, width=30)
        self.email_entry.pack(side=tk.LEFT, padx=5)
        
        # ボタン
        button_frame = ttk.Frame(commit_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="ユーザー情報を保存", command=self.save_user_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="コミット", command=self.create_commit).pack(side=tk.RIGHT, padx=5)
        
        # ユーザー設定を読み込み
        self.load_user_config()
    
    def setup_history_tab(self):
        """履歴タブの内容をセットアップ"""
        history_frame = ttk.Frame(self.history_tab, padding="10")
        history_frame.pack(fill=tk.BOTH, expand=True)
        
        # コミット履歴
        ttk.Label(history_frame, text="コミット履歴:", style='Header.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        # ツリービュー
        self.history_tree = ttk.Treeview(history_frame, columns=("author", "date"), height=10)
        self.history_tree.heading("#0", text="コミットハッシュ / メッセージ")
        self.history_tree.heading("author", text="作者")
        self.history_tree.heading("date", text="日付")
        self.history_tree.column("#0", width=400)
        self.history_tree.column("author", width=150)
        self.history_tree.column("date", width=150)
        self.history_tree.pack(fill=tk.BOTH, expand=True)
        
        self.history_tree.bind("<Double-1>", lambda e: self.show_commit_details())
        
        # コミット詳細
        ttk.Label(history_frame, text="コミット詳細:", style='Header.TLabel').pack(anchor=tk.W, pady=(10, 5))
        
        self.commit_details = scrolledtext.ScrolledText(history_frame, wrap=tk.WORD, height=8)
        self.commit_details.pack(fill=tk.BOTH, expand=True)
        
        # ボタン
        button_frame = ttk.Frame(history_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="更新", command=self.update_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="詳細を表示", command=self.show_commit_details).pack(side=tk.LEFT, padx=5)
    
    def setup_branch_tab(self):
        """ブランチタブの内容をセットアップ"""
        branch_frame = ttk.Frame(self.branch_tab, padding="10")
        branch_frame.pack(fill=tk.BOTH, expand=True)
        
        # ブランチリスト
        list_frame = ttk.Frame(branch_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(list_frame, text="ブランチ:", style='Header.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        self.branch_listbox = tk.Listbox(list_frame, height=15)
        self.branch_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 操作フレーム
        action_frame = ttk.Frame(branch_frame)
        action_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # 新規ブランチ作成
        create_frame = ttk.LabelFrame(action_frame, text="新規ブランチ作成", padding="10")
        create_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(create_frame, text="ブランチ名:").pack(anchor=tk.W)
        self.new_branch_var = tk.StringVar()
        ttk.Entry(create_frame, textvariable=self.new_branch_var).pack(fill=tk.X, pady=5)
        ttk.Button(create_frame, text="作成", command=self.create_branch).pack(anchor=tk.E)
        
        # ブランチ操作
        operations_frame = ttk.LabelFrame(action_frame, text="ブランチ操作", padding="10")
        operations_frame.pack(fill=tk.X)
        
        ttk.Button(operations_frame, text="チェックアウト", command=self.checkout_branch).pack(fill=tk.X, pady=2)
        ttk.Button(operations_frame, text="マージ", command=self.merge_branch).pack(fill=tk.X, pady=2)
        ttk.Button(operations_frame, text="削除", command=self.delete_branch).pack(fill=tk.X, pady=2)
        
        # 更新ボタン
        ttk.Button(action_frame, text="ブランチリストを更新", command=self.update_branches).pack(fill=tk.X, pady=10)
    
    def process_queue(self):
        """バックグラウンド処理のキューを処理"""
        try:
            while True:
                task, args, callback = self.task_queue.get_nowait()
                
                try:
                    result = task(*args)
                    if callback:
                        callback(result)
                except Exception as e:
                    messagebox.showerror("エラー", str(e))
                
                self.task_queue.task_done()
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_queue)
    
    def run_background_task(self, task, args=(), callback=None):
        """タスクをバックグラウンドで実行"""
        self.task_queue.put((task, args, callback))
    
    def open_repo(self):
        """既存のリポジトリを開く"""
        repo_path = filedialog.askdirectory(title="リポジトリディレクトリを選択")
        
        if not repo_path:
            return
        
        repo = Repository(repo_path)
        vcs_dir = Path(repo_path) / '.lvcs'
        
        if not vcs_dir.exists() or not vcs_dir.is_dir():
            messagebox.showerror("エラー", "選択されたディレクトリはLVCSリポジトリではありません")
            return
        
        self.repo = repo
        self.repo_path = repo_path
        
        # UIを更新
        self.repo_frame.pack_forget()
        self.setup_content()
    
    def init_repo(self):
        """新しいリポジトリを初期化"""
        repo_path = filedialog.askdirectory(title="新しいリポジトリのディレクトリを選択")
        
        if not repo_path:
            return
        
        repo = Repository(repo_path)
        success, message = repo.init()
        
        if not success:
            messagebox.showerror("エラー", message)
            return
        
        messagebox.showinfo("成功", message)
        
        self.repo = repo
        self.repo_path = repo_path
        
        # UIを更新
        self.repo_frame.pack_forget()
        self.setup_content()
    
    def update_repo_status(self):
        """リポジトリのステータスを更新"""
        if not self.repo:
            return
        
        # ブランチ情報を更新
        self.current_branch = self.repo.get_current_branch() or "（デタッチドHEAD）"
        self.branch_label.config(text=f"ブランチ: {self.current_branch}")
        
        # ファイルリストをクリア
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)
        
        # ステージングされたファイルリストをクリア
        self.staged_listbox.delete(0, tk.END)
        
        # 非同期でステータスを取得
        def get_status():
            success, status_info = self.repo.status()
            return success, status_info
        
        def update_ui(result):
            success, status_info = result
            
            if not success:
                messagebox.showerror("エラー", "リポジトリの状態を取得できませんでした")
                return
            
            # 変更されたファイルを表示
            for file_path in status_info['staged_changes']:
                self.files_tree.insert("", tk.END, text=file_path, values=("ステージング済み",))
                self.staged_listbox.insert(tk.END, file_path)
            
            for file_path in status_info['unstaged_changes']:
                self.files_tree.insert("", tk.END, text=file_path, values=("変更済み",))
            
            for file_path in status_info['untracked_files']:
                self.files_tree.insert("", tk.END, text=file_path, values=("未追跡",))
        
        self.run_background_task(get_status, callback=update_ui)
    
    def update_history(self):
        """コミット履歴を更新"""
        if not self.repo:
            return
        
        # 履歴リストをクリア
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # 非同期でログを取得
        def get_log():
            success, log_entries = self.repo.log(20)
            return success, log_entries
        
        def update_ui(result):
            success, log_entries = result
            
            if not success:
                messagebox.showerror("エラー", "コミット履歴を取得できませんでした")
                return
            
            # コミット履歴を表示
            for entry in log_entries:
                commit_id = entry['hash'][:8]
                message_first_line = entry['message'].split('\n')[0]
                display_text = f"{commit_id}: {message_first_line}"
                
                self.history_tree.insert("", tk.END, text=display_text, 
                                        values=(entry['author'], entry['date']),
                                        tags=(entry['hash'],))
        
        self.run_background_task(get_log, callback=update_ui)
    
    def update_branches(self):
        """ブランチリストを更新"""
        if not self.repo:
            return
        
        # ブランチリストをクリア
        self.branch_listbox.delete(0, tk.END)
        
        # 非同期でブランチを取得
        def get_branches():
            success, branch_info = self.repo.branch()
            return success, branch_info
        
        def update_ui(result):
            success, branch_info = result
            
            if not success:
                messagebox.showerror("エラー", "ブランチ情報を取得できませんでした")
                return
            
            # 現在のブランチを更新
            self.current_branch = branch_info['current']
            self.branch_label.config(text=f"ブランチ: {self.current_branch or '（デタッチドHEAD）'}")
            
            # ブランチリストを表示
            for branch in branch_info['branches']:
                if branch == branch_info['current']:
                    self.branch_listbox.insert(tk.END, f"* {branch}")
                else:
                    self.branch_listbox.insert(tk.END, f"  {branch}")
        
        self.run_background_task(get_branches, callback=update_ui)
    
    def show_file_menu(self, event):
        """ファイルのコンテキストメニューを表示"""
        if self.files_tree.selection():
            self.file_menu.post(event.x_root, event.y_root)
    
    def get_selected_file(self):
        """選択されたファイルのパスを取得"""
        selection = self.files_tree.selection()
        if not selection:
            return None
        
        return self.files_tree.item(selection[0], "text")
    
    def add_selected_file(self):
        """選択されたファイルを追加"""
        file_path = self.get_selected_file()
        if not file_path:
            messagebox.showwarning("警告", "ファイルが選択されていません")
            return
        
        # 非同期で追加
        def add_file(path):
            success, message = self.repo.add(path)
            return success, message
        
        def update_ui(result):
            success, message = result
            
            if success:
                messagebox.showinfo("成功", message)
            else:
                messagebox.showerror("エラー", message)
            
            self.update_repo_status()
        
        self.run_background_task(add_file, (file_path,), update_ui)
    
    def add_all_files(self):
        """すべての変更されたファイルを追加"""
        # 非同期で追加
        def add_all():
            success, message = self.repo.add(".")
            return success, message
        
        def update_ui(result):
            success, message = result
            
            if success:
                messagebox.showinfo("成功", message)
            else:
                messagebox.showerror("エラー", message)
            
            self.update_repo_status()
        
        self.run_background_task(add_all, callback=update_ui)
    
    def show_selected_diff(self):
        """選択されたファイルの差分を表示"""
        file_path = self.get_selected_file()
        if not file_path:
            messagebox.showwarning("警告", "ファイルが選択されていません")
            return
        
        # 非同期で差分を取得
        def get_diff(path):
            success, diff_output = self.repo.diff(path)
            return success, diff_output, path
        
        def update_ui(result):
            success, diff_output, path = result
            
            if not success:
                messagebox.showerror("エラー", f"ファイル {path} の差分を取得できませんでした")
                return
            
            # 差分テキストをクリア
            self.diff_text.delete(1.0, tk.END)
            self.diff_text.insert(tk.END, f"ファイル: {path}\n\n")
            
            # 差分を表示
            for line in diff_output:
                if line.startswith('+'):
                    self.diff_text.insert(tk.END, line + "\n", "add")
                elif line.startswith('-'):
                    self.diff_text.insert(tk.END, line + "\n", "remove")
                elif line.startswith('@@'):
                    self.diff_text.insert(tk.END, line + "\n", "hunk")
                elif line.startswith('---') or line.startswith('+++'):
                    self.diff_text.insert(tk.END, line + "\n", "info")
                else:
                    self.diff_text.insert(tk.END, line + "\n")
        
        self.run_background_task(get_diff, (file_path,), update_ui)
    
    def reset_selected_file(self):
        """選択されたファイルをリセット"""
        file_path = self.get_selected_file()
        if not file_path:
            messagebox.showwarning("警告", "ファイルが選択されていません")
            return
        
        # ハードリセットを確認
        hard_reset = messagebox.askyesno("リセット確認", "変更を完全に破棄しますか？（ハードリセット）")
        
        # 非同期でリセット
        def do_reset(path, hard):
            success, message = self.repo.reset(path, hard)
            return success, message
        
        def update_ui(result):
            success, message = result
            
            if success:
                messagebox.showinfo("成功", message)
            else:
                messagebox.showerror("エラー", message)
            
            self.update_repo_status()
        
        self.run_background_task(do_reset, (file_path, hard_reset), update_ui)
    
    def load_user_config(self):
        """ユーザー設定を読み込む"""
        if not self.repo:
            return
        
        config = self.repo.get_config()
        
        name = config.get('user', {}).get('name', '')
        email = config.get('user', {}).get('email', '')
        
        self.username_var.set(name)
        self.email_var.set(email)
    
    def save_user_config(self):
        """ユーザー設定を保存"""
        if not self.repo:
            return
        
        name = self.username_var.get()
        email = self.email_var.get()
        
        config = self.repo.get_config()
        
        if 'user' not in config:
            config['user'] = {}
        
        config['user']['name'] = name
        config['user']['email'] = email
        
        self.repo.set_config(config)
        messagebox.showinfo("成功", "ユーザー情報を保存しました")
    
    def create_commit(self):
        """コミットを作成"""
        if not self.repo:
            return
        
        message = self.commit_message.get(1.0, tk.END).strip()
        
        if not message:
            messagebox.showwarning("警告", "コミットメッセージを入力してください")
            return
        
        # ユーザー情報を確認
        name = self.username_var.get()
        email = self.email_var.get()
        
        if not name or not email:
            messagebox.showwarning("警告", "ユーザー名とメールアドレスを設定してください")
            return
        
        # 設定を保存
        config = self.repo.get_config()
        if 'user' not in config:
            config['user'] = {}
        
        config['user']['name'] = name
        config['user']['email'] = email
        self.repo.set_config(config)
        
        # 非同期でコミット
        def do_commit(msg):
            success, message = self.repo.commit(msg)
            return success, message
        
        def update_ui(result):
            success, result_message = result
            
            if success:
                messagebox.showinfo("成功", result_message)
                self.commit_message.delete(1.0, tk.END)
            else:
                messagebox.showerror("エラー", result_message)
            
            self.update_repo_status()
            self.update_history()
        
        self.run_background_task(do_commit, (message,), update_ui)
    
    def show_commit_details(self):
        """選択されたコミットの詳細を表示"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "コミットが選択されていません")
            return
        
        item = self.history_tree.item(selection[0])
        commit_hash = item['tags'][0]
        
        # コミット詳細を表示
        self.commit_details.delete(1.0, tk.END)
        self.commit_details.insert(tk.END, f"コミットハッシュ: {commit_hash}\n\n")
        self.commit_details.insert(tk.END, f"コミットメッセージ:\n{item['text'].split(':', 1)[1].strip()}\n\n")
        self.commit_details.insert(tk.END, f"作者: {item['values'][0]}\n")
        self.commit_details.insert(tk.END, f"日付: {item['values'][1]}\n")
    
    def create_branch(self):
        """新しいブランチを作成"""
        if not self.repo:
            return
        
        branch_name = self.new_branch_var.get().strip()
        
        if not branch_name:
            messagebox.showwarning("警告", "ブランチ名を入力してください")
            return
        
        # 非同期でブランチを作成
        def do_create_branch(name):
            success, message = self.repo.branch(name)
            return success, message
        
        def update_ui(result):
            success, message = result
            
            if success:
                messagebox.showinfo("成功", message)
                self.new_branch_var.set("")
            else:
                messagebox.showerror("エラー", message)
            
            self.update_branches()
        
        self.run_background_task(do_create_branch, (branch_name,), update_ui)
    
    def get_selected_branch(self):
        """選択されたブランチ名を取得"""
        selection = self.branch_listbox.curselection()
        if not selection:
            return None
        
        branch_text = self.branch_listbox.get(selection[0])
        # ブランチ名から先頭の「* 」または「  」を削除
        return branch_text[2:]
    
    def checkout_branch(self):
        """選択されたブランチをチェックアウト"""
        branch_name = self.get_selected_branch()
        if not branch_name:
            messagebox.showwarning("警告", "ブランチが選択されていません")
            return
        
        # 非同期でチェックアウト
        def do_checkout(name):
            success, message = self.repo.checkout(name)
            return success, message
        
        def update_ui(result):
            success, message = result
            
            if success:
                messagebox.showinfo("成功", message)
            else:
                messagebox.showerror("エラー", message)
            
            self.update_branches()
            self.update_repo_status()
        
        self.run_background_task(do_checkout, (branch_name,), update_ui)
    
    def merge_branch(self):
        """選択されたブランチをマージ"""
        branch_name = self.get_selected_branch()
        if not branch_name:
            messagebox.showwarning("警告", "ブランチが選択されていません")
            return
        
        # 同じブランチはマージできない
        if branch_name == self.current_branch:
            messagebox.showwarning("警告", "現在のブランチを自身にマージすることはできません")
            return
        
        # マージを確認
        if not messagebox.askyesno("マージ確認", f"ブランチ '{branch_name}' を現在のブランチ '{self.current_branch}' にマージしますか？"):
            return
        
        # 非同期でマージ
        def do_merge(name):
            success, message = self.repo.merge(name)
            return success, message
        
        def update_ui(result):
            success, message = result
            
            if success:
                messagebox.showinfo("成功", message)
            else:
                messagebox.showerror("エラー", message)
            
            self.update_repo_status()
            self.update_history()
        
        self.run_background_task(do_merge, (branch_name,), update_ui)
    
    def delete_branch(self):
        """選択されたブランチを削除"""
        branch_name = self.get_selected_branch()
        if not branch_name:
            messagebox.showwarning("警告", "ブランチが選択されていません")
            return
        
        # 現在のブランチは削除できない
        if branch_name == self.current_branch:
            messagebox.showwarning("警告", "現在チェックアウトされているブランチは削除できません")
            return
        
        # 削除を確認
        if not messagebox.askyesno("削除確認", f"ブランチ '{branch_name}' を削除しますか？"):
            return
        
        # 非同期で削除
        def do_delete(name):
            success, message = self.repo.branch(name, delete=True)
            return success, message
        
        def update_ui(result):
            success, message = result
            
            if success:
                messagebox.showinfo("成功", message)
            else:
                messagebox.showerror("エラー", message)
            
            self.update_branches()
        
        self.run_background_task(do_delete, (branch_name,), update_ui)


def main():
    """メイン関数"""
    root = tk.Tk()
    gui = GUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
