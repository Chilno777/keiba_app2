## Gitの更新の仕方

git add .
git commit -m ""
git push

それぞれの意味
1. git add .

変更したファイルを、コミット対象として追加する

2. git commit -m "変更内容を書く"

変更内容に名前をつけて保存する

3. git push

GitHubに反映する

git commit -m "READMEを追加"
git commit -m "勝率計算ロジックを調整"
git commit -m "指数順表示に変更"
git commit -m "開発ログを更新"
git commit -m "入力画面のUIを改善"

- 状況確認したいとき

これを打つと今の状態が見られます。

git status

たとえば、

何のファイルが変わったか
add されているか
まだ commit していないか

が分かります。

- 履歴を見たいとき
git log --oneline

これで、今までのコミット履歴を簡単に見られます。